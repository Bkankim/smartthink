# T11 트랜스크립트 - 플러그인 설치 방식과 호출 이름

생성 시각: 2026-09-08T02:44+09:00 | 세션: `claude --plugin-dir .` (리포 루트) | 임시 vault: $SMARTTHINK_VAULT = [REDACTED]/smartthink-v3-gates-20260908-020434

> 테스터가 모델이므로 슬래시 입력을 Skill 도구 호출로 재현했다. 각 호출의 결과 첫 줄(`Base directory for this skill: ...`)이 어느 SKILL.md가 열렸는지의 실측 증거다.

---

**[입력 1]** `/st status`  (→ Skill("st", "status"))
```
Launching skill: st
Alias for /smartthink. Invoke Skill tool: `Skill("smartthink", "status")`
```
→ `/st`는 전역 `~/.claude/commands/st.md` 별칭이며 **bare `smartthink`** 스킬로 넘긴다.

**[입력 2]** `/smartthink:st status`  (→ Skill("smartthink:st", "status"))
```
Launching skill: smartthink:st
Invoke the `smartthink` skill with the Skill tool, passing `status` through unchanged.
```
→ 플러그인 별칭(commands/st.md)도 **bare `smartthink`** 이름으로 넘긴다.

**[입력 3]** `/smartthink status`  (→ Skill("smartthink", "status"))
```
Launching skill: smartthink
Base directory for this skill: [REDACTED]/.claude/skills/smartthink

# 천재적 사고 엔진 시스템 (Genius Thinking Engine System)

3가지 모드로 동작한다:
- **Agent** (기본값) — 서브에이전트(STSA: SmartThink Sub-Agent)에 분석을 위임한다. ...
- **Deep** (`--deep`) — ...
- **Light** (`--lite`) — ...
```
→ bare `smartthink`는 **전역 v2 SKILL.md**(`~/.claude/skills/smartthink`)를 연다. v3 플러그인이 아니다. (테스터는 v2 지시를 실행하지 않고 관찰만 했다. v2에는 `status` 서브커맨드가 없어 주제로 취급된다.)

**[입력 4 - T1에서 실측]** `/smartthink:smartthink init`  (→ Skill("smartthink:smartthink", "init"))
```
Launching skill: smartthink:smartthink
Base directory for this skill: [REDACTED]/workspace/smartthink/skills/smartthink

# SmartThink v3 - 컨텍스트 무장 엔진 (Context Armory Engine)
```
→ **`smartthink:smartthink`만 플러그인 v3 SKILL.md를 연다.** `${CLAUDE_SKILL_DIR}` 플레이스홀더는 로더가 실제 경로로 치환해 전달했다.

**[입력 5]** `/smartthink:smartthink 지역 보행자 안전 안내를 개선해줘`

**[스킬 - 재무장 경고]** 표시(이전 주제 4개) → **[테스터]** Enter

**[스킬 출력 - 게이트]**
```
━━ SmartThink 무장 게이트 ━━

1. 입력 해석
   지역(동네 단위) 보행자 안전 안내(표지·노면 표시·안내판·알림)의 현행 체계를 진단하고
   위험 인지와 안전 행동으로 이어지도록 개선안을 만드는 작업.

2. 진단
   Cynefin: Complicated  |  분류: 문제 해결

3. 추천 모듈 (5개, ★ = 주력)
   ★ 핵심 엔진 - 제1원리(안내의 목적을 "정보 제공"이 아닌 "위험 인지·행동 유도"로 재정의)와 역전 사고(안내가 무시되는 경로)
   ★ 인지 무기고 - 주의 한계·위험 지각·익숙함 편향을 안내 배치·문구 기준으로
   ★ 패턴 합성 - 통학로·교차로·골목·야간의 반복 위험 신호를 안내 체계로 묶기
     TRIZ 혁신 시스템 - "눈에 띄되 과밀하지 않게" 모순의 분리 원칙
     실행 속도 - 현장 소규모 실험으로 안내 개선안을 빠르게 검증하는 루프

4. 예상 비용 (추정치)
   메인에 실릴 팩      ≈ 131K 토큰  (원문 124.2K + 적용 레이어 2.0K + 1·2·6절 2K + 3절 3K)
   서브에이전트 작업    ≈ 144K 토큰  (원문 124.2K + 리서치·합성 15K + 쓰기·정리 5K)
   ※ 두 값 모두 추정이며 실제와 다를 수 있습니다. (index.json 사전 계산값)

5. 리서치: ON (기본)

6. 조작
   Enter    진행
   숫자     예산 상한 지정 (예: 60000)
   모듈 ±   추가·제거
   --nosearch  리서치 끄기
```
**[테스터]** 진행하지 않음 - 스킬 진입(T2와 같은 게이트)이 관찰됐고, 다섯 번째 팩 생성은 이 게이트의 목적 밖이라 여기서 멈췄다. (참고: 같은 주제·같은 형식의 게이트를 Codex가 리포 SKILL.md를 읽고 출력한 것이 T13-blocked.md에 있다.)

**[에이전트 이름 - T2에서 실측]** `Agent(subagent_type: "st-armorer")` → not found. 목록에 `smartthink:st-armorer`, `smartthink:st-thinker`(플러그인)와 bare `st-thinker`, `st-searcher`(전역 v2)가 공존. 이후 모든 게이트는 `smartthink:st-armorer` / `smartthink:st-thinker`로 스폰했다.

---
**판정: PASS** - `/skills` 상당 목록에 SmartThink 스킬이 보이고 agents/·commands/가 플러그인 루트에서 인식됨(네임스페이스 `smartthink:`). 실제 성공한 호출 이름은 **`/smartthink:smartthink`** 이며 이 기록이 게이트의 목적이다. 단 별칭 `/st`는 "SmartThink와 같은 스킬"이 아니라 이 머신의 전역 v2를 호출한다(아래 관찰 파일).
