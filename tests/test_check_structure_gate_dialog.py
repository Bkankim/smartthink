"""check-structure.py D: the gate asks through AskUserQuestion and no prompt says "press Enter" (#46).

Each case runs the checker of a throwaway copy of the repo, tampered where the case says, and
judges it by the exit code and the named check line. The real checkout is only read.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL = Path("skills") / "smartthink" / "SKILL.md"
LIFECYCLE = Path("skills") / "smartthink" / "references" / "lifecycle.md"
README_KO = Path("README.ko.md")
CHECK_LINE = "D. wiring: gate asks through a dialog, no Enter hints"
GATE_PROCEED_NOW = "   진행        추천대로 진행\n"


class GateDialogCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.copy = Path(self._tmp.name).resolve() / "repo"
        shutil.copytree(
            REPO_ROOT,
            self.copy,
            ignore=shutil.ignore_patterns(".git", ".fablize", "evidence", "__pycache__", ".pytest_cache"),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_checker(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.copy / "scripts" / "check-structure.py")],
            cwd=self.copy,
            capture_output=True,
            text=True,
            check=False,
        )

    def replace(self, rel: Path, old: str, new: str) -> None:
        path = self.copy / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture drifted: {old!r} not in {rel}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assert_check(self, passed: bool) -> str:
        result = self.run_checker()
        mark = "PASS" if passed else "FAIL"
        self.assertIn(f"{mark} {CHECK_LINE}", result.stdout, result.stdout[-3000:])
        return result.stdout

    def test_current_repo_passes(self) -> None:
        self.assert_check(True)

    def test_old_enter_gate_line_fails(self) -> None:
        self.replace(SKILL, GATE_PROCEED_NOW, "   Enter    진행\n")
        self.assertIn("tells the user to press Enter", self.assert_check(False))

    def test_init_enter_accept_hint_fails(self) -> None:
        self.replace(LIFECYCLE, '("응"이면 수락)', "(Enter = 수락)")
        self.assert_check(False)

    def test_readme_enter_hint_fails(self) -> None:
        self.replace(README_KO, "          OFF\n", "          OFF\n   Enter    진행\n")
        self.assert_check(False)

    def test_missing_dialog_section_fails(self) -> None:
        self.replace(SKILL, "### 선택창 게이트", "### 다른 절")
        self.assertIn("no '### 선택창 게이트' section", self.assert_check(False))

    def test_dialog_section_without_cancel_rule_fails(self) -> None:
        self.replace(SKILL, "Esc) 거절하면 **무장하지 마라.**", "Esc) 거절하면 **그대로 진행한다.**")
        self.replace(SKILL, "**무장하지 마라.** 비싼 커밋을", "**진행한다.** 비싼 커밋을")
        self.assert_check(False)


if __name__ == "__main__":
    unittest.main()
