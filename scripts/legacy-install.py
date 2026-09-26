#!/usr/bin/env python3
"""Find and move aside SmartThink leftovers that shadow the current install.

Earlier releases were sometimes installed by copying files into ~/.claude instead of the
installer's symlinks. Those real files keep the bare names (/st, /smartthink, st-thinker), so a
newer install is silently shadowed, and the installers refuse to replace real files. This tool
is shared by install.sh, uninstall.sh and `/st status`.

  detect    list leftovers, one "<path>\t<reason>" per line. Read-only.
  migrate   move every leftover under ~/.claude/.backup/smartthink-legacy-<timestamp>/,
            keeping its path relative to ~/.claude. Nothing is deleted.

Only files that identify themselves as SmartThink are leftovers. Symlinks are never leftovers:
the installers already own and replace them.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SMARTTHINK_MARK = re.compile(r"smartthink", re.IGNORECASE)
ALIAS_MARK = re.compile(r"alias for /smartthink|smartthink alias", re.IGNORECASE)
# The current skill spawns st-armorer; a SKILL.md without it predates v3.
CURRENT_SKILL_MARK = "st-armorer"
# Agents a copy install could have left. The second one was removed in v3 (folded into st-armorer).
AGENT_NAMES = ("st-thinker", "st-searcher")  # st-searcher: removed agent, listed only to detect it


def claude_dir() -> Path:
    return Path.home() / ".claude"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def frontmatter_name(text: str) -> str | None:
    match = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
    if match is None:
        return None
    name = re.search(r"^name:\s*(\S+)", match.group(1), re.MULTILINE)
    return name.group(1) if name else None


def is_real(path: Path) -> bool:
    return path.exists() and not path.is_symlink()


def detect(base: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    skill = base / "skills" / "smartthink"
    if is_real(skill) and skill.is_dir() and CURRENT_SKILL_MARK not in read(skill / "SKILL.md"):
        found.append((skill, "copied skill directory from a release before v3"))
    for name in AGENT_NAMES:
        agent = base / "agents" / f"{name}.md"
        text = read(agent)
        if is_real(agent) and frontmatter_name(text) == name and SMARTTHINK_MARK.search(text):
            found.append((agent, f"copied {name} agent definition"))
    command = base / "commands" / "st.md"
    if is_real(command) and ALIAS_MARK.search(read(command)):
        found.append((command, "copied /st alias"))
    return found


def backup_root(base: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = base / ".backup" / f"smartthink-legacy-{stamp}"
    suffix = 1
    while root.exists():
        suffix += 1
        root = base / ".backup" / f"smartthink-legacy-{stamp}-{suffix}"
    return root


def migrate(base: Path, leftovers: list[tuple[Path, str]]) -> Path | None:
    if not leftovers:
        return None
    root = backup_root(base)
    for path, _reason in leftovers:
        target = root / path.relative_to(base)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
        print(f"moved\t{path}\t{target}")
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description="Find or move aside SmartThink install leftovers.")
    parser.add_argument("action", choices=("detect", "migrate"))
    arguments = parser.parse_args()
    base = claude_dir()
    leftovers = detect(base)
    if arguments.action == "detect":
        for path, reason in leftovers:
            print(f"{path}\t{reason}")
        return 0
    try:
        root = migrate(base, leftovers)
    except OSError as error:
        print(f"error: could not move a leftover: {error}", file=sys.stderr)
        return 1
    if root is not None:
        print(f"backup\t{root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
