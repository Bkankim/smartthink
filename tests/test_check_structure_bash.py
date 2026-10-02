"""check-structure.py D: Bash the docs tell a session to run is one simple command (issue #26).

Claude Code matches a Bash allow rule against each command of a compound line, and a read-only
command outside the working directory prompts whatever the rules say, so a `;`/`&&`/`||`/pipe line
in SKILL.md, lifecycle.md or the armorer definition turns into a prompt on every arming run.
Each case runs the checker of a throwaway copy of the repo, tampered where the case says, and
judges it by the exit code and the named check line. The real checkout is only read.
"""
from __future__ import annotations

import importlib.util
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
LIFECYCLE_LINE = "D. wiring: lifecycle.md Bash is the bundle or a recorded exception"
SINGLE_CMD = "python3 {SCRIPTS_DIR}/resolve-vault.py --ensure"

# The shapes observed in T9 and T15 (tests/evidence), written the way a doc would show them.
COMPOUND_BLOCKS = (
    '```bash\nls -la "{VAULT}"; cat "{VAULT}/evolution-state.md"\n```',
    "```bash\nreadlink {SKILL_DIR} && ls {SCRIPTS_DIR}\n```",
    '```bash\ncd "{VAULT}" && ls packs\n```',
    "```bash\ntest -w {VAULT} || echo read-only\n```",
    "```bash\ncat {SETTINGS} | python3 -m json.tool\n```",
)
COMPOUND_INLINE = "확인은 `ls {VAULT}/packs; grep -n '^## ' {VAULT}/packs/p/pack.md`로 한다.\n"
# Issue #28 1: single-looking lines the shell still splits or rewrites, so a prefix rule misses them.
RULE_BREAKING_BLOCKS = (
    "```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --ensure > /tmp/v.json\n```",
    "```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --ensure >> /tmp/v.json\n```",
    "```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --ensure 2>/dev/null\n```",
    "```bash\ncat <<EOF\n```",
    "```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --vault $(pwd)\n```",
    '```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --vault "$(pwd)"\n```',
    "```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --vault `pwd`\n```",
    "```bash\npython3 {SCRIPTS_DIR}/resolve-vault.py --ensure &\n```",
    "`X=y python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`를 실행한다.",
)
# Issue #28 2: commands whose first word the old word list did not know, or a one-word fenced line.
UNLISTED_BLOCKS = (
    "```bash\nbash -c 'ls {VAULT}'\n```",
    "`jq . {VAULT}/manifest.json`으로 본다.",
    "`{SCRIPTS_DIR}/resolve-vault.py --ensure`를 실행한다.",
    "```bash\npwd\n```",
)


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

    def test_redirection_substitution_background_and_assignment_fail(self) -> None:
        for block in RULE_BREAKING_BLOCKS:
            with self.subTest(block=block):
                self.assert_fails_with(SKILL, block)
        with self.subTest(target=str(ARMORER)):
            self.assert_fails_with(ARMORER, "`python3 {SCRIPTS_DIR}/assemble-pack.py --pack-dir x > /tmp/x`로 조립한다.")

    def test_unlisted_first_words_fail_the_bundle_checks(self) -> None:
        for target, row in ((SKILL, BUNDLE_LINE), (LIFECYCLE, LIFECYCLE_LINE)):
            for block in UNLISTED_BLOCKS:
                with self.subTest(target=str(target), block=block):
                    path = self.copy / target
                    original = path.read_text(encoding="utf-8")
                    path.write_text(original + "\n" + block + "\n", encoding="utf-8")
                    try:
                        result = self.run_checker()
                    finally:
                        path.write_text(original, encoding="utf-8")
                    self.assertEqual(result.returncode, 1, result.stdout)
                    rows = [line for line in result.stdout.splitlines() if row in line]
                    self.assertEqual(len(rows), 1, result.stdout)
                    self.assertTrue(rows[0].startswith("FAIL"), result.stdout)

    def test_prohibition_exempts_only_its_own_sentence(self) -> None:
        # Issue #28 3: docs put a whole paragraph on one line, so a forbidding word anywhere on it
        # used to exempt every command on it, including one the next sentence tells the session to run.
        cases = (
            (SKILL, BUNDLE_LINE, "`wc -c`로 재지 마라. 대신 `ls -la {VAULT}/packs`로 확인한다."),
            (SKILL, BUNDLE_LINE, "`ls -la {VAULT}/packs`로 확인한다. `wc -c`로 재지 마라."),
            (LIFECYCLE, LIFECYCLE_LINE, "`wc -c`는 쓰지 않는다. 최근 팩은 `ls -la {VAULT}/packs`로 본다."),
            (LIFECYCLE, LIFECYCLE_LINE, "| 팩 | `ls -la {VAULT}/packs`로 본다 | `wc -c`로 재지 마라 |"),
        )
        for target, row, line in cases:
            with self.subTest(line=line):
                path = self.copy / target
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "\n" + line + "\n", encoding="utf-8")
                try:
                    result = self.run_checker()
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertEqual(result.returncode, 1, result.stdout)
                rows = [out for out in result.stdout.splitlines() if row in out]
                self.assertEqual(len(rows), 1, result.stdout)
                self.assertTrue(rows[0].startswith("FAIL"), result.stdout)
                self.assertIn("ls -la", rows[0] + result.stdout)
                self.assertNotIn("`wc -c`", result.stdout)

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

    def test_lifecycle_bash_outside_the_inventory_fails(self) -> None:
        # final-review 20260927-072558: status judged the vault with `test -w {VAULT}`, a Bash
        # outside the rule bundle that no review had listed. lifecycle.md may name only the bundle
        # and the exceptions recorded in tests/evidence/26-bash-inventory.md.
        path = self.copy / LIFECYCLE
        original = path.read_text(encoding="utf-8")
        for line in ("| vault 쓰기 가능 | `test -w {VAULT}`로 판정 |", "`ls -la {VAULT}/packs`로 최근 팩을 본다."):
            with self.subTest(line=line):
                path.write_text(original + "\n" + line + "\n", encoding="utf-8")
                try:
                    result = self.run_checker()
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertEqual(result.returncode, 1, result.stdout)
                rows = [row for row in result.stdout.splitlines() if LIFECYCLE_LINE in row]
                self.assertEqual(len(rows), 1, result.stdout)
                self.assertTrue(rows[0].startswith("FAIL"), result.stdout)

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

    def judge(self, addition: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        """Run the checker with one tampered line and return the result plus the two judged rows."""
        path = self.copy / SKILL
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n" + addition + "\n", encoding="utf-8")
        try:
            result = self.run_checker()
        finally:
            path.write_text(original, encoding="utf-8")
        rows = []
        for name in (CHECK_LINE, BUNDLE_LINE):
            found = [line for line in result.stdout.splitlines() if name in line]
            self.assertEqual(len(found), 1, result.stdout)
            rows.append(found[0])
        return result, rows

    def test_assignment_prefix_matrix_in_inline_and_fence(self) -> None:
        # Issue #43 1 and 2: both judges read a leading VAR=value the same way. C2: an unclosed quote
        # after a good assignment used to send _command_word back to whitespace words, so the span was
        # no command. C3: a quoted `'V=1'` word was an assignment to _command_word only.
        # (label, line as a doc writes it, inline FAIL, bash fence FAIL). The fence column keeps every
        # verdict that was already FAIL (#37); `'V=1'` was a miss on both surfaces and closes with C3.
        matrix = (
            ("C2 unclosed quote after an assignment", f'V="my vault" W=it\'s {SINGLE_CMD}', True, True),
            ("C3 quoted assignment word", f"'V=1' {SINGLE_CMD}", True, True),
            ("quoted value with a space (#37)", f'V="my vault" {SINGLE_CMD}', True, True),
            ("no assignment", SINGLE_CMD, False, False),
            ("fully unparseable", 'V="my vault python3 x.py', False, True),
        )
        for label, line, inline_fails, fence_fails in matrix:
            for surface, addition, fails in (
                ("inline", f"`{line}`", inline_fails),
                ("bash fence", f"```bash\n{line}\n```", fence_fails),
            ):
                with self.subTest(case=label, surface=surface):
                    result, rows = self.judge(addition)
                    self.assertNotIn("Traceback", result.stdout + result.stderr)
                    self.assertIn(" passed, ", result.stdout)
                    for row in rows:
                        self.assertTrue(row.startswith("FAIL" if fails else "PASS"), f"want {'FAIL' if fails else 'PASS'}: {row}")
                    self.assertEqual(result.returncode, 1 if fails else 0, result.stdout)

    def test_assignment_judges_do_not_crash_on_unparseable_text(self) -> None:
        spec = importlib.util.spec_from_file_location("check_structure_43", REPO_ROOT / "scripts" / "check-structure.py")
        checker = importlib.util.module_from_spec(spec)
        sys.modules["check_structure_43"] = checker
        spec.loader.exec_module(checker)
        for line in ('V="a', "V='a", "V=a\\", 'V="a" W=\'b', "'V=1", '"', "'", "\\", "X=", "", "   ", 'A="x" B="y'):
            with self.subTest(line=line):
                self.assertIsInstance(checker._command_word(line), str)
                self.assertIsInstance(checker._is_command(line), bool)
                operator = checker._compound_operator(line)
                self.assertTrue(operator is None or isinstance(operator, str))

    def test_operators_inside_quotes_or_prose_pass(self) -> None:
        # A quoted ; or | is an argument, and a bare `&&` span names the operator in prose.
        path = self.copy / SKILL
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n`grep -n '^## [0-9]\\. |x' pack.md`, `&&`, `;` 같은 연산자를 섞지 마라.\n"
            + "`grep -n '> $(x) & <<' pack.md`처럼 작은따옴표 안의 연산자도 확인용 Bash로 쓰지 마라.\n",
            encoding="utf-8",
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout).startswith("PASS"))


if __name__ == "__main__":
    unittest.main()
