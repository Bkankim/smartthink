"""check-structure.py D: spawn and alias names are picked from the session list first.

A non-plugin install (install.sh symlinks) registers only bare names, so trying the
`smartthink:` name first costs one failed tool call on every invocation. The list-first
rule removes that call: the harness already shows which name is registered.

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
ALIAS = Path("commands") / "st.md"
CHECK_LINE = "D. wiring: plugin namespace on spawns and the /st alias"

# The anchor each file's list-first rule line carries.
SKILL_ANCHOR = "세션 에이전트 목록"
ALIAS_ANCHOR = "available skills list"


class ListFirstNameResolutionTest(unittest.TestCase):
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

    def line_for(self, output: str, name: str) -> str:
        lines = [line for line in output.splitlines() if name in line]
        self.assertEqual(len(lines), 1, output)
        return lines[0]

    def drop_anchor_lines(self, target: Path, anchor: str) -> None:
        path = self.copy / target
        text = path.read_text(encoding="utf-8")
        kept = [line for line in text.splitlines(keepends=True) if anchor not in line]
        self.assertEqual(len(kept), len(text.splitlines(keepends=True)) - 1, f"{target} anchor")
        path.write_text("".join(kept), encoding="utf-8")

    def test_untampered_copy_passes(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout, CHECK_LINE).startswith("PASS"))

    def test_skill_without_list_first_rule_fails(self) -> None:
        self.drop_anchor_lines(SKILL, SKILL_ANCHOR)
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(self.line_for(result.stdout, CHECK_LINE).startswith("FAIL"))
        self.assertIn(str(SKILL), result.stdout)

    def test_alias_without_list_first_rule_fails(self) -> None:
        self.drop_anchor_lines(ALIAS, ALIAS_ANCHOR)
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(self.line_for(result.stdout, CHECK_LINE).startswith("FAIL"))
        self.assertIn(str(ALIAS), result.stdout)


if __name__ == "__main__":
    unittest.main()
