#!/usr/bin/env python3
"""Fill section 5 of an armory pack with verbatim module copies.

The armorer (or the inline path) Writes pack.md whole: sections 1-4, the section 5 title with an
empty body, then section 6. This script then inserts each selected module between the section 5
and section 6 titles, byte for byte, wrapped in the marker pair whose format is fixed by
references/analysis-method.md ("원문 무결성 규칙"). Copying through a script instead of retyping
keeps the hash intact, and one script instead of printf/cat redirections keeps the Bash surface to
a single command that one narrow allow rule can cover (issue #21).

Usage:
  python3 <SCRIPTS_DIR>/assemble-pack.py --pack-dir <DIR> --modules <name.md> [<name.md> ...]

  python3 <SCRIPTS_DIR>/assemble-pack.py --permission-rule

Output: JSON {"pack", "modules", "bytes", "est_tokens_pack"} on stdout, exit 0.
--permission-rule prints {"permission_rule", "permission_rule_effective", "script"}: the one Bash
allow rule `st init` offers so the armorer's section 5 assembly runs without a prompt.
Errors go to stderr with a non-zero exit, and pack.md is left untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "skills" / "smartthink" / "references"
# The nine frozen modules are the keys of index.json; nothing else may be copied into section 5.
INDEX_JSON = REFERENCES_DIR / "index.json"

SECTION_FIVE = "## 5. 레퍼런스 원문".encode("utf-8")
SECTION_SIX = "## 6. 과거 인사이트와 프로필".encode("utf-8")

# The marker spellings. check-structure.py D compares these templates with analysis-method.md.
BEGIN_MARKER = "<!-- MODULE-BEGIN: {name} sha256={sha256} -->"
END_MARKER = "<!-- MODULE-END: {name} -->"

# pack.md size to token estimate, the same divisor the armorer uses for est_tokens.pack.
TOKEN_DIVISOR = 2.2


class AssemblyError(Exception):
    pass


def find_title(data: bytes, title: bytes, start: int = 0) -> int:
    """Offset of the line that is exactly `title` (trailing blanks allowed), or -1."""
    index = start
    while True:
        index = data.find(title, index)
        if index < 0:
            return -1
        line_end = data.find(b"\n", index)
        rest = data[index + len(title) : line_end if line_end >= 0 else len(data)]
        if (index == 0 or data[index - 1 : index] == b"\n") and not rest.strip(b" \t\r"):
            return index
        index += len(title)


def module_block(name: str) -> bytes:
    source = (REFERENCES_DIR / name).read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    separator = b"" if source.endswith(b"\n") else b"\n"
    return (
        BEGIN_MARKER.format(name=name, sha256=digest).encode("utf-8")
        + b"\n"
        + source
        + separator
        + END_MARKER.format(name=name).encode("utf-8")
        + b"\n"
    )


def check_module_names(names: list[str]) -> None:
    try:
        known = set(json.loads(INDEX_JSON.read_text(encoding="utf-8"))["modules"])
    except (OSError, ValueError, KeyError) as error:
        raise AssemblyError(f"cannot read the module list from {INDEX_JSON}: {error}") from error
    unknown = [name for name in names if name not in known]
    if unknown:
        raise AssemblyError(
            "not one of the nine modules: " + ", ".join(unknown) + " (known: " + ", ".join(sorted(known)) + ")"
        )


def check_pack_path(pack_dir: Path) -> Path:
    # The Bash allow rule lets this command run without a prompt, so the script keeps its own
    # blast radius small: it only rewrites {VAULT}/packs/<pack>/pack.md.
    if pack_dir.resolve().parent.name != "packs":
        raise AssemblyError(f"{pack_dir} is not a pack directory ({{VAULT}}/packs/<pack>/)")
    pack_md = pack_dir / "pack.md"
    if pack_md.is_symlink():
        raise AssemblyError(f"{pack_md} is a symlink; refusing to read or replace it")
    if not pack_md.is_file():
        raise AssemblyError(f"{pack_md} not found; Write pack.md (section 5 title, empty body) first")
    return pack_md


def assemble(pack_md: Path, names: list[str]) -> bytes:
    check_module_names(names)
    data = pack_md.read_bytes()
    five = find_title(data, SECTION_FIVE)
    if five < 0:
        raise AssemblyError(f"{pack_md}: no '## 5. 레퍼런스 원문' title line")
    body_start = data.find(b"\n", five)
    body_start = len(data) if body_start < 0 else body_start + 1
    six = find_title(data, SECTION_SIX, body_start)
    body_end = len(data) if six < 0 else six
    if data[body_start:body_end].strip():
        raise AssemblyError(
            f"{pack_md}: section 5 already has content; Write pack.md again with an empty "
            "section 5 body before assembling (running twice would stack the modules)"
        )

    blocks = b"\n".join(module_block(name) for name in names)
    head = data[:body_start]
    tail = data[body_end:]
    return head + b"\n" + blocks + (b"\n" if tail else b"") + tail


def permission_rule() -> dict:
    # Claude Code matches Bash rules against the command text; everything before the trailing
    # " *" must be written exactly as the armorer runs it: python3 {SCRIPTS_DIR}/assemble-pack.py,
    # where {SCRIPTS_DIR} is the symlink-resolved absolute path. A space in that path splits the
    # command into different words, so no prefix rule would match it.
    script = str(Path(__file__).resolve())
    return {
        "permission_rule": f"Bash(python3 {script} *)",
        "permission_rule_effective": not any(char.isspace() for char in script),
        "script": script,
    }


def write_atomically(path: Path, data: bytes) -> None:
    mode = path.stat().st_mode & 0o7777
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".pack-", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        # mkstemp creates 0600; keep the mode the Write tool gave pack.md.
        os.chmod(temp, mode)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill pack.md section 5 with verbatim modules.")
    parser.add_argument("--pack-dir", type=Path, help="pack directory holding the Written pack.md")
    parser.add_argument("--modules", nargs="+", metavar="NAME", help="module file names, e.g. core-engines.md")
    parser.add_argument(
        "--permission-rule",
        action="store_true",
        help="print the Bash allow rule for this script as JSON and exit",
    )
    arguments = parser.parse_args()
    if not arguments.permission_rule and (arguments.pack_dir is None or not arguments.modules):
        parser.error("--pack-dir and --modules are required unless --permission-rule is given")
    return arguments


def main() -> int:
    arguments = parse_arguments()
    if arguments.permission_rule:
        print(json.dumps(permission_rule(), ensure_ascii=False))
        return 0
    try:
        pack_md = check_pack_path(arguments.pack_dir)
        data = assemble(pack_md, list(arguments.modules))
        write_atomically(pack_md, data)
    except (AssemblyError, OSError) as error:
        print(f"assemble-pack: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "pack": str(pack_md),
                "modules": list(arguments.modules),
                "bytes": len(data),
                "est_tokens_pack": round(len(data) / TOKEN_DIVISOR),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
