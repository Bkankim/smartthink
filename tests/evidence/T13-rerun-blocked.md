# T13 재실측 BLOCKED 기록 (#8)

실행일: 2026-09-26 22:56~23:17 (+09:00) | 세부: `T13-rerun-transcript.md`, 팩 `T13-rerun-pack.md`, `T13-rerun-manifest.json`

## 판정

**BLOCKED** - 이 게이트의 목적인 "Agent 도구가 없는 Codex의 인라인 경로"가 이 환경에서 성립하지 않는다. 설치된 Codex(0.155.1, `multi_agent = true`, `[features.multi_agent_v2] enabled = true`)에는 서브에이전트 도구 `spawn_agent`/`wait_agent`가 있어, 스킬 0단계가 armorer 경로를 고른 것은 명세대로다. 인라인 안내문 `이 환경에는 Agent 도구가 없어 리서치를 메인이 직접 수행합니다.`는 두 회차 모두 표시되지 않았다.

## 시도한 호출과 오류 원문

| 시도 | 명령·입력 | 결과 원문 |
|---|---|---|
| 1 | `/smartthink 지역 보행자 안전 안내를 개선해줘` | `• Unrecognized command '/smartthink'. Type "/" for a list of supported commands.` |
| 2 | `/skills` → `1. List skills` → `smartthink` | `smartthink (smartthink)  [Skill] ALWAYS use this skill before ...` (등록 확인) |
| 3 | `$smartthink` + 과제 (env만 셸에서 지정) | resolver `{"path": "~/.claude/smartthink-vault", "source": "default"}` - TUI 셸 env가 데몬 명령에 전달되지 않음. 실제 vault `ls`·`head` 읽기 발생, 테스터가 즉시 중단(쓰기 없음, mtime 불변) |
| 4 (run1) | `codex -c 'shell_environment_policy.set.SMARTTHINK_VAULT="<VAULT1>"'` + `$smartthink` 과제 | resolver `source: env`. 게이트 → `진행` → `spawn_agent(st_armorer)` → 팩 생성, H 5/5, 브리핑 후 턴 종료. 인라인 안내 없음 |
| 5 (run2) | `codex --disable multi_agent --disable multi_agent_v2 -c ...` + 같은 입력 | 여전히 `spawn_agent` 호출(도구 호출 집계 `exec 4, spawn_agent 1, wait_agent 1`). 인라인 안내 없음. armorer가 manifest.json을 못 써 메인이 작성, H 5/5 |
| 6 | `codex exec -c features.multi_agent_v2.enabled=false -c features.multi_agent=false '<도구 이름 나열>'` | `... custom_collaboration__spawn_agent, custom_collaboration__wait_agent, web_search` (도구가 남음) |

## 다음에 필요한 조건

- 서브에이전트 도구가 실제로 없는 Codex 세션(멀티 에이전트 기능이 없는 버전·설정). 도구 목록에 `spawn_agent`가 없음을 먼저 확인한다.
- 그 외 조건(스킬 등록, 리포 밖 cwd, `-c shell_environment_policy.set.SMARTTHINK_VAULT`, `$smartthink` 호출)은 이번 재실측으로 확립돼 gates.md T13 사전 조건에 반영했다.

## 이번에 충족된 부분 (참고)

Codex 스킬 진입, env vault 사용, 게이트 6항목·비용 2단위, 팩 6절 제목 순서, manifest 11필드(`harness: "codex"`), `check-structure.py --pack` H 5/5 exit 0, 1절 브리핑 후 `무장 완료. 이제 작업을 지시하세요.`로 턴 종료.
