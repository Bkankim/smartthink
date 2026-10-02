"""Issue #43 repro (C2, C3): run the real checker on a throwaway copy with one tampered line.

Usage (from the repo root): python3 tests/evidence/43-repro.py
Part 1 probes the three helpers directly (which function misses, per input).
Part 2 appends one line to SKILL.md of a temp copy, runs scripts/check-structure.py there and prints
the exit code, the two D. wiring rows and any traceback. The checkout itself is only read.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CMD = "python3 {SCRIPTS_DIR}/resolve-vault.py --ensure"
CASES = (
    ("C2 unclosed quote after an assignment", f'V="my vault" W=it\'s {CMD}'),
    ("C3 quoted assignment word", f"'V=1' {CMD}"),
    ("control: quoted value with space (#37)", f'V="my vault" {CMD}'),
    ("control: no assignment", CMD),
    ("control: fully unparseable", 'V="my vault python3 x.py'),
)


def probe() -> None:
    spec = importlib.util.spec_from_file_location("check_structure", REPO_ROOT / "scripts" / "check-structure.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_structure"] = module
    spec.loader.exec_module(module)
    for label, line in CASES:
        try:
            word = module._command_word(line)
            command = module._is_command(line)
            operator = module._compound_operator(line)
            print(f"probe: {label}: _command_word={word!r} _is_command={command} _compound_operator={operator!r}")
        except Exception as error:  # noqa: BLE001 - the repro reports any crash as a finding
            print(f"probe: {label}: CRASH {type(error).__name__}: {error}")


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
    probe()
    print("case: untampered")
    run(None)
    for label, line in CASES:
        for surface, addition in (("inline", f"`{line}`"), ("fence ", f"```bash\n{line}\n```")):
            print(f"case: {surface} {label}: {addition.splitlines()[-2 if addition.startswith('```') else 0]}")
            run(addition)
