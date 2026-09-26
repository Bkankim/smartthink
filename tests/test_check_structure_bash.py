"""check-structure.py D: Bash the docs tell a session to run is one simple command (issue #26).

Claude Code matches a Bash allow rule against each command of a compound line, and a read-only
command outside the working directory prompts whatever the rules say, so a `;`/`&&`/`||`/pipe line
in SKILL.md, lifecycle.md or the armorer definition turns into a prompt on every arming run.
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
ARMORER = Path("agents") / "st-armorer.md"
FALLBACK = Path("skills") / "smartthink" / "references" / "armorer-prompt.md"
CHECK_LINE = "D. wiring: session Bash instructions are single commands"
BUNDLE_LINE = "D. wiring: SKILL.md arming Bash stays inside the rule bundle"

# The shapes observed in T9 and T15 (tests/evidence), written the way a doc would show them.
COMPOUND_BLOCKS = (
    '```bash\nls -la "{VAULT}"; cat "{VAULT}/evolution-state.md"\n```',
    "```bash\nreadlink {SKILL_DIR} && ls {SCRIPTS_DIR}\n```",
    '```bash\ncd "{VAULT}" && ls packs\n```',
    "```bash\ntest -w {VAULT} || echo read-only\n```",
    "```bash\ncat {SETTINGS} | python3 -m json.tool\n```",
)
COMPOUND_INLINE = "확인은 `ls {VAULT}/packs; grep -n '^## ' {VAULT}/packs/p/pack.md`로 한다.\n"


class SessionBashCheckTest(unittest.TestCase):
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

    def assert_fails_with(self, target: Path, addition: str) -> None:
        path = self.copy / target
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n" + addition + "\n", encoding="utf-8")
        try:
            result = self.run_checker()
        finally:
            path.write_text(original, encoding="utf-8")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("FAIL"), result.stdout)
        self.assertIn(str(target), result.stdout)

    def test_untampered_copy_passes(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("PASS"))

    def test_compound_code_block_in_skill_md_fails(self) -> None:
        for block in COMPOUND_BLOCKS:
            with self.subTest(block=block):
                self.assert_fails_with(SKILL, block)

    def test_compound_inline_command_fails_in_every_session_doc(self) -> None:
        for target in (SKILL, LIFECYCLE, ARMORER, FALLBACK):
            with self.subTest(target=str(target)):
                self.assert_fails_with(target, COMPOUND_INLINE)

    def test_skill_md_bash_outside_the_rule_bundle_fails(self) -> None:
        # final-review 20260927-064432 (a)1: the index.json fallback told the main session to run
        # `wc -c`, a single command but one no init rule covers, so it prompted on every such run.
        tampered = (
            "- **index.json이 없으면**: 선택 모듈 파일의 크기를 직접 재고(`wc -c`) 같은 계수로 근사하라.",
            "vault가 있는지 `ls -la {VAULT}`로 확인한다.",
            "`python3 {SCRIPTS_DIR}/migrate-evolution.py --write`를 실행한다.",
        )
        path = self.copy / SKILL
        original = path.read_text(encoding="utf-8")
        for line in tampered:
            with self.subTest(line=line):
                path.write_text(original + "\n" + line + "\n", encoding="utf-8")
                try:
                    result = self.run_checker()
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertEqual(result.returncode, 1, result.stdout)
                lines = [row for row in result.stdout.splitlines() if BUNDLE_LINE in row]
                self.assertEqual(len(lines), 1, result.stdout)
                self.assertTrue(lines[0].startswith("FAIL"), result.stdout)

    def test_prohibited_or_bundled_commands_in_skill_md_pass(self) -> None:
        path = self.copy / SKILL
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n`wc -c` 같은 Bash로 재지 마라. `python3 {SCRIPTS_DIR}/resolve-vault.py --module-sizes a.md`를 쓴다.\n",
            encoding="utf-8",
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue([row for row in result.stdout.splitlines() if BUNDLE_LINE in row][0].startswith("PASS"))

    def test_operators_inside_quotes_or_prose_pass(self) -> None:
        # A quoted ; or | is an argument, and a bare `&&` span names the operator in prose.
        path = self.copy / SKILL
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n`grep -n '^## [0-9]\\. |x' pack.md`, `&&`, `;` 같은 연산자를 섞지 마라.\n",
            encoding="utf-8",
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("PASS"))


if __name__ == "__main__":
    unittest.main()
