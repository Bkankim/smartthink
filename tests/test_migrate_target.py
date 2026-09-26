"""migrate-evolution.py must pick its default target from the resolved vault only.

Runs against a throwaway HOME so the real vault is never read or written.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATE = REPO_ROOT / "scripts" / "migrate-evolution.py"
LEGACY_STATE = "# SmartThink 진화 상태\n\n## 핵심 인사이트\n- legacy prose\n"


class MigrateTargetTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.default_vault = self.home / ".claude" / "smartthink-vault"
        self.default_vault.mkdir(parents=True)
        (self.default_vault / "evolution-state.md").write_text(LEGACY_STATE, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_migrate(self, vault_env: str | None) -> subprocess.CompletedProcess[str]:
        env = {key: value for key, value in os.environ.items() if key != "SMARTTHINK_VAULT"}
        env["HOME"] = str(self.home)
        if vault_env is not None:
            env["SMARTTHINK_VAULT"] = vault_env
        return subprocess.run(
            [sys.executable, str(MIGRATE)], env=env, capture_output=True, text=True, check=False
        )

    def test_env_vault_without_state_does_not_fall_back_to_default(self) -> None:
        empty = self.root / "empty-vault"
        empty.mkdir()

        completed = self.run_migrate(str(empty))

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        self.assertNotIn(str(self.default_vault), completed.stdout)

    def test_default_vault_is_the_target_when_nothing_is_set(self) -> None:
        completed = self.run_migrate(None)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(str(self.default_vault / "evolution-state.md"), completed.stdout)


if __name__ == "__main__":
    unittest.main()
