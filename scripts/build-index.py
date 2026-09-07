#!/usr/bin/env python3
"""Build the SmartThink mental-model reference index.

SKILL.md consumes this file to estimate arming-gate token cost from reference size.
check-structure.py also uses the stored SHA-256 values to verify pack-source integrity.
Only the nine immutable mental-model modules are indexed; procedure documents are excluded.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, NotRequired, TypedDict

TOKEN_DIVISOR: Final = 2.2
MODULE_FILENAMES: Final = (
    "anti-fragile-strategy.md",
    "cognitive-arsenal.md",
    "core-engines.md",
    "execution-velocity.md",
    "meta-cognition.md",
    "pattern-synthesis.md",
    "reality-distortion.md",
    "triz-innovation.md",
    "unicorn-playbook.md",
)
REPO_ROOT: Final = Path(__file__).resolve().parent.parent
REFERENCES_DIR: Final = REPO_ROOT / "skills" / "smartthink" / "references"
DEFAULT_OUTPUT: Final = REFERENCES_DIR / "index.json"


class ModuleEntry(TypedDict):
    """A fixed integrity and cost record for one reference module."""

    bytes: int
    est_tokens: int
    sha256: str
    title: str


class Totals(TypedDict):
    """Aggregate reference-module counts used by the gate."""

    bytes: int
    count: int
    est_tokens: int


class IndexDocument(TypedDict):
    """The complete serialized reference index."""

    generated: str
    modules: dict[str, ModuleEntry]
    schema: int
    token_divisor: float
    totals: Totals


class ComparableIndex(TypedDict):
    """Index fields which must remain stable between equivalent builds."""

    modules: dict[str, ModuleEntry]
    schema: int
    token_divisor: float
    totals: Totals
    generated: NotRequired[str]


def first_title(contents: bytes, filename: str) -> str:
    """Return the first level-one Markdown heading, or the filename as fallback."""
    for line in contents.decode("utf-8", errors="replace").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return filename


def build_document() -> IndexDocument | None:
    """Read the fixed modules and create the index payload, or report missing inputs."""
    missing_paths = [REFERENCES_DIR / filename for filename in MODULE_FILENAMES]
    missing_paths = [path for path in missing_paths if not path.is_file()]
    if missing_paths:
        joined_paths = ", ".join(str(path.relative_to(REPO_ROOT)) for path in missing_paths)
        print(f"error: required reference module(s) missing: {joined_paths}", file=sys.stderr)
        return None

    modules: dict[str, ModuleEntry] = {}
    total_bytes = 0
    total_tokens = 0
    for filename in MODULE_FILENAMES:
        contents = (REFERENCES_DIR / filename).read_bytes()
        byte_count = len(contents)
        estimated_tokens = round(byte_count / TOKEN_DIVISOR)
        modules[filename] = {
            "bytes": byte_count,
            "est_tokens": estimated_tokens,
            "sha256": hashlib.sha256(contents).hexdigest(),
            "title": first_title(contents, filename),
        }
        total_bytes += byte_count
        total_tokens += estimated_tokens

    return {
        "schema": 1,
        "generated": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "token_divisor": TOKEN_DIVISOR,
        "modules": modules,
        "totals": {
            "bytes": total_bytes,
            "est_tokens": total_tokens,
            "count": len(MODULE_FILENAMES),
        },
    }


def comparable_document(document: IndexDocument) -> ComparableIndex:
    """Remove the wall-clock field used only to identify the latest generation."""
    return {
        "schema": document["schema"],
        "token_divisor": document["token_divisor"],
        "modules": document["modules"],
        "totals": document["totals"],
    }


def render_json(value: IndexDocument | ComparableIndex) -> str:
    """Serialize JSON in the stable format committed to the repository."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def check_output(output_path: Path, expected: IndexDocument) -> int:
    """Compare an existing index with a fresh build, ignoring its timestamp."""
    try:
        current = json.loads(output_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        current_text = "<missing index.json>\n"
    except json.JSONDecodeError as error:
        current_text = f"<invalid JSON: {error}>\n"
    else:
        if isinstance(current, dict):
            current.pop("generated", None)
            current_text = json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        else:
            current_text = "<invalid index.json root: expected an object>\n"

    expected_text = render_json(comparable_document(expected))
    if current_text == expected_text:
        return 0

    print(f"error: {output_path} does not match a fresh index build (excluding generated)", file=sys.stderr)
    print(
        "".join(
            difflib.unified_diff(
                current_text.splitlines(keepends=True),
                expected_text.splitlines(keepends=True),
                fromfile=str(output_path),
                tofile="fresh build",
            )
        ),
        file=sys.stderr,
        end="",
    )
    return 1


def parse_arguments() -> argparse.Namespace:
    """Parse the output target and the non-mutating CI check option."""
    parser = argparse.ArgumentParser(description="Build SmartThink's reference cost and integrity index.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="write or check this index path (default: %(default)s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare an existing index with a fresh build without writing",
    )
    return parser.parse_args()


def main() -> int:
    """Build the index or validate the existing output against current references."""
    arguments = parse_arguments()
    document = build_document()
    if document is None:
        return 1

    output_path: Path = arguments.out
    if arguments.check:
        return check_output(output_path, document)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_json(document), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
