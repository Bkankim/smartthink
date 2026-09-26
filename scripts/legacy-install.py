#!/usr/bin/env python3
"""Find and move aside SmartThink leftovers that shadow the current install.

Earlier releases were sometimes installed by copying files into ~/.claude instead of the
installer's symlinks. Those real files keep the bare names (/st, /smartthink, st-thinker), so a
newer install is silently shadowed, and the installers refuse to replace real files. This tool
is shared by install.sh, uninstall.sh and `/st status`.

  detect    list leftovers, one "<path>\t<reason>" per line. Read-only.
  migrate   move every leftover under ~/.claude/.backup/smartthink-legacy-<timestamp>/,
            keeping its path relative to ~/.claude. Nothing is deleted.
  --blocking  with either action: skip links into an older checkout, which the installers
              replace or remove on their own.

Only files that identify themselves as SmartThink are leftovers. Symlinks to current content
are left to the installers, which own and replace them. Symlinks into an older checkout (pre-v3
content, or the removed agent) are leftovers too, because they shadow the bare names the same way.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SMARTTHINK_MARK = re.compile(r"smartthink", re.IGNORECASE)
# The pre-v3 alias text. The current commands/st.md says "SmartThink alias", which must not match.
ALIAS_MARK = re.compile(r"alias for /smartthink", re.IGNORECASE)
# The current skill spawns st-armorer and the current st-thinker reads pack.md; files without
# these predate v3.
CURRENT_SKILL_MARK = "st-armorer"
CURRENT_THINKER_MARK = "pack.md"
# Agents a copy install could have left, and the agent removed in v3 (folded into st-armorer).
REMOVED_AGENT = "st-searcher"  # removed in v3, named only to detect leftovers
AGENT_NAMES = ("st-thinker", REMOVED_AGENT)


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


def detect(base: Path, blocking_only: bool = False) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    skill = base / "skills" / "smartthink"
    skill_text = read(skill / "SKILL.md")
    if (
        is_real(skill)
        and skill.is_dir()
        and SMARTTHINK_MARK.search(skill_text)
        and CURRENT_SKILL_MARK not in skill_text
    ):
        found.append((skill, "copied skill directory from a release before v3"))
    for name in AGENT_NAMES:
        agent = base / "agents" / f"{name}.md"
        text = read(agent)
        if is_real(agent) and frontmatter_name(text) == name and SMARTTHINK_MARK.search(text):
            found.append((agent, f"copied {name} agent definition"))
    # A symlink into another, still-present v2 clone keeps the removed agent listed. The
    # installers only replace links they own, so this one is moved like a copied file.
    removed = base / "agents" / f"{REMOVED_AGENT}.md"
    text = read(removed)
    if removed.is_symlink() and frontmatter_name(text) == REMOVED_AGENT and SMARTTHINK_MARK.search(text):
        found.append((removed, f"link to the removed {REMOVED_AGENT} agent in another checkout"))
    command = base / "commands" / "st.md"
    if is_real(command) and ALIAS_MARK.search(read(command)):
        found.append((command, "copied /st alias"))
    # Links into an older checkout shadow the bare names just like copies do, so `/st status`
    # reports them. The installers replace (install) or remove (uninstall) these links anyway, so
    # they are not blocking. Links to current content are never reported.
    if blocking_only:
        return found
    if skill.is_symlink() and SMARTTHINK_MARK.search(skill_text) and CURRENT_SKILL_MARK not in skill_text:
        found.append((skill, "link to a skill from a release before v3"))
    thinker = base / "agents" / "st-thinker.md"
    text = read(thinker)
    if (
        thinker.is_symlink()
        and frontmatter_name(text) == "st-thinker"
        and SMARTTHINK_MARK.search(text)
        and CURRENT_THINKER_MARK not in text
    ):
        found.append((thinker, "link to an st-thinker from a release before v3"))
    if command.is_symlink() and ALIAS_MARK.search(read(command)):
        found.append((command, "link to a /st alias from a release before v3"))
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
    parser.add_argument(
        "--blocking",
        action="store_true",
        help="only leftovers the installers cannot replace or remove themselves (used by install.sh/uninstall.sh)",
    )
    arguments = parser.parse_args()
    base = claude_dir()
    leftovers = detect(base, blocking_only=arguments.blocking)
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
