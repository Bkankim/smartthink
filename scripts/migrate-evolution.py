#!/usr/bin/env python3
"""Convert legacy evolution-state prose into the structured v3 format.

The retain procedure invokes this tool immediately before its first v3 write.
It backs up a legacy file before replacing it and leaves already-v3 files untouched.
Legacy prose is preserved; only data promoted into the YAML header is removed.
Running without --write is a dry run: the conversion is reported and nothing is
written. Pass --write to back up the original and convert it in place.

The script owns the backup, so no manual copy is needed. If a backup already
exists at evolution-state.v2.bak.md and is byte identical to the original, it is
kept and the conversion proceeds, so a manual copy made beforehand is not an
error. A backup that differs from the original is a conflict: the run stops
without touching either file until --force replaces it.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

BACKUP_NAME: Final = "evolution-state.v2.bak.md"
MODULE_NAMES: Final = {
    "핵심 엔진": "core-engines",
    "유니콘 플레이북": "unicorn-playbook",
    "현실 왜곡": "reality-distortion",
    "인지 무기고": "cognitive-arsenal",
    "패턴 합성": "pattern-synthesis",
    "실행 속도": "execution-velocity",
    "안티프래질 전략": "anti-fragile-strategy",
    "triz 혁신 시스템": "triz-innovation",
    "메타인지": "meta-cognition",
}
MODULE_SLUGS: Final = frozenset(MODULE_NAMES.values())
HEADING_PATTERN: Final = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
SESSION_PATTERN: Final = re.compile(r"\[s(\d+)\s+r\d+\]")
DIVERSITY_PATTERN: Final = re.compile(r"다양성\s+H(?:\s*[=≈:]\s*|\s+)([0-9]+(?:\.[0-9]+)?)")


@dataclass(frozen=True, slots=True)
class Section:
    # One level-two Markdown section from a legacy document.

    heading: str
    content: str


@dataclass(frozen=True, slots=True)
class Migration:
    # The rendered document and the facts recovered from legacy prose.

    content: str
    sessions: int
    diversity: float
    diversity_source: str
    weights: dict[str, dict[str, int]]
    unknown_modules: tuple[str, ...]
    insights: int
    gaps: int
    section_titles: tuple[str, ...]


def parse_arguments() -> argparse.Namespace:
    # Parse the target path and the migration options; writing is opt-in.
    parser = argparse.ArgumentParser(
        description=(
            "Convert a legacy evolution-state.md file to v3. Without --write this is a dry run. "
            "--write creates the evolution-state.v2.bak.md backup itself; an existing backup that "
            "matches the original is kept and the conversion continues, while one that differs stops "
            "the run until --force replaces it."
        )
    )
    parser.add_argument("path", nargs="?", type=Path, help="path to evolution-state.md")
    parser.add_argument("--write", action="store_true", help="back up the original and convert it in place")
    parser.add_argument("--dry-run", action="store_true", help="accepted for compatibility; a dry run is the default")
    parser.add_argument("--force", action="store_true", help="replace a v2 backup that differs from the original")
    return parser.parse_args()


def resolve_path(argument: Path | None) -> Path | None:
    # Return the explicit target or the first existing default vault target.
    if argument is not None:
        return argument
    vault = os.environ.get("SMARTTHINK_VAULT")
    candidates = [Path(vault) / "evolution-state.md"] if vault else []
    candidates.append(Path.home() / ".claude" / "smartthink-vault" / "evolution-state.md")
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def split_sections(text: str) -> tuple[str, tuple[Section, ...]]:
    # Split prose into its prefix and all level-two sections without loss.
    matches = tuple(HEADING_PATTERN.finditer(text))
    prefix = text[: matches[0].start()] if matches else text
    sections = tuple(
        Section(match.group(1), text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)])
        for index, match in enumerate(matches)
    )
    return prefix, sections


def normalize_module(value: str) -> str | None:
    # Map a legacy display name or slug to one of the nine canonical module keys.
    compact = re.sub(r"\s+", " ", value.strip().strip("*-`"))
    lowered = compact.casefold()
    if lowered in MODULE_SLUGS:
        return lowered
    return MODULE_NAMES.get(compact) or MODULE_NAMES.get(lowered)


def extract_history(section: Section) -> tuple[int, dict[str, dict[str, int]], tuple[str, ...], bool]:
    # Recover sessions and typed module counts from a permissive Markdown table.
    rows = [line for line in section.content.splitlines() if line.lstrip().startswith("|")]
    if len(rows) < 2:
        return 0, {}, (), False
    headers = [cell.strip() for cell in rows[0].strip().strip("|").split("|")]
    session_index = next((index for index, cell in enumerate(headers) if "세션" in cell), None)
    module_index = next((index for index, cell in enumerate(headers) if "모듈" in cell), None)
    class_index = next((index for index, cell in enumerate(headers) if "분류" in cell or "사고 유형" in cell), None)
    if session_index is None or module_index is None:
        return 0, {}, (), False
    maximum = 0
    weights: dict[str, dict[str, int]] = {}
    unknown: list[str] = []
    for row in rows[1:]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if all(re.fullmatch(r"[: -]+", cell) for cell in cells):
            continue
        if len(cells) <= max(session_index, module_index):
            continue
        if cells[session_index].isdigit():
            maximum = max(maximum, int(cells[session_index]))
        if class_index is None or len(cells) <= class_index or not cells[class_index]:
            continue
        classification = re.sub(r"\s+", "-", cells[class_index])
        bucket = weights.setdefault(classification, {})
        for name in re.split(r"[,/·;]", cells[module_index]):
            module = normalize_module(name)
            if module is None:
                if name.strip() and name.strip() not in {"-", "없음"}:
                    unknown.append(name.strip())
                continue
            bucket[module] = min(10, bucket.get(module, 0) + 1)
    return maximum, weights, tuple(dict.fromkeys(unknown)), class_index is not None


def calculate_diversity(weights: dict[str, dict[str, int]]) -> float:
    # Calculate Shannon entropy from the recovered routing weights.
    totals: dict[str, int] = {}
    for bucket in weights.values():
        for module, weight in bucket.items():
            totals[module] = totals.get(module, 0) + weight
    total = sum(totals.values())
    if total == 0:
        return 0.0
    return round(-sum((weight / total) * math.log(weight / total) for weight in totals.values()), 2)


def render_weights(weights: dict[str, dict[str, int]]) -> str:
    # Render routing weights without a YAML dependency.
    if not weights:
        return "routing_weights: {}\n"
    lines = ["routing_weights:"]
    for classification, modules in weights.items():
        lines.append(f"  {json.dumps(classification, ensure_ascii=False)}:")
        lines.extend(f"    {module}: {weight:.2f}" for module, weight in modules.items())
    return "\n".join(lines) + "\n"


def build_migration(source: str) -> Migration | None:
    # Promote recoverable legacy data into a v3 header while preserving prose.
    prefix, sections = split_sections(source)
    recognized = False
    history_sessions = 0
    weights: dict[str, dict[str, int]] = {}
    unknown_modules: tuple[str, ...] = ()
    history_has_classification = False
    diversity_value: float | None = None
    diversity_heading_found = False
    body = prefix
    insight_count = 0
    gap_count = 0
    section_titles: list[str] = []
    for section in sections:
        heading = section.heading.strip()
        output_heading = heading
        output_content = section.content
        if heading.startswith("모듈 사용 이력"):
            recognized = True
            history_sessions, weights, unknown_modules, history_has_classification = extract_history(section)
        diversity_match = DIVERSITY_PATTERN.search(heading)
        if heading.startswith("다양성"):
            recognized = True
            diversity_heading_found = True
            if diversity_match:
                diversity_value, output_heading = float(diversity_match.group(1)), "다양성"
                origin_match = re.search(r"원천:\s*(.+)$", heading)
                if origin_match:
                    output_content = f"\n원천: {origin_match.group(1)}" + section.content
        if heading.startswith("핵심 인사이트"):
            recognized, insight_count = True, sum(1 for line in section.content.splitlines() if re.match(r"^\s*-\s+", line))
        if heading.startswith("활성 갭"):
            recognized, gap_count = True, sum(1 for line in section.content.splitlines() if re.match(r"^\s*-\s+", line))
        if heading.startswith("진화 액션"):
            recognized, remainder = True, heading.removeprefix("진화 액션").lstrip(": ")
            output_heading = "진화 액션"
            output_content = (f"\n{remainder}" if remainder else "") + section.content
        body += f"## {output_heading}{output_content}"
        section_titles.append(output_heading)
    if not recognized:
        return None
    freshness_sessions = [int(match.group(1)) for match in SESSION_PATTERN.finditer(source)]
    sessions = max([history_sessions, *freshness_sessions], default=0)
    if not history_has_classification:
        weights = {}
    diversity = diversity_value if diversity_value is not None else calculate_diversity(weights)
    diversity_source = "legacy diversity heading" if diversity_value is not None else "warning: diversity heading found but numeric value was not parsed" if diversity_heading_found else "no diversity heading; recalculated routing weights"
    updated = datetime.now().astimezone().isoformat(timespec="seconds")
    header = f"---\nversion: 3\nupdated: {updated}\nsessions: {sessions}\ndiversity_h: {diversity:.2f}\n"
    return Migration(header + render_weights(weights) + "---\n" + body.lstrip("\n"), sessions, diversity, diversity_source, weights, unknown_modules, insight_count, gap_count, tuple(section_titles))


def write_bytes(path: Path, content: bytes) -> None:
    # Atomically replace a file in its own directory.
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temporary_path, path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def classify_backup(backup: Path, original: bytes) -> str:
    # Decide what a --write run does with the backup: create, keep, or refuse.
    if not backup.exists():
        return "create"
    try:
        return "keep" if backup.read_bytes() == original else "conflict"
    except OSError:
        return "conflict"


def write_command(target: Path, backup_state: str) -> str:
    # Build the exact command that performs the write this dry run only described.
    parts = ["python3", "scripts/migrate-evolution.py", shlex.quote(str(target)), "--write"]
    if backup_state in {"conflict", "replace"}:
        parts.append("--force")
    return " ".join(parts)


def describe_backup(backup: Path, backup_state: str, dry_run: bool) -> str:
    # Describe the backup outcome in the same words for dry runs and real writes.
    if backup_state == "keep":
        return f"{'would keep' if dry_run else 'kept'} the existing {backup} (byte identical to the original)"
    if backup_state == "conflict":
        return f"{backup} exists and differs from the original; --force is needed to replace it"
    if backup_state == "replace":
        return f"{'would replace' if dry_run else 'replaced'} {backup} (--force; the previous backup differed from the original)"
    return f"{'would create' if dry_run else 'created'} {backup}"


def report(target: Path, backup: Path, migration: Migration, dry_run: bool, backup_state: str) -> None:
    # Print a human-readable account of recovered and unavailable legacy data.
    print(f"target: {target}")
    print(f"backup: {describe_backup(backup, backup_state, dry_run)}")
    print(f"sessions: {migration.sessions} (legacy history or freshness tags; 0 means no evidence)")
    print(f"diversity_h: {migration.diversity:.2f} ({migration.diversity_source})")
    print("preserved sections: " + ", ".join(migration.section_titles))
    if migration.weights:
        print(f"routing_weights: recovered {sum(len(bucket) for bucket in migration.weights.values())} module weights")
    else:
        print("routing_weights: not recovered; legacy history has no usable classification/module pairs, so future retain runs will populate it")
    if migration.unknown_modules:
        print("unrecognized module labels: " + ", ".join(migration.unknown_modules))
    if migration.insights > 10 or migration.gaps > 5:
        print(f"slot overflow preserved without deletion: insights={migration.insights}, gaps={migration.gaps}")
    if dry_run:
        if backup_state == "conflict":
            print(f"warning: the backup at {backup} differs from the original; writing needs --force to replace it")
        print("dry-run: no files were written\n")
        print(migration.content, end="" if migration.content.endswith("\n") else "\n")
        print(f"\nto write this conversion, run: {write_command(target, backup_state)}")


def main() -> int:
    """Run the migration and return the documented process exit code."""
    arguments = parse_arguments()
    target = resolve_path(arguments.path)
    if target is None:
        print("error: provide evolution-state.md or set SMARTTHINK_VAULT to an existing vault", file=sys.stderr)
        return 2
    try:
        original = target.read_bytes()
    except OSError as error:
        print(f"error: cannot read {target}: {error}", file=sys.stderr)
        return 1
    if original.splitlines()[:1] == [b"---"]:
        print(f"already v3: {target}")
        return 0
    try:
        migration = build_migration(original.decode("utf-8"))
    except UnicodeDecodeError as error:
        print(f"error: {target} is not UTF-8: {error}", file=sys.stderr)
        return 1
    if migration is None:
        print("error: no legacy evolution sections were parsed; original file was left unchanged", file=sys.stderr)
        return 1
    backup = target.with_name(BACKUP_NAME)
    backup_state = classify_backup(backup, original)
    if backup_state == "conflict" and arguments.force:
        backup_state = "replace"
    if not arguments.write:
        report(target, backup, migration, True, backup_state)
        return 0
    if backup_state == "conflict" and not arguments.force:
        print(
            f"error: the backup at {backup} exists and does not match {target}; "
            "it holds a different original, so nothing was written. "
            "Rename it if you want to keep it, or rerun with --force to replace it",
            file=sys.stderr,
        )
        return 1
    if backup_state != "keep":
        try:
            write_bytes(backup, original)
        except OSError as error:
            print(f"error: backup failed at {backup}; original was not converted: {error}", file=sys.stderr)
            return 1
    try:
        write_bytes(target, migration.content.encode("utf-8"))
    except OSError as error:
        print(f"error: conversion write failed after backup at {backup}: {error}", file=sys.stderr)
        return 1
    report(target, backup, migration, False, backup_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
