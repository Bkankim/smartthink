# T8-headless: 정의 없는 git 없는 사본에서 `claude -p` 무장 - general-purpose 폴백

- 실행일: 2026-10-29 14:55 (+09:00), Claude Code 2.1.312, `claude -p --model opus --output-format stream-json --verbose`, 표준 입력 `/dev/null`.
- 코드: main 519b1e8을 `rsync --exclude .git --exclude .fablize --exclude .final-review`로 `<ROOT>/plugin`에 복사한 뒤 `agents/st-armorer.md`를 지웠다. 확인: `ls <ROOT>/plugin/agents` = `st-thinker.md`뿐, `.git` 0개. 리포의 정의는 건드리지 않았다(restore-check 해당 없음).
- 환경: 격리 `CLAUDE_CONFIG_DIR=<ROOT>/cfg`(사용자 레벨 agents·skills 없음), 가짜 `HOME=<ROOT>/home`, `SMARTTHINK_VAULT=<ROOT>/vault`, 작업 디렉터리 `<ROOT>/work`(git 아님). settings allow는 T12 예시대로 `Bash`·`Read`·`Glob`·`Grep`·`Edit/Write(//<ROOT>/vault/**)`·`WebSearch`·`WebFetch`·`Agent`·`Skill`, deny는 실제 vault·포인터·기본 위치. 인증은 자식 env에만(값 미기록). 첫 시도는 토큰 스크립트를 가짜 HOME 아래에서 불러 `Not logged in`(exit 1, 46ms)으로 끝났고, 토큰을 HOME 교체 전에 읽게 고쳐 재실행했다.
- 입력: `/smartthink:smartthink --nosearch 지역 박물관의 안내 표지 체계를 개선해줘` (비대화식 지시 문구 없음).
- 정리: 증거 추출 뒤 `<ROOT>`(plugin 사본·cfg·home·work·vault 포함)를 `rm -rf`로 지웠고 `ls <ROOT>` = `No such file or directory`로 부재를 확인했다. 실제 홈의 `~/.config/smartthink/vault-pointer`(mtime 2026-09-27)와 `~/.local/share/smartthink`(없음)는 그대로다.
- 남긴 증거: 이 파일, `T8-headless-manifest.json`(armorer의 manifest.json Write 원문, 11필드). 조립 뒤 pack.md 사본은 정리 전에 옮기지 않아 남지 않았다. 팩 검사 결과는 아래 `--pack` 출력이 유일한 근거다.
- 판정: **PASS**

## 1. 관찰

- init 이벤트의 에이전트 목록: `claude, Explore, general-purpose, Plan, smartthink:st-thinker, statusline-setup`. 두 armorer 이름이 모두 없다.
- 목록 우선 이름 해석(#34·#38): 목록에 두 이름이 없으므로 **실패 스폰 0회**. `smartthink:st-armorer`·bare `st-armorer` 시도 없이 메인이 `references/armorer-prompt.md`를 Read하고 바로 `general-purpose`를 스폰했다. git 이력 사용 0회.
- 폴백 prompt 대조: Agent `prompt`(14,348자)와 `references/armorer-prompt.md`를 줄 단위로 비교했다. 차이는 두 곳뿐이다: 파일 머리의 `---` 위 안내 블록(22줄)이 빠졌고, 끝의 자리표시 줄 `(이 아래에 메인이 SKILL.md 5a의 `## Input` 블록을 치환 완료 상태로 붙인다.)`이 `## Input` 블록 13줄로 바뀌었다. `---` 아래 본문은 한 글자도 바뀌지 않았다(파일 1절 규약대로 "구분선 아래 전문 + Input 블록").
- 게이트: 헤드리스라 6항목 게이트 블록 출력은 선택이다(SKILL.md 4단계, T12 기준). 판정 근거인 헤드리스 요약 줄은 아래에 있다. 비용은 브리핑 말미 `비용: 팩 ≈123K / 작업 ≈130K`과 게이트 추정 116K 대비 차이 고지로 나왔다.
- 첫 팩 접근 순서: stream 줄 번호로 armorer의 manifest.json Write(서브에이전트 이벤트) 뒤에 메인의 Glob(123행)과 pack.md Read(125행)가 온다. 완료 알림 전 팩 접근은 없다.
- 백그라운드: Agent 결과가 `Async agent launched successfully`였다. 메인은 1줄 고지(`무장 팩을 만드는 중입니다. 완료 알림이 오면 브리핑을 출력하겠습니다.`)만 내고 첫 result(7턴, 107.9s)를 냈다. `-p` 프로세스는 종료하지 않고 완료 알림을 받아 두 번째 result(3턴)에서 팩 Read와 브리핑을 냈다. exit 0. `subagent_stats.by_type = {general-purpose: 1}`, `started_in_background = 1`.
- 헤드리스 요약 줄(두 번째 result 원문): `헤드리스: 자동 진행 | 상한 120K | 절삭: 실행 속도 모듈 제외(-12.7K) | 복원: 없음 | 팩: <ROOT>/vault/packs/2026-10-29-local-museum-wayfinding-signage/ (실측 ≈123K, 상한 3K 초과)`. 초과는 절삭 1패스 규칙대로 고지만 했다(T12 기준상 FAIL 아님).
- 팩: `pack.md`·`manifest.json` 한 쌍, `python3 scripts/check-structure.py --pack <팩>` = `pack: 5 passed, 0 failed, 0 skipped`.
- 관찰 1건(판정 무관): 2.1.312 `-p`의 도구 목록에 **Glob·Grep이 없다**(init `tools`에 없음). 메인의 팩 존재 확인 `Glob`이 `No such tool available: Glob`으로 1회 실패한 뒤 Read로 확인했다. armorer는 반환 전에 확인용 Bash `ls <vault>/packs/`를 1회 썼다. SKILL.md 46행 세션 도구 규율 위반이다. 이 회차는 Bash 허용 설정이라 프롬프트가 없었지만, 같은 동작이 default 모드에서 나오면 프롬프트 1회가 된다. T16-rerun 대화형 두 회차의 armorer에는 `ls`가 없었다. 대화형 2.1.312에는 Glob이 있다(T16-rerun).

## 2. 수정 뒤 재실측 (같은 환경, 새 `<ROOT>` 매 회차)

1절 관찰(Glob·Grep 부재로 메인 Glob 실패, armorer `ls`)을 고친 뒤 같은 입력으로 다시 돌렸다. 수정: SKILL.md 세션 도구 규율·5a 반환 확인·5b 브리핑 전 확인, `agents/st-armorer.md`·`references/armorer-prompt.md`의 확인용 Bash 금지 줄에 "도구 목록에 Glob·Grep이 없으면 Read로 확인하고 `ls`·`grep`으로 대신하지 마라", 폴백 프롬프트 도구 줄에 "Grep·Glob도 목록에 있을 때만".

| 회차 | 코드 | 없는 도구 호출 실패 | 규칙 밖 Bash | 실패 스폰 | 요약 줄 | `--pack` |
|---|---|---|---|---|---|---|
| run1 (1절) | main 519b1e8 | 1 (메인 Glob) | 1 (armorer `ls <vault>/packs/`) | 0 | 있음 | 5/5 |
| run2 | 1차 수정(Glob만) | 0 | 1 (armorer `grep -n ... analysis-method.md`) | 0 | 있음 | 5/5 |
| run3 | 2차 수정(Glob·Grep) | 1 (armorer Grep) | 0 | 0 | 있음 | 5/5 |
| run4 | 최종본(폴백 도구 줄 포함, 5b 문구 전) | 1 (메인 Glob) | 0 | 0 | 있음 | 5/5 |

- 규칙 밖 Bash(default 모드에서 프롬프트가 되는 호출)는 2차 수정부터 0회다. 이게 이 수정의 목적이다.
- 없는 도구 호출 실패 1회는 모델 비결정성으로 남는다. 프롬프트·오동작은 없고 다음 도구로 Read를 쓴다. run4 뒤 규칙을 3절처럼 하나로 고정해 다시 쟀다.

## 3. 최종본 재실측 (리뷰 반영 뒤, 2026-10-29 15:55)

2절의 조건 분기("Glob이 있으면 Glob, 없으면 Read")가 run3·run4에서 없는 도구 호출 실패를 남겼다. 그래서 규칙을 하나로 고정했다: 메인의 존재 확인은 `manifest.json` Read, pack.md는 6단계 Read가 확인(실패하면 반환 규약 위반으로 폴백), armorer는 Write 결과로 존재 확인을 대신한다. Grep·Glob은 도구 목록에 있을 때만 호출한다(armorer·thinker 정의와 폴백 프롬프트 네 곳에 같은 문장, check-structure D절 동기화 규칙 추가). 같은 브랜치 최종본으로 두 갈래를 동시에 돌렸다. `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`(SKILL.md 5a 4번)을 설정했다.

| 갈래 | 사본 | 스폰 | 없는 도구 호출 실패 | 규칙 밖 Bash | 실패 스폰 | 요약 줄 | `--pack` | exit |
|---|---|---|---|---|---|---|---|---|
| nodef | git 없음, `agents/st-armorer.md` 없음 | general-purpose | 0 | 0 | 0 | 있음 | 5/5 | 0 |
| def | git 없음, 정의 있음(정상 설치 헤드리스) | smartthink:st-armorer | 0 | 0 | 0 | 있음 | 5/5 | 0 |

두 갈래 모두 init `tools`에 Glob·Grep이 없었다. 메인의 오류 1건은 빈 vault의 `profile.md` 부재(정상)다.

nodef 도구 호출:

```
main     Bash   python3 <ROOT>/plugin/scripts/resolve-vault.py --ensure
main     Read   <ROOT>/vault/profile.md
main       ERR  File does not exist. Note: your current working directory is <ROOT>/...
main     Read   <ROOT>/vault/evolution-state.md
main     Read   <ROOT>/plugin/skills/smartthink/references/index.json
main     Read   <ROOT>/plugin/skills/smartthink/references/armorer-prompt.md
main     Agent  general-purpose
armorer  Read   <ROOT>/plugin/skills/smartthink/references/triz-innovation.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/core-engines.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/cognitive-arsenal.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/pattern-synthesis.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/analysis-method.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/core-engines.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/cognitive-arsenal.md
armorer  Write  <ROOT>/vault/packs/2026-10-29-museum-wayfinding-signage/pack.md
armorer  Bash   python3 <ROOT>/plugin/scripts/assemble-pack.py --pack-dir "<ROOT>/...
armorer  Bash   date +%Y-%m-%dT%H:%M:%S%z
armorer  Write  <ROOT>/vault/packs/2026-10-29-museum-wayfinding-signage/manifest.json
main     Read   <ROOT>/vault/packs/2026-10-29-museum-wayfinding-signage/manifest.json
main     Read   <ROOT>/vault/packs/2026-10-29-museum-wayfinding-signage/pack.md
```

def 도구 호출:

```
main     Bash   python3 <ROOT>/plugin/scripts/resolve-vault.py --ensure
main     Read   <ROOT>/plugin/skills/smartthink/references/index.json
main     Read   <ROOT>/vault/profile.md
main       ERR  File does not exist. Note: your current working directory is <ROOT>/...
main     Read   <ROOT>/vault/evolution-state.md
main     Agent  smartthink:st-armorer
armorer  Read   <ROOT>/plugin/skills/smartthink/references/core-engines.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/cognitive-arsenal.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/triz-innovation.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/analysis-method.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/core-engines.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/cognitive-arsenal.md
armorer  Write  <ROOT>/vault/packs/2026-10-29-regional-museum-signage/pack.md
armorer  Bash   python3 <ROOT>/plugin/scripts/assemble-pack.py --pack-dir "<ROOT>/...
armorer  Bash   date +%Y-%m-%dT%H:%M:%S%z
armorer  Write  <ROOT>/vault/packs/2026-10-29-regional-museum-signage/manifest.json
main     Read   <ROOT>/vault/packs/2026-10-29-regional-museum-signage/manifest.json
main     Read   <ROOT>/vault/packs/2026-10-29-regional-museum-signage/pack.md
main     Read   <ROOT>/vault/packs/2026-10-29-regional-museum-signage/pack.md
```

## 4. run1 도구 호출 (stream-json 추출, 주체 = parent_tool_use_id 유무)

```
main     Bash   python3 <ROOT>/plugin/scripts/resolve-vault.py --ensure
main     Read   <ROOT>/vault/profile.md
main       ERR  File does not exist. Note: your current working directory is <ROOT>/work.
main     Read   <ROOT>/vault/evolution-state.md
main     Read   <ROOT>/plugin/skills/smartthink/references/index.json
main     Read   <ROOT>/plugin/skills/smartthink/references/armorer-prompt.md
main     Agent  general-purpose
armorer  Read   <ROOT>/plugin/skills/smartthink/references/triz-innovation.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/core-engines.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/cognitive-arsenal.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/pattern-synthesis.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/analysis-method.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/core-engines.md
armorer  Read   <ROOT>/plugin/skills/smartthink/references/cognitive-arsenal.md
armorer  Bash   date +%Y-%m-%dT%H:%M:%S%z
armorer  Write  <ROOT>/vault/packs/2026-10-29-local-museum-wayfinding-signage/pack.md
armorer  Bash   python3 <ROOT>/plugin/scripts/assemble-pack.py --pack-dir "<ROOT>/...
armorer  Write  <ROOT>/vault/packs/2026-10-29-local-museum-wayfinding-signage/manifest.json
armorer  Bash   ls <ROOT>/vault/packs/
main     Glob   <ROOT>/vault/packs/2026-10-29-local-museum-wayfinding-signage/*
main       ERR  <tool_use_error>Error: No such tool available: Glob. Glob is not available in this session - find files with `find` via the Bash tool instead.</tool_use_error>
main     Read   <ROOT>/vault/packs/2026-10-29-local-museum-wayfinding-signage/pack.md
```
