"""check-structure.py E: the run's goal is asked at the arming gate, not in init (issue #30).

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
LIFECYCLE = Path("skills") / "smartthink" / "references" / "lifecycle.md"
SKILL = Path("skills") / "smartthink" / "SKILL.md"
CHECK_LINE = "E. schema: run goal asked at the gate, not in init"

INIT_ROW_NOW = "| ② | (결번) 이번 작업의 목표는 init이 묻지 않고 무장 게이트가 받는다(#30) | - |"
INIT_ROW_OLD = "| ② | 현재 목표 | 2. 현재 목표 |"
GATE_QUESTION = "   이번에 무엇을 하려는가? (목표·성공 기준 한 줄)\n"
ARMORER = Path("agents") / "st-armorer.md"
FALLBACK = Path("skills") / "smartthink" / "references" / "armorer-prompt.md"
ANALYSIS = Path("skills") / "smartthink" / "references" / "analysis-method.md"
# code-review of PR #32: the gate asked for the goal but the Input template, the pack spec and the
# armorer's topic-only rule still said A/B/C, so the answer never reached pack section 2.
GOAL_HANDOFF = (
    (SKILL, "주제만 온 경우 게이트에서 답한 목표(목표·성공 기준)가 있으면 그 목표, 없으면 예상 작업 A/B/C}"),
    (SKILL, "주제만 온 경우 게이트에서 답한 목표가 있으면 그 목표의 재진술, 없으면 예상 작업 A/B/C)"),
    (ARMORER, "Interpretation에 게이트에서 답한 목표(목표·성공 기준)가 있으면"),
    (FALLBACK, "Interpretation에 게이트에서 답한 목표(목표·성공 기준)가 있으면"),
    # issue #37 2: Step 0.5 mode B still assumed A/B/C, so the bias briefing and section 2 disagreed.
    (ANALYSIS, "주제만 온 경우 게이트에서 답한 목표(목표·성공 기준)가 있으면 그 목표의 재진술이고"),
)


class GoalAtGateCheckTest(unittest.TestCase):
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

    def line_for(self, output: str) -> str:
        lines = [line for line in output.splitlines() if CHECK_LINE in line]
        self.assertEqual(len(lines), 1, output)
        return lines[0]

    def replace(self, target: Path, old: str, new: str) -> None:
        path = self.copy / target
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, f"{target}: expected one {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def test_untampered_copy_passes(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("PASS"))

    def test_init_asking_the_goal_again_fails(self) -> None:
        self.replace(LIFECYCLE, INIT_ROW_NOW, INIT_ROW_OLD)
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("FAIL"), result.stdout)

    def test_gate_without_the_goal_question_fails(self) -> None:
        self.replace(SKILL, GATE_QUESTION, "")
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("FAIL"), result.stdout)

    def test_goal_answer_dropped_on_the_way_to_the_pack_fails(self) -> None:
        for target, phrase in GOAL_HANDOFF:
            with self.subTest(target=str(target), phrase=phrase[:30]):
                path = self.copy / target
                original = path.read_text(encoding="utf-8")
                self.replace(target, phrase, phrase.replace("게이트에서 답한 목표", "예상 작업"))
                try:
                    result = self.run_checker()
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertTrue(self.line_for(result.stdout).startswith("FAIL"), result.stdout)


if __name__ == "__main__":
    unittest.main()
