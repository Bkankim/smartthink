#!/usr/bin/env python3
"""SmartThink v3 integration gate.

This checker guards four contracts that no single file can guarantee on its own:
  1. Plugin layout - the paths and plugin.json keys a Claude Code plugin needs to load.
  2. Reference integrity - the nine mental-model modules are frozen, and
     references/index.json must state their real SHA-256 and token estimate.
  3. Wiring contract - SKILL.md, agents/st-armorer.md, agents/st-thinker.md and
     references/thinker-prompt.md must agree on the pack section titles, the manifest
     fields, the spawned sub-agent names and the fallback prompt. A silent divergence
     here is the failure mode this script exists to catch.
  4. v3 schema and hygiene - the .data seed templates, the removal of v2 leftovers, and
     no em dashes or private paths in a public repository.
With --pack it also validates a real armory pack, including verbatim hash integrity of
the module blocks copied into section 5.

Usage:
  python3 scripts/check-structure.py [--verbose] [--strict] [--pack DIR] [--digest]

Exit code is 1 if any check FAILs, else 0, across every group. Checks that depend on a
file another worker still owns report SKIP; --strict promotes those to FAIL for the final
gate. SKIPs that merely mean "you did not ask for this" (the pack group without --pack)
are never promoted.

The summary prints two lines: the repo-wide tally, then a "pack: N passed, M failed,
K skipped" line counting only the H group, so a gate that cares about one pack can judge
that line instead of the exit code. Style checks (em dash) skip tests/evidence, which
holds verbatim captures rather than editable prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import traceback
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SKILL_DIR = REPO_ROOT / "skills" / "smartthink"
REFERENCES_DIR = SKILL_DIR / "references"
DATA_DIR = SKILL_DIR / ".data"
AGENTS_DIR = REPO_ROOT / "agents"

SKILL_MD = SKILL_DIR / "SKILL.md"
ARMORER_MD = AGENTS_DIR / "st-armorer.md"
THINKER_MD = AGENTS_DIR / "st-thinker.md"
THINKER_PROMPT_MD = REFERENCES_DIR / "thinker-prompt.md"
ARMORER_PROMPT_MD = REFERENCES_DIR / "armorer-prompt.md"
ANALYSIS_METHOD_MD = REFERENCES_DIR / "analysis-method.md"
INDEX_JSON = REFERENCES_DIR / "index.json"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"

# The nine mental-model modules. v3 freezes their content, so they are also
# exempt from the em dash rule below: fixing their punctuation would break every hash.
MODULES = (
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

TOKEN_DIVISOR = 2.2

PACK_SECTIONS = (
    "## 1. 무장 브리핑",
    "## 2. 작업 해석",
    "## 3. 리서치 합성",
    "## 4. 작업 적용 레이어",
    "## 5. 레퍼런스 원문",
    "## 6. 과거 인사이트와 프로필",
)

MANIFEST_FIELDS = (
    "task",
    "interpretation",
    "cynefin",
    "classification",
    "modules",
    "budget",
    "research",
    "profile_version",
    "est_tokens",
    "created",
    "harness",
)

THINKER_PROMPT_VARS = {"PACK_PATH", "MANIFEST_PATH", "TASK", "SKILL_DIR", "VAULT"}
V2_PROMPT_VARS = (
    "TOPIC",
    "CYNEFIN",
    "CLASSIFICATION",
    "SELECTED_MODULES",
    "SELECTED_ENGINES",
    "SEARCH_DATA",
    "SEARCH_MODE",
    "EVOLUTION_STATE",
)

# Instructions that must stay identical between the agent definition and its fallback
# prompt. If one side drifts, the environment without agents/ silently behaves differently.
THINKER_SYNC_RULES = (
    ("Step 5 runs only after the confirmation signal", r"확정.{0,3}\s*신호를\s*받은\s*뒤에만"),
    ("no duplicate module loading", r"중복\s*로딩\s*금지"),
    ("references the fixed pack section structure", r"pack\.md\s*절\s*구조"),
    ("30-turn budget", r"30\s*턴"),
)

# Same idea for the armorer: references/armorer-prompt.md is what general-purpose receives
# when no st-armorer definition resolves. What is checked is a sync of key-instruction regexes
# (plus the section titles and manifest fields elsewhere), not a full-body diff.
# Its only substitution slots are the three Path Variables of the SKILL.md 5a Input block
# ({SCRIPTS_DIR} since #21: the armorer calls assemble-pack.py by its absolute path).
ARMORER_PROMPT_VARS = {"SKILL_DIR", "SCRIPTS_DIR", "VAULT"}
ARMORER_SYNC_RULES = (
    ("returns only the manifest summary", r"manifest\s*요약만\s*\**\s*반환"),
    ("never returns the pack body", r"팩\s*본문\s*반환\s*금지"),
    ("section 5 copied byte-for-byte by assemble-pack.py", r"assemble-pack\.py로\s*바이트를\s*이어\s*붙여라"),
    ("single Write to pack.md", r"pack\.md에\s*대한\s*Write는\s*한\s*번뿐"),
    ("research only after reading the references", r"레퍼런스를\s*먼저\s*읽은\s*뒤에\s*검색"),
    # Anchored to the body line "턴 예산 40턴." so the fallback preamble's "40턴을" cannot satisfy it.
    ("40-turn budget", r"턴\s*예산\s*40\s*턴\."),
    ("browser lane capped at three calls per run", r"브라우저\s*호출은\s*한\s*런에\s*최대\s*3회"),
)

# Files another worker still owns. A missing or stale entry here reports SKIP instead of
# FAIL so parallel waves stay green. Empty this set before the release gate; --strict
# promotes every one of these to FAIL in the meantime.
PENDING_PATHS = frozenset(
    {
        "scripts/migrate-evolution.py",  # evolution-state v2 to v3 migration, not written yet
    }
)

REQUIRED_PATHS = (
    ".claude-plugin/plugin.json",
    "skills/smartthink/SKILL.md",
    "skills/smartthink/references",
    "agents",
    "commands/st.md",
    "scripts",
    "tests/gates.md",
    "install.sh",
    "uninstall.sh",
    "scripts/resolve-vault.py",
    "LICENSE",
)

PLUGIN_JSON_KEYS = ("name", "version", "description", "author")

# Written as an escape so this file does not match its own scan.
EM_DASH = "\u2014"

# Tool and runtime caches: never part of the shipped plugin, never scanned.
EXCLUDED_DIRS = frozenset({".git", ".ruff_cache", ".fablize", "__pycache__", "node_modules"})

# Gate evidence is a verbatim capture of what a run produced: pack copies quote the frozen
# modules and transcripts quote model output, so editing it to satisfy a style rule would
# destroy the very thing it is evidence of. Style checks skip the whole directory.
VERBATIM_EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence"

# Patterns are assembled from fragments on purpose: writing them as single literals would
# make this file match its own scan and report a false hit.
PRIVATE_PATTERNS = (
    ("gvai" + "develop", "maintainer account handle"),
    ("bkan" + "-hq", "private host / org name"),
    ("workspace/" + "vault", "private vault path"),
    ("/Users" + "/", "hardcoded absolute home path"),
    ("smartthink-v3" + ".md", "private design document"),
)

# Prose that records the removal of a v2 feature is fine; wiring that still uses it is not.
ABOLITION_WORDS = ("폐지", "삭제", "제거", "없어졌", "사라졌", "abolish", "deprecat", "removed", "absorbed")

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"


# --------------------------------------------------------------------------- helpers


@dataclass
class Result:
    """Outcome of one check."""

    status: str
    detail: str = ""
    evidence: list[str] = field(default_factory=list)
    promotable: bool = True  # a SKIP that --strict may turn into a FAIL


def ok(detail: str = "", evidence: list[str] | None = None) -> Result:
    return Result(STATUS_PASS, detail, evidence or [])


def bad(detail: str, evidence: list[str] | None = None) -> Result:
    return Result(STATUS_FAIL, detail, evidence or [])


def skip(detail: str, evidence: list[str] | None = None, promotable: bool = True) -> Result:
    return Result(STATUS_SKIP, detail, evidence or [], promotable)


def rel(path: Path) -> str:
    """Repo-relative path for messages, so output is identical from any CWD."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def est_tokens(size: int) -> int:
    return round(size / TOKEN_DIVISOR)


def line_of(text: str, index: int) -> int:
    """1-indexed line number of a character offset, for actionable FAIL messages."""
    return text.count("\n", 0, index) + 1


def find_lines(text: str, needle: str) -> list[int]:
    lines = []
    for number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            lines.append(number)
    return lines


def is_pending(path: Path) -> bool:
    return rel(path) in PENDING_PATHS


# ------------------------------------------------------------------ frontmatter parser


def _scalar(raw: str):
    """Coerce one YAML scalar. Only the forms this repo actually uses."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def _parse_map(lines: list[str]) -> dict:
    """Parse the subset of YAML this repo writes: key: value, nested maps, {}, # comments."""
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    index = 0
    total = len(lines)

    while index < total:
        raw = lines[index]
        index += 1
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = re.match(r"^([A-Za-z_][\w.-]*)\s*:\s*(.*)$", stripped)
        if match is None:
            continue

        indent = len(raw) - len(raw.lstrip(" "))
        key, value = match.group(1), match.group(2).strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value in (">", "|", ">-", "|-", ">+", "|+"):
            block: list[str] = []
            while index < total:
                nxt = lines[index]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip(" "))) <= indent:
                    break
                block.append(nxt.strip())
                index += 1
            parent[key] = " ".join(part for part in block if part)
        elif value == "{}":
            parent[key] = {}
        elif value == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value)

    return root


def parse_frontmatter(text: str) -> dict | None:
    """Return the frontmatter map, or None when the file has no delimited frontmatter."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for position in range(1, len(lines)):
        if lines[position].strip() == "---":
            return _parse_map(lines[1:position])
    return None


def load_frontmatter(path: Path) -> tuple[dict | None, str | None]:
    text = read_text(path)
    if text is None:
        return None, f"{rel(path)} is unreadable or missing"
    front = parse_frontmatter(text)
    if front is None:
        return None, f"{rel(path)} has no '---' delimited frontmatter"
    return front, None


def frontmatter_line(path: Path, key: str) -> str:
    """Best-effort file:line anchor for a frontmatter key, for FAIL messages."""
    text = read_text(path) or ""
    for number, line in enumerate(text.splitlines(), start=1):
        if re.match(rf"^\s*{re.escape(key)}\s*:", line):
            return f"{rel(path)}:{number}"
    return rel(path)


# ------------------------------------------------------------------ A. plugin layout


def check_required_paths() -> Result:
    missing = [candidate for candidate in REQUIRED_PATHS if not (REPO_ROOT / candidate).exists()]
    if missing:
        pending = [item for item in missing if item in PENDING_PATHS]
        hard = [item for item in missing if item not in PENDING_PATHS]
        if hard:
            return bad(
                "missing required path(s): " + ", ".join(hard),
                [f"expected at {REPO_ROOT / item}" for item in hard],
            )
        return skip("not built yet (owned by another worker): " + ", ".join(pending))
    return ok(f"{len(REQUIRED_PATHS)} required paths present", list(REQUIRED_PATHS))


def check_plugin_json() -> Result:
    text = read_text(PLUGIN_JSON)
    if text is None:
        return bad(f"{rel(PLUGIN_JSON)} is missing or unreadable")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return bad(f"{rel(PLUGIN_JSON)}:{error.lineno} is not valid JSON: {error.msg}")
    if not isinstance(data, dict):
        return bad(f"{rel(PLUGIN_JSON)} top level is {type(data).__name__}, expected an object")
    missing = [key for key in PLUGIN_JSON_KEYS if key not in data]
    if missing:
        return bad(
            f"{rel(PLUGIN_JSON)} is missing key(s): " + ", ".join(missing),
            [f"present keys: {', '.join(sorted(data))}"],
        )
    return ok(
        f"valid JSON with {', '.join(PLUGIN_JSON_KEYS)}",
        [f"name={data['name']} version={data['version']}"],
    )


def check_searcher_removed() -> Result:
    searcher = AGENTS_DIR / "st-searcher.md"
    if searcher.exists():
        return bad(
            f"{rel(searcher)} still exists; st-searcher was abolished (absorbed into st-armorer). Delete the file."
        )
    return ok("agents/st-searcher.md is absent as required")


def check_agent_definitions_present() -> Result:
    missing = [rel(path) for path in (ARMORER_MD, THINKER_MD) if not path.exists()]
    if missing:
        return bad("missing agent definition(s): " + ", ".join(missing))
    return ok("st-armorer.md and st-thinker.md present", [rel(ARMORER_MD), rel(THINKER_MD)])


# ------------------------------------------------------- B. reference integrity (frozen modules)


def check_modules_present() -> Result:
    missing = [name for name in MODULES if not (REFERENCES_DIR / name).exists()]
    if missing:
        return bad(
            f"{len(missing)} of {len(MODULES)} mental-model references missing: " + ", ".join(missing),
            [f"expected under {rel(REFERENCES_DIR)}/"],
        )
    return ok(f"all {len(MODULES)} mental-model references present")


def check_index_hashes() -> Result:
    if not INDEX_JSON.exists():
        return skip(f"{rel(INDEX_JSON)} not built yet; run scripts/build-index.py")
    text = read_text(INDEX_JSON)
    if text is None:
        return bad(f"{rel(INDEX_JSON)} is unreadable")
    try:
        index = json.loads(text)
    except json.JSONDecodeError as error:
        return bad(f"{rel(INDEX_JSON)}:{error.lineno} is not valid JSON: {error.msg}")

    modules = index.get("modules")
    if not isinstance(modules, dict):
        return bad(f"{rel(INDEX_JSON)} has no 'modules' object")

    problems: list[str] = []
    evidence: list[str] = []
    for name in MODULES:
        entry = modules.get(name)
        if entry is None:
            problems.append(f"{name}: not registered in {rel(INDEX_JSON)} (re-run scripts/build-index.py)")
            continue
        data = read_bytes(REFERENCES_DIR / name)
        if data is None:
            problems.append(f"{name}: registered in the index but the file is missing on disk")
            continue
        actual = sha256_hex(data)
        declared = entry.get("sha256")
        if declared != actual:
            problems.append(
                f"{name}: sha256 mismatch. index says {declared}, file hashes to {actual}. "
                "Either the reference was modified (frozen content: restore it) or the index is stale "
                "(re-run scripts/build-index.py)."
            )
            continue
        if entry.get("bytes") != len(data):
            problems.append(
                f"{name}: index bytes={entry.get('bytes')} but the file is {len(data)} bytes; the index is stale"
            )
            continue
        evidence.append(f"{name}: {len(data)} bytes, sha256 {actual[:12]}...")

    extra = [name for name in modules if name not in MODULES]
    if extra:
        problems.append(f"{rel(INDEX_JSON)} registers unknown module(s): {', '.join(sorted(extra))}")

    if problems:
        return bad(f"{len(problems)} index problem(s)", problems)
    return ok(f"all {len(MODULES)} modules registered with matching sha256", evidence)


def check_index_token_estimates() -> Result:
    if not INDEX_JSON.exists():
        return skip(f"{rel(INDEX_JSON)} not built yet; run scripts/build-index.py")
    try:
        index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return bad(f"{rel(INDEX_JSON)} could not be parsed: {error}")

    modules = index.get("modules", {})
    problems: list[str] = []
    evidence: list[str] = []
    for name in MODULES:
        entry = modules.get(name)
        if not isinstance(entry, dict):
            continue  # already reported by the sha256 check
        data = read_bytes(REFERENCES_DIR / name)
        if data is None:
            continue
        expected = est_tokens(len(data))
        if entry.get("est_tokens") != expected:
            problems.append(
                f"{name}: est_tokens={entry.get('est_tokens')} but round({len(data)}/{TOKEN_DIVISOR}) "
                f"= {expected}; re-run scripts/build-index.py"
            )
        else:
            evidence.append(f"{name}: est_tokens {expected}")

    divisor = index.get("token_divisor")
    if divisor is not None and abs(float(divisor) - TOKEN_DIVISOR) > 1e-9:
        problems.append(
            f"{rel(INDEX_JSON)} token_divisor={divisor} but the contract fixes it at {TOKEN_DIVISOR}"
        )

    if problems:
        return bad(f"{len(problems)} token estimate problem(s)", problems)
    return ok(f"est_tokens == round(bytes/{TOKEN_DIVISOR}) for all modules", evidence)


# ------------------------------------------------------- C. agent definition contract


def _agent_frontmatter(path: Path) -> tuple[dict | None, Result | None]:
    front, error = load_frontmatter(path)
    if front is None:
        return None, bad(error or f"{rel(path)} frontmatter could not be parsed")
    return front, None


def check_agent_frontmatter_names() -> Result:
    problems: list[str] = []
    evidence: list[str] = []
    for path in (ARMORER_MD, THINKER_MD):
        front, failure = _agent_frontmatter(path)
        if failure is not None:
            problems.append(failure.detail)
            continue
        expected = path.stem
        actual = front.get("name")
        if actual != expected:
            problems.append(
                f"{frontmatter_line(path, 'name')}: name is {actual!r} but the filename requires {expected!r}"
            )
        else:
            evidence.append(f"{rel(path)}: name={actual}")
    if problems:
        return bad("agent name contract broken", problems)
    return ok("both agent definitions parse and their name matches the filename", evidence)


def check_agents_have_no_model() -> Result:
    """Omitting model makes the sub-agent inherit the session model."""
    problems: list[str] = []
    for path in (ARMORER_MD, THINKER_MD):
        front, failure = _agent_frontmatter(path)
        if failure is not None:
            problems.append(failure.detail)
            continue
        if "model" in front:
            problems.append(
                f"{frontmatter_line(path, 'model')}: frontmatter declares model={front['model']!r}. "
                "Remove the key so the agent inherits the session model."
            )
    if problems:
        return bad("model field present", problems)
    return ok("neither definition pins a model (session inheritance holds)")


def check_agents_have_no_skills_preload() -> Result:
    """A skills: preload breaks in environments where the skill is not installed."""
    problems: list[str] = []
    for path in (ARMORER_MD, THINKER_MD):
        front, failure = _agent_frontmatter(path)
        if failure is not None:
            problems.append(failure.detail)
            continue
        if "skills" in front:
            problems.append(
                f"{frontmatter_line(path, 'skills')}: frontmatter declares skills={front['skills']!r}. "
                "The preload was removed; detect the skill at runtime instead."
            )
    if problems:
        return bad("skills preload present", problems)
    return ok("neither definition preloads skills")


def _check_agent_budget(path: Path, effort: str, max_turns: int, decision: str) -> Result:
    front, failure = _agent_frontmatter(path)
    if failure is not None:
        return failure
    problems: list[str] = []
    if front.get("effort") != effort:
        problems.append(
            f"{frontmatter_line(path, 'effort')}: effort is {front.get('effort')!r}, {decision} requires {effort!r}"
        )
    if front.get("maxTurns") != max_turns:
        problems.append(
            f"{frontmatter_line(path, 'maxTurns')}: maxTurns is {front.get('maxTurns')!r}, "
            f"{decision} requires {max_turns}"
        )
    if problems:
        return bad(f"{rel(path)} budget contract broken", problems)
    return ok(f"{rel(path)}: effort={effort}, maxTurns={max_turns} ({decision})")


def check_thinker_budget() -> Result:
    return _check_agent_budget(THINKER_MD, "xhigh", 30, "contract")


def check_armorer_budget() -> Result:
    return _check_agent_budget(ARMORER_MD, "high", 40, "contract")


def _tool_list(front: dict) -> list[str]:
    raw = front.get("tools")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw]
    return []


def check_armorer_has_search_tools() -> Result:
    """Research was absorbed into the armorer, so it needs the web tools."""
    front, failure = _agent_frontmatter(ARMORER_MD)
    if failure is not None:
        return failure
    tools = _tool_list(front)
    missing = [name for name in ("WebSearch", "WebFetch") if name not in tools]
    if missing:
        return bad(
            f"{frontmatter_line(ARMORER_MD, 'tools')}: tools is missing {', '.join(missing)}. "
            "st-armorer is the research owner.",
            [f"declared tools: {', '.join(tools) or '(none)'}"],
        )
    return ok("st-armorer declares WebSearch and WebFetch", [f"tools: {', '.join(tools)}"])


def check_thinker_has_no_search_tools() -> Result:
    """Pack section 3 owns research; the thinker must not search on its own."""
    front, failure = _agent_frontmatter(THINKER_MD)
    if failure is not None:
        return failure
    tools = _tool_list(front)
    present = [name for name in ("WebSearch", "WebFetch") if name in tools]
    if present:
        return bad(
            f"{frontmatter_line(THINKER_MD, 'tools')}: tools declares {', '.join(present)}. "
            "Research belongs to pack section 3 (produced by st-armorer); remove the search tools.",
            [f"declared tools: {', '.join(tools)}"],
        )
    return ok("st-thinker declares no search tools", [f"tools: {', '.join(tools)}"])


# ------------------------------------------------------------- D. wiring contract


def _title_lines(text: str, title: str) -> list[int]:
    """Lines that are exactly this heading. A heading with extra words is a different
    heading, so substring matching would miss the drift this check exists to catch."""
    pattern = re.compile("^" + re.escape(title) + r"[ \t]*$", re.M)
    return [line_of(text, match.start()) for match in pattern.finditer(text)]


def check_pack_section_titles() -> Result:
    """The single most load-bearing shared string set between SKILL.md, st-armorer.md and its
    fallback prompt (general-purpose writes the pack from the fallback when no definition resolves)."""
    sources = {}
    for path in (SKILL_MD, ARMORER_MD, ARMORER_PROMPT_MD):
        text = read_text(path)
        if text is None:
            return bad(f"{rel(path)} is missing or unreadable")
        sources[path] = text

    problems: list[str] = []
    evidence: list[str] = []
    for title in PACK_SECTIONS:
        hits = {path: _title_lines(text, title) for path, text in sources.items()}
        absent = [path for path, lines in hits.items() if not lines]
        if absent:
            for path in absent:
                # A near miss (the title inside a longer heading) is the usual drift.
                near = [
                    f"{rel(path)}:{number}: {line.strip()}"
                    for number, line in enumerate(sources[path].splitlines(), start=1)
                    if title in line and line.strip() != title
                ]
                message = f"{title!r} is not a standalone heading line in {rel(path)}"
                if near:
                    message += "; closest line(s): " + " | ".join(near[:2])
                present = [rel(other) for other, lines in hits.items() if lines]
                if present:
                    message += f" (it is correct in {', '.join(present)})"
                problems.append(message)
        else:
            anchors = [f"{rel(path)}:{lines[0]}" for path, lines in hits.items()]
            evidence.append(f"{title} -> {', '.join(anchors)}")

    if problems:
        return bad(
            f"{len(problems)} of {len(PACK_SECTIONS)} pack section titles are not shared verbatim",
            problems + ["every file must contain the exact same 6 strings; a near-miss breaks pack parsing"],
        )
    return ok(f"all 6 pack section titles appear verbatim in all {len(sources)} files", evidence)


def check_manifest_fields_shared() -> Result:
    sources = {}
    for path in (SKILL_MD, ARMORER_MD, ARMORER_PROMPT_MD):
        text = read_text(path)
        if text is None:
            return bad(f"{rel(path)} is missing or unreadable")
        sources[path] = text

    problems: list[str] = []
    for name in MANIFEST_FIELDS:
        absent = [rel(path) for path, text in sources.items() if name not in text]
        if absent:
            problems.append(f"manifest field {name!r} is never mentioned in {', '.join(absent)}")
    if problems:
        return bad(
            f"{len(problems)} of {len(MANIFEST_FIELDS)} manifest fields are not described on both sides",
            problems,
        )
    return ok(
        f"all {len(MANIFEST_FIELDS)} manifest fields mentioned in SKILL.md, st-armorer.md "
        "and armorer-prompt.md"
    )


def plugin_namespace() -> str:
    """The prefix a plugin install registers skills and agents under: plugin.json name.

    plugin.json is the SSOT; check_plugin_json validates it separately. If it is
    unreadable this falls back to the directory contract so the namespace checks below
    still report something specific rather than crashing on a second file's problem.
    """
    try:
        data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        name = data.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    except (OSError, ValueError):
        pass
    return "smartthink"


def strip_plugin_namespace(name: str) -> str:
    """'smartthink:st-armorer' names the same definition file as 'st-armorer'."""
    prefix = f"{plugin_namespace()}:"
    return name[len(prefix) :] if name.startswith(prefix) else name


def check_spawned_agents_exist() -> Result:
    text = read_text(SKILL_MD)
    if text is None:
        return bad(f"{rel(SKILL_MD)} is missing or unreadable")
    problems: list[str] = []
    evidence: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r'subagent_type:\s*"([^"]+)"', text):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        if name == "general-purpose":
            evidence.append("general-purpose (built-in fallback, no definition file needed)")
            continue
        # A plugin session registers agents/<bare>.md as "<plugin>:<bare>". Both spellings
        # resolve to the same file, so the prefix comes off before the existence check.
        bare = strip_plugin_namespace(name)
        definition = AGENTS_DIR / f"{bare}.md"
        if not definition.exists():
            problems.append(
                f"{rel(SKILL_MD)}:{line_of(text, match.start())} spawns {name!r} but "
                f"{rel(definition)} does not exist"
            )
        else:
            evidence.append(f"{name} -> {rel(definition)}")
    if not seen:
        return bad(f"{rel(SKILL_MD)} spawns no sub-agent; the armorer path cannot run")
    if problems:
        return bad("SKILL.md spawns an agent with no definition", problems)
    return ok(f"all {len(seen)} spawned sub-agent names resolve", evidence)


def check_namespaced_invocation() -> Result:
    """Plugin-registered names carry the plugin prefix, and the fallback is written down.

    A bare `subagent_type` is not a harmless shorthand: in a plugin session
    `st-armorer` is not found (so the skill wrongly concludes the definition is
    missing and drops to general-purpose), and `st-thinker` silently resolves to a
    same-named user-level definition. Both were measured in gate T2/T11. The prefixed
    name is therefore the canonical spelling, and the one-shot bare-name retry that
    covers non-plugin installs has to be stated in prose, not assumed.
    """
    prefix = f"{plugin_namespace()}:"
    text = read_text(SKILL_MD)
    if text is None:
        return bad(f"{rel(SKILL_MD)} is missing or unreadable")

    problems: list[str] = []
    evidence: list[str] = []

    unprefixed: list[str] = []
    prefixed = 0
    for match in re.finditer(r'subagent_type:\s*"([^"]+)"', text):
        name = match.group(1)
        if name == "general-purpose":
            continue
        if name.startswith(prefix):
            prefixed += 1
        else:
            unprefixed.append(f"{rel(SKILL_MD)}:{line_of(text, match.start())} spawns {name!r}")
    if unprefixed:
        problems.append(
            f"subagent_type must be written as {prefix}<name> so a plugin session resolves it: "
            + "; ".join(unprefixed)
        )
    else:
        evidence.append(f"{prefixed} prefixed subagent_type spawn(s) in {rel(SKILL_MD)}")

    # The retry rule keeps non-plugin installs (install.sh symlinks into ~/.claude/agents)
    # working, so the prefixed name alone is not the whole contract.
    retry_rule = None
    for number, line in enumerate(text.splitlines(), start=1):
        if "bare" in line and re.search(r"1\s*회", line) and "재시도" in line:
            retry_rule = number
            break
    if retry_rule is None:
        problems.append(
            f"{rel(SKILL_MD)} states no one-shot bare-name retry rule; a non-plugin install "
            "registers the bare name only and would fall through to general-purpose"
        )
    else:
        evidence.append(f"{rel(SKILL_MD)}:{retry_rule} bare-name retry rule")

    # Trying the prefixed name first costs a non-plugin install one failed spawn on every
    # run. The harness already lists the registered name, so the list decides first and
    # the retry only covers runtimes that show no list.
    list_first = find_lines(text, "세션 에이전트 목록")
    if not list_first:
        problems.append(
            f"{rel(SKILL_MD)} states no list-first rule (세션 에이전트 목록); a non-plugin "
            "install pays one failed spawn per run before the bare-name retry"
        )
    else:
        evidence.append(f"{rel(SKILL_MD)}:{list_first[0]} list-first name rule")

    # The /st alias is the other half of the same collision: a bare `smartthink` call
    # from a plugin command leaks to whatever else owns that name (gate T11).
    command_md = REPO_ROOT / "commands" / "st.md"
    command_text = read_text(command_md)
    if command_text is None:
        problems.append(f"{rel(command_md)} is missing or unreadable")
    else:
        # A bare mention elsewhere is not enough: the line that decides between the two
        # listed names has to send the call to the prefixed one.
        prefixed_skill = f"`{prefix}{plugin_namespace()}`"
        hits = [
            number
            for number, line in enumerate(command_text.splitlines(), start=1)
            if "If both are listed" in line and prefixed_skill in line
        ]
        if not hits:
            problems.append(
                f"{rel(command_md)} does not send the call to {prefixed_skill} when both names "
                "are listed; the alias would resolve to whatever else owns the bare skill name"
            )
        else:
            evidence.append(f"{rel(command_md)}:{hits[0]} invokes {prefixed_skill} when both are listed")
    if command_text is not None:
        alias_list = find_lines(command_text, "available skills list")
        if not alias_list:
            problems.append(
                f"{rel(command_md)} states no list-first rule (available skills list); a "
                "non-plugin install pays one failed Skill call per /st before the retry"
            )
        else:
            evidence.append(f"{rel(command_md)}:{alias_list[0]} list-first name rule")

    if problems:
        return bad(f"{len(problems)} namespace wiring problem(s)", problems)
    return ok("plugin namespace on spawns and on the /st alias", evidence)


def check_referenced_reference_files() -> Result:
    """Every references/* path the wiring names must exist on disk."""
    wiring = (SKILL_MD, ARMORER_MD, THINKER_MD, THINKER_PROMPT_MD, ARMORER_PROMPT_MD)
    required = {"analysis-method.md", "thinker-prompt.md", "armorer-prompt.md", "lifecycle.md", "index.json"}
    mentioned: dict[str, str] = {}

    for path in wiring:
        text = read_text(path)
        if text is None:
            continue
        for match in re.finditer(r"references/([A-Za-z0-9._-]+\.(?:md|json))", text):
            name = match.group(1)
            mentioned.setdefault(name, f"{rel(path)}:{line_of(text, match.start())}")

    for name in required:
        mentioned.setdefault(name, "required by the v3 wiring contract")

    missing = {
        name: anchor for name, anchor in mentioned.items() if not (REFERENCES_DIR / name).exists()
    }
    if missing:
        pending = {
            name: anchor
            for name, anchor in missing.items()
            if rel(REFERENCES_DIR / name) in PENDING_PATHS
        }
        hard = {name: anchor for name, anchor in missing.items() if name not in pending}
        if hard:
            return bad(
                f"{len(hard)} referenced reference file(s) do not exist",
                [f"references/{name} referenced at {anchor} but not on disk" for name, anchor in sorted(hard.items())],
            )
        return skip(
            "referenced but not built yet: " + ", ".join(sorted(pending)),
            [f"references/{name} referenced at {anchor}" for name, anchor in sorted(pending.items())],
        )
    return ok(
        f"all {len(mentioned)} referenced reference files exist",
        [f"references/{name} ({anchor})" for name, anchor in sorted(mentioned.items())],
    )


def check_thinker_prompt_sync() -> Result:
    """The fallback SSOT must carry the definition's load-bearing instructions."""
    definition = read_text(THINKER_MD)
    fallback = read_text(THINKER_PROMPT_MD)
    if definition is None:
        return bad(f"{rel(THINKER_MD)} is missing or unreadable")
    if fallback is None:
        return bad(f"{rel(THINKER_PROMPT_MD)} is missing or unreadable")

    problems: list[str] = []
    evidence: list[str] = []
    for label, pattern in THINKER_SYNC_RULES:
        in_definition = re.search(pattern, definition) is not None
        in_fallback = re.search(pattern, fallback) is not None
        if in_definition and in_fallback:
            evidence.append(f"{label}: present in both")
        elif in_definition:
            problems.append(
                f"{label!r} is in {rel(THINKER_MD)} but missing from {rel(THINKER_PROMPT_MD)}; "
                "the fallback path would behave differently. Copy the instruction across."
            )
        elif in_fallback:
            problems.append(
                f"{label!r} is in {rel(THINKER_PROMPT_MD)} but missing from {rel(THINKER_MD)}; "
                "the agent definition would behave differently. Copy the instruction across."
            )
        else:
            problems.append(
                f"{label!r} is missing from both {rel(THINKER_MD)} and {rel(THINKER_PROMPT_MD)}; "
                "the instruction was dropped entirely."
            )
    if problems:
        return bad(f"{len(problems)} of {len(THINKER_SYNC_RULES)} sync rules broken", problems)
    return ok(f"all {len(THINKER_SYNC_RULES)} sync rules hold on both sides", evidence)


def check_thinker_prompt_variables() -> Result:
    text = read_text(THINKER_PROMPT_MD)
    if text is None:
        return bad(f"{rel(THINKER_PROMPT_MD)} is missing or unreadable")

    # A leading $ means a shell/environment reference, not a substitution slot.
    found = {match.group(1) for match in re.finditer(r"(?<!\$)\{([A-Z][A-Z0-9_]*)\}", text)}
    problems: list[str] = []

    unexpected = sorted(found - THINKER_PROMPT_VARS)
    absent = sorted(THINKER_PROMPT_VARS - found)
    if absent:
        problems.append("declared substitution variable(s) never used: " + ", ".join(absent))
    if unexpected:
        anchors = []
        for name in unexpected:
            hits = find_lines(text, "{" + name + "}")
            anchors.append(f"{name} at {rel(THINKER_PROMPT_MD)}:{hits[0] if hits else '?'}")
        problems.append("unknown substitution variable(s): " + ", ".join(anchors))

    leftovers = []
    for name in V2_PROMPT_VARS:
        hits = find_lines(text, "{" + name + "}")
        if hits:
            leftovers.append(f"{{{name}}} at {rel(THINKER_PROMPT_MD)}:{hits[0]}")
    if leftovers:
        problems.append("v2 substitution variable(s) still present: " + ", ".join(leftovers))

    if problems:
        return bad("thinker-prompt substitution variables do not match the v3 contract", problems)
    return ok(
        f"exactly the {len(THINKER_PROMPT_VARS)} v3 variables, no v2 leftovers",
        [", ".join(sorted(found))],
    )


def check_armorer_prompt_sync() -> Result:
    """references/armorer-prompt.md is the fallback SSOT for the armorer (issue #15).

    Without it the main session briefed general-purpose from `git show`, which a copy or
    plugin-cache install cannot do. This checks the definition's key instructions by the
    ARMORER_SYNC_RULES regexes (not a full-body diff) and that the fallback uses exactly the
    three 5a Path Variables as substitution slots.
    """
    definition = read_text(ARMORER_MD)
    fallback = read_text(ARMORER_PROMPT_MD)
    if definition is None:
        return bad(f"{rel(ARMORER_MD)} is missing or unreadable")
    if fallback is None:
        return bad(f"{rel(ARMORER_PROMPT_MD)} is missing or unreadable")

    problems: list[str] = []
    evidence: list[str] = []
    for label, pattern in ARMORER_SYNC_RULES:
        in_definition = re.search(pattern, definition) is not None
        in_fallback = re.search(pattern, fallback) is not None
        if in_definition and in_fallback:
            evidence.append(f"{label}: present in both")
        elif in_definition:
            problems.append(
                f"{label!r} is in {rel(ARMORER_MD)} but missing from {rel(ARMORER_PROMPT_MD)}; "
                "the fallback path would behave differently. Copy the instruction across."
            )
        elif in_fallback:
            problems.append(
                f"{label!r} is in {rel(ARMORER_PROMPT_MD)} but missing from {rel(ARMORER_MD)}; "
                "the agent definition would behave differently. Copy the instruction across."
            )
        else:
            problems.append(
                f"{label!r} is missing from both {rel(ARMORER_MD)} and {rel(ARMORER_PROMPT_MD)}; "
                "the instruction was dropped entirely."
            )

    found = {match.group(1) for match in re.finditer(r"(?<!\$)\{([A-Z][A-Z0-9_]*)\}", fallback)}
    absent = sorted(ARMORER_PROMPT_VARS - found)
    if absent:
        problems.append("declared substitution variable(s) never used: " + ", ".join(absent))
    unexpected = sorted(found - ARMORER_PROMPT_VARS)
    if unexpected:
        anchors = []
        for name in unexpected:
            hits = find_lines(fallback, "{" + name + "}")
            anchors.append(f"{name} at {rel(ARMORER_PROMPT_MD)}:{hits[0] if hits else '?'}")
        problems.append(
            "substitution variable(s) outside the 5a Path Variables: " + ", ".join(anchors)
        )

    if problems:
        return bad(f"{len(problems)} armorer fallback sync problem(s)", problems)
    evidence.append("substitution variables: " + ", ".join(sorted(found)))
    return ok(f"all {len(ARMORER_SYNC_RULES)} sync rules hold on both sides", evidence)

# Issue #21: section 5 used to be built with printf/cat redirections into the pack file, and each
# of those Bash calls prompted even with the vault Edit rule installed. The only writer is now
# scripts/assemble-pack.py, which one narrow Bash rule can allow. A leftover redirection
# instruction would bring the prompts back and bypass the script's own path checks.
ASSEMBLER_PY = REPO_ROOT / "scripts" / "assemble-pack.py"
ASSEMBLER_CALL_RE = re.compile(r"python3 \{SCRIPTS_DIR\}/assemble-pack\.py --pack-dir ")
# Any shell write that bypasses the script: printf/cat/echo with a > or >> redirect (heredoc
# included), tee in any form, and mkdir -p for the pack directory.
PACK_REDIRECT_RE = re.compile(r"^.*(?:\b(?:printf|cat|echo)\b[^\n]*>|\btee\b|\bmkdir\s+-p\b).*$", re.M)


# SKILL.md carries the same rule for the inline path (final-review #9). Only that section is
# scanned; its Write-only branch for harnesses without Bash has no redirection and stays allowed.
INLINE_SECTION_TITLE = "## 5b단계: 인라인 경로"


def _inline_section(text: str) -> str | None:
    start = text.find(INLINE_SECTION_TITLE)
    if start < 0:
        return None
    end = text.find("\n## ", start + len(INLINE_SECTION_TITLE))
    return text[start : end if end >= 0 else len(text)]


def check_armorer_assembles_with_script() -> Result:
    """st-armorer.md, armorer-prompt.md and SKILL.md 5b build section 5 by calling assemble-pack.py only."""
    problems: list[str] = []
    evidence: list[str] = []
    if not ASSEMBLER_PY.exists():
        problems.append(f"{rel(ASSEMBLER_PY)} is missing; section 5 has no writer")
    skill = read_text(SKILL_MD)
    inline = _inline_section(skill) if skill is not None else None
    if inline is None:
        problems.append(f"{rel(SKILL_MD)} has no '{INLINE_SECTION_TITLE}' section to check")
    for path, text in (
        (ARMORER_MD, read_text(ARMORER_MD)),
        (ARMORER_PROMPT_MD, read_text(ARMORER_PROMPT_MD)),
        (SKILL_MD, inline),
    ):
        if text is None:
            if path != SKILL_MD:
                problems.append(f"{rel(path)} is missing or unreadable")
            continue
        # Line numbers are reported against the whole file, also for the SKILL.md section.
        base = line_of(skill, skill.find(INLINE_SECTION_TITLE)) - 1 if path == SKILL_MD else 0
        call = ASSEMBLER_CALL_RE.search(text)
        if call is None:
            problems.append(
                f"{rel(path)} never calls `python3 {{SCRIPTS_DIR}}/assemble-pack.py --pack-dir ...`; "
                "section 5 must be assembled by the script"
            )
        else:
            evidence.append(f"{rel(path)}:{base + line_of(text, call.start())} calls assemble-pack.py")
        for match in PACK_REDIRECT_RE.finditer(text):
            problems.append(
                f"{rel(path)}:{base + line_of(text, match.start())} writes the pack with a shell command "
                f"({match.group(0).strip()[:60]}); use assemble-pack.py instead"
            )
    if problems:
        return bad(f"{len(problems)} section 5 assembly problem(s)", problems)
    return ok("definition, fallback and SKILL.md 5b assemble section 5 with assemble-pack.py only", evidence)


# Docs whose Bash a session runs while arming or in a subcommand (issue #26).
SESSION_BASH_DOCS = (SKILL_MD, REFERENCES_DIR / "lifecycle.md", ARMORER_MD, ARMORER_PROMPT_MD)
# A code line or inline span is taken as a shell command when its first word (after any leading
# VAR=value assignments) is one of these or a script path. `claude -p` and `codex exec` stay out:
# the docs name them for the caller that starts a run, never for the session to type (issue #28 2).
SHELL_COMMAND_WORDS = {
    "awk", "basename", "bash", "cat", "cd", "chmod", "command", "cp", "curl", "cut", "date", "diff",
    "dirname", "du", "echo", "env", "eval", "exec", "file", "find", "git", "grep", "head", "jq", "ln",
    "ls", "mkdir", "mv", "node", "nohup", "npx", "open", "pip", "pnpm", "printf", "pwd", "python",
    "python3", "readlink", "realpath", "rm", "sed", "sh", "sha256sum", "shasum", "sort", "source",
    "stat", "sudo", "tail", "tar", "tee", "test", "time", "touch", "tr", "uniq", "uv", "wc", "which",
    "xargs", "zsh",
}
# A fenced block in one of these languages is all commands, whatever each line starts with.
SHELL_FENCE_LANGS = {"bash", "sh", "shell", "zsh", "console"}
SCRIPT_PATH_RE = re.compile(r"^(?:\{[A-Z_]+\}|~|\.{1,2})?/\S*\.(?:py|sh)$")
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
# One parsed shell word that opens with VAR=: shlex drops the quotes, so the value may hold spaces.
ASSIGNMENT_WORD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
FENCE_RE = re.compile(r"^[ \t>]*```[ \t]*(?P<lang>[\w-]*)[^\n]*\n(?P<body>.*?)^[ \t>]*```", re.M | re.S)
INLINE_CODE_RE = re.compile(r"(?<!`)`(?P<code>[^`\n]+)`(?!`)")
# A doc placeholder such as <모듈 파일명...> or <SETTINGS>, not a redirection.
PLACEHOLDER_RE = re.compile(r"<[^<>\n]*[^<>\s\d&][^<>\n]*>")


def _compound_operator(command: str) -> str | None:
    """The first shape that splits or rewrites a shell command line, or None.

    ; && || and | chain commands. Redirection (> >> < <<), $(...), backticks, a trailing & and a
    leading VAR=value leave one command whose text no longer starts with the allow rule's prefix
    (issue #28 1). Single quotes make all of these an argument; double quotes still expand $( and `.
    """
    first = command.split(" ", 1)[0]
    if ASSIGNMENT_RE.match(first):
        return f"{first.split('=', 1)[0]}="
    command = PLACEHOLDER_RE.sub(lambda match: "x" * len(match.group(0)), command)
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote == "'":
            if char == "'":
                quote = ""
        elif command.startswith("$(", index):
            return "$("
        elif char == "`":
            return "`"
        elif quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char == ";":
            return ";"
        elif command.startswith("&&", index):
            return "&&"
        elif command.startswith("||", index):
            return "||"
        elif char == "|":
            return "|"
        elif command.startswith(">>", index) or command.startswith("<<", index):
            return command[index : index + 2]
        elif char in "<>":
            return char
        elif char == "&":
            return "&"
        index += 1
    return None


def _command_word(command: str) -> str:
    """The word a shell runs: the first one after any leading VAR=value assignments.

    The line is split the way a shell would, so `V="my vault" python3 x.py` yields python3 and not
    `vault"` (issue #37 4). Text shlex cannot split (an unclosed quote) falls back to whitespace words.
    """
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""  # a shell reads a mid-word # as part of the value (`V=a#b cmd`), shlex would drop the rest
    try:
        for word in lexer:
            if not ASSIGNMENT_WORD_RE.match(word):
                return word
    except ValueError:
        for word in command.split():
            if not ASSIGNMENT_RE.match(word):
                return word
    return ""


def _is_command(command: str) -> bool:
    word = _command_word(command)
    return word in SHELL_COMMAND_WORDS or bool(SCRIPT_PATH_RE.match(word))


def _shell_commands(text: str) -> list[tuple[int, str, bool]]:
    """(offset, line, in_shell_fence) for every code line and inline span that reads as a command.

    Every non-comment line of a bash/sh fence is a command, one-word lines included; elsewhere a
    line or span counts only when _is_command says so (issue #28 2).
    """
    found: list[tuple[int, str, bool]] = []
    fenced: list[tuple[int, int]] = []
    for block in FENCE_RE.finditer(text):
        fenced.append(block.span())
        shell = block.group("lang").lower() in SHELL_FENCE_LANGS
        offset = block.start("body")
        for line in block.group("body").splitlines(keepends=True):
            command = line.strip()
            if command and not command.startswith("#") and (shell or _is_command(command)):
                found.append((offset, command, shell))
            offset += len(line)
    for span in INLINE_CODE_RE.finditer(text):
        command = span.group("code").strip()
        if not any(start <= span.start() < end for start, end in fenced) and _is_command(command):
            found.append((span.start(), command, False))
    return found


def _named_as_one_word(command: str, in_shell_fence: bool) -> bool:
    """A lone word in prose (`ls`, `date`) names a tool; on its own shell-fence line it runs one."""
    return not in_shell_fence and len(command.split()) < 2


def _forbidden_in_sentence(text: str, offset: int) -> bool:
    """A forbidding word follows the command inside the sentence that holds it (issue #28 3).

    Docs keep a paragraph on one line, so the whole line is too wide a scope: a prohibition in one
    sentence would clear a command the next sentence tells the session to run. Code spans are
    blanked first so a . or | inside a command does not end the sentence.
    """
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    line = text[start:end if end >= 0 else None]
    masked = INLINE_CODE_RE.sub(lambda match: "`" + "x" * len(match.group("code")) + "`", line)
    here = offset - start
    right = SENTENCE_END_RE.search(masked, here)
    return bool(PROHIBITION_RE.search(masked, here, right.start() if right else len(masked)))


def check_session_bash_single_commands() -> Result:
    """Shell commands shown to a session are single commands, never ; && || or pipe lines."""
    problems: list[str] = []
    for path in SESSION_BASH_DOCS:
        text = read_text(path)
        if text is None:
            problems.append(f"{rel(path)} is missing or unreadable")
            continue
        for offset, command, _ in _shell_commands(text):
            operator = _compound_operator(command)
            if operator:
                problems.append(
                    f"{rel(path)}:{line_of(text, offset)} uses '{operator}' ({command[:70]}); allow rules "
                    "match one plain command, so run one command per call with no redirection, "
                    "substitution, & or VAR= prefix"
                )
    if problems:
        return bad(f"{len(problems)} compound shell command(s)", problems)
    return ok("SKILL.md, lifecycle.md and the armorer definition and fallback show single commands only")


# The arming commands `st init` installs a rule for (or, for readlink, the one install.sh extra):
# SKILL.md must not tell the main session to run anything else (final-review of #26 (a)1).
BUNDLE_COMMAND_RE = re.compile(
    r"^(?:python3 \{SCRIPTS_DIR\}/(?:resolve-vault\.py|assemble-pack\.py|<)|readlink \{SKILL_DIR\})"
)
# A command named in a sentence that forbids it is a prohibition, not an instruction.
PROHIBITION_RE = re.compile(r"마라|말고|금지|않는다|하지 않")
# A sentence ends at . ! ? before a space or line end, or at a table cell border.
SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)|\s\|(?=\s|$)")


def check_skill_bash_inside_bundle() -> Result:
    """SKILL.md shows the main session no Bash beyond the rule bundle, except to forbid it."""
    text = read_text(SKILL_MD)
    if text is None:
        return bad(f"{rel(SKILL_MD)} is missing or unreadable")
    problems: list[str] = []
    for offset, command, in_shell_fence in _shell_commands(text):
        if _named_as_one_word(command, in_shell_fence) or BUNDLE_COMMAND_RE.match(command):
            continue
        if _forbidden_in_sentence(text, offset):
            continue
        problems.append(
            f"{rel(SKILL_MD)}:{line_of(text, offset)} tells the session to run `{command[:60]}`, which no "
            "init rule covers; use Read/Glob or a resolve-vault.py/assemble-pack.py option instead"
        )
    if problems:
        return bad(f"{len(problems)} Bash instruction(s) outside the rule bundle", problems)
    return ok("SKILL.md names only resolve-vault.py, assemble-pack.py and the install.sh readlink as Bash")


# lifecycle.md (init/retain/status) may also name these, each kept on purpose with its reason in
# tests/evidence/26-bash-inventory.md. Anything else outside the bundle must be converted or listed.
LIFECYCLE_EXCEPTION_RE = re.compile(
    r"^(?:git log\b|cp \"<SETTINGS>\"|python3 \{SCRIPTS_DIR\}/(?:migrate-evolution|legacy-install)\.py\b)"
)


def check_lifecycle_bash_inventory() -> Result:
    """lifecycle.md names only bundle commands and the recorded exceptions as Bash, except to forbid them."""
    path = REFERENCES_DIR / "lifecycle.md"
    text = read_text(path)
    if text is None:
        return bad(f"{rel(path)} is missing or unreadable")
    problems: list[str] = []
    for offset, command, in_shell_fence in _shell_commands(text):
        if _named_as_one_word(command, in_shell_fence):
            continue
        if BUNDLE_COMMAND_RE.match(command) or LIFECYCLE_EXCEPTION_RE.match(command):
            continue
        if _forbidden_in_sentence(text, offset):
            continue
        problems.append(
            f"{rel(path)}:{line_of(text, offset)} tells the session to run `{command[:60]}`, which is neither in "
            "the rule bundle nor a recorded exception; convert it or record it in tests/evidence/26-bash-inventory.md"
        )
    if problems:
        return bad(f"{len(problems)} unlisted Bash instruction(s)", problems)
    return ok("lifecycle.md names only bundle commands and the recorded init/retain/status exceptions")


# The three marker spellings pack section 5 is built from. analysis-method.md is the SSOT;
# st-armorer.md needs its own copy because the armorer is told to read only Step 0.5 of that
# file, so a format written down there alone is a format the pack writer never sees.
MARKER_KINDS = ("MODULE-BEGIN", "MODULE-END", "MODULE-DIGEST")

# Deliberately looser than the pack-mode regexes: this one has to catch a malformed marker
# (missing space, uppercase field, stray indent) so the shape comparison below can report the
# drift, instead of finding nothing and reporting "missing" for a marker that is right there.
MARKER_LINE_RE = re.compile(
    r"^[ \t>]*(?P<marker><!--\s*MODULE-(?:BEGIN|END|DIGEST)\b.*?-->)[ \t]*$", re.M
)

# The script's templates are Python string literals such as "<!-- MODULE-END: {name} -->".
ASSEMBLER_MARKER_RE = re.compile(r"[\"'](?P<marker><!--\s*MODULE-(?:BEGIN|END|DIGEST)\b[^\"'\n]*?-->)[\"']")


def _marker_shape(marker: str) -> str:
    """Collapse the parts that vary per module (filename, hash value) so two files that agree
    on the format compare equal even when their examples name different modules."""
    shape = re.sub(r"(?<=sha256=)\S+", "<sha>", marker)
    return re.sub(r"(?<=: )\S+(?=( sha256=| -->))", "<file>", shape)


def _marker_shapes(text: str) -> dict[str, set[str]]:
    shapes: dict[str, set[str]] = {kind: set() for kind in MARKER_KINDS}
    for match in MARKER_LINE_RE.finditer(text):
        marker = match.group("marker")
        for kind in MARKER_KINDS:
            if kind in marker:
                shapes[kind].add(_marker_shape(marker))
                break
    return shapes


def check_module_marker_forms() -> Result:
    """st-armorer.md must spell the section 5 markers exactly the way analysis-method.md does.

    The v3 gate run found 3 of 7 packs with no marker at all: the format existed only in
    analysis-method.md, so whether a pack got markers depended on how far the armorer happened
    to read. The format now lives in the agent definition too, and this check keeps the copy
    from drifting away from the SSOT.
    """
    canon = read_text(ANALYSIS_METHOD_MD)
    if canon is None:
        return bad(f"{rel(ANALYSIS_METHOD_MD)} is missing or unreadable")
    in_canon = _marker_shapes(canon)

    problems: list[str] = []
    evidence: list[str] = []
    # armorer-prompt.md is what general-purpose writes section 5 from when no definition
    # resolves (#15), so it carries the same copy of the format and is held to the same SSOT.
    for path in (ARMORER_MD, ARMORER_PROMPT_MD):
        definition = read_text(path)
        if definition is None:
            problems.append(f"{rel(path)} is missing or unreadable")
            continue
        in_armorer = _marker_shapes(definition)
        for kind in MARKER_KINDS:
            canonical = in_canon[kind]
            written = in_armorer[kind]
            if not canonical:
                problems.append(
                    f"{rel(ANALYSIS_METHOD_MD)} shows no {kind} marker; the SSOT for the section 5 "
                    "format is gone, so there is nothing to check the copy against"
                )
                continue
            if not written:
                problems.append(
                    f"{rel(path)} shows no {kind} marker. The armorer writes section 5, so the "
                    f"format must be in its definition, not only in {rel(ANALYSIS_METHOD_MD)}."
                )
                continue
            agreed = written & canonical
            if not agreed:
                problems.append(
                    f"{kind} format drifted: {rel(path)} writes {sorted(written)} but "
                    f"{rel(ANALYSIS_METHOD_MD)} writes {sorted(canonical)}"
                )
                continue
            evidence.append(f"{rel(path)} {kind}: {sorted(agreed)[0]}")

    # Since #21 the section 5 markers are written by assemble-pack.py, not by a printf template in
    # the definition (the blind spot of #19). Its templates are string literals, so they are read
    # as such; it writes verbatim packs only, hence BEGIN and END but no DIGEST.
    source = read_text(ASSEMBLER_PY)
    if source is None:
        problems.append(f"{rel(ASSEMBLER_PY)} is missing or unreadable")
    else:
        templates: dict[str, set[str]] = {kind: set() for kind in MARKER_KINDS}
        for match in ASSEMBLER_MARKER_RE.finditer(source):
            marker = match.group("marker")
            kind = next(kind for kind in MARKER_KINDS if kind in marker)
            templates[kind].add(_marker_shape(marker))
        for kind in ("MODULE-BEGIN", "MODULE-END"):
            written, canonical = templates[kind], in_canon[kind]
            if not written:
                problems.append(f"{rel(ASSEMBLER_PY)} has no {kind} marker template")
            elif canonical and written != written & canonical:
                problems.append(
                    f"{kind} format drifted: {rel(ASSEMBLER_PY)} writes {sorted(written)} but "
                    f"{rel(ANALYSIS_METHOD_MD)} writes {sorted(canonical)}"
                )
            elif canonical:
                evidence.append(f"{rel(ASSEMBLER_PY)} {kind}: {sorted(written)[0]}")

    if problems:
        return bad(f"{len(problems)} module marker form problem(s)", problems)
    return ok(
        f"all {len(MARKER_KINDS)} module marker forms match {rel(ANALYSIS_METHOD_MD)}", evidence
    )


# ---------------------------------------------------------------- E. v3 data schema


def check_evolution_state_schema() -> Result:
    path = DATA_DIR / "evolution-state.md"
    front, error = load_frontmatter(path)
    if front is None:
        return bad(error or f"{rel(path)} frontmatter could not be parsed")
    required = ("version", "updated", "sessions", "diversity_h", "routing_weights")
    missing = [key for key in required if key not in front]
    problems: list[str] = []
    if missing:
        problems.append(
            f"{rel(path)}: frontmatter is missing key(s) {', '.join(missing)}; "
            f"present keys: {', '.join(front) or '(none)'}"
        )
    if front.get("version") != 3:
        problems.append(
            f"{frontmatter_line(path, 'version')}: version is {front.get('version')!r}, expected 3"
        )
    if problems:
        return bad("evolution-state.md schema broken", problems)
    return ok(f"{rel(path)}: version 3 with all 5 header keys", [", ".join(required)])


def check_profile_schema() -> Result:
    path = DATA_DIR / "profile.md"
    front, error = load_frontmatter(path)
    if front is None:
        return bad(error or f"{rel(path)} frontmatter could not be parsed")
    problems: list[str] = []
    missing = [key for key in ("version", "updated") if key not in front]
    if missing:
        problems.append(f"{rel(path)}: frontmatter is missing key(s) {', '.join(missing)}")
    if front.get("version") != 3:
        problems.append(
            f"{frontmatter_line(path, 'version')}: version is {front.get('version')!r}, expected 3"
        )
    if problems:
        return bad("profile.md schema broken", problems)
    return ok(f"{rel(path)}: version 3 with version + updated")


def check_profile_blocks() -> Result:
    """The six profile blocks, in order."""
    path = DATA_DIR / "profile.md"
    text = read_text(path)
    if text is None:
        return bad(f"{rel(path)} is missing or unreadable")

    blocks = (
        ("정체성", r"^##\s*1\.\s*정체성"),
        ("현재 목표", r"^##\s*2\.\s*현재\s*목표"),
        ("스타일", r"^##\s*3\.\s*스타일"),
        ("기본값", r"^##\s*4\.\s*기본값"),
        ("소스", r"^##\s*5\.\s*소스"),
        ("이력 요약", r"^##\s*6\.\s*이력\s*요약"),
    )
    positions: list[tuple[str, int]] = []
    missing: list[str] = []
    for label, pattern in blocks:
        match = re.search(pattern, text, re.M)
        if match is None:
            missing.append(label)
        else:
            positions.append((label, match.start()))
    if missing:
        return bad(
            f"{rel(path)}: profile block(s) missing: " + ", ".join(missing),
            [f"expected headings: {', '.join(label for label, _ in blocks)}"],
        )
    out_of_order = [
        f"{positions[i][0]} (line {line_of(text, positions[i][1])}) comes after "
        f"{positions[i + 1][0]} (line {line_of(text, positions[i + 1][1])})"
        for i in range(len(positions) - 1)
        if positions[i][1] > positions[i + 1][1]
    ]
    if out_of_order:
        return bad(f"{rel(path)}: profile blocks are out of order", out_of_order)
    return ok(
        "all 6 profile blocks present in order",
        [f"{label} at line {line_of(text, offset)}" for label, offset in positions],
    )


# Issue #30: the run's goal is asked at the arming gate, not in the init interview.
INIT_GOAL_ROW_RE = re.compile(r"^\|\s*②\s*\|\s*현재\s*목표\s*\|", re.M)
GATE_GOAL_QUESTION = "이번에 무엇을 하려는가"
# Where a topic-only run's answer to that question must travel to reach pack section 2: the line
# that names it (a marker) must say to prefer the goal answered at the gate over A/B/C.
GATE_GOAL_ANSWER = "게이트에서 답한 목표"
GOAL_HANDOFF_LINES = (
    (SKILL_MD, "- **Interpretation**:"),
    (SKILL_MD, "    2. 작업 해석 ("),
    (ARMORER_MD, "- **주제만 온 경우**:"),
    (ARMORER_PROMPT_MD, "- **주제만 온 경우**:"),
    (REFERENCES_DIR / "analysis-method.md", "1. **작업 해석** - 팩 2절 초안."),
    (REFERENCES_DIR / "analysis-method.md", "   - **풀 3 - 작업 해석 유래**:"),
    (REFERENCES_DIR / "analysis-method.md", "3. 각 편향을 아래 형식 3줄로 쓴다."),
)


def check_goal_asked_at_gate() -> Result:
    """init does not ask for the current goal; gate item 1 does."""
    lifecycle = REFERENCES_DIR / "lifecycle.md"
    problems: list[str] = []
    evidence: list[str] = []
    text = read_text(lifecycle)
    if text is None:
        problems.append(f"{rel(lifecycle)} is missing or unreadable")
    else:
        for match in INIT_GOAL_ROW_RE.finditer(text):
            problems.append(
                f"{rel(lifecycle)}:{line_of(text, match.start())} init interview asks for the current goal again"
            )
    skill = read_text(SKILL_MD)
    if skill is None:
        problems.append(f"{rel(SKILL_MD)} is missing or unreadable")
    else:
        gate = skill.find("1. 입력 해석")
        end = skill.find("2. 진단", gate)
        if gate < 0 or end < 0 or GATE_GOAL_QUESTION not in skill[gate:end]:
            problems.append(f"{rel(SKILL_MD)} gate item 1 has no '{GATE_GOAL_QUESTION}' goal question")
        else:
            evidence.append(f"{rel(SKILL_MD)}:{line_of(skill, skill.find(GATE_GOAL_QUESTION, gate))} gate goal question")
    for path, marker in GOAL_HANDOFF_LINES:
        text = read_text(path)
        if text is None:
            problems.append(f"{rel(path)} is missing or unreadable")
            continue
        start = text.find("\n" + marker)
        line = text[start + 1 : text.find("\n", start + 1)] if start >= 0 else ""
        if GATE_GOAL_ANSWER not in line:
            problems.append(
                f"{rel(path)}: the '{marker.strip()}' line does not carry the {GATE_GOAL_ANSWER} to pack section 2"
            )
    if problems:
        return bad("the run's goal is not taken at the arming gate or does not reach the pack", problems)
    return ok(
        "init interview has no current-goal question; gate item 1 asks it and the answer reaches pack section 2",
        evidence,
    )


def check_data_is_empty_seed() -> Result:
    """The plugin ships templates, never real user state."""
    path = DATA_DIR / "evolution-state.md"
    front, error = load_frontmatter(path)
    if front is None:
        return bad(error or f"{rel(path)} frontmatter could not be parsed")
    problems: list[str] = []
    sessions = front.get("sessions")
    if sessions != 0:
        problems.append(
            f"{frontmatter_line(path, 'sessions')}: sessions is {sessions!r}, expected 0. "
            "The shipped template must not carry real usage; user state lives in the vault."
        )
    weights = front.get("routing_weights")
    if weights:
        problems.append(
            f"{frontmatter_line(path, 'routing_weights')}: routing_weights is not empty "
            f"({weights!r}); the shipped template must start blank."
        )
    if problems:
        return bad(f"{rel(DATA_DIR)} contains real user data", problems)
    return ok("shipped .data seed is blank (sessions=0, routing_weights empty)")


# Prose that let the model pick {VAULT} by judgment. Issue #10: an empty env vault was skipped.
VAULT_PROSE_LEFTOVERS = (
    (r"2\s*(?:→|->)\s*3\s*순", "candidate cascade that invites a fallback"),
    (r"profile\.md가\s*선언한\s*vault", "profile declaration ranked above the env var"),
    (r"SMARTTHINK_VAULT:-[^}]", "shell default that bypasses the resolver and the pointer"),
)


def check_vault_resolver_wiring() -> Result:
    """{VAULT} must come from scripts/resolve-vault.py, never from re-derived prose."""
    resolver = REPO_ROOT / "scripts" / "resolve-vault.py"
    if not resolver.is_file():
        return bad(f"{rel(resolver)} is missing", ["The skill and the installers depend on it for {VAULT}."])
    problems: list[str] = []
    callers = (SKILL_MD, REFERENCES_DIR / "lifecycle.md", REPO_ROOT / "install.sh", REPO_ROOT / "uninstall.sh")
    for path in callers:
        text = read_text(path) or ""
        if "resolve-vault.py" not in text:
            problems.append(f"{rel(path)}: does not call resolve-vault.py")
    prose_files = callers + (DATA_DIR / "README.md",)
    for path in prose_files:
        for number, line in enumerate((read_text(path) or "").splitlines(), start=1):
            for pattern, reason in VAULT_PROSE_LEFTOVERS:
                if re.search(pattern, line):
                    problems.append(f"{rel(path)}:{number}: {reason}: {line.strip()}")
    if problems:
        return bad(f"{len(problems)} vault resolution leftover(s)", problems)
    return ok("SKILL.md, lifecycle.md and both installers resolve {VAULT} through resolve-vault.py")


# Issue #20: the default vault moved out of ~/.claude with no compatibility path, so the old
# folder name must not survive as a convention. History (CHANGELOG.md) and tests/ may mention it.
OLD_VAULT_TOKEN = "smartthink" + "-vault"


def old_vault_convention_files() -> list[Path]:
    files = [
        REPO_ROOT / name
        for name in ("README.md", "README.ko.md", "CONTRIBUTING.md", "install.sh", "uninstall.sh", ".gitignore")
    ]
    files += sorted((REPO_ROOT / "docs").rglob("*.md"))
    files += sorted((REPO_ROOT / "scripts").glob("*.py"))
    files += sorted((REPO_ROOT / "commands").glob("*.md")) + sorted(AGENTS_DIR.glob("*.md"))
    files += sorted(path for path in SKILL_DIR.rglob("*") if path.is_file() and path.suffix in (".md", ".json"))
    this_gate = Path(__file__).resolve()
    return [path for path in files if path.is_file() and path.resolve() != this_gate]


def check_no_old_default_vault() -> Result:
    """The pre-#20 default vault path is gone from docs, scripts and installers."""
    problems = []
    for path in old_vault_convention_files():
        for number, line in enumerate((read_text(path) or "").splitlines(), start=1):
            if OLD_VAULT_TOKEN in line:
                problems.append(f"{rel(path)}:{number}: {line.strip()}")
    if problems:
        return bad(f"{len(problems)} mention(s) of the pre-#20 default vault", problems)
    return ok("no convention names the pre-#20 default vault")


# Issue #14: a rule path with a single leading / is relative to the settings file, so the vault
# never matches, and a hardcoded ~/.claude/settings.json ignores CLAUDE_CONFIG_DIR.
PERMISSION_RULE_LEFTOVERS = (
    (r"Edit\(\s*[<{]VAULT[>}]", "vault placeholder rule expands to a single-/ path"),
    (r"Edit\(/(?!/)", "single-/ rule path is relative to the settings file"),
    (r"~/\.claude/settings\.json", "hardcoded settings file ignores CLAUDE_CONFIG_DIR"),
)
# A line may show the single-/ form only as the literal placeholder, and only to forbid it or flag
# it as NG. Warnings are whole words so "NG" inside <SETTINGS> or WARNING does not count.
PERMISSION_RULE_WARNINGS = re.compile(r"쓰지 마라|매칭 안 됨|\bNG\b")
SINGLE_SLASH_EXAMPLE = "Edit(/<절대경로>/**)"


def check_permission_rule_format() -> Result:
    """init/status and every doc that describes the rule must name only ~/ or // rules in the resolved settings."""
    problems: list[str] = []
    for path in (REFERENCES_DIR / "lifecycle.md", SKILL_MD, DATA_DIR / "README.md", ANALYSIS_METHOD_MD):
        text = read_text(path)
        if text is None:
            problems.append(f"{rel(path)}: missing or unreadable, so its rule wording cannot be checked")
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern, reason in PERMISSION_RULE_LEFTOVERS:
                if not re.search(pattern, line):
                    continue
                if (
                    pattern.startswith(r"Edit\(/")
                    and PERMISSION_RULE_WARNINGS.search(line)
                    and not re.search(pattern, line.replace(SINGLE_SLASH_EXAMPLE, ""))
                ):
                    continue
                problems.append(f"{rel(path)}:{number}: {reason}: {line.strip()}")
    # The init step that installs the rule must itself take it from the resolver; a mention in
    # the status section alone does not count.
    lifecycle = read_text(REFERENCES_DIR / "lifecycle.md") or ""
    start = lifecycle.find("### 4. 권한 규칙 제안")
    end = lifecycle.find("\n### ", start + 1) if start >= 0 else -1
    init_step = lifecycle[start:end if end >= 0 else None] if start >= 0 else ""
    if "--permission-rule" not in init_step:
        problems.append(
            f"{rel(REFERENCES_DIR / 'lifecycle.md')}: init step '### 4. 권한 규칙 제안' does not take the rule "
            "from resolve-vault.py --permission-rule"
        )
    if problems:
        return bad(f"{len(problems)} permission rule leftover(s)", problems)
    return ok("lifecycle.md takes the vault rule and settings path from resolve-vault.py --permission-rule")


# Issue #9: without a stated signal the model defaults to interactive and ends the
# headless turn at the gate. The signals must be tool-free (Bash env reads can be denied).
HEADLESS_SIGNALS = ("### 헤드리스 판별", "Claude Agent SDK", "AskUserQuestion")
# Each section must carry the branch itself; a bare mention of 헤드리스 or a link is not enough.
HEADLESS_SECTION_RULES = {
    "## 4단계: 게이트 HITL-1": ("헤드리스면 묻지 않는다", "같은 턴에서", "게이트에서 턴을 끝내"),
    "### `--budget N`": ("헤드리스면 묻지 않는다", "같은 턴에서"),
}


def check_headless_gate_branch() -> Result:
    """SKILL.md names tool-free headless signals and branches inside the gate and --budget."""
    text = read_text(SKILL_MD)
    if text is None:
        return bad(f"{rel(SKILL_MD)} is missing or unreadable")
    problems = [f"{rel(SKILL_MD)}: headless signal text missing: {s!r}" for s in HEADLESS_SIGNALS if s not in text]
    for heading, phrases in HEADLESS_SECTION_RULES.items():
        start = text.find(heading)
        end = text.find("\n#", start + len(heading)) if start >= 0 else -1
        body = text[start:end if end >= 0 else len(text)] if start >= 0 else ""
        for phrase in phrases:
            if phrase not in body:
                problems.append(f"{rel(SKILL_MD)}: {heading!r} body lacks headless rule text {phrase!r}")
    if problems:
        return bad(f"{len(problems)} headless gate wiring problem(s)", problems)
    return ok("SKILL.md states tool-free headless signals and a headless branch in the gate and --budget")


# ----------------------------------------------------------------- F. v2 leftovers


def check_no_deep_flag() -> Result:
    text = read_text(SKILL_MD)
    if text is None:
        return bad(f"{rel(SKILL_MD)} is missing or unreadable")
    hits = find_lines(text, "--deep")
    if hits:
        return bad(
            f"{rel(SKILL_MD)} still mentions the v2 --deep mode",
            [f"{rel(SKILL_MD)}:{number}" for number in hits],
        )
    return ok("SKILL.md defines no --deep mode")


def check_skill_frontmatter_clean() -> Result:
    """effort and argument-hint are not documented skill frontmatter keys."""
    front, error = load_frontmatter(SKILL_MD)
    if front is None:
        return bad(error or f"{rel(SKILL_MD)} frontmatter could not be parsed")
    present = [key for key in ("effort", "argument-hint") if key in front]
    if present:
        return bad(
            f"{rel(SKILL_MD)} frontmatter still declares " + ", ".join(present) + " (both were removed)",
            [frontmatter_line(SKILL_MD, key) for key in present],
        )
    return ok("SKILL.md frontmatter has neither effort nor argument-hint")


def check_no_legacy_prefix_aliases() -> Result:
    """The agent/light/search prefixes are gone. Prose recording that is fine;
    a table row or rule that still maps a prefix to a mode is not."""
    text = read_text(SKILL_MD)
    if text is None:
        return bad(f"{rel(SKILL_MD)} is missing or unreadable")

    mapping_rows: list[str] = []
    ambiguous: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # A table row whose first cell is exactly one alias token is an alias mapping.
        row = re.match(r"^\|\s*`?(agent|light|search)`?\s*\|", stripped)
        if row is not None:
            mapping_rows.append(f"{rel(SKILL_MD)}:{number}: alias table row for {row.group(1)!r}: {stripped}")
            continue
        # An explicit prefix-to-mode rule outside a table.
        if re.search(r"접두어|prefix", stripped) and re.search(r"`(agent|light|search) `", stripped):
            if not any(word in stripped for word in ABOLITION_WORDS):
                ambiguous.append(f"{rel(SKILL_MD)}:{number}: {stripped}")

    if mapping_rows:
        return bad(
            "legacy prefix alias mapping still present",
            mapping_rows + ["the agent/light/search prefixes were abolished; delete the mapping"],
        )
    if ambiguous:
        return skip(
            "prefix-related line(s) found without an explicit abolition word; judge by hand",
            ambiguous,
        )
    return ok("no legacy prefix alias mapping in SKILL.md (abolition prose is allowed)")


def _iter_repo_files(suffixes: tuple[str, ...], roots: tuple[Path, ...]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            if root.suffix in suffixes:
                found.append(root)
            continue
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if EXCLUDED_DIRS.intersection(path.parts):
                continue
            if path.is_file() and path.suffix in suffixes:
                found.append(path)
    return found


def check_no_searcher_wiring() -> Result:
    """Nothing may still spawn, install or symlink st-searcher."""
    roots = (
        SKILL_DIR,
        AGENTS_DIR,
        REPO_ROOT / "scripts",
        REPO_ROOT / "commands",
        REPO_ROOT / "docs",
        REPO_ROOT / "install.sh",
        REPO_ROOT / "uninstall.sh",
    ) + tuple(sorted(REPO_ROOT.glob("*.md")))
    files = _iter_repo_files((".md", ".py", ".sh", ".json"), roots)

    hard: list[str] = []
    pending: list[str] = []
    for path in files:
        if path.resolve() == Path(__file__).resolve():
            continue  # this checker names the agent in order to forbid it
        text = read_text(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if "st-searcher" not in line:
                continue
            if any(word in line for word in ABOLITION_WORDS):
                continue  # prose recording the removal
            if path.name == "CHANGELOG.md":
                continue  # a changelog documents past releases by definition
            entry = f"{rel(path)}:{number}: {line.strip()}"
            if is_pending(path):
                pending.append(entry)
            else:
                hard.append(entry)

    if hard:
        return bad(
            f"{len(hard)} live reference(s) to the abolished st-searcher",
            hard
            + [
                "st-searcher was folded into st-armorer and agents/st-searcher.md no longer exists, "
                "so these lines point at a missing agent."
            ]
            + ([f"({len(pending)} more in files still owned by another worker)"] if pending else []),
        )
    if pending:
        return skip(
            f"{len(pending)} reference(s) remain only in files another worker still owns",
            pending,
        )
    return ok("no live st-searcher wiring left")


# -------------------------------------------------------------- G. document hygiene


def check_no_em_dash() -> Result:
    """Project rule: hyphens only. The nine frozen modules are exempt because
    editing them would break every hash in index.json and in every existing pack,
    and tests/evidence is exempt because it is a verbatim capture, not editable prose."""
    roots = (REPO_ROOT,)
    candidates = _iter_repo_files((".md", ".py"), roots)
    files = [
        path
        for path in candidates
        if not (path.parent == REFERENCES_DIR and path.name in MODULES)
        and VERBATIM_EVIDENCE_DIR not in path.parents
    ]
    evidence_skipped = len(
        [path for path in candidates if VERBATIM_EVIDENCE_DIR in path.parents]
    )
    exempt = [name for name in MODULES if EM_DASH in (read_text(REFERENCES_DIR / name) or "")]

    hits: list[str] = []
    for path in files:
        text = read_text(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EM_DASH in line:
                hits.append(f"{rel(path)}:{number}: {line.strip()[:100]}")

    note = (
        f"{len(exempt)} frozen module(s) contain em dashes and are exempt: {', '.join(exempt)}"
        if exempt
        else "no exemption needed"
    )
    evidence_note = f"{evidence_skipped} verbatim evidence file(s) under {rel(VERBATIM_EVIDENCE_DIR)} not scanned"
    if hits:
        return bad(
            f"{len(hits)} em dash occurrence(s) in editable files; replace each with a hyphen",
            hits + [note, evidence_note],
        )
    return ok(f"no em dashes in {len(files)} editable .md/.py files", [note, evidence_note])


def check_no_private_information() -> Result:
    roots = (
        SKILL_DIR,
        AGENTS_DIR,
        REPO_ROOT / "scripts",
        REPO_ROOT / "docs",
    ) + tuple(sorted(REPO_ROOT.glob("*.md")))
    files = _iter_repo_files((".md", ".py", ".json"), roots)

    hard: list[str] = []
    pending: list[str] = []
    for path in files:
        text = read_text(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern, why in PRIVATE_PATTERNS:
                if pattern in line:
                    entry = f"{rel(path)}:{number}: {why} ({pattern!r}): {line.strip()[:100]}"
                    if is_pending(path):
                        pending.append(entry)
                    else:
                        hard.append(entry)
    if hard:
        return bad(
            f"{len(hard)} private-information hit(s) in a public repository",
            hard + ["Replace with a neutral placeholder or the public GitHub path."],
        )
    if pending:
        return skip(f"{len(pending)} hit(s) only in files another worker still owns", pending)
    return ok(f"no private-information patterns in {len(files)} scanned files")


# ------------------------------------------------------------- H. pack verification


MODULE_BEGIN_RE = re.compile(
    rb"^<!-- MODULE-BEGIN: (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) -->[ \t]*$", re.M
)
MODULE_END_RE = re.compile(rb"^<!-- MODULE-END: (?P<name>\S+) -->[ \t]*$", re.M)
MODULE_DIGEST_RE = re.compile(rb"^<!-- MODULE-DIGEST: (?P<name>\S+) -->[ \t]*$", re.M)


def _pack_paths(pack: Path) -> tuple[Path, Path]:
    if pack.is_file() and pack.name == "pack.md":
        return pack, pack.parent / "manifest.json"
    return pack / "pack.md", pack / "manifest.json"


def check_pack_files(context: "Context") -> Result:
    if context.pack is None:
        return skip("no --pack given", promotable=False)
    pack_md, manifest_json = _pack_paths(context.pack)
    missing = [str(path) for path in (pack_md, manifest_json) if not path.exists()]
    if missing:
        return bad("pack is incomplete, missing: " + ", ".join(missing))
    return ok("pack.md and manifest.json present", [str(pack_md), str(manifest_json)])


def check_pack_manifest(context: "Context") -> Result:
    if context.pack is None:
        return skip("no --pack given", promotable=False)
    _, manifest_json = _pack_paths(context.pack)
    text = read_text(manifest_json)
    if text is None:
        return bad(f"{manifest_json} is missing or unreadable")
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as error:
        return bad(f"{manifest_json}:{error.lineno} is not valid JSON: {error.msg}")
    if not isinstance(manifest, dict):
        return bad(f"{manifest_json} top level is {type(manifest).__name__}, expected an object")

    problems: list[str] = []
    missing = [name for name in MANIFEST_FIELDS if name not in manifest]
    if missing:
        problems.append(f"{manifest_json}: missing field(s) " + ", ".join(missing))
    if "research" in manifest and not isinstance(manifest["research"], bool):
        problems.append(
            f"{manifest_json}: research is {manifest['research']!r} "
            f"({type(manifest['research']).__name__}), it must be a JSON boolean"
        )
    if problems:
        return bad("manifest.json does not match the v3 schema", problems)
    return ok(
        f"manifest has all {len(MANIFEST_FIELDS)} fields, research is boolean",
        [f"research={manifest['research']}, modules={manifest.get('modules')}"],
    )


def _load_manifest(pack: Path) -> dict:
    _, manifest_json = _pack_paths(pack)
    try:
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def check_pack_sections(context: "Context") -> Result:
    if context.pack is None:
        return skip("no --pack given", promotable=False)
    pack_md, _ = _pack_paths(context.pack)
    text = read_text(pack_md)
    if text is None:
        return bad(f"{pack_md} is missing or unreadable")

    research = _load_manifest(context.pack).get("research")
    offsets: list[tuple[str, int]] = []
    problems: list[str] = []
    for title in PACK_SECTIONS:
        match = re.search("^" + re.escape(title) + r"[ \t]*$", text, re.M)
        index = match.start() if match else -1
        if index < 0:
            optional = title == PACK_SECTIONS[2] and research is False
            if optional:
                continue
            problems.append(
                f"{pack_md}: section {title!r} is missing"
                + (" (allowed only when manifest research is false)" if title == PACK_SECTIONS[2] else "")
            )
        else:
            offsets.append((title, index))

    for i in range(len(offsets) - 1):
        if offsets[i][1] > offsets[i + 1][1]:
            problems.append(
                f"{pack_md}: {offsets[i][0]!r} (line {line_of(text, offsets[i][1])}) appears after "
                f"{offsets[i + 1][0]!r} (line {line_of(text, offsets[i + 1][1])})"
            )
    if problems:
        return bad("pack section structure broken", problems)
    return ok(
        f"{len(offsets)} sections present in order"
        + (" (section 3 omitted, research=false)" if research is False and len(offsets) == 5 else ""),
        [f"{title} at line {line_of(text, offset)}" for title, offset in offsets],
    )


def _section_five_bounds(data: bytes) -> tuple[int, int] | None:
    start = data.find(PACK_SECTIONS[4].encode("utf-8"))
    if start < 0:
        return None
    end = data.find(PACK_SECTIONS[5].encode("utf-8"), start)
    return start, (end if end >= 0 else len(data))


def check_pack_verbatim_integrity(context: "Context") -> Result:
    """Three hashes must agree: the reference file, the marker, and the copied block."""
    if context.pack is None:
        return skip("no --pack given", promotable=False)
    pack_md, _ = _pack_paths(context.pack)
    data = read_bytes(pack_md)
    if data is None:
        return bad(f"{pack_md} is missing or unreadable")

    bounds = _section_five_bounds(data)
    if bounds is None:
        return bad(f"{pack_md}: section {PACK_SECTIONS[4]!r} not found, cannot verify verbatim integrity")
    start, end = bounds
    body = data[start:end]

    digests = list(MODULE_DIGEST_RE.finditer(body))
    begins = list(MODULE_BEGIN_RE.finditer(body))

    if context.digest or (digests and not begins):
        if not digests:
            return bad(
                f"{pack_md}: --digest pack but section 5 has no "
                "'<!-- MODULE-DIGEST: <file> -->' marker"
            )
        if begins:
            return bad(
                f"{pack_md}: section 5 mixes MODULE-DIGEST and MODULE-BEGIN markers; "
                "a pack is entirely verbatim or entirely digest"
            )
        names = [match.group("name").decode("utf-8") for match in digests]
        return ok(
            f"digest pack: {len(names)} MODULE-DIGEST marker(s), hash check waived by design",
            names,
        )

    if not begins:
        return bad(
            f"{pack_md}: section 5 has no '<!-- MODULE-BEGIN: <file> sha256=<64 hex> -->' marker. "
            "Every module block must be wrapped so its verbatim copy can be hashed."
        )

    index_modules: dict = {}
    if INDEX_JSON.exists():
        try:
            index_modules = json.loads(INDEX_JSON.read_text(encoding="utf-8")).get("modules", {})
        except (OSError, json.JSONDecodeError):
            index_modules = {}

    problems: list[str] = []
    evidence: list[str] = []
    for begin in begins:
        name = begin.group("name").decode("utf-8")
        declared = begin.group("sha").decode("ascii")
        anchor = f"{pack_md}:{line_of(data.decode('utf-8', 'replace'), start + begin.start())}"

        end_match = None
        for candidate in MODULE_END_RE.finditer(body, begin.end()):
            if candidate.group("name") == begin.group("name"):
                end_match = candidate
                break
        if end_match is None:
            problems.append(f"{anchor}: MODULE-BEGIN for {name} has no matching MODULE-END")
            continue

        block = body[begin.end() + 1 : end_match.start()]
        source = read_bytes(REFERENCES_DIR / name)
        if source is None:
            problems.append(f"{anchor}: {name} is not a reference file under {rel(REFERENCES_DIR)}/")
            continue
        file_hash = sha256_hex(source)

        if declared != file_hash:
            problems.append(
                f"{anchor}: marker declares sha256={declared} but "
                f"{rel(REFERENCES_DIR / name)} hashes to {file_hash}"
            )
            continue

        indexed = index_modules.get(name, {}).get("sha256") if index_modules else None
        if indexed is not None and indexed != file_hash:
            problems.append(
                f"{anchor}: {rel(INDEX_JSON)} declares sha256={indexed} for {name} but the file "
                f"hashes to {file_hash}; the index is stale or the reference was modified"
            )
            continue

        # The only tolerated difference is one separator newline before the END marker.
        block_hash = sha256_hex(block)
        trimmed_hash = sha256_hex(block[:-1]) if block.endswith(b"\n") else None
        if block_hash != file_hash and trimmed_hash != file_hash:
            problems.append(
                f"{anchor}: the copy of {name} in section 5 hashes to {block_hash} "
                f"(or {trimmed_hash} without the trailing separator newline) but the source is "
                f"{file_hash}. The text was altered; section 5 must be byte-identical."
            )
            continue
        evidence.append(f"{name}: {len(block)} bytes, sha256 {file_hash[:12]}... matches file and marker")

    if problems:
        return bad(f"{len(problems)} verbatim integrity problem(s)", problems)
    return ok(f"{len(begins)} module block(s) byte-identical to their source", evidence)


def check_pack_markers_scoped(context: "Context") -> Result:
    if context.pack is None:
        return skip("no --pack given", promotable=False)
    pack_md, _ = _pack_paths(context.pack)
    data = read_bytes(pack_md)
    if data is None:
        return bad(f"{pack_md} is missing or unreadable")
    bounds = _section_five_bounds(data)
    if bounds is None:
        return skip(f"{pack_md}: section 5 not found, nothing to scope")
    start, end = bounds

    stray = [
        match
        for regex in (MODULE_BEGIN_RE, MODULE_DIGEST_RE)
        for match in regex.finditer(data)
        if not (start <= match.start() < end)
    ]
    if stray:
        text = data.decode("utf-8", "replace")
        return bad(
            f"{len(stray)} module marker(s) outside section 5",
            [f"{pack_md}:{line_of(text, match.start())}" for match in stray],
        )
    return ok("all module markers live inside section 5")


# --------------------------------------------------------------------------- runner


@dataclass
class Context:
    pack: Path | None
    digest: bool
    verbose: bool
    strict: bool


# The pack group is the only group --pack turns on, so its tally is reported separately.
PACK_GROUP = "H"

CHECKS: tuple[tuple[str, str, object], ...] = (
    ("A", "layout: required paths exist", check_required_paths),
    ("A", "layout: plugin.json is valid and complete", check_plugin_json),
    ("A", "layout: st-searcher.md removed", check_searcher_removed),
    ("A", "layout: st-armorer.md and st-thinker.md exist", check_agent_definitions_present),
    ("B", "references: 9 mental-model modules exist", check_modules_present),
    ("B", "references: index.json sha256 matches file bytes", check_index_hashes),
    ("B", "references: index.json est_tokens recomputes", check_index_token_estimates),
    ("C", "agents: frontmatter parses and name matches filename", check_agent_frontmatter_names),
    ("C", "agents: no model field (session inheritance)", check_agents_have_no_model),
    ("C", "agents: no skills preload", check_agents_have_no_skills_preload),
    ("C", "agents: st-thinker effort/maxTurns", check_thinker_budget),
    ("C", "agents: st-armorer effort/maxTurns", check_armorer_budget),
    ("C", "agents: st-armorer owns the web tools", check_armorer_has_search_tools),
    ("C", "agents: st-thinker has no web tools", check_thinker_has_no_search_tools),
    ("D", "wiring: 6 pack section titles shared verbatim", check_pack_section_titles),
    ("D", "wiring: 11 manifest fields described on both sides", check_manifest_fields_shared),
    ("D", "wiring: spawned sub-agent names resolve to agents/", check_spawned_agents_exist),
    ("D", "wiring: plugin namespace on spawns and the /st alias", check_namespaced_invocation),
    ("D", "wiring: referenced references/ files exist", check_referenced_reference_files),
    ("D", "wiring: st-thinker definition and fallback prompt in sync", check_thinker_prompt_sync),
    ("D", "wiring: thinker-prompt substitution variables", check_thinker_prompt_variables),
    ("D", "wiring: st-armorer definition and fallback prompt in sync", check_armorer_prompt_sync),
    ("D", "wiring: st-armorer assembles section 5 with assemble-pack.py", check_armorer_assembles_with_script),
    ("D", "wiring: section 5 module marker forms match the SSOT", check_module_marker_forms),
    ("D", "wiring: session Bash instructions are single commands", check_session_bash_single_commands),
    ("D", "wiring: SKILL.md arming Bash stays inside the rule bundle", check_skill_bash_inside_bundle),
    ("D", "wiring: lifecycle.md Bash is the bundle or a recorded exception", check_lifecycle_bash_inventory),
    ("D", "wiring: headless gate signals and branches", check_headless_gate_branch),
    ("E", "schema: evolution-state.md v3 header", check_evolution_state_schema),
    ("E", "schema: profile.md v3 header", check_profile_schema),
    ("E", "schema: profile.md six blocks in order", check_profile_blocks),
    ("E", "schema: run goal asked at the gate, not in init", check_goal_asked_at_gate),
    ("E", "schema: shipped .data is a blank seed", check_data_is_empty_seed),
    ("E", "vault: {VAULT} comes from resolve-vault.py", check_vault_resolver_wiring),
    ("E", "vault: permission rule is ~/ or // in the resolved settings", check_permission_rule_format),
    ("E", "vault: no pre-#20 default vault path in the conventions", check_no_old_default_vault),
    ("F", "v2: no --deep mode in SKILL.md", check_no_deep_flag),
    ("F", "v2: SKILL.md frontmatter has no effort/argument-hint", check_skill_frontmatter_clean),
    ("F", "v2: no legacy prefix alias mapping", check_no_legacy_prefix_aliases),
    ("F", "v2: no live st-searcher wiring", check_no_searcher_wiring),
    ("G", "hygiene: no em dash in editable files", check_no_em_dash),
    ("G", "hygiene: no private information", check_no_private_information),
    (PACK_GROUP, "pack: pack.md and manifest.json exist", check_pack_files),
    (PACK_GROUP, "pack: manifest schema and boolean research", check_pack_manifest),
    (PACK_GROUP, "pack: section titles present and ordered", check_pack_sections),
    (PACK_GROUP, "pack: section 5 verbatim hash integrity", check_pack_verbatim_integrity),
    (PACK_GROUP, "pack: module markers scoped to section 5", check_pack_markers_scoped),
)


def run_check(function, context: Context) -> Result:
    """One failing check must never stop the rest of the gate."""
    try:
        # Pack checks need the CLI context; the repo-only checks take no argument.
        if function.__code__.co_argcount:
            return function(context)
        return function()
    except Exception:  # noqa: BLE001 - a crashing check is a failing check, not a crash
        detail = traceback.format_exc().strip().splitlines()[-1]
        return Result(STATUS_FAIL, f"the check itself raised: {detail}", traceback.format_exc().splitlines())


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SmartThink v3 structure and wiring gate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", action="store_true", help="print the evidence behind each check")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat SKIP as FAIL (final gate). SKIPs that only mean 'not requested' stay SKIP.",
    )
    parser.add_argument(
        "--pack",
        type=Path,
        metavar="DIR",
        help="also verify a real armory pack directory (or its pack.md)",
    )
    parser.add_argument(
        "--digest",
        action="store_true",
        help="with --pack: the pack is a --digest pack, so section 5 uses MODULE-DIGEST and hashes are waived",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    context = Context(
        pack=arguments.pack.resolve() if arguments.pack else None,
        digest=arguments.digest,
        verbose=arguments.verbose,
        strict=arguments.strict,
    )

    passed = failed = skipped = 0
    pack_passed = pack_failed = pack_skipped = 0
    for group, name, function in CHECKS:
        result = run_check(function, context)
        status = result.status
        if status == STATUS_SKIP and context.strict and result.promotable:
            status = STATUS_FAIL
            result.detail = f"promoted by --strict: {result.detail}"

        label = f"{group}. {name}"
        if group == PACK_GROUP:
            if status == STATUS_PASS:
                pack_passed += 1
            elif status == STATUS_SKIP:
                pack_skipped += 1
            else:
                pack_failed += 1
        if status == STATUS_PASS:
            passed += 1
            print(f"{STATUS_PASS} {label}" + (f": {result.detail}" if context.verbose and result.detail else ""))
        elif status == STATUS_SKIP:
            skipped += 1
            print(f"{STATUS_SKIP} {label}: {result.detail}")
        else:
            failed += 1
            print(f"{STATUS_FAIL} {label}: {result.detail}")

        if context.verbose:
            for line in result.evidence:
                print(f"       - {line}")
        elif status == STATUS_FAIL:
            for line in result.evidence:
                print(f"       - {line}")

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    print(f"pack: {pack_passed} passed, {pack_failed} failed, {pack_skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
