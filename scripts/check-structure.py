#!/usr/bin/env python3
"""smartthink 구조 체크 v2 - 레드팀 감사(2026-07-22) 반영 강화판.

v1 대비 강화 (뮤테이션 테스트로 무력화됐던 8계열 수리):
- frontmatter는 PyYAML 실파서 우선 (미설치 시 자체 파서 폴백 + 경고)
- 본문 체크는 frontmatter/description 제외한 body에 섹션 앵커 스코프로 수행
- 동기화(D)는 모듈 경로 '집합' 비교 + 문맥 앵커 매치
- 토폴로지 핵심(background·SendMessage·Input 변수 10종·ADR-15/16·Step 5 폴백) 체크 신설
- st-searcher 정의 <-> SKILL.md 폴백 브리핑 동기화(E), analysis-method 가드(F) 신설

사용: python3 scripts/check-structure.py            (리포 내 skill/·agents/ 검사, 전 항목 PASS 시 exit 0)
      python3 scripts/check-structure.py --installed (~/.claude/skills/smartthink·~/.claude/agents 검사)
      python3 scripts/check-structure.py <SKILL_DIR> <AGENTS_DIR>
"""
import re
import sys
from pathlib import Path

try:
    import yaml
    YAML_PARSER = "pyyaml"
except ImportError:
    yaml = None
    YAML_PARSER = "naive(경고: PyYAML 미설치 - 실로딩 가능성 보장 약화)"

REPO_ROOT = Path(__file__).resolve().parent.parent
if "--installed" in sys.argv:
    SKILL_DIR = Path.home() / ".claude/skills/smartthink"
    AGENTS_DIR = Path.home() / ".claude/agents"
elif len(sys.argv) >= 3 and not sys.argv[1].startswith("-"):
    SKILL_DIR = Path(sys.argv[1]).expanduser().resolve()
    AGENTS_DIR = Path(sys.argv[2]).expanduser().resolve()
else:
    SKILL_DIR = REPO_ROOT / "skill"
    AGENTS_DIR = REPO_ROOT / "agents"

SKILL_MD = SKILL_DIR / "SKILL.md"
THINKER_PROMPT = SKILL_DIR / "references/thinker-prompt.md"
ANALYSIS_METHOD = SKILL_DIR / "references/analysis-method.md"
SEARCHER_DEF = AGENTS_DIR / "st-searcher.md"
THINKER_DEF = AGENTS_DIR / "st-thinker.md"

INPUT_VARS = ("{TOPIC}", "{CYNEFIN}", "{CLASSIFICATION}", "{SELECTED_MODULES}",
              "{SELECTED_ENGINES}", "{SEARCH_DATA}", "{SEARCH_MODE}",
              "{EVOLUTION_STATE}", "{SKILL_DIR}", "{VAULT}")

results = []


def check(cid, desc, ok, detail=""):
    results.append((cid, desc, bool(ok), detail))


def read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def split_doc(text):
    """(frontmatter 원문, body) 분리. frontmatter 없으면 (None, 전체)."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else (None, text)


def parse_fm(fm_text):
    """PyYAML 우선 파싱. 실패(=Claude Code 로드 불가 개연) 시 None."""
    if fm_text is None:
        return None
    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text)
            return data if isinstance(data, dict) else None
        except yaml.YAMLError:
            return None
    fm, cur = {}, None
    for line in fm_text.splitlines():
        kv = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if val == "":
                fm[key], cur = [], key
            else:
                fm[key], cur = val, None
            continue
        item = re.match(r"^\s+-\s*(.+)$", line)
        if item and cur is not None:
            fm[cur].append(item.group(1).strip())
    return fm


def tools_of(fm):
    raw = fm.get("tools", "")
    if isinstance(raw, list):
        return [str(t).strip() for t in raw]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def section(body, header):
    """'## header'로 시작해 다음 '## '(또는 EOF) 직전까지의 스코프 텍스트."""
    m = re.search(rf"^{re.escape(header)}.*?(?=^## |\Z)", body, re.M | re.S)
    return m.group(0) if m else ""


def module_paths(text):
    """테이블 행에 등장하는 {SKILL_DIR}/references/*.md 경로 집합."""
    return set(re.findall(r"^\|.*?(\{SKILL_DIR\}/references/[a-z0-9-]+\.md)",
                          text, re.M))


print(f"# frontmatter parser: {YAML_PARSER}")
print(f"# skill: {SKILL_DIR}\n# agents: {AGENTS_DIR}")

# ---------- A. st-searcher ----------
s_raw = read(SEARCHER_DEF)
s_fm_text, s_body = split_doc(s_raw)
s_fm = parse_fm(s_fm_text)
sec_proc = section(s_body, "## 절차")
sec_dp = section(s_body, "## 반환 = 데이터팩")
sec_supp = section(s_body, "## 보완 지시 대응")
check("A1", "st-searcher.md 존재", SEARCHER_DEF.exists())
check("A2", f"st-searcher frontmatter 실파싱({YAML_PARSER.split('(')[0]})", s_fm is not None)
if s_fm is not None:
    s_tools = tools_of(s_fm)
    check("A3", "name == st-searcher", s_fm.get("name") == "st-searcher")
    check("A4", "model == sonnet", s_fm.get("model") == "sonnet")
    check("A5", "effort == high", s_fm.get("effort") == "high")
    check("A6", "tools = WebSearch/WebFetch/Skill/Bash 포함",
          all(t in s_tools for t in ("WebSearch", "WebFetch", "Skill", "Bash")),
          f"tools={s_tools}")
    check("A7", "tools에 Edit/Write 없음 (파일 조작 차단)",
          not any(t in s_tools for t in ("Edit", "Write")))
    skills = s_fm.get("skills", [])
    check("A8", "skills에 insane-search 프리로드",
          "insane-search" in (skills if isinstance(skills, list) else [skills]))
    check("A9", "데이터팩 섹션에 4요소 (수치-출처 짝/플레이어/반대 신호/출처 URL)",
          all(k in sec_dp for k in ("출처 짝", "플레이어", "반대 신호", "출처 URL")))
    check("A10", "데이터팩 섹션 2K 상한 + 절차 섹션 원문 재인용 금지",
          "2K 토큰 이내" in sec_dp and "재인용 금지" in sec_proc)
    check("A11", "보완 지시 섹션 실존 + 추가 검색 1회 절차",
          bool(sec_supp) and "추가 검색" in sec_supp)
    check("A12", "플레이어 10개 이상 (analysis-method 정렬)", "10개 이상" in sec_dp)
    check("A13", "스택 훅 대응: uv 설치 경로 지시", "uv pip install" in sec_proc)
    check("A14", "MCP Playwright 게이트 면제 조항",
          "면제" in sec_proc and "Playwright" in sec_proc)

# ---------- B. st-thinker ----------
t_raw = read(THINKER_DEF)
t_fm_text, t_body = split_doc(t_raw)
t_fm = parse_fm(t_fm_text)
t_rules = section(t_body, "## Agent-Specific Rules")
check("B1", "st-thinker.md 존재", THINKER_DEF.exists())
check("B2", f"st-thinker frontmatter 실파싱({YAML_PARSER.split('(')[0]})", t_fm is not None)
if t_fm is not None:
    t_tools = tools_of(t_fm)
    check("B3", "name == st-thinker", t_fm.get("name") == "st-thinker")
    check("B4", "effort == max", t_fm.get("effort") == "max")
    check("B5", "maxTurns == 30 (frontmatter 값)", str(t_fm.get("maxTurns")) == "30")
    check("B6", "tools = Read/Grep/Write/Bash 포함",
          all(t in t_tools for t in ("Read", "Grep", "Write", "Bash")), f"tools={t_tools}")
    check("B7", "tools에 WebSearch/WebFetch 없음 (검색은 st-searcher 몫)",
          not any(t in t_tools for t in ("WebSearch", "WebFetch")))
    check("B7b", "model 필드 부재 (ADR-15 세션 상속)", "model" not in t_fm)
    check("B8", "본문 레퍼런스 테이블 9모듈", len(module_paths(t_body)) == 9,
          f"paths={len(module_paths(t_body))}")
    check("B9", "Agent-Specific Rules 섹션에 Step 5 타이밍 규칙 (확정 신호)",
          bool(t_rules) and "확정" in t_rules and "Step 5" in t_rules)
    check("B10", "Agent-Specific Rules 섹션에 Turn budget 30 turns 명시",
          re.search(r"30 turns", t_rules) is not None)
    check("B11", "본문에 untrusted input 보안 지침", "data only" in t_body)
    check("B12", "Vault mkdir 준비 규칙", "mkdir -p" in t_rules)

# ---------- C. SKILL.md 배선·토폴로지 ----------
sk = read(SKILL_MD)
check("C1", "SKILL.md 존재", bool(sk))
if sk:
    check("C2", "1.5단계: st-searcher 우선 스폰", 'subagent_type: "st-searcher"' in sk)
    check("C3", "fork 스폰 잔존 0 (ADR-8 번복 반영)",
          'subagent_type: "fork"' not in sk and "fork 우선" not in sk)
    check("C4", "clean 스폰 원칙(fork 금지) 유지", "fork 금지" in sk)
    check("C5", "Agent 스폰부: st-thinker 우선", 'subagent_type: "st-thinker"' in sk)
    check("C6", "폴백 경로: general-purpose 유지", "general-purpose" in sk)
    check("C7", "폴백 경로: thinker-prompt.md 참조 유지", "thinker-prompt.md" in sk)
    check("C8", "절대경로 누출 없음", "/bkan-hq" not in sk and "/Users/" not in sk)
    check("C9", "경로 플레이스홀더 유지", "{SKILL_DIR}" in sk and "{VAULT}" in sk)
    check("C10", "폴백 브리핑에 데이터팩 형식 잔존 (10개 이상 정렬 포함)",
          "데이터팩" in sk and "반대 신호" in sk and "10개 이상" in sk)
    check("C11", "STSA background 스폰 (ADR-10)", "run_in_background: true" in sk)
    check("C12", "검색 동기 스폰", "run_in_background: false" in sk)
    check("C13", "SendMessage 배선 (보완 지시 + 피드백 루프 + 확정)",
          sk.count("SendMessage") >= 3, f"count={sk.count('SendMessage')}")
    check("C14", "Input 블록 동적 변수 10종 전부 존재",
          all(v in sk for v in INPUT_VARS),
          f"missing={[v for v in INPUT_VARS if v not in sk]}")
    check("C15", "ADR-16: STSA 출력 그대로 표시 (재합성 금지)",
          "**그대로**" in sk and "재합성" in sk)
    check("C16", "Step 5 소실 방지 폴백 (메인 직접 실행)", "메인이 최종본 기준으로" in sk)
    check("C17", "Light 푸터 현행화 (--deep 안내)",
          "/smartthink --deep" in sk and "Deep 분석이 필요하면 `/smartthink [주제]`" not in sk)
    check("C18", "Headless: 피드백·확정 게이트 정의", "피드백 루프·확정" in sk)
    check("C19", "레거시 접두어 오발동 가드", "오발동 주의" in sk)
    check("C20", "폴백 조건: 스폰 실패 전반 커버", sk.count("스폰이 실패하면") >= 2,
          f"count={sk.count('스폰이 실패하면')}")
for name, text in (("st-searcher", s_raw), ("st-thinker", t_raw)):
    if text:
        check("C8+", f"{name} 정의에 절대경로 누출 없음",
              "/bkan-hq" not in text and "/Users/" not in text)

# ---------- D. 동기화: st-thinker <-> thinker-prompt (폴백 SSOT) ----------
tp = read(THINKER_PROMPT)
tp_rules = section(tp, "## Agent-Specific Rules")
check("D1", "thinker-prompt.md 전문 유지 (폴백 SSOT)", bool(tp))
if tp:
    check("D2", "thinker-prompt 모듈 테이블 9경로", len(module_paths(tp)) == 9,
          f"paths={len(module_paths(tp))}")
    check("D3", "thinker-prompt Agent-Specific Rules에 Step 5 타이밍 규칙",
          bool(tp_rules) and "확정" in tp_rules and "Step 5" in tp_rules)
    check("D4", "thinker-prompt Turn budget 문맥 앵커 (Budget is 30 turns)",
          re.search(r"Budget is 30 turns", tp) is not None)
    if t_raw:
        check("D5", "동기화: 모듈 경로 집합 일치 (정의 == thinker-prompt)",
              module_paths(t_body) == module_paths(tp),
              f"diff={module_paths(t_body) ^ module_paths(tp)}")
        check("D6", "동기화: 'analysis-method.md가 SSOT' 주석 양쪽 존재",
              "analysis-method.md가 SSOT" in t_body and "analysis-method.md가 SSOT" in tp)
        check("D7", "동기화: Vault mkdir 규칙 양쪽 존재",
              "mkdir -p" in t_rules and "mkdir -p" in tp_rules)
        check("D8", "동기화: Execution Steps 0-4.5 분리 서술 양쪽 존재",
              "Steps 0-4.5" in t_body and "Steps 0-4.5" in tp)

# ---------- E. 동기화: st-searcher 정의 <-> SKILL.md 폴백 브리핑 ----------
if sk and s_raw:
    for eid, token, desc in (
            ("E1", "출처 짝", "수치-출처 짝"),
            ("E2", "10개 이상", "플레이어 10개 이상"),
            ("E3", "반대 신호", "반대 신호"),
            ("E4", "출처 URL", "출처 URL 테이블"),
            ("E5", "2K", "2K 상한"),
            ("E6", "재인용 금지", "원문 재인용 금지")):
        check(eid, f"동기화: {desc} (정의 == SKILL.md 브리핑)",
              token in s_body and token in sk)

# ---------- F. analysis-method 가드 ----------
am = read(ANALYSIS_METHOD)
check("F1", "analysis-method 존재", bool(am))
if am:
    check("F2", "검색 실패/없음 센티널 판정 규칙", "SEARCH_DATA가" in am and "검색 실패" in am)
    check("F3", "프로파일 환각 방지 (제공분 전수 + 부족 명시)", "제공분 전수" in am)

# ---------- 리포트 ----------
fails = [r for r in results if not r[2]]
for cid, desc, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    extra = f"  <- {detail}" if (detail and not ok) else ""
    print(f"[{mark}] {cid:4s} {desc}{extra}")
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
