"""check-structure.py must fail when the pre-#20 default vault path creeps back into the conventions.

Each case runs the gate against a throwaway copy of the repository, never the checkout itself.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_LABEL = "E. vault: no pre-#20 default vault path in the conventions"
OLD_PATH = "~/.claude/" + "smartthink-vault"


class OldVaultPathCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.copy = Path(self._tmp.name) / "repo"
        shutil.copytree(
            REPO_ROOT,
            self.copy,
            ignore=shutil.ignore_patterns(".git", ".fablize", "__pycache__", ".pytest_cache"),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_gate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.copy / "scripts" / "check-structure.py")],
            cwd=self.copy,
            capture_output=True,
            text=True,
            check=False,
        )

    def append(self, relative: str, line: str) -> None:
        path = self.copy / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def test_clean_copy_passes(self) -> None:
        completed = self.run_gate()

        self.assertIn(f"PASS {CHECK_LABEL}", completed.stdout)
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_old_path_in_an_installer_fails(self) -> None:
        self.append("install.sh", f'# vault: {OLD_PATH}')

        completed = self.run_gate()

        self.assertIn(f"FAIL {CHECK_LABEL}", completed.stdout)
        self.assertIn("install.sh", completed.stdout)
        self.assertEqual(completed.returncode, 1)

    def test_equivalent_spellings_fail(self) -> None:
        self.append("skills/smartthink/references/lifecycle.md", "기본값 `$HOME/.claude/smartthink-vault`")
        self.append("scripts/migrate-evolution.py", 'OLD = Path.home() / ".claude" / "smartthink-vault"')

        completed = self.run_gate()

        self.assertIn(f"FAIL {CHECK_LABEL}", completed.stdout)
        self.assertIn("lifecycle.md", completed.stdout)
        self.assertIn("migrate-evolution.py", completed.stdout)
        self.assertEqual(completed.returncode, 1)

    def test_history_and_evidence_may_mention_it(self) -> None:
        self.append("CHANGELOG.md", f"- the default vault moved away from {OLD_PATH}")
        self.append("tests/evidence/old-run.txt", f"vault={OLD_PATH}")

        completed = self.run_gate()

        self.assertIn(f"PASS {CHECK_LABEL}", completed.stdout)


if __name__ == "__main__":
    unittest.main()
