# 37 - 게이트 목표 분기 (모드 B) 수정 전 / 수정 후 / 되돌림 확인

## 1. 수정 전(HEAD=origin/main 0d2dd64의 `git archive` 사본)에서 검사기가 analysis-method.md를 보지 않음

$ grep -c "게이트에서 답한 목표" skills/smartthink/references/analysis-method.md
0
$ sed -n "/^GOAL_HANDOFF_LINES/,/^)/p" scripts/check-structure.py
GOAL_HANDOFF_LINES = (
    (SKILL_MD, "- **Interpretation**:"),
    (SKILL_MD, "    2. 작업 해석 ("),
    (ARMORER_MD, "- **주제만 온 경우**:"),
    (ARMORER_PROMPT_MD, "- **주제만 온 경우**:"),
)
$ python3 scripts/check-structure.py | grep "E. schema: run goal"
PASS E. schema: run goal asked at the gate, not in init

## 2. 수정 후 작업 트리

$ grep -n "게이트에서 답한 목표" skills/smartthink/references/analysis-method.md | cut -c1-120
75:1. **작업 해석** - 팩 2절 초안. 작업이 온 경우는 재진술. 주제만 온 경우 게이트에서 답한 목표(목표·성공 기준)가 있으면 그 목표의 재진술이고, 그 답이 없을 때만 예상 작업 A/B/C
84:   - **풀 3 - 작업 해석 유래**: 게이트에서 답한 목표가 있으면 그 목표를 익숙한 다른 작업으로 바꿔 읽어 목표·성공 기준에서 벗어나는 것. 그 답이 없을 때만 예상 작업 A/B/C 중 익숙한 하나로
87:3. 각 편향을 아래 형식 3줄로 쓴다. **일반론 금지** - "확증 편향을 조심하라"처럼 어느 작업에나 붙는 문장은 실격이다. 이 작업의 고유명사(주제·모듈명·게이트에서 답한 목표의 핵심어, 그 답이 없으면
$ python3 scripts/check-structure.py | grep "E. schema: run goal"
PASS E. schema: run goal asked at the gate, not in init

## 3. 분기 문구 임시 제거(작업 트리 수정 -> 실행 -> 원복)

(분기 문구를 "주제만 온 경우는 예상 작업 A/B/C"로 되돌린 상태)
$ python3 scripts/check-structure.py; echo exit=$?   (E절 줄과 요약만 발췌)
FAIL E. schema: run goal asked at the gate, not in init: the run's goal is not taken at the arming gate or does not reach the pack
  - skills/smartthink/references/analysis-method.md: the '1. **작업 해석** - 팩 2절 초안.' line does not carry the 게이트에서 답한 목표 to pack section 2
41 passed, 1 failed, 5 skipped
pack: 0 passed, 0 failed, 5 skipped
exit=1

## 4. 원복 후

$ grep -c "그 답이 없을 때만 예상 작업 A/B/C" skills/smartthink/references/analysis-method.md
2
$ python3 scripts/check-structure.py | grep -E "E. schema: run goal|passed"
PASS E. schema: run goal asked at the gate, not in init
42 passed, 0 failed, 5 skipped
pack: 0 passed, 0 failed, 5 skipped
