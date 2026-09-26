"""Behaviour of scripts/resolve-vault.py, exercised through its CLI.

Every case runs against a throwaway HOME so the real vault is never read or written.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOLVER = REPO_ROOT / "scripts" / "resolve-vault.py"
TEMPLATES = REPO_ROOT / "skills" / "smartthink" / ".data"


class ResolveVaultTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.default_vault = self.home / ".claude" / "smartthink-vault"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_resolver_raw(self, *args: str, vault_env: str | None = None) -> subprocess.CompletedProcess[str]:
        env = {key: value for key, value in os.environ.items() if key != "SMARTTHINK_VAULT"}
        env["HOME"] = str(self.home)
        if vault_env is not None:
            env["SMARTTHINK_VAULT"] = vault_env
        return subprocess.run(
            [sys.executable, str(RESOLVER), *args],
            env=env,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def run_resolver(self, *args: str, vault_env: str | None = None) -> dict:
        env = {key: value for key, value in os.environ.items() if key != "SMARTTHINK_VAULT"}
        env["HOME"] = str(self.home)
        if vault_env is not None:
            env["SMARTTHINK_VAULT"] = vault_env
        completed = subprocess.run(
            [sys.executable, str(RESOLVER), *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def write_pointer(self, target: str) -> None:
        self.default_vault.mkdir(parents=True)
        (self.default_vault / "vault-pointer").write_text(target + "\n", encoding="utf-8")

    def test_empty_env_vault_is_used_not_skipped(self) -> None:
        empty = self.root / "empty-vault"
        empty.mkdir()
        # A seeded default vault is the tempting fallback the old prose rule allowed.
        self.default_vault.mkdir(parents=True)
        (self.default_vault / "evolution-state.md").write_text("real insights\n", encoding="utf-8")

        result = self.run_resolver(vault_env=str(empty))

        self.assertEqual(result, {"path": str(empty), "source": "env"})

    def test_missing_env_vault_is_created_by_ensure(self) -> None:
        missing = self.root / "not-yet" / "vault"

        result = self.run_resolver("--ensure", vault_env=str(missing))

        self.assertEqual(result, {"path": str(missing), "source": "env"})
        self.assertTrue((missing / "packs").is_dir())
        self.assertFalse(self.default_vault.exists())

    def test_pointer_is_used_when_env_is_unset(self) -> None:
        notes = self.root / "notes" / "smartthink"
        self.write_pointer(str(notes))

        result = self.run_resolver()

        self.assertEqual(result, {"path": str(notes), "source": "pointer"})

    def test_env_wins_over_pointer(self) -> None:
        self.write_pointer(str(self.root / "notes" / "smartthink"))
        explicit = self.root / "explicit"

        result = self.run_resolver(vault_env=str(explicit))

        self.assertEqual(result, {"path": str(explicit), "source": "env"})

    def test_blank_env_counts_as_unset(self) -> None:
        result = self.run_resolver(vault_env="   ")

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_relative_env_vault_is_used_with_a_warning(self) -> None:
        completed = self.run_resolver_raw(vault_env="rel-vault")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"path": str(self.root / "rel-vault"), "source": "env"})
        self.assertIn("relative", completed.stderr)

    def test_blank_env_warns_that_it_is_ignored(self) -> None:
        completed = self.run_resolver_raw(vault_env="   ")

        self.assertIn("blank", completed.stderr)

    def test_default_when_nothing_is_set(self) -> None:
        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_relative_pointer_is_ignored(self) -> None:
        self.write_pointer("notes/smartthink")

        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_ensure_never_overwrites_existing_state(self) -> None:
        vault = self.root / "vault"
        vault.mkdir()
        (vault / "evolution-state.md").write_text("kept\n", encoding="utf-8")

        self.run_resolver("--ensure", vault_env=str(vault))

        self.assertEqual((vault / "evolution-state.md").read_text(encoding="utf-8"), "kept\n")
        self.assertTrue((vault / "packs").is_dir())

    def test_ensure_seeds_evolution_state_but_not_profile(self) -> None:
        # A missing profile.md is the signal that makes the skill suggest `/st init`.
        vault = self.root / "vault"

        self.run_resolver("--ensure", vault_env=str(vault))

        self.assertEqual(
            (vault / "evolution-state.md").read_bytes(),
            (TEMPLATES / "evolution-state.md").read_bytes(),
        )
        self.assertFalse((vault / "profile.md").exists())

    def run_rule(self, vault_env: str | None = None, config_dir: str | None = None) -> dict:
        # CLAUDE_CONFIG_DIR is controlled explicitly so the runner's own value never leaks in.
        env = {key: value for key, value in os.environ.items() if key not in ("SMARTTHINK_VAULT", "CLAUDE_CONFIG_DIR")}
        env["HOME"] = str(self.home)
        if vault_env is not None:
            env["SMARTTHINK_VAULT"] = vault_env
        if config_dir is not None:
            env["CLAUDE_CONFIG_DIR"] = config_dir
        completed = subprocess.run(
            [sys.executable, str(RESOLVER), "--permission-rule"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_rule_for_default_vault_is_home_relative(self) -> None:
        result = self.run_rule()

        self.assertEqual(result["source"], "default")
        self.assertEqual(result["permission_rule"], "Edit(~/.claude/smartthink-vault/**)")

    def test_rule_for_vault_under_home_uses_tilde(self) -> None:
        result = self.run_rule(vault_env=str(self.home / "notes" / "smartthink"))

        self.assertEqual(result["permission_rule"], "Edit(~/notes/smartthink/**)")

    def test_rule_for_vault_outside_home_uses_double_slash(self) -> None:
        # A single leading / is relative to the settings file and never matches (issue #14).
        outside = self.root / "outside-vault"

        result = self.run_rule(vault_env=str(outside))

        self.assertEqual(result["permission_rule"], f"Edit(/{outside}/**)")
        self.assertTrue(result["permission_rule"].startswith("Edit(//"))

    def test_settings_path_defaults_to_home_claude(self) -> None:
        result = self.run_rule()

        self.assertEqual(result["settings_path"], str(self.home / ".claude" / "settings.json"))

    def test_settings_path_follows_claude_config_dir(self) -> None:
        config = self.root / "isolated-config"

        result = self.run_rule(config_dir=str(config))

        self.assertEqual(result["settings_path"], str(config / "settings.json"))

    def test_blank_claude_config_dir_counts_as_unset(self) -> None:
        result = self.run_rule(config_dir="  ")

        self.assertEqual(result["settings_path"], str(self.home / ".claude" / "settings.json"))

    def test_rule_under_home_claude_is_not_effective(self) -> None:
        # Writes under ~/.claude prompt as sensitive files no matter what the allow rules say.
        self.assertFalse(self.run_rule()["permission_rule_effective"])
        self.assertFalse(self.run_rule(vault_env=str(self.home / ".claude" / "other"))["permission_rule_effective"])

    def test_rule_outside_home_claude_is_effective(self) -> None:
        self.assertTrue(self.run_rule(vault_env=str(self.home / "notes" / "smartthink"))["permission_rule_effective"])
        self.assertTrue(self.run_rule(vault_env=str(self.root / "outside"))["permission_rule_effective"])

    def test_symlink_into_home_claude_is_not_effective(self) -> None:
        # The rule string keeps the user's spelling; only the effectiveness check resolves links.
        self.default_vault.mkdir(parents=True)
        link = self.home / "vault-link"
        link.symlink_to(self.default_vault)

        result = self.run_rule(vault_env=str(link))

        self.assertFalse(result["permission_rule_effective"])
        self.assertEqual(result["permission_rule"], "Edit(~/vault-link/**)")

    def test_config_dir_does_not_change_effectiveness(self) -> None:
        # The sensitive-path check follows HOME, so a vault inside CLAUDE_CONFIG_DIR is fine.
        config = self.root / "isolated-config"

        result = self.run_rule(vault_env=str(config / "vault"), config_dir=str(config))

        self.assertTrue(result["permission_rule_effective"])

    def test_rule_fields_are_opt_in(self) -> None:
        result = self.run_resolver()

        self.assertEqual(set(result), {"path", "source"})


if __name__ == "__main__":
    unittest.main()
