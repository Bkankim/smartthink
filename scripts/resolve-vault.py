#!/usr/bin/env python3
"""Resolve the SmartThink vault path deterministically and print it as JSON.

This is the single source of truth for {VAULT}. The skill runs it and uses the printed path
as-is; it never re-derives the path from prose. Precedence:

1. SMARTTHINK_VAULT, when set to a non-blank value. Used even if the directory is empty or
   missing: an explicit vault never falls back to another one.
2. The pointer file ${XDG_CONFIG_HOME:-~/.config}/smartthink/vault-pointer, when its first
   non-blank line is an absolute path. `st init` writes it when the user picks a non-default vault.
3. The default ${XDG_DATA_HOME:-~/.local/share}/smartthink.

The default sits outside ~/.claude on purpose (issue #20): Claude Code prompts for every write
under ~/.claude whatever the allow rules say. The pre-#20 default and its pointer are not read.

Output: {"path": "<absolute path>", "source": "env|pointer|default"}
--permission-rule adds "permission_rule" (the Edit allow rule `st init` installs for the vault) and
"settings_path" (${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json, the file it goes into), plus
"permission_rule_effective": false when the vault sits under ~/.claude, which Claude Code treats as
sensitive and keeps prompting for whatever the allow rules say.
--ensure also creates packs/ and copies the evolution-state template when absent. profile.md is
left to `st init`.
--candidates instead lists existing note stores under HOME for `st init` step 5 to offer: signals,
last change, rough file count, git status and warnings per candidate, plus the create-new default.
It reads folder names and mtimes only (never file contents) and never marks a candidate as chosen.
Existing files are never overwritten.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "skills" / "smartthink" / ".data"
# profile.md is deliberately not seeded: its absence is what makes the skill suggest `/st init`.
SEED_FILES = ("evolution-state.md",)


def xdg_dir(variable: str, fallback: str) -> Path:
    # The XDG spec says a relative or empty value is invalid and must be ignored.
    value = (os.environ.get(variable) or "").strip()
    if value and Path(value).is_absolute():
        return Path(value)
    return Path.home() / fallback


def default_vault() -> Path:
    return xdg_dir("XDG_DATA_HOME", ".local/share") / "smartthink"


def pointer_path() -> Path:
    return xdg_dir("XDG_CONFIG_HOME", ".config") / "smartthink" / "vault-pointer"


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
    raw = os.environ.get("SMARTTHINK_VAULT")
    explicit = (raw or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            print(
                f"warning: SMARTTHINK_VAULT '{explicit}' is relative; resolved against {os.getcwd()}",
                file=sys.stderr,
            )
        return Path(os.path.abspath(path)), "env"
    if raw is not None and raw != "":
        print("warning: SMARTTHINK_VAULT is blank; treating it as unset", file=sys.stderr)
    target = read_pointer(pointer_path())
    if target is not None:
        return Path(os.path.abspath(target)), "pointer"
    return default_vault(), "default"


def permission_rule(vault: Path) -> str:
    # A rule path starting with a single / is relative to the settings file, so it never matches an
    # absolute vault (issue #14). Use ~/ under the home directory and // (absolute) elsewhere.
    home = Path.home()
    try:
        relative = vault.relative_to(home)
    except ValueError:
        return f"Edit(//{str(vault).lstrip('/')}/**)"
    return "Edit(~/**)" if relative == Path(".") else f"Edit(~/{relative.as_posix()}/**)"


def rule_is_effective(vault: Path) -> bool:
    # Claude Code prompts for every write under $HOME/.claude ("a sensitive file") even when an
    # allow rule matches, and this follows HOME, not CLAUDE_CONFIG_DIR (issue #14 probes P1-P6).
    # Compare real paths so a vault reached through a symlink into ~/.claude is still caught.
    try:
        Path(os.path.realpath(vault)).relative_to(os.path.realpath(Path.home() / ".claude"))
    except ValueError:
        return True
    return False


def settings_path() -> Path:
    # Claude Code reads user settings from CLAUDE_CONFIG_DIR when it is set, not from ~/.claude.
    config_dir = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    base = Path(config_dir).expanduser() if config_dir else Path.home() / ".claude"
    return Path(os.path.abspath(base)) / "settings.json"


# Files or folders whose presence marks a note store. Their contents are never read.
MARKERS = (".obsidian", ".logseq", "dendron.yml", ".foam")
# Folder name words that suggest a note store, matched case-insensitively with _ and spaces as -.
NAME_WORDS = ("second-brain", "vault", "notes")
MAX_DEPTH = 3
# The walk never enters these. Hidden folders (app state, ~/.claude, .git, .Trash) are skipped too.
SKIPPED_NAMES = {"Library", "node_modules"}
# Never offered even when a registry names them: Claude Code guards writes under .claude and .git
# (issue #14, #20), and a trashed or dependency folder is not a note store. Library stays allowed
# for registry entries because iCloud-synced Obsidian vaults live under ~/Library.
REFUSED_PARTS = {".claude", ".git", ".Trash", "node_modules"}
# Candidate facts are cheap approximations: names and mtimes only, never file contents.
FILE_COUNT_CAP = 5000
STALE_DAYS = 180
NEARLY_EMPTY_FILES = 3
WORKSPACE_REPOS = 3


def walk_dirs(home: Path, deadline: float, state: dict):
    # Yield every directory under home down to MAX_DEPTH levels, never following symlinks, and
    # stop (setting state["timed_out"]) once the deadline passes.
    stack = [(home, 0)]
    while stack:
        if time.monotonic() >= deadline:
            state["timed_out"] = True
            return
        directory, depth = stack.pop()
        if depth:
            yield directory
        if depth == MAX_DEPTH:
            continue
        try:
            entries = list(os.scandir(directory))
        except OSError:
            continue
        for entry in entries:
            if (
                entry.is_dir(follow_symlinks=False)
                and not entry.name.startswith(".")
                and entry.name not in SKIPPED_NAMES
            ):
                stack.append((Path(entry.path), depth + 1))


def signals_of(directory: Path) -> list[str]:
    signals = [f"marker:{name}" for name in MARKERS if (directory / name).exists()]
    name = re.sub(r"[\s_]+", "-", directory.name.lower())
    word = next((word for word in NAME_WORDS if word in name), None)
    if word:
        signals.append(f"name:{word}")
    return signals


def obsidian_registries() -> list[Path]:
    # Obsidian keeps the vaults it has opened here (macOS, then Linux).
    return [
        Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json",
        xdg_dir("XDG_CONFIG_HOME", ".config") / "obsidian" / "obsidian.json",
    ]


def count_files(directory: Path) -> tuple[int, float | None]:
    # Count files (stopping at FILE_COUNT_CAP) and track the newest mtime, skipping hidden folders.
    count, newest = 0, None
    stack = [directory]
    while stack and count < FILE_COUNT_CAP:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith(".") or entry.name in SKIPPED_NAMES:
                continue
            if entry.is_dir(follow_symlinks=False):
                stack.append(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                count += 1
                mtime = entry.stat(follow_symlinks=False).st_mtime
                newest = mtime if newest is None else max(newest, mtime)
    return count, newest


def in_git_repo(directory: Path) -> bool:
    return any((folder / ".git").exists() for folder in (directory, *directory.parents))


def nested_repos(directory: Path) -> int:
    # Repositories among the children and grandchildren: a work folder, not a note store.
    return sum(1 for folder in (*directory.glob("[!.]*"), *directory.glob("[!.]*/[!.]*")) if (folder / ".git").is_dir())


def describe(directory: Path, signals: list[str]) -> dict:
    count, newest = count_files(directory)
    if newest is None:
        newest = directory.stat().st_mtime
    warnings = []
    if time.time() - newest > STALE_DAYS * 86400:
        warnings.append("stale")
    if count <= NEARLY_EMPTY_FILES:
        warnings.append("nearly-empty")
    if nested_repos(directory) >= WORKSPACE_REPOS:
        warnings.append("workspace-root")
    return {
        "path": str(directory),
        "signals": signals,
        "last_modified": datetime.fromtimestamp(newest, timezone.utc).date().isoformat(),
        "file_count": count,
        "git_repo": in_git_repo(directory),
        "warnings": warnings,
        "suggested_vault": str(directory / "smartthink"),
    }


def is_refused(directory: Path) -> bool:
    if REFUSED_PARTS.intersection(directory.parts):
        return True
    return not rule_is_effective(directory)


def registered_vaults() -> list[Path]:
    paths = []
    for registry in obsidian_registries():
        try:
            vaults = json.loads(registry.read_text(encoding="utf-8")).get("vaults", {})
        except (OSError, ValueError, AttributeError):
            continue
        for entry in vaults.values() if isinstance(vaults, dict) else ():
            value = entry.get("path") if isinstance(entry, dict) else None
            if isinstance(value, str) and Path(value).is_absolute() and Path(value).is_dir():
                path = Path(os.path.abspath(value))
                if not is_refused(path):
                    paths.append(path)
    return paths


def candidates(time_limit: float) -> dict:
    # Keyed by real path so the registry and the walk can name the same folder differently.
    found: dict[str, dict] = {}

    def add(directory: Path, signals: list[str]) -> None:
        entry = found.setdefault(os.path.realpath(directory), {"path": directory, "signals": []})
        entry["signals"] += [signal for signal in signals if signal not in entry["signals"]]

    for directory in registered_vaults():
        add(directory, ["registry:obsidian"] + signals_of(directory))
    state = {"timed_out": False}
    for directory in walk_dirs(Path.home(), time.monotonic() + time_limit, state):
        signals = signals_of(directory)
        if signals:
            add(directory, signals)
    listed = sorted((describe(entry["path"], entry["signals"]) for entry in found.values()), key=lambda c: c["path"])
    return {
        "candidates": listed,
        "create_new": {"path": str(default_vault())},
        "scan": {"root": str(Path.home()), "max_depth": MAX_DEPTH, "timed_out": state["timed_out"]},
    }


def ensure(vault: Path) -> None:
    (vault / "packs").mkdir(parents=True, exist_ok=True)
    for name in SEED_FILES:
        target = vault / name
        if not target.exists():
            shutil.copyfile(TEMPLATE_DIR / name, target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the resolved SmartThink vault as JSON.")
    parser.add_argument("--ensure", action="store_true", help="create packs/ and seed a missing evolution-state.md")
    parser.add_argument(
        "--permission-rule",
        action="store_true",
        help="also print the vault Edit allow rule and the settings.json it belongs in",
    )
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="list existing note stores under HOME for `st init` to offer (never picks one)",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=10.0,
        metavar="SECONDS",
        help="with --candidates: stop walking HOME after this many seconds (default 10)",
    )
    arguments = parser.parse_args()
    if arguments.candidates:
        print(json.dumps(candidates(arguments.time_limit), ensure_ascii=False))
        return 0
    vault, source = resolve()
    if arguments.ensure:
        try:
            ensure(vault)
        except OSError as error:
            print(f"error: cannot prepare vault {vault}: {error}", file=sys.stderr)
            return 1
    result = {"path": str(vault), "source": source}
    if arguments.permission_rule:
        result["permission_rule"] = permission_rule(vault)
        result["settings_path"] = str(settings_path())
        result["permission_rule_effective"] = rule_is_effective(vault)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
