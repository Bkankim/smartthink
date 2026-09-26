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
"settings_path" (${CLAUDE_CONFIG_DIR:-~/.claude}/settings.json, the file it goes into; null with a
warning when CLAUDE_CONFIG_DIR is relative), plus "permission_rule_effective" and
"permission_rule_reason". The rule is not effective, and the reason says why, when the vault sits
under ~/.claude ("home-claude") or under a .claude/.git/.vscode/.idea folder ("protected-folder"),
which Claude Code treats as sensitive whatever the allow rules say, or when its path holds glob or
rule syntax the rule does not escape ("special-characters").
It also prints the rest of the bundle `st init` offers so an arming run asks nothing (issue #26):
"bash_rules" and "command_prefixes" for the two scripts a session runs (this one and
assemble-pack.py, taken from the path this script was invoked by, symlinks not resolved) with
"bash_rules_effective", and "read_rule" for the sibling skills/smartthink/ directory the session and
the armorer Read, with "read_rule_effective"; "read_rules" adds the user-level skills/smartthink
symlinks (install.sh) that resolve to that directory, since the session Reads through the link.
"vault_writable" says whether the vault (or the nearest existing folder on its path) and an existing
packs/ are writable directories (what `st status` reports).
--module-sizes NAME... prints {"modules": {name: {"bytes", "est_tokens"} or null}} for files in the
sibling skills/smartthink/references/, the gate's fallback when index.json is missing; a name that is
not a plain file there is null with a warning on stderr, and the exit code stays 0.
--ensure also creates packs/ and copies the evolution-state template when absent. profile.md is
left to `st init`.
--ensure also prints "bash_rules_effective" and "bash_rules_reason" (whether unquoted script calls can
match the Bash rules) and "vault_writable" (the vault root and packs/ are writable), which the arming
gate reads instead of the exit code.
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


def path_rule(tool: str, directory: Path) -> str:
    # A rule path starting with a single / is relative to the settings file, so it never matches an
    # absolute directory (issue #14). Use ~/ under the home directory and // (absolute) elsewhere.
    home = Path.home()
    try:
        relative = directory.relative_to(home)
    except ValueError:
        return f"{tool}(//{str(directory).lstrip('/')}/**)"
    return f"{tool}(~/**)" if relative == Path(".") else f"{tool}(~/{relative.as_posix()}/**)"


def permission_rule(vault: Path) -> str:
    return path_rule("Edit", vault)


def under_home_claude(vault: Path) -> bool:
    # Claude Code prompts for every write under $HOME/.claude ("a sensitive file") even when an
    # allow rule matches, and this follows HOME, not CLAUDE_CONFIG_DIR (issue #14 probes P1-P6).
    # Compare real paths so a vault reached through a symlink into ~/.claude is still caught.
    try:
        Path(os.path.realpath(vault)).relative_to(os.path.realpath(Path.home() / ".claude"))
    except ValueError:
        return False
    return True


# Glob and rule syntax the rule string does not escape (issue #23): a vault named "Obsidian [main]"
# would turn [main] into a character class, so the rule may never match the vault.
RULE_SYNTAX = set("[]*?{}()")
# Folder names Claude Code treats as sensitive wherever they appear in a path: headless probes
# (issue #20, Claude Code 2.1.283) denied Writes under each despite a matching Edit(//abs/**) allow
# rule, inside or outside a repo and whatever the cwd. A hidden folder like .notes was not guarded.
PROTECTED_FOLDERS = {".claude", ".git", ".vscode", ".idea"}


def ineffective_reason(vault: Path) -> str | None:
    # Why an Edit allow rule for this vault would not stop the write prompts, or None if it would.
    if under_home_claude(vault):
        return "home-claude"
    if PROTECTED_FOLDERS.intersection((*vault.parts, *Path(os.path.realpath(vault)).parts)):
        return "protected-folder"
    if RULE_SYNTAX.intersection(str(vault)):
        return "special-characters"
    return None


# The scripts an arming run executes through Bash (issue #26): the main session resolves {VAULT},
# the armorer assembles pack section 5. Each gets one allow rule so neither prompts.
SESSION_SCRIPTS = ("resolve-vault.py", "assemble-pack.py")
# Same set as assemble-pack.py: in an unquoted command these change the words or fail to parse.
SHELL_SPECIAL = set("'\"`$\\;&|<>()[]{}*?!#~")


def bash_rules_status() -> dict:
    # Whether the unquoted `python3 {SCRIPTS_DIR}/<script>` form can match a prefix rule. With
    # whitespace or a shell special character in the path the session must quote the script path
    # (or it splits into other words), and a quoted command never matches the rule, so the rule is
    # not effective and each call prompts (final-review of #26 #1).
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    special = any(char.isspace() or char in SHELL_SPECIAL for char in scripts_dir)
    return {"bash_rules_effective": not special, "bash_rules_reason": "special-characters" if special else None}


def script_rules() -> dict:
    # Bash rules match the command text, so the prefix is python3 plus this script's directory as
    # invoked: symlinks are not resolved, exactly as assemble-pack.py --permission-rule does (#21).
    # init runs this through the same {SCRIPTS_DIR} string the skill and the armorer type.
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    prefixes = {Path(name).stem: f"python3 {scripts_dir}/{name}" for name in SESSION_SCRIPTS}
    # The session and the armorer Read {SKILL_DIR}/references/ (index.json, the modules), which
    # sits outside the working directory for a plugin user and prompted on every Read (T16-before).
    # {SKILL_DIR} is the skills/smartthink/ sibling of the same, unresolved {SCRIPTS_DIR}.
    skill_dir = Path(os.path.dirname(scripts_dir)) / "skills" / "smartthink"
    read_dirs = (skill_dir, *linked_skill_dirs(skill_dir))
    return {
        "command_prefixes": prefixes,
        "bash_rules": [f"Bash({prefix} *)" for prefix in prefixes.values()],
        **bash_rules_status(),
        "read_rule": path_rule("Read", skill_dir),
        "read_rules": [path_rule("Read", path) for path in read_dirs],
        # Every listed path counts: a link path like ~/claude[work]/skills/smartthink never matches.
        "read_rule_effective": not any(RULE_SYNTAX.intersection(str(path)) for path in read_dirs),
    }


def linked_skill_dirs(skill_dir: Path) -> list[Path]:
    # install.sh links <user skills>/smartthink to the checkout, and the session Reads references/
    # through that link, not through the checkout path; a rule naming only the checkout path still
    # prompted (final-review of #26 (c), T16-after install.sh row). Claude Code loads user skills
    # from $CLAUDE_CONFIG_DIR when set, install.sh writes ~/.claude, so both are candidates.
    real = os.path.realpath(skill_dir)
    candidates = [Path.home() / ".claude" / "skills" / "smartthink"]
    config_dir = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    if config_dir and Path(config_dir).expanduser().is_absolute():
        candidates.append(Path(os.path.abspath(Path(config_dir).expanduser())) / "skills" / "smartthink")
    linked: list[Path] = []
    for candidate in candidates:
        if candidate != skill_dir and candidate not in linked and candidate.is_symlink() and os.path.realpath(candidate) == real:
            linked.append(candidate)
    return linked


# bytes -> token estimate, the divisor build-index.py uses for index.json.
TOKEN_DIVISOR = 2.2


def module_sizes(names: list[str]) -> dict:
    # The gate's fallback when references/index.json is missing (final-review of #26 (a)1): the
    # session used to measure files with Bash `wc -c`, a command no allow rule covers. This script
    # already has one, so it reports the sizes. Only plain file names inside references/ are read.
    references = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "skills" / "smartthink" / "references"
    # A name that is not a plain file there comes back as null with a warning, so one bad name does
    # not cost the gate the other estimates (final-review of #26 #5).
    modules: dict[str, dict | None] = {}
    for name in names:
        if Path(name).name != name or not (references / name).is_file():
            print(f"warning: not a file in {references}: {name}", file=sys.stderr)
            modules[name] = None
            continue
        size = (references / name).stat().st_size
        modules[name] = {"bytes": size, "est_tokens": round(size / TOKEN_DIVISOR)}
    return {"modules": modules}


def vault_writable(vault: Path) -> bool:
    # `st status` used Bash `test -w {VAULT}`, a command outside the rule bundle (final-review of
    # #26). Judged on the nearest existing ancestor, as install.sh does: a vault not created yet is
    # writable when the folder it would be created in is.
    # The armorer writes under packs/, so an existing packs/ must be writable too (final-review #2).
    packs = vault / "packs"
    if os.path.lexists(packs) and not (os.path.isdir(packs) and os.access(packs, os.W_OK)):
        return False
    base = str(vault)
    while base and not os.path.lexists(base):
        base = os.path.dirname(base)
    base = base or "."  # a relative SMARTTHINK_VAULT resolves against the cwd
    return os.path.isdir(base) and os.access(base, os.W_OK)


def settings_path() -> Path | None:
    # Claude Code reads user settings from CLAUDE_CONFIG_DIR when it is set, not from ~/.claude.
    # A relative value resolves against the session's own cwd, which this process cannot know
    # (issue #23), so name no file rather than one the session may not read.
    config_dir = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    if not config_dir:
        return Path.home() / ".claude" / "settings.json"
    base = Path(config_dir).expanduser()
    if not base.is_absolute():
        print(
            f"warning: CLAUDE_CONFIG_DIR '{config_dir}' is relative; not naming a settings file for it",
            file=sys.stderr,
        )
        return None
    return Path(os.path.abspath(base)) / "settings.json"


# Files or folders whose presence marks a note store. Their contents are never read.
MARKERS = (".obsidian", ".logseq", "dendron.yml", ".foam")
# Folder name words that suggest a note store, matched case-insensitively with _ and spaces as -.
NAME_WORDS = ("second-brain", "vault", "notes")
MAX_DEPTH = 3
# The walk never enters these. Hidden folders (app state, ~/.claude, .git, .Trash) are skipped too.
SKIPPED_NAMES = {"Library", "node_modules"}
# Never offered even when a registry names them, together with PROTECTED_FOLDERS (Claude Code guards
# writes there): a trashed or dependency folder is not a note store. Library stays allowed
# for registry entries because iCloud-synced Obsidian vaults live under ~/Library.
REFUSED_PARTS = {".Trash", "node_modules"}
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


def present(path: Path) -> bool:
    # Path.exists() raises PermissionError on Python < 3.14 for an unreadable parent; treat as absent.
    try:
        return path.exists()
    except OSError:
        return False


def signals_of(directory: Path) -> list[str]:
    signals = [f"marker:{name}" for name in MARKERS if present(directory / name)]
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


def count_files(directory: Path, deadline: float) -> tuple[int, float | None, str | None]:
    # Count files (stopping at FILE_COUNT_CAP) and track the newest mtime, skipping hidden folders.
    # The third value says why the count is incomplete: "deadline", "error" (a stat failed, e.g. a
    # file vanished mid-scan), "cap" (FILE_COUNT_CAP reached, the mtimes are a sample), or None.
    count, newest = 0, None
    stack = [directory]
    while stack:
        if time.monotonic() >= deadline:
            return count, newest, "deadline"
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith(".") or entry.name in SKIPPED_NAMES:
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    mtime = entry.stat(follow_symlinks=False).st_mtime
                    count += 1
                    newest = mtime if newest is None else max(newest, mtime)
                    if count >= FILE_COUNT_CAP:
                        return count, newest, "cap"
            except OSError:
                return count, newest, "error"
    return count, newest, None


def in_git_repo(directory: Path) -> bool:
    # Stop below HOME: a $HOME/.git dotfiles repo does not version an ordinary folder under home.
    home = Path.home()
    for folder in (directory, *directory.parents):
        if folder == home:
            return False
        if present(folder / ".git"):
            return True
    return False


def nested_repos(directory: Path, deadline: float) -> int | None:
    # Repositories among the children and grandchildren: a work folder, not a note store.
    # None when the deadline passed before the answer was known.
    found = 0
    for pattern in ("[!.]*", "[!.]*/[!.]*"):
        for folder in directory.glob(pattern):
            if time.monotonic() >= deadline:
                return None
            # A worktree or submodule has a .git file, not a folder; both mark a repository.
            if present(folder / ".git"):
                found += 1
                if found >= WORKSPACE_REPOS:
                    return found
    return found


def describe(directory: Path, signals: list[str], deadline: float, state: dict) -> dict:
    count, newest, cut = count_files(directory, deadline)
    # The repo count does not depend on the file sample, so it is still taken when the cap was hit.
    repos = nested_repos(directory, deadline) if cut in (None, "cap") else None
    if cut in (None, "cap") and repos is None:
        cut = "deadline"
    if newest is None:
        try:
            newest = directory.stat().st_mtime
        except OSError:
            newest, cut = time.time(), cut or "error"
    warnings = []
    if cut is None:
        if time.time() - newest > STALE_DAYS * 86400:
            warnings.append("stale")
        if count <= NEARLY_EMPTY_FILES:
            warnings.append("nearly-empty")
    else:
        # The facts were cut short (time limit, failed stat or file cap), so these warnings would be guesses.
        warnings.append("partial")
        if cut == "deadline":
            state["timed_out"] = True
    if repos is not None and repos >= WORKSPACE_REPOS:
        warnings.append("workspace-root")
    if ineffective_reason(directory / "smartthink") == "special-characters":
        # The Edit rule for this vault may not match, so its writes would keep prompting (issue #23).
        warnings.append("special-characters")
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
    # Check the real path too: a registered folder may be a symlink into a protected folder.
    parts = (*directory.parts, *Path(os.path.realpath(directory)).parts)
    if (REFUSED_PARTS | PROTECTED_FOLDERS).intersection(parts):
        return True
    return under_home_claude(directory)


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
    deadline = time.monotonic() + time_limit
    for directory in walk_dirs(Path.home(), deadline, state):
        signals = signals_of(directory)
        if signals:
            add(directory, signals)
    # One deadline covers the walk and describing the candidates it found.
    described = (describe(entry["path"], entry["signals"], deadline, state) for entry in found.values())
    listed = sorted(described, key=lambda candidate: candidate["path"])
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
    parser.add_argument(
        "--module-sizes",
        nargs="+",
        metavar="NAME",
        help="print bytes and est_tokens of these references/ files (gate fallback without index.json)",
    )
    arguments = parser.parse_args()
    if arguments.module_sizes:
        print(json.dumps(module_sizes(arguments.module_sizes), ensure_ascii=False))
        return 0
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
    if arguments.ensure:
        result.update(bash_rules_status())
        # --ensure exits 0 on an existing read-only vault, so the arming gate reads this instead.
        result["vault_writable"] = vault_writable(vault)
    if arguments.permission_rule:
        result["permission_rule"] = permission_rule(vault)
        target = settings_path()
        result["settings_path"] = str(target) if target else None
        reason = ineffective_reason(vault)
        result["permission_rule_effective"] = reason is None
        result["permission_rule_reason"] = reason
        result["vault_writable"] = vault_writable(vault)
        result.update(script_rules())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
