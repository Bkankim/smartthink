#!/usr/bin/env python3
"""Resolve the SmartThink vault path deterministically and print it as JSON.

This is the single source of truth for {VAULT}. The skill runs it and uses the printed path
as-is; it never re-derives the path from prose. Precedence:

1. SMARTTHINK_VAULT, when set to a non-blank value. Used even if the directory is empty or
   missing: an explicit vault never falls back to another one.
2. The pointer file ~/.claude/smartthink-vault/vault-pointer, when its first non-blank line is an
   absolute path. `st init` writes it when the user picks a non-default vault.
3. The default ~/.claude/smartthink-vault.

Output: {"path": "<absolute path>", "source": "env|pointer|default"}
--ensure also creates packs/ and copies the evolution-state template when absent. profile.md is
left to `st init`.
Existing files are never overwritten.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "skills" / "smartthink" / ".data"
# profile.md is deliberately not seeded: its absence is what makes the skill suggest `/st init`.
SEED_FILES = ("evolution-state.md",)


def default_vault() -> Path:
    return Path.home() / ".claude" / "smartthink-vault"


def read_pointer(pointer: Path) -> Path | None:
    # Return the pointer's target, or None when the file is absent or its value is unusable.
    try:
        lines = pointer.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    value = next((line.strip() for line in lines if line.strip()), "")
    target = Path(value).expanduser() if value else None
    if target is None or not target.is_absolute():
        if value:
            print(f"warning: ignoring {pointer}: '{value}' is not an absolute path", file=sys.stderr)
        return None
    return target


def resolve() -> tuple[Path, str]:
    explicit = os.environ.get("SMARTTHINK_VAULT", "").strip()
    if explicit:
        return Path(os.path.abspath(Path(explicit).expanduser())), "env"
    target = read_pointer(default_vault() / "vault-pointer")
    if target is not None:
        return Path(os.path.abspath(target)), "pointer"
    return default_vault(), "default"


def ensure(vault: Path) -> None:
    (vault / "packs").mkdir(parents=True, exist_ok=True)
    for name in SEED_FILES:
        target = vault / name
        if not target.exists():
            shutil.copyfile(TEMPLATE_DIR / name, target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the resolved SmartThink vault as JSON.")
    parser.add_argument("--ensure", action="store_true", help="create packs/ and seed a missing evolution-state.md")
    arguments = parser.parse_args()
    vault, source = resolve()
    if arguments.ensure:
        try:
            ensure(vault)
        except OSError as error:
            print(f"error: cannot prepare vault {vault}: {error}", file=sys.stderr)
            return 1
    print(json.dumps({"path": str(vault), "source": source}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
