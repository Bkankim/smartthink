"""check-structure.py D: a VAR=value prefix with a quoted value is still a VAR= prefix (issue #37 4).

`_command_word` split the line on whitespace, so `V="my vault" python3 x.py` read as the word
`vault"` and an inline span was never judged a command; the D check passed a line that, typed into
a session, breaks the allow-rule prefix match again (#26/#28). Each case runs the checker of a
throwaway copy of the repo with one line appended to SKILL.md, in an inline span and in a bash
fence, and judges it by the exit code and the named check lines. The real checkout is only read.
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
SINGLE_LINE = "D. wiring: session Bash instructions are single commands"
BUNDLE_LINE = "D. wiring: SKILL.md arming Bash stays inside the rule bundle"
CMD = "python3 {SCRIPTS_DIR}/resolve-vault.py --ensure"

# (label, the line as a doc would write it, command word a shell runs or None when unparseable,
#  judged FAIL on the inline path, judged FAIL on the bash fence path)
CASES = (
    ("double-quoted value with space", f'V="my vault" {CMD}', "python3", True, True),
    ("single-quoted value with space", f"V='my vault' {CMD}", "python3", True, True),
    ("value without space", f"V=myvault {CMD}", "python3", True, True),
    ("several assignments", f'A=1 V="my vault" B=\'x y\' {CMD}', "python3", True, True),
    # final-review: shlex treats # as a comment start by default; a shell keeps it in the value.
    ("value with a hash", f"COLOR=#fff V=foo#bar {CMD}", "python3", True, True),
    # Nothing a shell could run: the old whitespace rule stays, so the inline span is still not
    # judged (no crash is the requirement); the fence path was FAIL before and stays FAIL.
    ("unclosed quote", 'V="my vault python3 x.py', None, False, True),
)


def load_checker():
    spec = importlib.util.spec_from_file_location("check_structure", REPO_ROOT / "scripts" / "check-structure.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_structure"] = module
    spec.loader.exec_module(module)
    return module


class CommandWordTest(unittest.TestCase):
    def test_command_word_skips_quoted_assignments(self) -> None:
        checker = load_checker()
        for label, line, word, _, _ in CASES:
            with self.subTest(case=label):
                if word is not None:
                    self.assertEqual(checker._command_word(line), word)
                else:
                    # unparseable: no exception, and the first non-assignment word as before
                    self.assertEqual(checker._command_word(line), 'vault')

    def test_plain_commands_are_unchanged(self) -> None:
        checker = load_checker()
        for line, word in (
            ("ls -la {VAULT}", "ls"),
            ("python3 {SCRIPTS_DIR}/resolve-vault.py --ensure", "python3"),
            ("grep -n '^## ' {VAULT}/packs/p/pack.md", "grep"),
            ("--flag=value python3 x.py", "--flag=value"),
            ("X=", ""),
            ("", ""),
        ):
            with self.subTest(line=line):
                self.assertEqual(checker._command_word(line), word)


class AssignmentCheckTest(unittest.TestCase):
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

    def run_with(self, addition: str) -> subprocess.CompletedProcess[str]:
        path = self.copy / SKILL
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n" + addition + "\n", encoding="utf-8")
        try:
            return subprocess.run(
                [sys.executable, str(self.copy / "scripts" / "check-structure.py")],
                cwd=self.copy,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            path.write_text(original, encoding="utf-8")

    def row(self, output: str, name: str) -> str:
        rows = [line for line in output.splitlines() if name in line]
        self.assertEqual(len(rows), 1, output)
        return rows[0]

    def test_assignment_matrix(self) -> None:
        for label, line, _, inline_fails, fence_fails in CASES:
            for surface, addition, fails in (
                ("inline", f"`{line}`", inline_fails),
                ("bash fence", f"```bash\n{line}\n```", fence_fails),
            ):
                with self.subTest(case=label, surface=surface):
                    result = self.run_with(addition)
                    self.assertNotIn("Traceback", result.stdout + result.stderr)
                    self.assertIn(" passed, ", result.stdout)
                    single = self.row(result.stdout, SINGLE_LINE)
                    if fails:
                        self.assertEqual(result.returncode, 1, result.stdout)
                        self.assertTrue(single.startswith("FAIL"), result.stdout)
                        self.assertTrue(self.row(result.stdout, BUNDLE_LINE).startswith("FAIL"), result.stdout)
                    else:
                        self.assertEqual(result.returncode, 0, result.stdout)
                        self.assertTrue(single.startswith("PASS"), result.stdout)

    def test_untampered_copy_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.copy / "scripts" / "check-structure.py")],
            cwd=self.copy,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
