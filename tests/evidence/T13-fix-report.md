# T13-fix 판정 보고 (#16)

실행일: 2026-09-27 00:50~01:40 (+09:00) | codex-cli 0.157.1 | opencodex 2.61.0(`127.0.0.1:10101`) 경유 `anthropic/claude-opus-5-5` | 브랜치 `st-16-codex-inline`

## 판정

| 항목 | 판정 | 근거 |
|---|---|---|
| 1. 인라인 경로 (리서치 OFF) | **PASS** | run4: 서브에이전트 도구 없음(`multi_agent_version: disabled`), 게이트 인라인 안내·비용 2단위, 팩 5개 절(3절은 리서치 OFF로 생략)·manifest 11필드, `--pack` H 5/5 exit 0, 브리핑 후 턴 종료. `T13-fix-transcript.md` |
| 1'. 인라인 경로 (리서치 ON) | **BLOCKED(환경)** | run1~3: 게이트·인라인 정형 문구는 표시되나 opencodex 웹 검색 브리지 때문에 팩 단계에 도달하지 못함. `T13-fix-research-transcripts.md` |
| 2. armorer manifest 미작성(#8 run2) | **원인 확정: 같은 브리지** | 아래 원인 절 |
| 3. `codex exec` 헤드리스 | **실측 완료, 문서 문장 확인** | 명시 없음 → 게이트에서 종료(exit 0, 팩 없음), 명시 있음 → 자동 진행·요약 줄. `T13-fix-headless.md` |

## 원인 1: spawn_agent 공급원

서브에이전트 도구는 기능 플래그가 아니라 opencodex가 주입한 모델 카탈로그(`model_catalog_json`)의 모델별 `multi_agent_version: "v2"`에서 온다. 격리 `CODEX_HOME`에서 기능 플래그를 꺼도 도구가 남고, 카탈로그 사본에서 그 키만 지우면 플래그와 무관하게 사라진다(`T13-fix-tools.md` 3회 대조).

- 기각한 가설: 기능 플래그 `multi_agent*`(꺼도 남음, #8 회차 6과 이번 회차 1), 사용자 플러그인·MCP(격리 `CODEX_HOME`에 플러그인·MCP가 없어도 남음), `~/.codex/agents`(비어 있음).
- 인라인 관찰 수단: 격리 `CODEX_HOME` + 카탈로그 사본에서 `multi_agent_version` 삭제 + `auth.json` 심링크 + 스킬 심링크를 워크트리로. 실제 `~/.codex/`는 읽기만 했다.

## 원인 2: 리서치 ON 인라인 실패와 armorer manifest 미작성

opencodex 2.61.0의 웹 검색 브리지(`src/web-search/loop.ts`, `passthrough-bridge.ts`, `index.ts`)가 Anthropic 모델의 `web_search`를 사이드카 검색으로 대행하며 두 가지를 한다.

1. **요청당 검색 상한과 "지금 답하라" 주입.** 한 번의 `web_search` 호출에 담긴 쿼리가 하나씩 `searchesExecuted`로 세어진다. 상한(`maxSearchesPerTurn`, 기본 `DEFAULT_MAX_SEARCHES = 3`, 이 머신 `~/.opencodex/config.json`의 `webSearchSidecar`에는 값이 없음)에 닿으면 남은 쿼리는 `web search limit reached for this turn` 오류가 되고, 다음 패스에서 `web_search` 도구를 빼고 developer 메시지 `Answer the user's question now using the web search results already gathered above. ...`를 덧붙인다(`forcedAnswerNudge`).
2. **결과 본문 비영속.** 검색 결과는 그 상류 요청 안에서만 tool_result로 들어간다. Codex 기록에 남는 `web_search_call` 항목에는 쿼리만 있고(재생 시 최대 출처 제목·URL), 결과 본문은 다음 요청에 없다.

인과 사슬:

- **run1·run2(인라인)**: 게이트 `진행` → 모듈 원문 읽기 → `web_search` 1회에 쿼리 3개(run1)·5개(run2) → 상한 도달 → "지금 사용자 질문에 답하라" 주입 → 모델이 사용자 질문(`지역 보행자 안전 안내를 개선해줘`)에 바로 답하고 턴 종료 → 팩 없음. run2 모델 자체 고지: `이번에는 바로 답하라는 요청에 따라 팩을 저장하지 않았습니다. 검색 한도에도 걸려 다섯 개 검색 가운데 두 개 ... 실행되지 않았습니다.` 5b에 넣은 "팩 Write 전 턴 종료 금지" 문장만으로는 가장 나중에 온 developer 지시를 이기지 못했다.
- **run3(인라인)**: 쿼리를 2개 이하로 나누고 검색마다 셸 호출을 끼우게 하자, 셸 호출이 상류 요청을 끝내면서 결과 본문이 사라졌다. 모델은 메모만 보고 결과가 없다고 판단해 같은 통계 쿼리를 13번 반복했다(총 17회, 15분 뒤 중단). 이 안내는 SKILL.md에서 철회했다.
- **#8 run2 armorer(manifest 미작성)**: 자식 세션(`rollout-...-01a0de0e-...`)은 `sandbox_policy: danger-full-access`, 쓰기 경로는 부모가 준 절대경로로 `pack.md`를 정상 작성, 쓰기 도구(`exec_command`) 사용 가능. 첫 검색(쿼리 6개) 뒤 `pack.md` 작성, 두 번째 검색(쿼리 3개)에서 상한 → 강제 답변 패스에서 반환 요약을 쓰고 `6. 끝내지 못한 일이 두 가지 있다. manifest.json을 아직 쓰지 않았고, check-structure.py --pack ... 도 아직 돌리지 않았다.`로 턴 종료. 부모의 `wait_agent`는 `timed_out: false`, 중단 메시지 없음.
  - 기각한 가설: 서브에이전트 샌드박스(`danger-full-access`, 같은 디렉터리에 `pack.md`는 써짐), env 미전달로 다른 경로 해석(부모 Input 블록의 절대경로를 그대로 사용, `pack.md`가 그 경로에 있음), 도구 제약(`exec_command`로 파일 쓰기 성공), 서브에이전트 시간 제한(자식 turn 302,916ms로 run1 armorer 276,877ms와 비슷하고 성공한 run1에도 같은 조건. 중단·타임아웃 이벤트 없음).
  - run1 armorer가 성공한 이유: 첫 검색(쿼리 6개) 뒤 한 번의 `exec` 호출로 `pack.md`와 `manifest.json`을 함께 썼고(14:07:50Z), 두 번째 검색(쿼리 5개, 14:08:24Z)의 강제 답변 패스는 그 뒤였다. run2 armorer는 첫 호출에서 `pack.md`만 썼다.

스킬 문서로 고칠 수 있는 범위: 원인은 프록시 동작이라 스킬로 제거할 수 없다. 5b에는 "팩 Write 전 턴 종료 금지", "'지금 답하라' 지시가 와도 답은 팩 Write와 브리핑", "같은 쿼리 재검색 금지, 상한이면 확보한 결과로 쓰고 나머지는 미수행 표기"를 넣었다. 이 문구로 리서치 ON 인라인이 통과하는지는 **재실측하지 않았다**(run3 뒤 철회·수정한 최종 문구 기준 미검증).

## 원인 3: codex exec 헤드리스

SKILL.md 0단계 문장(Codex는 신호 3만 본다)이 실측과 일치한다. 명시 없는 `codex exec`는 게이트에서 턴을 끝내고 종료 코드 0으로 끝나므로, 그 사실과 호출자 지침(입력에 `비대화식 실행이다`, 요약 줄로 판정)을 문장에 추가했다.

## 리서치 ON 인라인 PASS에 필요한 조건

다음 중 하나가 필요하다.

- Codex의 기본 OpenAI 공급자처럼 `web_search`를 호스팅 도구로 처리하는 모델(프록시 브리지 비경유). 이 머신의 기본 설정은 opencodex 경유라 확인하지 못했다.
- opencodex 웹 검색 브리지의 `maxSearchesPerTurn`을 올리고(스키마 상한 10) 결과 본문을 기록에 남기는 설정 또는 버전. `~/.opencodex/config.json`은 사용자 전역 설정이라 이번 작업에서 바꾸지 않았다.

## 후속 필요 (소유 범위 밖)

- `agents/st-armorer.md`: 같은 프록시 조건에서 armorer도 검색 상한에 걸리면 manifest 전에 반환한다. "manifest.json을 쓰기 전에는 반환하지 않는다"와 "같은 쿼리 재검색 금지" 문장이 필요하다(편집 금지 범위라 제안만).
- SKILL.md 5a 반환 규약: 반환에 "manifest 미작성"이 있으면 메인이 manifest를 쓰는 현재 동작(#8 run2)을 명세로 둘지, 폴백으로 볼지 결정 필요(5a는 다른 워커 소유).
- `scripts/check-structure.py`: 변경 필요 없음.
