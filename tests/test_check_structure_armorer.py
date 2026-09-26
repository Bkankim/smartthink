"""check-structure.py D: the armorer assembles section 5 with assemble-pack.py (issue #21).

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
ARMORER = Path("agents") / "st-armorer.md"
FALLBACK = Path("skills") / "smartthink" / "references" / "armorer-prompt.md"
ASSEMBLER = Path("scripts") / "assemble-pack.py"
CHECK_LINE = "D. wiring: st-armorer assembles section 5 with assemble-pack.py"
MARKER_LINE = "D. wiring: section 5 module marker forms match the SSOT"

# The pre-#21 instruction, verbatim: a printf redirection straight into the pack file.
PRINTF_APPEND = """
```bash
printf '<!-- MODULE-BEGIN: %s sha256=%s -->\\n' "$NAME" "$HASH" >> "$PACK"
cat "$SRC" >> "$PACK"
```
"""


class ArmorerAssemblyCheckTest(unittest.TestCase):
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

    def test_untampered_copy_passes(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.line_for(result.stdout, CHECK_LINE).startswith("PASS"))
        self.assertTrue(self.line_for(result.stdout, MARKER_LINE).startswith("PASS"))

    def test_printf_append_into_the_pack_fails(self) -> None:
        for target in (ARMORER, FALLBACK):
            with self.subTest(target=str(target)):
                path = self.copy / target
                original = path.read_text(encoding="utf-8")
                path.write_text(original + PRINTF_APPEND, encoding="utf-8")
                try:
                    result = self.run_checker()
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertEqual(result.returncode, 1, result.stdout)
                line = self.line_for(result.stdout, CHECK_LINE)
                self.assertTrue(line.startswith("FAIL"), line)
                self.assertIn(str(target), result.stdout)

    def test_assembler_marker_template_drift_fails(self) -> None:
        # Issue #19: the marker format of whatever writes section 5 must be held to the SSOT.
        # The writer is now assemble-pack.py, so a typo in its template must fail D.
        path = self.copy / ASSEMBLER
        original = path.read_text(encoding="utf-8")
        tampered = original.replace("sha256={sha256} -->", "sha={sha256} -->", 1)
        self.assertNotEqual(tampered, original)
        path.write_text(tampered, encoding="utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout)
        line = self.line_for(result.stdout, MARKER_LINE)
        self.assertTrue(line.startswith("FAIL"), line)
        self.assertIn(str(ASSEMBLER), result.stdout)


if __name__ == "__main__":
    unittest.main()
