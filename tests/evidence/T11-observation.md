# T11 관찰 - 호출 이름과 agents 등록 필드

실측 환경: Claude Code 2.1.263, `claude --plugin-dir .` (리포 루트 v3), 전역 v2 설치가 남아 있는 머신(`~/.claude/skills/smartthink`, `~/.claude/commands/st.md`, `~/.claude/agents/st-thinker.md`, `~/.claude/agents/st-searcher.md`).

## 1. 호출 이름

| 입력 | 실제로 열리는 것 | 근거 |
|---|---|---|
| `/smartthink:smartthink` | **플러그인 v3** SKILL.md | Base directory = 리포/skills/smartthink |
| `/smartthink` | 전역 **v2** SKILL.md | Base directory = ~/.claude/skills/smartthink |
| `/st` | 전역 v2 별칭 → bare `smartthink` → **v2** | 별칭 본문 `Skill("smartthink", ...)` |
| `/smartthink:st` | 플러그인 별칭 → bare `smartthink` → **v2** | 별칭 본문 "Invoke the `smartthink` skill" |

- `/smartthink` 단축 호출은 **되지 않는다**(전역 v2가 bare 이름을 선점). 플러그인 스킬은 **네임스페이스가 붙은 `/smartthink:smartthink`** 로만 열린다.
- 전역 v2를 제거한 환경에서 bare `smartthink`가 플러그인으로 해석되는지는 이 세션에서 확인할 수 없었다(전역 설치를 건드리지 않음).
- 플러그인 자체 별칭 `commands/st.md`가 bare `smartthink`를 호출하므로, 이름 충돌 환경에서는 플러그인 별칭이 v2로 새어 나간다. 별칭이 `smartthink:smartthink`를 지정해야 자기 플러그인을 가리킨다.

## 2. 에이전트 이름

- 플러그인 `agents/st-armorer.md`, `agents/st-thinker.md`는 `smartthink:st-armorer`, `smartthink:st-thinker`로 등록된다. SKILL.md가 지시하는 bare `subagent_type: "st-armorer"`는 "not found"(T2 실측)이고, bare `"st-thinker"`는 전역 v2 정의를 조용히 가리킨다(오류 없이 다른 에이전트가 뜬다).
- `check-structure.py` D. wiring "spawned sub-agent names resolve to agents/"는 파일 존재만 보므로 이 런타임 이름 차이를 잡지 못한다.

## 3. plugin.json에 agents 등록 필드가 필요한가

**필요 없다.** `.claude-plugin/plugin.json`에는 name/version/description/author/homepage/repository/license/keywords만 있고 `agents`·`commands`·`skills` 필드가 없는데도 `agents/`, `commands/`, `skills/`가 루트 자동 인식으로 전부 등록됐다(위 목록). 등록 이름은 `<plugin name>:<file basename>` 규칙.

## 4. 기타

- `${CLAUDE_SKILL_DIR}`은 Skill 도구가 본문에 치환해 넣어 준다(모델 env에는 없음). SKILL.md의 "미해석이면 위치에서 추론" 폴백은 이 세션에서 필요 없었다.
- 이 세션의 Agent 도구는 `run_in_background` 파라미터가 없고 항상 백그라운드 + 완료 알림이다. SKILL.md의 "동기 스폰"은 알림 대기로 구현된다.
