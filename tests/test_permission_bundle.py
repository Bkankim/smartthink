"""The allow-rule bundle `st init` installs, printed by resolve-vault.py --permission-rule (issue #26).

An arming run needs, besides the vault Edit rule: a Bash rule for each script the session runs
(resolve-vault.py in the main session, assemble-pack.py in the armorer) and a Read rule for the
skill directory, which sits outside the working directory of a plugin user. Bash rules match the
command text, so each rule must start with exactly what the docs make a session type. Every case
runs a copy of the scripts under a throwaway root with a fake HOME; the real home is never touched.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ("resolve-vault.py", "assemble-pack.py")
CONTROLLED = ("SMARTTHINK_VAULT", "CLAUDE_CONFIG_DIR", "XDG_DATA_HOME", "XDG_CONFIG_HOME")


class PermissionBundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.vault = self.root / "vault"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def install_copy(self, plugin_root: Path) -> None:
        # A checkout-shaped copy: scripts/ next to skills/smartthink/, as the plugin ships it.
        (plugin_root / "scripts").mkdir(parents=True)
        for name in SCRIPTS:
            (plugin_root / "scripts" / name).write_bytes((REPO_ROOT / "scripts" / name).read_bytes())
        (plugin_root / "skills" / "smartthink" / ".data").mkdir(parents=True)
        seed = REPO_ROOT / "skills" / "smartthink" / ".data" / "evolution-state.md"
        (plugin_root / "skills" / "smartthink" / ".data" / "evolution-state.md").write_bytes(seed.read_bytes())

    def bundle(self, scripts_dir: Path, **extra: str) -> dict:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env.update(HOME=str(self.home), SMARTTHINK_VAULT=str(self.vault), **extra)
        completed = subprocess.run(
            [sys.executable, str(scripts_dir / "resolve-vault.py"), "--permission-rule"],
            env=env,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def run_resolver(self, scripts_dir: Path, *args: str, **extra: str) -> dict:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env.update(HOME=str(self.home), SMARTTHINK_VAULT=str(self.vault), **extra)
        completed = subprocess.run(
            [sys.executable, str(scripts_dir / "resolve-vault.py"), *args],
            env=env, cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_bash_rules_effective_is_reported_by_ensure_and_permission_rule(self) -> None:
        # final-review 20260927-073516 #1: the session decides whether to quote {SCRIPTS_DIR} from
        # this field, and arming only runs --ensure, so both outputs carry it with the reason.
        self.install_copy(self.root / "safe")
        self.install_copy(self.root / "with space")
        for option in ("--ensure", "--permission-rule"):
            with self.subTest(option=option):
                safe = self.run_resolver(self.root / "safe" / "scripts", option)
                self.assertIs(safe["bash_rules_effective"], True)
                self.assertIsNone(safe["bash_rules_reason"])
                spaced = self.run_resolver(self.root / "with space" / "scripts", option)
                self.assertIs(spaced["bash_rules_effective"], False)
                self.assertEqual(spaced["bash_rules_reason"], "special-characters")

    def test_bash_rules_use_the_invoked_scripts_dir_under_a_symlinked_ancestor(self) -> None:
        # Same reason as assemble-pack (final-review #7 of #21): the session types
        # python3 {SCRIPTS_DIR}/<script> with the {SCRIPTS_DIR} string it was given, so resolving a
        # linked ancestor (/tmp -> /private/tmp) would give a rule nobody's command starts with.
        self.install_copy(self.root / "real")
        (self.root / "link").symlink_to(self.root / "real")
        invoked = self.root / "link" / "scripts"

        result = self.bundle(invoked)

        self.assertEqual(
            result["command_prefixes"],
            {
                "resolve-vault": f"python3 {invoked}/resolve-vault.py",
                "assemble-pack": f"python3 {invoked}/assemble-pack.py",
            },
        )
        self.assertEqual(
            result["bash_rules"],
            [f"Bash(python3 {invoked}/resolve-vault.py *)", f"Bash(python3 {invoked}/assemble-pack.py *)"],
        )
        self.assertIs(result["bash_rules_effective"], True)

    def test_read_rule_covers_the_skill_dir_next_to_the_invoked_scripts(self) -> None:
        # T16-before: every Read of references/ outside the working directory prompted, while vault
        # Reads did not (the Edit rule covers them). {SKILL_DIR} is {SCRIPTS_DIR}/../skills/smartthink.
        cached = self.home / ".claude" / "plugins" / "cache" / "m" / "smartthink" / "1.0"
        self.install_copy(cached)
        self.assertEqual(
            self.bundle(cached / "scripts")["read_rule"],
            "Read(~/.claude/plugins/cache/m/smartthink/1.0/skills/smartthink/**)",
        )

        self.install_copy(self.root / "real")
        (self.root / "link").symlink_to(self.root / "real")
        result = self.bundle(self.root / "link" / "scripts")
        self.assertEqual(result["read_rule"], f"Read(/{self.root}/link/skills/smartthink/**)")
        self.assertIs(result["read_rule_effective"], True)

    def test_read_rules_add_the_install_sh_link_the_session_reads_through(self) -> None:
        # final-review 20260927-064432 (c): install.sh links ~/.claude/skills/smartthink to the
        # checkout, the session Reads through that link, and a rule naming only the checkout path
        # still prompted (T16-after, install.sh row). The link path must be in the bundle too.
        self.install_copy(self.root / "checkout")
        skill = self.root / "checkout" / "skills" / "smartthink"
        user_skills = self.home / ".claude" / "skills"
        user_skills.mkdir(parents=True)
        (user_skills / "smartthink").symlink_to(skill)
        config = self.root / "cfg"
        (config / "skills").mkdir(parents=True)
        (config / "skills" / "smartthink").symlink_to(skill)
        unrelated = self.root / "other-skill"
        unrelated.mkdir()
        (user_skills / "other").symlink_to(unrelated)

        result = self.bundle(self.root / "checkout" / "scripts", CLAUDE_CONFIG_DIR=str(config))

        self.assertEqual(
            result["read_rules"],
            [
                f"Read(/{skill}/**)",
                "Read(~/.claude/skills/smartthink/**)",
                f"Read(/{config}/skills/smartthink/**)",
            ],
        )

    def test_read_rule_effective_covers_the_link_paths(self) -> None:
        # final-review 20260927-073516 #3: a clean checkout linked from a config dir whose path has
        # rule syntax gives a read rule that never matches, so the whole Read bundle is not effective.
        self.install_copy(self.root / "checkout")
        skill = self.root / "checkout" / "skills" / "smartthink"
        config = self.root / "claude[work]"
        (config / "skills").mkdir(parents=True)
        (config / "skills" / "smartthink").symlink_to(skill)

        clean = self.bundle(self.root / "checkout" / "scripts")
        linked = self.bundle(self.root / "checkout" / "scripts", CLAUDE_CONFIG_DIR=str(config))

        self.assertIs(clean["read_rule_effective"], True)
        self.assertEqual(len(linked["read_rules"]), 2)
        self.assertIs(linked["read_rule_effective"], False)

    def test_read_rules_for_a_plugin_install_hold_only_the_skill_dir(self) -> None:
        self.install_copy(self.root / "plugin")
        result = self.bundle(self.root / "plugin" / "scripts")
        self.assertEqual(result["read_rules"], [result["read_rule"]])

    def test_vault_writable_replaces_the_status_test_w(self) -> None:
        # final-review 20260927-072558 (a)1: status judged the vault with Bash `test -w {VAULT}`,
        # outside the working directory and outside the rule bundle. The resolver reports it, judged
        # on the nearest existing ancestor as install.sh does (a vault not created yet is writable
        # when its parent is).
        self.install_copy(self.root / "plugin")
        scripts = self.root / "plugin" / "scripts"
        parent = self.root / "notes"
        parent.mkdir()

        self.vault = parent / "smartthink"
        self.assertIs(self.bundle(scripts)["vault_writable"], True)
        self.vault.mkdir()
        self.assertIs(self.bundle(scripts)["vault_writable"], True)

        locked = self.root / "locked"
        locked.mkdir()
        self.vault = locked / "smartthink"
        locked.chmod(0o555)
        try:
            self.assertIs(self.bundle(scripts)["vault_writable"], False)
        finally:
            locked.chmod(0o755)

        # A relative SMARTTHINK_VAULT (used with a warning) walks up to "" and must stop at the cwd.
        self.vault = Path("rel") / "vault"
        self.assertIs(self.bundle(scripts)["vault_writable"], True)

    def test_ensure_reports_vault_writable_for_the_root_and_packs(self) -> None:
        # final-review 20260927-073516 #2: --ensure exits 0 on a read-only vault, so the arming
        # gate reads this field. The armorer writes under packs/, so a read-only packs/ is not
        # writable either.
        self.install_copy(self.root / "plugin")
        scripts = self.root / "plugin" / "scripts"
        self.vault = self.root / "vault"
        self.assertIs(self.run_resolver(scripts, "--ensure")["vault_writable"], True)
        packs = self.vault / "packs"
        packs.chmod(0o555)
        try:
            for option in ("--ensure", "--permission-rule"):
                with self.subTest(option=option):
                    self.assertIs(self.run_resolver(scripts, option)["vault_writable"], False)
        finally:
            packs.chmod(0o755)
        self.vault.chmod(0o555)
        try:
            self.assertIs(self.run_resolver(scripts, "--ensure")["vault_writable"], False)
        finally:
            self.vault.chmod(0o755)

    def test_module_sizes_replace_the_wc_fallback(self) -> None:
        # final-review 20260927-064432 (a)1: without index.json the gate measured module sizes with
        # Bash `wc -c`, a command outside the rule bundle. The resolver, already allowed, reports them.
        self.install_copy(self.root / "plugin")
        references = self.root / "plugin" / "skills" / "smartthink" / "references"
        references.mkdir()
        (references / "core-engines.md").write_bytes(b"x" * 22)
        (references / "meta-cognition.md").write_bytes(b"y" * 100)
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env.update(HOME=str(self.home), SMARTTHINK_VAULT=str(self.vault))
        script = self.root / "plugin" / "scripts" / "resolve-vault.py"

        def run(*names: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(script), "--module-sizes", *names],
                env=env, cwd=self.root, capture_output=True, text=True, check=False,
            )

        result = run("core-engines.md", "meta-cognition.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"modules": {
                "core-engines.md": {"bytes": 22, "est_tokens": 10},
                "meta-cognition.md": {"bytes": 100, "est_tokens": 45},
            }},
        )
        # final-review 20260927-073516 #5: one bad name must not cost the gate every estimate. It
        # comes back as null with a warning, the others are measured, and the exit code stays 0.
        # A path is never followed outside references/.
        for bad in ("../scripts/resolve-vault.py", "missing.md"):
            with self.subTest(name=bad):
                mixed = run("core-engines.md", bad)
                self.assertEqual(mixed.returncode, 0, mixed.stderr)
                self.assertEqual(
                    json.loads(mixed.stdout),
                    {"modules": {"core-engines.md": {"bytes": 22, "est_tokens": 10}, bad: None}},
                )
                self.assertIn(bad, mixed.stderr)

    def test_every_documented_script_call_starts_with_its_rule_prefix(self) -> None:
        # The rule only helps if the command a doc shows, with {SCRIPTS_DIR} filled in, starts with
        # the prefix. `python3 "{SCRIPTS_DIR}/resolve-vault.py"` (quoted) never does.
        self.install_copy(self.root / "real")
        (self.root / "link").symlink_to(self.root / "real")
        invoked = self.root / "link" / "scripts"
        prefixes = self.bundle(invoked)["command_prefixes"]
        docs = (
            Path("skills") / "smartthink" / "SKILL.md",
            Path("skills") / "smartthink" / "references" / "lifecycle.md",
            Path("agents") / "st-armorer.md",
            Path("skills") / "smartthink" / "references" / "armorer-prompt.md",
        )
        calls = 0
        for doc in docs:
            text = (REPO_ROOT / doc).read_text(encoding="utf-8")
            for match in re.finditer(r"python3 [^`\n]*?(resolve-vault|assemble-pack)\.py[^`\n]*", text):
                if "{SCRIPTS_DIR}" not in match.group(0):
                    continue
                calls += 1
                command = match.group(0).replace("{SCRIPTS_DIR}", str(invoked))
                with self.subTest(doc=str(doc), call=match.group(0)):
                    self.assertTrue(command.startswith(prefixes[match.group(1)]), command)
        self.assertGreater(calls, 0)


if __name__ == "__main__":
    unittest.main()
