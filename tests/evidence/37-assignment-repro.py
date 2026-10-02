"""Issue #37 item 4 repro: run the real checker on a throwaway copy with one tampered line.

Usage (from the repo root): python3 tests/evidence/37-assignment-repro.py
Each case appends one line to SKILL.md of a temp copy, runs scripts/check-structure.py there and
prints the exit code, the D. wiring lines and any traceback. The checkout itself is only read.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CASES = (
    ("inline  double-quoted value with space", '`V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`'),
    ("inline  single-quoted value with space", "`V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`"),
    ("inline  value without space", "`V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`"),
    ("inline  several assignments", '`A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`'),
    ("inline  unclosed quote", '`V="my vault python3 x.py`'),
    ("fence   double-quoted value with space", '```bash\nV="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure\n```'),
    ("fence   single-quoted value with space", "```bash\nV='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure\n```"),
    ("fence   value without space", "```bash\nV=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure\n```"),
    ("fence   several assignments", '```bash\nA=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure\n```'),
    ("fence   unclosed quote", '```bash\nV="my vault python3 x.py\n```'),
)


def run(addition: str | None) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp).resolve() / "repo"
        shutil.copytree(
            REPO_ROOT,
            copy,
            ignore=shutil.ignore_patterns(".git", ".fablize", "evidence", "__pycache__", ".pytest_cache"),
        )
        if addition is not None:
            skill = copy / "skills" / "smartthink" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\n" + addition + "\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "scripts/check-structure.py"], cwd=copy, capture_output=True, text=True, check=False
        )
        print(f"  exit={result.returncode}")
        for line in result.stdout.splitlines():
            if line.startswith(("PASS D.", "FAIL D.")) and ("single commands" in line or "rule bundle" in line):
                print(f"  {line}")
            elif line.startswith("  ") and "SKILL.md" in line and "uses '" in line:
                print(f"  {line.strip()[:150]}")
        if "Traceback" in result.stderr:
            print("  TRACEBACK:", result.stderr.strip().splitlines()[-1])
        elif result.stderr.strip():
            print("  stderr:", result.stderr.strip().splitlines()[-1])
        summary = [line for line in result.stdout.splitlines() if " passed, " in line and "failed" in line]
        print(f"  {summary[0] if summary else 'no summary line'}")


if __name__ == "__main__":
    print("case: untampered")
    run(None)
    for label, addition in CASES:
        print(f"case: {label}: {addition.splitlines()[-2 if addition.startswith('```') else 0]}")
        run(addition)
