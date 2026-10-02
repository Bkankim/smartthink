"""Issue #43: old vs new assignment judges over every command the docs show plus synthetic shapes.

Usage (from the repo root): python3 tests/evidence/43-differential.py <old check-structure.py>
The old file is `git show origin/main:scripts/check-structure.py` saved anywhere. Prints every input
where _compound_operator, _command_word or _is_command differ, and the corpus size.
"""
from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def corpus(new) -> list[str]:
    lines: list[str] = []
    for path in new.SESSION_BASH_DOCS:
        text = path.read_text(encoding="utf-8")
        lines += [command for _, command, _ in new._shell_commands(text)]
    for doc in REPO_ROOT.rglob("*.md"):
        if ".git" in doc.parts or "evidence" in doc.parts:
            continue
        for block in new.FENCE_RE.finditer(doc.read_text(encoding="utf-8")):
            lines += [line.strip() for line in block.group("body").splitlines() if line.strip()]
    prefixes = ("", "V=1 ", "V=\"my vault\" ", "V='my vault' ", "'V=1' ", '"V=1" ', "V=a#b ", "A=1 B=2 ", "V=1\t",
                "V=\"a\" W=it's ", 'V="a ', "V=a\\", "X= ", "=1 ", "1V=2 ", "V\\=1 ", "A=1 'B=2' ")
    bodies = ("python3 {SCRIPTS_DIR}/resolve-vault.py --ensure", "ls -la", "x; y", "a | b", "echo '$(x)'", "", "cat > f",
              "'")
    lines += [p + b for p, b in itertools.product(prefixes, bodies)]
    return lines


def main() -> None:
    old = load("old_check", Path(sys.argv[1]))
    new = load("new_check", REPO_ROOT / "scripts" / "check-structure.py")
    inputs = sorted(set(corpus(new)))
    differ = 0
    for line in inputs:
        row = {}
        for name, module in (("old", old), ("new", new)):
            try:
                row[name] = (module._compound_operator(line), module._command_word(line), module._is_command(line))
            except Exception as error:  # noqa: BLE001 - a crash is a finding
                row[name] = f"CRASH {type(error).__name__}"
        if row["old"] != row["new"]:
            differ += 1
            print(f"DIFF {line!r}\n  old={row['old']}\n  new={row['new']}")
    print(f"inputs={len(inputs)} differing={differ}")


if __name__ == "__main__":
    main()
