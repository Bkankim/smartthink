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

    def test_default_when_nothing_is_set(self) -> None:
        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_relative_pointer_is_ignored(self) -> None:
        self.write_pointer("notes/smartthink")

        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_ensure_seeds_templates_without_overwriting(self) -> None:
        vault = self.root / "vault"
        vault.mkdir()
        (vault / "evolution-state.md").write_text("kept\n", encoding="utf-8")

        self.run_resolver("--ensure", vault_env=str(vault))

        self.assertEqual((vault / "evolution-state.md").read_text(encoding="utf-8"), "kept\n")
        self.assertEqual(
            (vault / "profile.md").read_bytes(),
            (TEMPLATES / "profile.md").read_bytes(),
        )
        self.assertTrue((vault / "packs").is_dir())


if __name__ == "__main__":
    unittest.main()
