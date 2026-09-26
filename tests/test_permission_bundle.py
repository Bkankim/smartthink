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
        (plugin_root / "skills" / "smartthink").mkdir(parents=True)

    def bundle(self, scripts_dir: Path) -> dict:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env.update(HOME=str(self.home), SMARTTHINK_VAULT=str(self.vault))
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
