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
--permission-rule adds "permission_rule" (the Edit allow rule `st init` installs for the vault) and
"settings_path" (${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json, the file it goes into), plus
"permission_rule_effective": false when the vault sits under ~/.claude, which Claude Code treats as
sensitive and keeps prompting for whatever the allow rules say.
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
    target = read_pointer(default_vault() / "vault-pointer")
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
    arguments = parser.parse_args()
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
