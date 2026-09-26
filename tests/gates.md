# SmartThink v3 실행 게이트

## 1. 머리말

이 문서는 SmartThink v3의 사람이 직접 실행하는 수동 게이트 테스트다. 각 게이트는 구현이 아니라 관찰 가능한 결과를 판정한다. 실행자는 아래 절차를 순서대로 수행하고, 명시된 증거를 `tests/evidence/`에 남긴다.

실행 전에는 리포지터리 루트에서 브랜치가 `v3`인지 확인한다. 플러그인을 아직 설치하지 않은 상태의 Claude Code 테스트는 리포지터리 루트를 플러그인 루트로 하여 `claude --plugin-dir .`로 시작한다. 이 문서에서 `/st`는 `commands/st.md`의 별칭이고 `/smartthink`는 스킬 호출을 뜻한다.

### 증거 규약

모든 증거 파일은 `tests/evidence/` 바로 아래에 남긴다. 파일명은 `T<번호>-<설명>.<확장자>`로 통일한다. 예를 들어 `T2-manifest.json`, `T2-pack.md`, `T2-transcript.md`를 쓴다. 증거 디렉터리의 `.gitkeep`은 삭제하거나 수정하지 않는다.

- JSON이나 Markdown 산출물은 원본을 복사한다. 개인 경로, 토큰, 계정 식별자, 무관한 설정값이 있으면 해당 부분만 `[REDACTED]`로 치환하고 치환 사실을 트랜스크립트에 적는다.
- 트랜스크립트는 명령 또는 슬래시 명령을 입력한 줄부터, 해당 게이트의 최종 응답 또는 승인 직전 질문까지 연속으로 발췌한다. 중간 대화가 판정에 필요하면 생략하지 않는다.
- 설정 파일 증거는 원본 전체가 아니라 관련 `permissions.allow` 항목의 전후 diff만 남긴다. 설정 백업은 증거 디렉터리가 아닌 사용자 설정 위치 옆에 둔다.
- 파일을 새로 만드는 게이트는 생성 시각과 실행에 쓴 임시 vault 경로를 트랜스크립트 첫 줄에 적는다. 실제 사용자 vault의 내용은 증거로 복사하지 않는다.
- 증거는 원본 그대로 두고 문체 규칙에 맞춰 고치지 않는다. `check-structure.py`의 em dash 검사는 `tests/evidence/` 전체를 훑지 않으므로, 팩 사본을 복사한 뒤에도 리포 전체 검사는 종료 코드 0을 유지한다.
- 한 팩만 판정할 때는 전체 종료 코드 대신 `--pack`을 준 실행의 요약 마지막 줄 `pack: N passed, M failed, K skipped`를 본다. 이 줄은 H 항목만 센다. `--pack` 없이 돌리면 다섯 항목이 모두 skipped로 잡힌다.

### 판정 규약

각 게이트의 결과는 다음 세 값 중 하나다.

- `PASS`: 모든 통과 기준이 충족되었고 요구 증거가 남아 있다.
- `FAIL`: 기능은 실행되었지만 통과 기준 중 하나라도 충족되지 않았다. 실패한 체크 항목, 실제 출력, 사용한 명령, 관련 산출물 경로를 `T<번호>-failure.md`에 남긴다.
- `BLOCKED`: 현재 하네스나 필요한 외부 도구가 없어 실행할 수 없다. 시도한 명령, 환경 제약, 다음에 필요한 환경을 `T<번호>-blocked.md`에 남긴다. 기능 실패로 단정하지 않는다.

권장 실행 순서는 T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13이다. T2는 T1이 만든 프로필을 사용하고 T6는 T2가 만든 원문 팩을 사용한다. T10은 T5의 `--report` 경로가 선행되어야 한다. T4, T5, T7, T8, T9, T12, T13은 독립 임시 vault를 써도 된다.

## 2. 사전 준비

리포지터리 루트에서 다음을 확인한다.

```bash
git branch --show-current
python3 scripts/check-structure.py
python3 scripts/build-index.py --check
```

- 첫 명령의 출력은 현재 기본 브랜치(`main`)이거나, 검증 대상으로 정한 브랜치(예: 이슈 작업 워크트리의 브랜치)여야 한다. 둘 다 아니면 실행을 중단하고 브랜치 문제로 기록한다. 결과 요약표 비고에 실행한 브랜치를 적는다.
- 구조 검사와 인덱스 검사는 종료 코드 0이어야 한다. 둘 중 하나라도 실패하면 T1부터 실행하지 말고 실패 출력을 별도 보관한다.
- `tests/evidence/`가 존재하고 쓰기 가능한지 확인한다. 이 준비 단계에서 증거 파일을 미리 만들 필요는 없다.

vault 규약(#20): 우선순위는 `SMARTTHINK_VAULT` > 포인터 `${XDG_CONFIG_HOME:-~/.config}/smartthink/vault-pointer` > 기본값 `${XDG_DATA_HOME:-~/.local/share}/smartthink`이다. 실제 홈의 이 두 경로는 게이트 실행 중 만들거나 쓰지 않는다. 기본값·포인터·후보 탐지 자체를 보는 게이트(T15)는 가짜 `HOME`에서 `XDG_DATA_HOME`·`XDG_CONFIG_HOME`을 지운 채 연다.

실제 vault를 오염시키지 않기 위해 테스트마다 임시 vault를 권장한다. 아래처럼 현재 셸에 테스트 vault를 지정하고, Claude Code도 같은 셸에서 시작한다.

```bash
export ST_VAULT="${TMPDIR:-/tmp}/smartthink-v3-gates-$(date +%Y%m%d-%H%M%S)"
export SMARTTHINK_VAULT="$ST_VAULT"
mkdir -p "$ST_VAULT"
claude --plugin-dir .
```

T7의 v2 변환 검사는 별도 vault를 쓴다.

```bash
export ST_VAULT_V2="${TMPDIR:-/tmp}/smartthink-v3-gates-v2-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ST_VAULT_V2"
```

### 격리 설정 세션

T8·T9처럼 사용자 레벨 정의나 권한 규칙이 결과를 바꾸는 게이트는 실제 설정 디렉터리(`~/.claude`)가 아닌 격리 설정 디렉터리에서 연다. 실제 설정에는 사용자 레벨 에이전트·스킬 심링크, 허용 규칙, 훅, 기본 권한 모드가 실려 있어 폴백이나 권한 프롬프트가 드러나지 않는다.

```bash
export ST_CFG="$(mktemp -d)"
echo '{}' > "$ST_CFG/settings.json"                                   # permissions 없는 유효 JSON
echo '{"hasCompletedOnboarding":true,"theme":"dark"}' > "$ST_CFG/.claude.json"   # 첫 실행 온보딩·로그인 화면 생략
CLAUDE_CONFIG_DIR="$ST_CFG" CLAUDE_CODE_OAUTH_TOKEN="$ANTHROPIC_OAUTH_TOKEN" SMARTTHINK_VAULT="$ST_VAULT" \
  claude --plugin-dir . --model opus
```

- 격리 설정에는 로그인 정보가 없다. 인증은 `CLAUDE_CODE_OAUTH_TOKEN`을 이 자식 프로세스 환경에만 넣어 주입한다. 값은 이미 셸 환경에 있는 변수(예: `$ANTHROPIC_OAUTH_TOKEN`)로 참조하고 명령줄에 리터럴로 쓰지 않는다. 리터럴은 셸 히스토리에 남는다. 토큰 값은 증거·로그에 남기지 않는다(`[REDACTED]`).
- 첫 실행은 폴더 신뢰 확인 화면이 뜬다. `Yes, I trust this folder`를 고른다.
- 격리 설정의 기본 권한 모드는 auto다(상태줄 `⏵⏵ auto mode on`). 권한 프롬프트를 관찰하는 게이트는 `--permission-mode default`를 붙이고 상태줄이 `⏸ manual mode on`인지 확인한다.
- 게이트에서 빈 Enter는 Claude Code·Codex 입력창이 비어 있으면 제출되지 않는다. `진행`처럼 텍스트로 답하고 그 사실을 트랜스크립트에 적는다.

임시 vault는 모든 증거를 옮기고 결과 요약표를 채운 뒤에만 정리한다. 대상 변수를 먼저 확인한 뒤 다음 명령을 쓴다. 빈 변수나 실제 vault에 이 명령을 적용하지 않는다.

```bash
test -n "$ST_VAULT" && test -d "$ST_VAULT" && rm -rf "$ST_VAULT"
test -n "$ST_VAULT_V2" && test -d "$ST_VAULT_V2" && rm -rf "$ST_VAULT_V2"
test -n "$ST_CFG" && test -d "$ST_CFG" && rm -rf "$ST_CFG"   # 격리 설정 세션을 썼을 때
```

## 3. 게이트 T1~T15

### T1. `/st init` 신규 프로필

- **목적**: 신규 vault에서 사전 스캔 확인과 승인형 인터뷰를 거쳐 v3 프로필 시드를 만든다.
- **사전 조건**: 사전 준비 검사가 모두 green이고, `$SMARTTHINK_VAULT` 아래에 `profile.md`가 없어야 하며 `references/lifecycle.md`가 존재해야 한다.
- **입력**: `claude --plugin-dir .`로 연 세션에 `/st init`을 입력하고, 사전 스캔 결과 확인 후 6문 인터뷰와 최종본을 승인한다. vault 경로 질문에는 현재 `$SMARTTHINK_VAULT`를 답한다.
- **통과 기준**:
  - 사전 스캔 결과가 인터뷰보다 먼저 표시되고, 로컬 읽기 전용이며 외부 전송하지 않는다고 알린다.
  - 스캔 결과 확인 질문이 표시된 뒤에만 인터뷰가 진행된다.
  - `{VAULT}/profile.md`가 생성되고 YAML 헤더에 `version: 3`과 ISO 8601 형식의 `updated:` 값이 있다.
  - 본문 블록 제목이 순서대로 `## 1. 정체성`, `## 2. 현재 목표`, `## 3. 스타일`, `## 4. 기본값`, `## 5. 소스`, `## 6. 이력 요약`이다.
  - 최종본을 쓰기 전에 보여주고 승인받는다. `evolution-state.md`와 `packs/`도 vault 시드로 존재한다.
- **증거**: `T1-profile.md`에 생성된 프로필 전문, `T1-transcript.md`에 스캔 결과부터 최종 승인과 완료 보고까지의 발췌를 남긴다.
- **실패 시 흔한 원인**: lifecycle 절차서 미배선, `SMARTTHINK_VAULT`를 Claude 시작 전 export하지 않음, 최종 승인 없이 파일을 씀.

### T2. 기본 무장 (작업 설명 입력)

- **목적**: 작업 설명을 armorer 경로로 무장해 팩을 만들고, 본 작업에 착수하지 않은 채 브리핑으로 종료하는지 확인한다.
- **사전 조건**: T1 PASS, `agents/st-armorer.md` 존재, Agent 도구와 검색 도구가 사용 가능한 Claude 세션, 해당 vault에 같은 주제 팩이 없어야 한다.
- **입력**: `/st --budget 60000 공공 도서관의 예약 대기열 안내 화면을 개선하는 실행 계획을 설계해줘`
- **통과 기준**:
  - 진행 전 `━━ SmartThink 무장 게이트 ━━`가 표시되고 입력 해석, 진단, 5개 추천 모듈, 리서치 상태, 조작 항목이 보인다.
  - 예상 비용에 `메인에 실릴 팩`과 `서브에이전트 작업`의 두 단위가 모두 토큰 추정치로 표시된다.
  - 승인 후 armorer가 동기로 실행되어 `$SMARTTHINK_VAULT/packs/<날짜>-<슬러그>/pack.md`와 `manifest.json` 한 쌍을 만든다.
  - `manifest.json`에 정확히 `task`, `interpretation`, `cynefin`, `classification`, `modules`, `budget`, `research`, `profile_version`, `est_tokens`, `created`, `harness` 필드가 있고, `est_tokens` 안에 `pack`과 `agent`가 있다.
  - `pack.md`에 정확히 `## 1. 무장 브리핑`, `## 2. 작업 해석`, `## 3. 리서치 합성`, `## 4. 작업 적용 레이어`, `## 5. 레퍼런스 원문`, `## 6. 과거 인사이트와 프로필` 6개 절 제목이 있다.
  - `python3 scripts/check-structure.py --pack <팩경로>`가 종료 코드 0으로 원문 해시 계약을 통과한다.
  - 출력은 1절 무장 브리핑과 `팩:` 요약, `무장 완료. 이제 작업을 지시하세요.` 안내로 끝나며, 요청한 실행 계획의 실제 설계나 구현을 시작하지 않는다.
- **증거**: `T2-manifest.json`, `T2-pack.md`, `T2-transcript.md`, `T2-structure-check.txt`에 각각 원본 manifest, pack, 게이트부터 턴 종료까지, 구조 검사 명령과 종료 코드 0을 남긴다.
- **실패 시 흔한 원인**: Agent 도구가 없어 인라인 경로로 내려감, 브리핑 뒤 본 작업을 계속 수행함, 원문 블록의 해시 또는 마커가 깨짐.

### T3. 주제만 입력

- **목적**: 작업 설명이 아닌 주제만 들어왔을 때 예상 작업 A/B/C를 게이트와 팩에 보존하는지 확인한다.
- **사전 조건**: T1 PASS, 새 임시 vault 또는 T2와 다른 주제, armorer 정의와 Agent 도구가 존재한다.
- **입력**: `/st 지역 축제 방문객 경험`
- **통과 기준**:
  - 게이트의 `1. 입력 해석`에 `주제만 들어왔습니다. 예상 작업:`과 A, B, C가 모두 표시된다.
  - 팩의 `## 2. 작업 해석`에 예상 작업 A/B/C가 각각 구체적인 작업 또는 결정으로 남아 있다.
  - Enter로 진행했을 때 A/B/C 셋 모두가 팩 2절에 남는다.
- **증거**: `T3-pack.md`에 생성 pack 전문, `T3-transcript.md`에 게이트 입력 해석부터 진행 승인까지의 발췌를 남긴다.

### T4. `--digest` 팩

- **목적**: 원문 팩 대신 5절 증류본을 쓰되 팩 크기와 마커 계약을 지키는지 확인한다.
- **사전 조건**: T1 PASS, 새 주제, `scripts/check-structure.py`가 `--pack`을 지원한다.
- **입력**: `/st --digest --budget 60000 지역 행사 자원봉사자 배치 방식을 검토해줘`
- **통과 기준**:
  - `pack.md` 5절에 각 모듈마다 `<!-- MODULE-DIGEST: <파일명>.md -->` 형식의 마커가 있다.
  - 5절에 `MODULE-BEGIN`, `sha256=`, `MODULE-END` 마커가 없고 원문 모드와 digest 모드가 섞이지 않는다.
  - `manifest.json`의 `modules`는 문자열 배열이며 digest 전용 필드가 추가되지 않았다.
  - **5절 바이트 / 2.2 ≤ 20000**이다. 상한은 5절에만 적용하고 팩 전체(`est_tokens.pack`)에는 적용하지 않는다 - 1~4·6절은 digest 여부와 무관하게 동일하기 때문이다. 측정: `awk '/^## 5\. 레퍼런스 원문$/{f=1} /^## 6\. 과거 인사이트와 프로필$/{f=0} f' <팩경로>/pack.md | wc -c`
  - `python3 scripts/check-structure.py --pack <팩경로> --digest`가 종료 코드 0이다.
  - 브리핑에 5절이 원문이 아닌 증류본이라는 사실이 한 줄로 명시된다.
- **증거**: `T4-manifest.json`, `T4-pack.md`, `T4-transcript.md`, `T4-structure-check.txt`를 남긴다. 마지막 파일에는 검사 명령과 종료 코드 0, 5절 바이트 측정 명령과 값을 포함한다.
- **실패 시 흔한 원인**: digest 팩에 원문 마커를 섞음, `est_tokens.pack`을 실제 pack 크기 기준으로 기록하지 않음, 5절 증류본이 20K 상한을 넘김, 팩 전체 크기를 5절 상한으로 오인해 1~4·6절을 임의로 축약함.

### T5. `--report`와 확정 후 진화 기록

- **목적**: thinker가 팩 경로만 입력으로 받아 보고서를 그대로 표시하고, 확정 전에는 진화 상태를 바꾸지 않다가 확정 뒤 Step 5를 실행하는지 확인한다.
- **사전 조건**: T1 PASS, `agents/st-thinker.md`와 `references/thinker-prompt.md` 존재, 새 주제와 `$SMARTTHINK_VAULT/evolution-state.md`의 사전 복사본이 있어야 한다.
- **입력**: `/st --report 공공 도서관 예약 안내 개선안을 분석해줘`
- **통과 기준**:
  - thinker 스폰 입력에 팩 본문이 아니라 `Pack Path`와 `Manifest Path`가 전달된다.
  - 6단계 무장 브리핑을 다시 출력하지 않고, thinker 보고서가 메인 재합성이나 요약 없이 그대로 표시된다.
  - 첫 보고서 수신 직후, 사용자 피드백과 `확정` 신호 전의 `evolution-state.md`가 사전 스냅샷과 바이트 단위로 같다.
  - 보고서에 한 번 피드백을 주면 같은 thinker가 SendMessage로 재개되어 수정본을 표시한다. 새 thinker를 재스폰하지 않는다.
  - 사용자가 `확정`을 입력한 뒤에만 Step 5가 실행되어 YAML의 `version`, `updated`, `sessions`, `diversity_h`, `routing_weights` 5개 키를 유지한 채 진화 상태가 변경된다.
  - `sessions`는 확정 전보다 1 증가하고, 최종본 기준의 변경 diff가 관찰된다.
- **증거**: `T5-evolution.before.md`, `T5-evolution.preconfirm.md`, `T5-evolution.after.md`, `T5-evolution.diff`, `T5-transcript.md`를 남긴다. `before`와 `preconfirm`이 동일하다는 비교 명령의 종료 코드도 트랜스크립트에 기록한다.
- **실패 시 흔한 원인**: 첫 보고서 직후 Step 5를 실행함, 메인이 보고서를 재작성함, 수정 피드백 때 thinker를 재스폰함.

### T6. `--pack` 재장전

- **목적**: 기존 팩을 새 비용 게이트 없이 읽어 1절 브리핑만 출력하는지 확인한다.
- **사전 조건**: T2 PASS와 구조 검사를 통과한 T2 팩 경로가 있다.
- **입력**: `/st --pack <T2에서 만든 팩 디렉터리 또는 pack.md 경로>`
- **통과 기준**:
  - `━━ SmartThink 무장 게이트 ━━`가 표시되지 않는다.
  - 지정한 pack을 읽고 `## 1. 무장 브리핑` 내용이 원본과 동일하게 출력된다.
  - 출력에 팩 요약과 `무장 완료. 이제 작업을 지시하세요.`가 있고, 새 pack을 만들거나 본 작업을 시작하지 않는다.
- **증거**: `T6-transcript.md`에 입력부터 턴 종료까지, `T6-briefing-source.md`에 비교용 T2 pack의 1절을 남긴다.

### T7. `/st retain` 승인과 v2 변환

- **목적**: 승인 전 기록 금지와 첫 retain의 v2-to-v3 백업 및 변환을 확인한다.
- **사전 조건**: 별도 `$ST_VAULT_V2`를 만들고, 첫 줄이 `---`가 아닌 v2 산문 `evolution-state.md`를 넣는다. 이 테스트에서는 `SMARTTHINK_VAULT="$ST_VAULT_V2"`로 Claude를 새로 시작한다.
- **입력**: 터미널에서 `printf '%s\n' '# legacy state' '## 핵심 인사이트 (0/10)' '_(없음)_' > "$ST_VAULT_V2/evolution-state.md"`를 실행한 뒤, 새 세션에서 `/st retain`을 입력한다. 초안의 문구 한 곳을 수정하고 승인한다.
- **통과 기준**:
  - 라우팅 가중치, 인사이트/갭, 프로필 델타의 세 덩어리 초안이 먼저 표시되고 각각 수락, 거부, 수정할 수 있다.
  - 승인 전 `evolution-state.md`가 v2 원문 그대로이며 `evolution-state.v2.bak.md`가 아직 생성되지 않는다.
  - 승인 뒤 원본 바이트가 `evolution-state.v2.bak.md`에 백업되고 비어 있지 않다.
  - 새 `evolution-state.md` 첫 줄은 `---`이고 헤더에 `version`, `updated`, `sessions`, `diversity_h`, `routing_weights`가 모두 있다.
  - 승인한 수정만 기록되고, 거부한 덩어리는 쓰지 않는다.
  - `scripts/migrate-evolution.py`를 쓰는 경로라면 `--write`가 붙어 있다. 인자 없는 실행은 dry-run이라 변환되지 않고, 그 출력만 보고 변환됐다고 판정하면 실패다.
- **증거**: `T7-transcript.md`, `T7-evolution.before.md`, `T7-evolution.after.md`, `T7-evolution-state.v2.bak.md`, `T7-evolution.diff`를 남긴다.
- **실패 시 흔한 원인**: 승인 전에 기록함, 백업 없이 변환함, v3 헤더의 필수 키가 빠짐.

### T8. armorer 정의 제거 폴백

- **목적**: `st-armorer` 정의가 없을 때 general-purpose 폴백 또는 인라인 경로가 명시된 비용 표기로 동작하는지 확인한다.
- **사전 조건**: T1 PASS, Agent 도구가 있는 세션이다. 변형은 둘이다: **기본 변형**(리포의 정의를 잠시 옮김)과 **git 없는 변형**(정의·`.git`을 뺀 사본, #15 이후 권장). 기본 변형은 다른 작업자가 같은 리포지터리를 사용하지 않는 시간에 하고, 먼저 `test -f agents/st-armorer.md`와 `shasum -a 256 agents/st-armorer.md`로 원본 존재와 해시를 기록한다. git 없는 변형은 리포를 건드리지 않으므로 이 기록이 필요 없다.
  - **정의를 치운 뒤 새 세션을 시작해야 한다.** 하네스는 에이전트 목록을 세션 시작 시 캐시하므로, 이미 열린 세션에서 파일을 옮기면 캐시된 정의가 그대로 스폰되어 폴백이 일어나지 않는다.
  - **2절의 격리 설정 세션에서 연다.** 사용자 레벨 `~/.claude/agents/st-armorer.md` 같은 bare 정의가 있으면 `smartthink:st-armorer` 실패 뒤 bare 재시도가 성공해 폴백이 드러나지 않는다. 권한 관찰이 목적이 아니므로 권한 모드는 auto 또는 `--dangerously-skip-permissions`여도 되며, 쓴 모드를 기록한다.
  - 플러그인 이름공간 호출 `/smartthink:smartthink`를 쓴다. 격리 설정에는 bare `/st` 별칭이 없다.
  - git 없는 변형은 폴백이 git 이력에 기대는지 드러낸다. 원본을 건드리지 않으므로 복원 단계가 없고, 테스트 뒤 사본을 지우면 끝난다.
- **입력**: 어느 변형이든 정의를 치운 **뒤** 격리 설정 세션을 새로 시작해 `/smartthink:smartthink <주제>`(예: `지역 박물관의 안내 표지 체계를 개선해줘`)를 입력하고 게이트에서 진행한다.
  - 기본 변형: 터미널에서 `mv agents/st-armorer.md "${TMPDIR:-/tmp}/st-armorer.md.gates"`를 실행하고 `ls agents/`로 부재를 확인한 뒤 `--plugin-dir "$WT"`로 연다. 테스트 직후 `mv "${TMPDIR:-/tmp}/st-armorer.md.gates" agents/st-armorer.md`로 반드시 복원하고 해시를 다시 확인한다.
  - git 없는 변형: `cp -R "$WT" <임시>/plugin && rm -rf <임시>/plugin/.git && rm <임시>/plugin/agents/st-armorer.md`로 사본을 만들고 `ls <임시>/plugin/agents`로 부재를 확인한 뒤, git이 아닌 작업 디렉터리에서 `--plugin-dir <임시>/plugin`으로 연다. 증거 추출 뒤 `rm -rf <임시>`로 사본을 지운다.
- **통과 기준**:
  - 게이트가 정상 표시되고 일반 경로와 같은 두 단위 예상 비용을 표시한다.
  - `st-armorer` 정의 없음이 관찰 가능하게 기록된다: `smartthink:st-armorer` not found, 이어서 bare `st-armorer` not found가 스폰 결과로 보인다.
  - 테스터 개입 없이 general-purpose armorer 폴백이 자동 발동하고, 성공하면 팩 한 쌍과 브리핑이 생성된다. `python3 scripts/check-structure.py --pack <팩 디렉터리>`의 `pack:` 줄이 5 passed다.
  - 폴백 브리핑은 `references/armorer-prompt.md`에서 온다: 메인이 그 파일을 Read하고, general-purpose prompt가 그 전문에 Input 블록을 붙인 것이다. `git show` 등 git 이력 사용은 메인·서브에이전트 모두 0회다(세션 jsonl의 Bash 명령으로 센다).
  - armorer가 백그라운드로 뜨면(Agent 도구에 `run_in_background`가 없는 하네스, 2.1.283은 항상) SKILL.md 5a 대기 규칙을 지킨다: 스폰부터 완료 알림까지 메인 출력은 1줄 상태 고지뿐이고 팩 Read·브리핑 출력·추측이 없으며, 첫 팩 접근은 알림 뒤다.
  - general-purpose 폴백도 실패하면 인라인 경로로 내려가며 게이트에 `이 환경에는 Agent 도구가 없어 리서치를 메인이 직접 수행합니다.`와 검색 원문이 메인 컨텍스트를 소모한다는 안내가 표시된다.
  - 어떤 경로든 팩을 만들었다면 절 구조와 manifest 계약을 지킨다.
  - 기본 변형: 테스트 후 `agents/st-armorer.md`가 원래 위치로 복원되고 해시가 같다. git 없는 변형: 리포의 `agents/st-armorer.md`는 처음부터 건드리지 않으며, 사본이 삭제되어 있다.
- **증거**: 파일명은 회차 접두어(`T8-`, `T8-rerun-`, `T8-fix-` 등)를 붙인다. 공통으로 `<접두어>transcript.md`, 생성되었다면 `<접두어>manifest.json`과 `<접두어>pack.md`를 남긴다.
  - 기본 변형: `<접두어>restore-check.txt`에 복원 확인 명령과 결과(전후 `ls`·`shasum`)를 남긴다.
  - git 없는 변형: restore-check 대신 transcript의 실행 조건에 사본 경로(`<임시>/plugin` 형태로 치환), 사본 생성 명령, `.git`·정의 부재 확인, 사본 삭제 사실을 기록한다.
- **실패 시 흔한 원인**: 에이전트 정의를 복원하지 않음, 폴백 실패 후 인라인 경로로 전환하지 않음, 인라인 리서치 비용 안내가 누락됨, 폴백 브리핑을 git 이력에서 복구함, 백그라운드 완료 알림 전에 브리핑을 출력함.

### T9. 백그라운드 Write 권한

- **목적**: vault 쓰기 권한 프롬프트의 실제 발생 여부와 init의 승인형 허용 규칙 설치를 기록한다.
- **사전 조건**: 2절의 격리 설정 세션을 쓰고 실제 `~/.claude/settings.json`은 건드리지 않는다. 격리 `settings.json`은 `permissions`가 없는 유효 JSON(`{}`)이다.
  - **bypass permissions 금지.** `--permission-mode default`(또는 acceptEdits)로 시작하고 상태줄 원문을 기록한다. bypass·auto 모드에서는 어떤 권한 프롬프트도 사람에게 뜨지 않아 이 게이트의 질문에 답할 수 없다. 진행 중 상태줄이 auto로 바뀌면 그 구간은 판정에서 빼고 다시 관찰한다.
  - 프롬프트는 테스터가 화면 원문을 기록한 뒤 `Yes`(1회 허용)로만 답한다. `don't ask again` 계열을 고르면 허용 규칙이 생겨 관찰이 오염된다.
  - 규칙 설치 뒤 비교는 **새 세션**에서도 한다. 실행 중 세션의 설정 반영 여부와 규칙 자체의 효과를 구분하기 위해서다.
- **입력**: 새 임시 vault로 `/smartthink:smartthink init`을 실행해 권한 규칙 설치 제안을 거절한 뒤, `/smartthink:smartthink 지역 문화센터 수업 신청 흐름을 개선해줘`를 입력한다. 프롬프트 발생 여부와 도구·경로를 기록한 뒤 새 세션에서 `/smartthink:smartthink init`을 다시 실행해 vault 허용 규칙(`resolve-vault.py --permission-rule`의 `permission_rule`)과 5절 조립 Bash 규칙(`assemble-pack.py --permission-rule`의 `permission_rule`) 설치를 승인하고 같은 무장 명령을 재실행한다. 설치 대상이 격리 설정이 아니라 `~/.claude/settings.json`이면 그 쓰기를 거절하고 `$CLAUDE_CONFIG_DIR/settings.json`을 대상으로 지시한 뒤 그 사실을 기록한다.
- **통과 기준**:
  - 첫 init은 vault 쓰기 허용 규칙(아래 형식 주의) 설치 여부를 묻고, 승인 전에는 `settings.json`을 바꾸지 않는다.
  - 첫 무장 중 백그라운드 Write 권한 프롬프트가 뜨는지 또는 뜨지 않는지가 관찰 결과로 명시된다. 어느 결과도 단독으로 FAIL은 아니다.
  - 승인 뒤에는 기존 JSON을 보존한 머지로 `permissions.allow`에 정확히 현재 vault를 가리키는 `Edit(<VAULT>/**)` 항목 하나만 추가하거나, 이미 있으면 중복 추가하지 않는다. Claude Code는 `/`로 시작하는 규칙 경로를 설정 파일 기준 상대경로로 해석하므로, 절대경로 vault를 가리키려면 `Edit(//<절대경로>/**)` 또는 `Edit(~/<홈 기준 경로>/**)` 형식이어야 한다. 단일 `/`로 시작하는 `Edit(/<절대경로>/**)`가 설치되면 이 기준은 FAIL이다(결함 추적: #14).
  - 설치 대상은 현재 세션의 사용자 설정 파일이다(`CLAUDE_CONFIG_DIR`가 있으면 그 안의 `settings.json`). 규칙 문자열과 대상 파일은 `resolve-vault.py --permission-rule`의 `permission_rule`·`settings_path`와 같아야 한다.
  - vault가 `$HOME/.claude` 아래(기본 vault 포함)면 Claude Code가 그 아래 쓰기를 민감 파일로 보고 허용 규칙과 무관하게 묻는다. 이때 resolver는 `permission_rule_effective: false`를 내고, init은 규칙을 제안하지 않고 이유와 대안(vault 이동)을 안내해야 통과다. 이 경우 무장 중 Write 프롬프트는 FAIL이 아니라 알려진 제약으로 기록한다(#14 프로브).
  - 재시도 결과와 프롬프트 발생 여부를 첫 시도와 비교해 기록한다. 규칙 설치 뒤 새 세션에서도 vault Write 프롬프트가 뜨면 규칙이 vault와 매칭되지 않는 것이다.
  - init은 Edit 규칙과 함께 `Bash(python3 <assemble-pack.py 절대경로> *)` 1개를 따로 묻고(위험 고지 포함) 승인한 규칙만 보존 머지로 추가한다(#21). 두 규칙 설치 뒤 새 세션 무장에서 armorer의 vault 쓰기(pack.md Write, `assemble-pack.py` Bash, manifest.json Write)는 프롬프트 0회여야 한다. armorer가 `mkdir`·heredoc·셸 리다이렉션·확인용 Bash를 쓰면 FAIL이다. 메인 세션의 resolver·읽기 확인 Bash나 리서치 WebFetch 프롬프트는 종류를 따로 기록하고 이 기준과 구분한다.
- **증거**: `T9-settings.diff`, `T9-transcript.md`, `T9-prompt-observation.md`를 남긴다(재실측이면 접두어를 `T9-<회차>-`로 바꾼다). diff에는 `permissions.allow` 관련 전후만 남기고 무관한 설정은 `[REDACTED]`로 처리한다.
- **실패 시 흔한 원인**: 설정 파일이 없거나 JSON이 깨져 설치를 시도하지 못함, 승인 전에 설정을 씀, 기존 `permissions.allow` 배열을 덮어씀.

### T10. SendMessage 재개와 메인 Step 5 폴백

- **목적**: 동일 thinker 피드백 재개와 thinker가 죽었을 때의 메인 Step 5 폴백을 각각 확인한다.
- **사전 조건**: T5 PASS, `st-thinker` 정의, 진화 상태의 사전 스냅샷이 있다. 이 게이트는 Agent 메시지 송수신을 노출하는 Claude 세션에서만 실행한다.
- **입력**: `/st --report 지역 도서관 예약 안내 개선안을 분석해줘`를 입력한 뒤, 첫 보고서에 `대상 사용자를 어린이 보호자로 한정해 수정해줘`라고 피드백하고 `확정`한다. 별도 재시도에서는 확정 직전 thinker를 중단 또는 턴 소진 상태로 만들고 `확정`한다.
- **통과 기준**:
  - 첫 피드백은 새 Agent가 아니라 기존 백그라운드 thinker로 SendMessage 재개되어 수정본이 반환된다.
  - 수정본 확정 전에는 진화 상태가 변경되지 않는다.
  - 정상 경로에서는 확정 신호 뒤 thinker가 Step 5를 실행한다.
  - thinker가 확정 신호에 무응답이거나 종료된 폴백 재시도에서는 메인이 최종본 기준으로 Step 5를 직접 실행하고, 갱신을 조용히 생략하지 않는다.
- **증거**: `T10-transcript.md`, `T10-evolution.before.md`, `T10-evolution.after.md`, `T10-fallback-transcript.md`, `T10-fallback-evolution.diff`를 남긴다.
- **실패 시 흔한 원인**: 피드백마다 thinker 재스폰, 확정 전 Step 5 실행, thinker 종료 뒤 메인이 진화 갱신을 누락.

### T11. 플러그인 설치 방식과 호출 이름

- **목적**: `--plugin-dir`에서 스킬, 에이전트, 별칭을 인식하고 실제 호출 이름을 실측한다.
- **사전 조건**: 플러그인을 전역 설치하지 않은 새 Claude Code 세션과 리포지터리 루트가 있다.
- **입력**: 터미널에서 `claude --plugin-dir .`를 실행한 뒤, 세션에 `/skills`를 입력하고 목록에 표시된 이름으로 스킬을 한 번 호출한다. `/smartthink`와 `/smartthink:smartthink` 중 실제로 열리는 이름을 기록한다. 이어서 `/st 지역 보행자 안전 안내를 개선해줘`를 입력한다.
- **통과 기준**:
  - `/skills` 출력에 SmartThink 스킬이 보이고 `agents/st-armorer.md`, `agents/st-thinker.md`, `commands/st.md`가 이 플러그인 루트에서 인식된다.
  - 별칭 `/st`가 SmartThink와 같은 스킬을 호출한다.
  - `/smartthink` 단축 호출인지 `/smartthink:smartthink` 네임스페이스 호출인지 실제 성공한 이름을 증거에 정확히 쓴다. 이 기록 자체가 이 게이트의 목적이다.
  - 호출 후 T2와 같은 게이트 또는 명확한 스킬 진입 결과가 관찰된다.
- **증거**: `T11-skills.txt`에 `/skills` 원문, `T11-transcript.md`에 호출 시도와 성공한 호출 이름, `T11-observation.md`에 호출 이름과 agents 등록 필드 필요 여부를 남긴다.
- **실패 시 흔한 원인**: `claude --plugin-dir .`를 리포지터리 루트 밖에서 실행함, 호출 이름을 추정만 하고 실측하지 않음.

### T12. 헤드리스 `claude -p`

- **목적**: 비대화식 실행에서 게이트가 자동 진행되고 120K 상한 및 절삭 기록이 적용되는지 확인한다. 두 호출 경로(`/st` 별칭과 `/smartthink:smartthink` 직접 호출)를 모두 본다.
- **사전 조건**: `claude -p` 사용 가능, 호출 경로마다 새 임시 vault, 리포지터리 루트를 플러그인 디렉터리로 전달할 수 있다.
  - Claude Code 세션 안에서 중첩 실행하면 자식 프로세스는 로그인 정보 대신 `CLAUDE_CODE_OAUTH_TOKEN`만 읽는다. 이 변수를 자식 env에만 넣는다(없으면 "Not logged in", exit 1). 토큰 값은 어떤 증거에도 남기지 않는다.
  - 사용자 레벨 정의와 CLAUDE.md·훅을 배제하려고 격리 `CLAUDE_CONFIG_DIR`에서 돌릴 때는 그 디렉터리의 `settings.json`에 allow 규칙을 넣는다. `-p` 자식은 승인 프롬프트에 답할 수 없어 규칙이 없으면 Bash·쓰기가 전부 거부된다(T14). 예: `"allow": ["Bash", "Read", "Glob", "Grep", "Edit(//<임시 vault 절대경로>/**)", "WebSearch", "WebFetch", "Agent", "Skill"]`, `"deny": ["Read(~/.local/share/smartthink/**)", "Edit(~/.local/share/smartthink/**)", "Read(~/.claude/smartthink-vault/**)", "Edit(~/.claude/smartthink-vault/**)"]`. 뒤의 두 규칙은 #20 이전 옛 위치(메인테이너 머신 잔존, 이전 전까지)를 막는 보호 규칙이다. 절대경로 규칙은 `//`로 시작한다(`/`는 설정 파일 기준 상대경로). 쓰기 규칙은 `Edit(...)`가 모든 파일 편집 도구를 덮는다. 넣은 settings.json 원문을 증거에 남긴다.
- **입력**: 우회 문구 없이 원문 그대로 두 경로를 각각 실행한다.
  - `/st` 경로: `SMARTTHINK_VAULT="$ST_VAULT" claude --plugin-dir . -p '/st --budget 200000 지역 도서관 예약 시스템의 장기 개선 전략을 검토해줘'`
  - 직접 호출 경로: `SMARTTHINK_VAULT="$ST_VAULT" claude --plugin-dir . -p '/smartthink:smartthink --budget 200000 지역 도서관 예약 시스템의 장기 개선 전략을 검토해줘'`
  - 회귀 확인용으로 T2 입력(`--budget 60000 공공 도서관의 예약 대기열 안내 화면을 개선하는 실행 계획을 설계해줘`)도 두 경로로 돌린다.
- **로딩된 SKILL.md 확인**: `-p` 표준 출력에는 마지막 메시지만 나오므로 세션 트랜스크립트(`<설정 디렉터리>/projects/<cwd 슬러그>/*.jsonl`)에서 `Base directory for this skill:` 줄을 찾아 리포 SKILL.md인지 확인하고 증거에 남긴다. 실제 설정에서는 사용자 레벨 심링크(`~/.claude/skills/smartthink`, `~/.claude/commands/st.md`)가 다른 체크아웃을 가리킬 수 있다. `/st`는 그 경로에서 어느 명령 정의가 잡혔는지(사용자 레벨 st.md 또는 플러그인 `smartthink:st`)도 기록한다.
- **통과 기준**:
  - **비대화식 지시 문구 없이 원문 입력만으로** 두 경로 모두 팩(`pack.md`+`manifest.json`)이 완성된다. 게이트에서 턴이 끝나거나 "진행할까요?"로 끝나면 FAIL이다.
  - 대화형 Enter나 예산 답을 기다리지 않고 무장 게이트를 자동 진행한다. 헤드리스에서 6항목 게이트 블록 출력은 선택이다(SKILL.md 4단계). 판정은 아래 표준 출력 요약 줄로 한다.
  - `-p` 표준 출력에는 마지막 응답만 남으므로, 표준 출력에 `헤드리스: 자동 진행 | 상한 NK | 절삭: … | 복원: 없음 | 팩: …` 요약 줄이 있다. 이 줄이 필수 판정 근거다.
  - 출력에 헤드리스 상한 120K가 적용되었음이 드러난다. 전달한 `--budget 200000`이 120K보다 우선하지 않는다(manifest `budget`이 120000 이하). 게이트 추정치가 상한 이하여야 한다. 완성 팩의 실측 `est_tokens.pack`이 상한을 넘는 것은 절삭 1패스·복원 없음 규칙상 FAIL이 아니며, 그 초과가 출력에 고지되어 있으면 된다.
  - 추정치가 120K를 넘으면 SKILL.md의 "예산 초과 시 절삭 순서"대로 실제 적용한 절삭과 이유, 복원 여부가 출력에 남는다.
  - 절삭이 없어도 자동 진행 결과, 팩 경로, 브리핑, 턴 종료가 출력에 남는다.
  - 각 팩을 `python3 scripts/check-structure.py --pack <팩 디렉터리>`로 검사해 `pack: 5 passed, 0 failed` 종료 코드 0이다.
- **증거**: 경로마다 `T12-rerun-<경로>-output.txt`(표준 출력·표준 오류, 로딩된 SKILL.md 경로, 사용한 설정), `T12-rerun-<경로>-pack.md`, `T12-rerun-<경로>-manifest.json`을 남긴다. 최초 실행(2026-09-08) 증거는 `T12-output.txt`, `T12-manifest.json`, `T12-pack.md`다.
- **실패 시 흔한 원인**: 헤드리스 판별 신호를 보지 않고 대화형으로 기본값을 잡아 게이트에서 턴을 끝냄(#9), 120K 대신 사용자가 준 더 큰 예산을 사용함, 절삭 결과를 출력에 남기지 않음, 중첩 실행에서 `CLAUDE_CODE_OAUTH_TOKEN` 누락, 격리 설정에 allow 규칙 누락.

### T13. Codex 인라인 경로

- **목적**: Agent 도구가 없는 Codex 환경에서 동등한 팩 명세와 브리핑을 만드는 인라인 경로를 별도로 실측한다.
- **사전 조건**: Codex에서 리포지터리 파일을 읽고 `$SMARTTHINK_VAULT`에 쓸 수 있는 별도 대화형 세션이다. Claude 전용 플러그인 진입이 Codex에 없으면 이 게이트는 `BLOCKED`로 남겨도 된다.
  - **스킬 등록**: `ln -s <리포>/skills/smartthink ~/.codex/skills/smartthink`. 등록 전 `ls -la ~/.codex/skills/smartthink`로 기존 링크를 확인하고, 등록 뒤 `readlink ~/.codex/skills/smartthink`가 검증 대상 체크아웃을 가리키는지 기록한다(다른 체크아웃이면 그 체크아웃의 SKILL.md가 로딩된다). 대화형 세션의 `/skills` → `List skills`에 `smartthink`가 보여야 한다.
  - **리포 밖 cwd**에서 시작한다(`mktemp -d`). cwd가 리포면 Codex가 등록 없이도 `skills/smartthink/SKILL.md`를 스스로 읽어 게이트를 흉내 내므로 등록 여부를 판별할 수 없다.
  - **vault 환경 변수는 `-c`로 넘긴다.** Codex TUI는 공유 로컬 app-server 데몬에서 명령을 실행해, TUI를 띄운 셸의 환경 변수가 도구 명령에 전달되지 않을 수 있다. 그러면 resolver가 `source: default`로 실제 기본 vault를 고른다. `-c 'shell_environment_policy.set.SMARTTHINK_VAULT="<임시 vault>"'`를 붙이고, 첫 resolver 출력이 `"source": "env"`인지 확인한다. `default`가 보이면 즉시 중단한다. 대화형 세션을 띄우기 **전에** 같은 `-c` 값으로 `codex exec -c 'shell_environment_policy.set.SMARTTHINK_VAULT="<임시 vault>"' 'printenv SMARTTHINK_VAULT'`를 실행해 임시 vault 경로가 출력되는지 먼저 확인한다. 사후 확인만으로는 resolver가 이미 기본 vault를 읽은 뒤다.
  - **인라인 경로는 서브에이전트 도구가 없는 Codex에서만 관찰된다.** 멀티 에이전트 기능(`spawn_agent`)이 있는 Codex에서는 0단계가 armorer 경로를 고르는 것이 명세대로다. 도구 목록에 `spawn_agent`가 있는지 먼저 기록한다.
  - **서브에이전트 도구를 끄는 수단은 격리 `CODEX_HOME`이다(#16).** opencodex가 주입한 모델 카탈로그(`model_catalog_json`)의 모델별 `multi_agent_version`이 도구를 켜므로 `--disable multi_agent*`나 `[features]`로는 꺼지지 않는다. 임시 `CODEX_HOME`에 카탈로그 사본(해당 모델 항목에서 `multi_agent_version` 키 삭제), 최소 `config.toml`(`model_catalog_json`=사본, `openai_base_url`, `model`, `approval_policy = "never"`, `sandbox_mode`, `[features] multi_agent = false, multi_agent_v2 = false`), `auth.json` 심링크(복사 금지), `skills/smartthink` → 검증 대상 체크아웃의 `skills/smartthink` 심링크를 둔다. 실제 `~/.codex/`는 읽기만 한다. 구성 스크립트는 `evidence/T13-fix-tools.md`에 있다. 이 방식은 사용자 스킬 등록(`~/.codex/skills/smartthink`, 메인 체크아웃)을 거치지 않으므로 워크트리 코드를 태울 때도 쓴다.
  - 대화형 세션을 띄우기 전에 같은 `CODEX_HOME`으로 `codex exec --skip-git-repo-check ... '<이 세션의 도구 이름을 그대로 나열하라>'`를 실행해 `spawn_agent`·`custom_collaboration__*`가 없음을 기록한다. 판정 근거는 이 도구 목록이다. 세션 rollout의 `turn_context.multi_agent_version`은 참고로만 기록한다(기능 플래그를 끄면 `disabled`, `[features]`를 비우면 도구가 없어도 `v1`로 남는다).
  - **리서치 ON 인라인은 opencodex 웹 검색 브리지를 거치면 팩 단계에 도달하지 못한다(#16).** 요청당 검색 쿼리 상한(기본 3)에 닿으면 프록시가 "지금 답하라" developer 지시를 넣고, 검색 결과 본문은 다음 요청 기록에 남지 않는다. 이 조건에서는 `--nosearch`로 인라인 경로를 관찰하고, 리서치 ON 회차는 프록시를 거치지 않는 호스팅 `web_search` 모델이 있을 때만 PASS 판정에 쓴다.
- **입력**: `T13-fix-tools.md` 구성 스크립트를 돌린 같은 셸에서, 리포 밖 임시 cwd로 옮겨 `: "${CH:?CODEX_HOME 미정의}"` 가드를 먼저 실행한 뒤 `CODEX_HOME="$CH" SMARTTHINK_VAULT="$ST_VAULT" codex --dangerously-bypass-approvals-and-sandbox -c 'shell_environment_policy.set.SMARTTHINK_VAULT="'"$ST_VAULT"'"'`를 실행하고 폴더 신뢰를 승인한 뒤, 새 Codex 세션에 `$smartthink --nosearch 지역 보행자 안전 안내를 개선해줘`를 입력하고 게이트에 `진행`으로 답한다(리서치 ON 회차는 `--nosearch`를 뺀다). Codex 스킬은 슬래시 명령이 아니어서 `/smartthink …`는 `Unrecognized command '/smartthink'`로 끝난다. 호출이 인식되지 않으면 실제 오류와 실행 환경을 기록하고 중단한다.
- **헤드리스 보조 회차(#16)**: 같은 `CODEX_HOME`으로 `codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -c 'shell_environment_policy.set.SMARTTHINK_VAULT="<새 임시 vault>"' '<입력>' < /dev/null`을 입력 끝에 `비대화식 실행이다.`가 없는 회차와 있는 회차로 두 번 돌린다. 없는 회차는 게이트에서 턴을 끝내고 팩 없이 종료 코드 0, 있는 회차는 헤드리스 요약 줄과 팩이 나와야 한다.
- **통과 기준**:
  - 실행 가능할 때 Agent 도구(서브에이전트 도구) 부재가 감지되고 인라인 경로임과 리서치 비용이 메인 컨텍스트에 실린다는 게이트 안내가 표시된다. `--nosearch` 회차는 리서치 비용이 없으므로 "인라인 경로이며 비용이 메인 컨텍스트에 실린다"는 안내로 판정한다.
  - 게이트 승인 뒤 `$SMARTTHINK_VAULT/packs/<날짜>-<슬러그>/pack.md`와 `manifest.json`이 생성된다.
  - 생성 팩은 T2의 6개 절 제목(`--nosearch`면 명세대로 3절을 뺀 5개 절, `manifest.research=false`)과 manifest의 11개 필드를 지키고, 1절 브리핑을 출력한 뒤 본 작업에 착수하지 않는다.
  - Codex가 호출 또는 스킬 로딩 자체를 지원하지 않으면 `BLOCKED`로 판정하고, 기능 FAIL로 오판하지 않는다.
- **증거**: 실행 시 `T13-transcript.md`, `T13-manifest.json`, `T13-pack.md`를 남긴다. 실행 불가 시 `T13-blocked.md`에 시도한 호출, 오류 원문, 필요한 Codex 통합 조건을 남긴다. #16 실측 증거는 `T13-fix-report.md`(판정·원인), `T13-fix-tools.md`, `T13-fix-transcript.md`, `T13-fix-pack.md`, `T13-fix-manifest.json`, `T13-fix-research-transcripts.md`, `T13-fix-headless.md`다.

### T14. 빈 `SMARTTHINK_VAULT`는 폴백하지 않는다

- **목적**: 명시적으로 지정된 vault가 비어 있어도 그대로 쓰고, 기본 vault(`${XDG_DATA_HOME:-~/.local/share}/smartthink`)를 건드리지 않는지 확인한다(이슈 #10 회귀).
- **사전 조건**: `scripts/resolve-vault.py`가 있다. 빈 임시 디렉터리 하나와 비교용 마커 파일을 만든다. 기본 vault를 오염시킬 수 있는 실험이므로 가능하면 격리된 `HOME`에서 실행하고, 실제 `HOME`에서 돌릴 때는 사전에 기본 vault를 백업한다.
- **입력**:
  ```bash
  export ST_EMPTY="$(mktemp -d)"; touch "$TMPDIR/st14-marker"
  SMARTTHINK_VAULT="$ST_EMPTY" python3 scripts/resolve-vault.py   # 단위 확인: source가 env여야 한다
  SMARTTHINK_VAULT="$ST_EMPTY" claude --plugin-dir . -p '/smartthink:smartthink --nosearch 지역 도서관 좌석 안내를 개선해줘'
  find "${XDG_DATA_HOME:-$HOME/.local/share}/smartthink" -newer "$TMPDIR/st14-marker" 2>/dev/null
  ```
  중첩 Claude Code 세션 안에서는 자식 프로세스가 `CLAUDE_CODE_OAUTH_TOKEN`만 읽는다(T12 참고). 게이트 자동 진행 회귀(#9)가 남아 있으면 입력 끝에 비대화식 진행 지시 1줄을 붙이고 그 사실을 기록한다.
- **통과 기준**:
  - resolver 단위 확인의 출력이 `{"path": "$ST_EMPTY", "source": "env"}`다.
  - 헤드리스 실행이 팩을 만든다면 `$ST_EMPTY/packs/` 아래에 만든다.
  - 마지막 `find` 출력이 비어 있다. 기본 vault에 새 파일이나 수정이 하나도 없다.
- **증거**: `T14-output.txt`에 resolver 출력, 헤드리스 표준 출력, `find` 결과를 남긴다. 실행 불가 시 `T14-blocked.md`에 시도한 명령, 오류 원문, 필요한 조건을 남긴다.
- **단위 대체 검증**: 헤드리스 실측이 막혀도 `tests/test_resolve_vault.py`와 `tests/test_migrate_target.py`가 같은 규칙(빈 env vault 사용, 기본 vault 폴백 없음)을 매번 검증한다.

### T15. init vault 후보 제안

- **목적**: `st init` ⑤가 `resolve-vault.py --candidates`의 결정적 탐지 결과를 보여 주고 자동 선택 없이 사용자가 고르게 하는지, 고른 뒤 포인터·권한 규칙이 새 규약 위치에 기록되고 새 세션 무장에서 vault Write/Edit 도구 프롬프트가 사라지는지 확인한다(이슈 #20).
- **사전 조건**: 2절의 격리 설정 세션 + 가짜 `HOME`. 실제 홈의 `~/.config/smartthink`·`~/.local/share/smartthink`를 만들거나 쓰지 않는다.
  - `XDG_DATA_HOME`·`XDG_CONFIG_HOME`·`SMARTTHINK_VAULT`를 지운다(`env -u`). 포인터를 보려면 env vault가 없어야 한다. 대신 resolver를 먼저 실행해 `path`가 가짜 홈 아래인지 확인한다.
  - 격리 `settings.json`은 `{"permissions":{"defaultMode":"default","deny":[...]}}`로 둔다. deny에는 실제 홈 절대경로(`//<실제 홈>/...`)로 새 기본값·포인터 디렉터리와 옛 위치(메인테이너 머신 잔존)를 넣는다. 가짜 `HOME`에서는 `~`가 가짜 홈을 가리키므로 `~/` 규칙으로는 실제 홈을 못 막는다.
  - 가짜 홈 픽스처(실제 사례 재현): Obsidian 등록 목록(`~/Library/Application Support/obsidian/obsidian.json`)이 파일 1개짜리 안 쓰는 기본 vault와 리포 30개를 담은 작업 폴더 루트를 가리키고, 진짜 보관소는 이름 신호만 있는 git 리포다.
- **입력**:
  ```bash
  env -u SMARTTHINK_VAULT -u XDG_DATA_HOME -u XDG_CONFIG_HOME HOME="$FAKE_HOME" CLAUDE_CONFIG_DIR="$ST_CFG" \
    CLAUDE_CODE_OAUTH_TOKEN="$ANTHROPIC_OAUTH_TOKEN" claude --plugin-dir . --model opus
  ```
  `/smartthink:smartthink init` → ⑤에서 진짜 보관소 후보를 고르고 `.gitignore` 질문과 권한 규칙 설치를 승인한다. 세션을 닫고 같은 명령으로 새 세션을 열어 `/smartthink:smartthink --nosearch 지역 도서관 좌석 예약 안내를 개선해줘`로 무장한다.
- **통과 기준**:
  - ⑤에 후보마다 신호·마지막 수정일·대략 파일 수·git 여부·경고가 붙은 목록과 "새로 만들기(기본값)"·"직접 입력"이 뜨고, 어느 후보도 미리 골라 두지 않는다(Enter 수락 기본값·추천 표시 없음). 안 쓰는 기본 vault와 작업 폴더 루트에 경고가 붙는다.
  - 고른 보관소의 `<보관소>/smartthink/`가 vault가 되고 기존 파일은 그대로다. git 리포면 `packs/` 제외 여부를 묻는다.
  - 포인터가 가짜 홈의 `~/.config/smartthink/vault-pointer`에 기록되고 resolver가 `source: pointer`로 같은 경로를 낸다.
  - `permission_rule_effective: true`로 규칙을 제안하고 승인 시 격리 settings.json에 보존 머지한다.
  - 새 세션 무장에서 vault에 대한 Write/Edit 도구 프롬프트가 0회다. Bash 프롬프트는 기록만 한다(#21 소관).
- **증거**: `T15-prompt-observation.md`(환경·픽스처·settings 전후·포인터·프롬프트 순서 기록·판정), `T15-transcript.md`(⑤ 화면 원문, 세션별 도구 호출 목록과 Base directory, 무장 마지막 화면), `T15-candidates.json`(가짜 홈 `--candidates` 출력).
- **단위 대체 검증**: `tests/test_resolve_vault.py`의 `CandidatesTest`가 같은 실제 사례 픽스처와 제외 규칙·경고·자동 선택 필드 부재를 매번 검증한다.

## 4. 실측 기록

아래 표는 실행 중 답이 나온 즉시 채운다. 추정이나 과거 지식으로 채우지 않는다.

| 질문 | 답이 나오는 게이트 | 결과 기입란 |
|---|---:|---|
| `plugin.json`에 agents 등록 필드가 필요한가 | T11 | **불필요**. plugin.json에 agents/commands/skills 필드 없이 `agents/`·`commands/`·`skills/`가 루트 자동 인식됨. 등록 이름은 `smartthink:st-armorer`, `smartthink:st-thinker`, `smartthink:st`, `smartthink:smartthink` (2026-09-08, Claude Code 2.1.263, `--plugin-dir .`) |
| `/smartthink` 단축 호출이 되는가, 아니면 네임스페이스가 붙는가 | T11 | **네임스페이스 필수: `/smartthink:smartthink`만 v3를 연다.** bare `/smartthink`·`/st`·플러그인 별칭 `/smartthink:st`는 모두 이 머신의 전역 v2(`~/.claude/skills/smartthink`, `~/.claude/commands/st.md`)로 해석됨(Base directory 실측). 에이전트도 bare `st-armorer`는 not found, bare `st-thinker`는 전역 v2 정의를 가리킴 |
| 백그라운드 Write에서 권한 프롬프트가 뜨는가 | T9 | **뜬다.** default 권한 모드(상태줄 `⏸ manual mode on`), 허용 규칙 없음에서 백그라운드 `smartthink:st-armorer`의 vault Write마다 부모 세션에 `Do you want to create pack.md?`·`manifest.json?` 프롬프트가 뜨고 응답 전까지 armorer가 멈춘다. init이 설치하는 `Edit(<VAULT>/**)`(단일 `/` 절대경로)로는 같은 세션·새 세션 모두 프롬프트가 사라지지 않았고, `Edit(//<VAULT>/**)`를 넣은 새 세션에서만 무프롬프트로 Write됐다(규칙 경로 `/`는 설정 파일 기준 상대경로). 2026-09-26~27, Claude Code 2.1.283, 격리 `CLAUDE_CONFIG_DIR`. 이전 기입(2026-09-08 "관찰 불가, bypass 모드")을 대체. #14 수정 후 재실측(2026-09-27): init이 `resolve-vault.py --permission-rule`로 `Edit(//<절대경로>/**)`를 `$CLAUDE_CONFIG_DIR/settings.json`에 설치하고 새 세션 무장에서 pack.md Write 프롬프트 0회. 기본 vault(`~/.claude/smartthink-vault`)는 `Edit(~/.claude/smartthink-vault/**)`가 있어도 pack.md·manifest.json Write마다 뜬다. Claude Code가 `$HOME/.claude` 아래를 민감 파일로 보고 허용 규칙을 무시하기 때문이다(`CLAUDE_CONFIG_DIR`과 무관). armorer의 Bash(mkdir·heredoc) 호출은 Edit 규칙 대상이 아니라 별도로 묻는다. #21 수정 후(2026-09-27): armorer의 5절 조립이 `assemble-pack.py` 1회로 바뀌고 init이 `Bash(python3 <절대경로> *)` 규칙을 함께 설치해, 새 세션 무장에서 armorer의 vault 쓰기 프롬프트 0회. 메인 세션의 resolver·읽기 확인 Bash 3회는 남는다(T9-bash) |
| SendMessage 재개가 동작하는가 | T10 | **동작함**(T5·T10). 첫 보고서 후 SendMessage → `Resuming agent <같은 id>`로 같은 thinker가 in-context 개정본 반환, 확정 신호도 같은 경로로 전달돼 Step 5 실행. 재스폰 없음 |
| 헤드리스에서 게이트 자동 진행이 되는가 | T12 | **됨(2026-09-26 #9 수정 후)**. 수정 전에는 판별 절차가 없어 설정에 따라 갈림: 격리 설정은 `/st`·`/smartthink:smartthink` 모두 게이트에서 턴 종료, 실제 설정은 자동 진행(I9-repro-R1~R4). 0단계에 도구 호출 없는 판별 신호(시스템 프롬프트 `Claude Agent SDK` 정체성 문장, `AskUserQuestion` 부재)와 4단계·`--budget` 절 안 헤드리스 분기를 넣은 뒤, 우회 문구 없는 원문 입력 6회(두 경로 x 실제·격리 설정, T2 입력 두 경로)가 모두 팩 완성, `--budget 200000`은 120K로(manifest.budget 120000), `--budget 60000`은 60K 유지, 표준 출력 요약 줄에 절삭·복원 기록. Bash로 `CLAUDE_CODE_ENTRYPOINT` 읽기는 auto 모드 `-p`에서 승인 거부(I9-repro-probe). 중첩 자식은 `CLAUDE_CODE_OAUTH_TOKEN` 필요 |

## 5. 결과 요약

| 게이트 번호 | 판정 | 실행일 | 증거 파일 | 비고 |
|---:|---|---|---|---|
| T1 | PASS | 2026-09-08 | T1-profile.md, T1-transcript.md | 스캔→확인→인터뷰→최종 승인→쓰기 순서 준수. version 3·ISO updated·6블록. 테스터(모델)가 인터뷰 답을 인라인 공급 |
| T2 | FAIL | 2026-09-08 | T2-manifest.json, T2-pack.md, T2-transcript.md, T2-structure-check.txt, T2-failure.md | `--budget 60000` 절삭 순서가 리서치를 먼저 끄고 되돌리지 않아 3절 부재(5/6 절). 나머지 기준(게이트·비용 2단위·manifest 11필드·해시 exit 0·턴 종료) 충족. bare `st-armorer` not found → `smartthink:st-armorer` |
| T2 | PASS | 2026-09-18 | T2-rerun-pack.md, T2-rerun-manifest.json, T2-rerun-output.txt, T24-rerun-structure-check.txt | 재실행(#5 e8d0cfb 반영, 코디네이터). 절삭이 모듈 제외 우선으로 동작해 리서치 유지: manifest `research: true`, 6절 전부, est pack 44383 ≤ 60000, `--pack` H 5/5 exit 0. 헤드리스 게이트 자동 진행 회귀 때문에 입력에 비대화식 진행 지시 1줄 추가(별도 이슈) |
| T3 | PASS | 2026-09-08 | T3-pack.md, T3-transcript.md | 게이트 1항목에 예상 작업 A/B/C, Enter 진행 후 팩 2절에 셋 모두 구체 작업으로 보존. 리서치 출처 27 |
| T4 | FAIL | 2026-09-08 | T4-manifest.json, T4-pack.md, T4-transcript.md, T4-structure-check.txt, T4-failure.md | MODULE-DIGEST 마커 0개(armorer 정의에 규격 없음), est_tokens.pack 32002 > 20000, 1절에 증류본 명시 없음. check --pack/--digest 모두 exit 1 |
| T4 | PASS | 2026-09-18 | T4-rerun-pack.md, T4-rerun-manifest.json, T4-rerun-output.txt, T24-rerun-structure-check.txt | 재실행(#3 b98c6da + #4 f78a763 반영, 코디네이터). MODULE-DIGEST 5개·원문 마커 0개, 1절 본문에 증류본 고지, 5절 43791바이트/2.2 = 19905 토큰 ≤ 20000(신기준: 상한은 5절만), `--pack --digest` H 5/5 exit 0. est_tokens.pack 44916은 1~4·6절 포함이라 위반 아님. 입력에 비대화식 진행 지시 1줄 추가(별도 이슈) |
| T5 | PASS | 2026-09-08 | T5-evolution.before.md, T5-evolution.preconfirm.md, T5-evolution.after.md, T5-evolution.diff, T5-transcript.md | Pack Path 입력·보고서 그대로 표시·확정 전 cmp 0·SendMessage 동일 thinker 재개·확정 후 Step 5(sessions 0→1, 5키 유지) |
| T6 | PASS | 2026-09-08 | T6-transcript.md, T6-briefing-source.md | 게이트 미표시, 1절 바이트 동일 출력, 신규 팩 없음. 사전 조건 편차: T2 FAIL이나 구조 검사 exit 0 팩 사용 |
| T7 | PASS | 2026-09-08 | T7-transcript.md, T7-evolution.before.md, T7-evolution.after.md, T7-evolution-state.v2.bak.md, T7-evolution.diff | 승인 전 원문 유지·.bak 부재, 승인 후 백업·`--write`·v3 헤더 5키, 거부 덩어리 미기록. 관찰: lifecycle 수동 백업 후 스크립트가 'backup exists' exit 1(`--force` 필요) |
| T8 | PASS | 2026-09-08 | T8-transcript.md, T8-manifest.json, T8-pack.md, T8-restore-check.txt | 조건부. 하네스가 에이전트 목록을 세션 시작 시 캐시해 정의 제거가 런타임 스폰 실패로 이어지지 않음. general-purpose 폴백은 테스터가 강제 실행 → 6절·해시 계약 통과. 정의 복원 sha 동일 |
| T8 | PASS | 2026-09-26 | T8-rerun-transcript.md, T8-rerun-pack.md, T8-rerun-manifest.json, T8-rerun-restore-check.txt | 재실측(#8, 브랜치 docs-8-gates-rerun = main 65272b5). 정의를 치운 뒤 격리 `CLAUDE_CONFIG_DIR` 새 세션(auto 모드, 권한 프롬프트 0회). `smartthink:st-armorer` not found → bare `st-armorer` not found → general-purpose 폴백이 테스터 개입 없이 자동 발동, 게이트 비용 2단위(팩 ≈131K/서브 ≈144K), 팩 6절·manifest 11필드, `--pack` H 5/5 exit 0. 복원 후 sha256 동일. 관찰: 폴백 브리핑을 `git show HEAD:agents/st-armorer.md`로 복구해 만듦, general-purpose가 동기가 아닌 백그라운드로 뜸, manifest `created`가 23:30으로 실제 작성 시각(23:02~23:10)과 다름(스킬 결함, 보고만) |
| T8 | PASS | 2026-09-27 | T8-fix-transcript.md, T8-fix-probe.md, T8-fix-pack.md, T8-fix-manifest.json, T8-fix-structure-check.txt | 재실측(#15, 브랜치 st-15-armorer-fallback f1ff5bc). git 없는 변형: `.git`과 `agents/st-armorer.md`를 뺀 사본(`<TMP>/plugin`, 생성·부재 확인·삭제는 T8-fix-transcript.md 실행 조건, restore-check 해당 없음) + 격리 `CLAUDE_CONFIG_DIR`, `--dangerously-skip-permissions`. `smartthink:st-armorer` → bare 둘 다 not found → 메인이 `references/armorer-prompt.md` Read → general-purpose(prompt = 파일 전문 + Input 블록). git 호출 메인 0·서브 0. 백그라운드 스폰(프로브: 2.1.283 Agent 스키마에 `run_in_background` 없음, 정식 armorer도 백그라운드) → 대기 중 1줄 고지만, 완료 알림 16:03:42 뒤 16:03:46 첫 팩 접근. 팩 6절·manifest 11필드, `--pack` 워크트리 검사기 exit 0(pack 5/5) |
| T9 | PASS | 2026-09-08 | T9-settings.diff, T9-transcript.md, T9-prompt-observation.md | 조건부. 거절 시 settings 무변경, 승인 시 보존 머지로 `Edit(<VAULT>/**)` 1개 추가. 프롬프트 발생 여부는 bypass 모드라 관찰 불가 |
| T9 | FAIL | 2026-09-26~27 | T9-rerun-prompt-observation.md, T9-rerun-settings.diff, T9-rerun-transcript.md, T9-rerun-failure.md | 재실측(#8, 브랜치 docs-8-gates-rerun = main 65272b5, default 권한 모드, 격리 `CLAUDE_CONFIG_DIR`). 프롬프트 관찰은 성공: 규칙 없을 때 백그라운드 Write 프롬프트 뜸. 실패 기준: init이 설치한 `Edit(<VAULT>/**)`가 vault와 매칭되지 않아(새 세션에서도 프롬프트) "현재 vault를 가리키는 규칙" 불충족, `Edit(//<VAULT>/**)`로는 해소. 설치 대상이 `CLAUDE_CONFIG_DIR`을 무시하고 실제 `~/.claude/settings.json`을 향함(테스터가 거절·재지시). 거절 시 무변경·보존 머지·1항목 추가는 충족. 세션 1 첫 무장은 auto 모드 오염으로 판정 제외 |
| T9 | PASS | 2026-09-27 | T9-fix-prompt-observation.md, T9-fix-settings.diff, T9-fix-transcript.md | #14 수정 후 재실측(브랜치 st-14-init-perm, default 권한 모드). env vault(홈 밖): init이 `Edit(//<VAULT>/**)`를 격리 `$CLAUDE_CONFIG_DIR/settings.json`에 보존 머지로 1항목 설치, 실제 `~/.claude/settings.json` 쓰기 시도 없음(sha256 불변), 새 세션 무장에서 vault Write 프롬프트 0회(pack.md Write 21ms). 기본 vault(가짜 HOME): 규칙 형식 `Edit(~/.claude/smartthink-vault/**)`는 맞지만 Write 프롬프트 2회, `$HOME/.claude` 민감 경로 보호가 원인이라 규칙으로 해소 불가(BLOCKED, 프로브 P1~P6). 후속 커밋으로 init이 이 경우 규칙을 제안하지 않고 vault 이동을 안내함을 확인. 기본 vault 무프롬프트는 후속 이슈 |
| T9 | PASS | 2026-09-27 | T9-bash-prompt-observation.md, T9-bash-settings.diff, T9-bash-transcript.md | #21 재실측(브랜치 st-21-assemble-pack, default 권한 모드, 격리 `CLAUDE_CONFIG_DIR`, env vault 홈 밖, `--nosearch`). init이 `Edit(//<VAULT>/**)`와 `Bash(python3 <HOME>/.../scripts/assemble-pack.py *)` 2개를 위험 고지와 함께 묻고 승인 뒤 보존 머지로 추가. 새 세션 무장에서 armorer 도구 호출은 Read 8, Write pack.md, Bash assemble-pack.py 1회, Write manifest.json이고 vault 쓰기 프롬프트 0회(mkdir·printf·cat·확인용 Bash 없음). 팩 `--pack` H 5/5. 남은 프롬프트 3회는 메인 세션 Bash(`resolve-vault.py --ensure` 1, vault 읽기 확인 `ls`·`cat`·`grep` 2)로 init 규칙 밖, 후속 |
| T10 | PASS | 2026-09-08 | T10-transcript.md, T10-evolution.before.md, T10-evolution.after.md, T10-fallback-transcript.md, T10-fallback-evolution.diff | 피드백 SendMessage 동일 thinker 재개(도구 0회 in-context 개정), 확정 전 무변경, 확정 후 thinker Step 5(sessions 1→2). 폴백: 재개 직후 TaskStop으로 종료시킨 뒤 메인이 Step 5 직접 실행(sessions 2→3). 유휴 thinker는 TaskStop 불가·SendMessage 재개 가능 |
| T11 | PASS | 2026-09-08 | T11-skills.txt, T11-transcript.md, T11-observation.md | 실제 호출 이름 `/smartthink:smartthink`. `/st`·`/smartthink`·`/smartthink:st`는 전역 v2로 감. agents 등록 필드 불필요 |
| T11 | PASS | 2026-09-26 | T11-rerun-st.txt, T11-rerun-agents.txt | 재실측(#2 할 일 3, 3.0.1 설치 후, 실제 HOME 새 헤드리스 세션, `--model opus`, `SMARTTHINK_VAULT`=임시). bare `/st`가 v3 게이트(`━━ SmartThink 무장 게이트 ━━`, 비용 2단위: 팩 약 144K / 서브에이전트 약 157K)를 띄움. 에이전트 목록에 `st-searcher` 없음, bare `st-thinker`는 리포 v3 정의 심링크. resolver가 임시 env vault에 시드, 실제 기본 vault `find -newer` 비어 있음 |
| T12 | PASS | 2026-09-08 | T12-output.txt, T12-manifest.json, T12-pack.md | run1(문서 원문)은 Not logged in exit 1(중첩 자식 인증). run2(`CLAUDE_CODE_OAUTH_TOKEN` 주입)에서 자동 진행·120K 상한·절삭 출력·턴 종료. 헤드리스도 `/st`가 v2를 먼저 열고 스스로 v3 재호출 |
| T12 | PASS | 2026-09-26 | T12-rerun-{st,direct}-{iso,real}-{output.txt,pack.md,manifest.json}, T12-rerun-t2-{st,direct}-iso-{output.txt,pack.md,manifest.json}, I9-repro-R1~R4.txt, I9-repro-probe.txt | 재실측(#9 수정 후, `--model opus`, 비대화식 지시 문구 없음, 임시 vault·임시 cwd). T12 입력 `/st`·`/smartthink:smartthink` x 격리·실제 설정 4회와 T2 입력 두 경로(격리) 2회 전부 게이트에서 멈추지 않고 팩 완성, 로딩된 SKILL.md는 모두 워크트리. manifest.budget: T12 120000(`--budget 200000` 미우선), T2 60000. 표준 출력에 `헤드리스: 자동 진행 \| 상한 NK \| 절삭 … \| 복원: 없음 \| 팩 …` 줄 6/6. 사본 `--pack` H 5/5 exit 0 6/6. 비고: 6항목 게이트 블록은 트랜스크립트 1/6(st-iso)만 표시(헤드리스에서 선택). direct-iso는 게이트 추정 116.6K ≤ 120K였고 완성 팩 실측 est 127169 초과를 출력에 고지(기준 충족). 격리 설정 `/st`는 플러그인 `smartthink:st`로 해석 |
| T12 | PASS | 2026-09-27 | T12-rerun-st-real2-output.txt, T12-rerun-st-real2-pack.md, T12-rerun-st-real2-manifest.json | 확인 재실측(final-review 20260926-234935 후속 판정 반영: 헤드리스 게이트 블록 선택·요약 줄 필수, 판별은 신호1 AND 신호2 또는 신호3, 6단계 요약 줄 연결). `/st` 실제 설정, 원문 입력, 우회 문구 없음. 팩 완성, 로딩 SKILL.md 워크트리, manifest.budget 120000(`--budget 200000` 미우선), 표준 출력 요약 줄 있음(`절삭: 메타인지 제외(게이트 추정 141.7K → 116.6K)`), 사본 `--pack` H 5/5 exit 0. 실측 est_tokens.pack 122243이 상한을 2.2K 넘었고 절삭 1패스 규칙에 따라 재절삭 없이 출력에 고지(기준 충족) |
| T13 | BLOCKED | 2026-09-08 | T13-blocked.md | codex exec에서 `/smartthink` 미등록(자유 텍스트로 처리). cwd가 리포라 SKILL.md를 읽어 게이트만 출력, 인라인 안내문 없음, 팩 없음 |
| T13 | BLOCKED | 2026-09-26 | T13-rerun-blocked.md, T13-rerun-transcript.md, T13-rerun-pack.md, T13-rerun-manifest.json | 재실측(#8, 브랜치 docs-8-gates-rerun = main 65272b5, codex-cli 0.155.1, `~/.codex/skills/smartthink` 등록(메인 체크아웃을 가리킴, 이 브랜치와 같은 커밋), 리포 밖 cwd). 스킬 진입은 `$smartthink`로 성공(`/smartthink`는 Unrecognized command), 게이트·팩(6절·11필드·`harness: "codex"`·H 5/5)·브리핑 후 턴 종료 충족. 그러나 이 Codex에는 `spawn_agent`가 있어 armorer 경로로 진행했고 인라인 안내문은 나오지 않음. `--disable multi_agent*`로도 도구가 남아 인라인 경로 관찰 불가. 첫 시도는 TUI 셸 env가 데몬 명령에 전달되지 않아 실제 기본 vault를 읽음(쓰기 없음, 즉시 중단) |
| T13 | PASS (리서치 OFF) / BLOCKED (리서치 ON, 환경) | 2026-09-27 | T13-fix-report.md, T13-fix-tools.md, T13-fix-transcript.md, T13-fix-pack.md, T13-fix-manifest.json, T13-fix-research-transcripts.md, T13-fix-headless.md | #16 재실측(브랜치 st-16-codex-inline, codex-cli 0.157.1, opencodex 2.61.0 경유 `anthropic/claude-opus-5-5`). `spawn_agent` 공급원은 opencodex 모델 카탈로그의 `multi_agent_version`이라 기능 플래그로는 안 꺼짐. 격리 `CODEX_HOME`(카탈로그 사본에서 키 삭제, 스킬은 워크트리 심링크)에서 도구 목록에 서브에이전트 도구가 없음을 확인. `--nosearch` 인라인 run4: 게이트 인라인 안내·비용 2단위, 팩(3절 생략)·manifest 11필드(`harness: "codex-inline"`), `--pack` H 5/5 exit 0, 브리핑 후 턴 종료. 리서치 ON run1~3은 opencodex 웹 검색 브리지(요청당 쿼리 3개 상한 뒤 "지금 답하라" 주입, 결과 본문 비영속) 때문에 팩 없이 개선안을 답하거나 같은 쿼리를 반복. #8 run2 armorer의 manifest 미작성도 같은 브리지 상한이 원인. `codex exec` 헤드리스: 명시 없음 → 게이트에서 종료(exit 0, 팩 없음), `비대화식 실행이다.` 명시 → 자동 진행·요약 줄·H 5/5. final-review 뒤 SKILL.md 5b는 하네스 무관 규칙 1개(팩 두 파일 Write 전 턴 종료 금지, "지금 답하라" 류 지시도 팩 Write·브리핑으로 수행, 브리핑 전 Read/Glob 확인)만 남겼고 이 최종 문구는 리서치 ON에서 미실측 |
| T14 | BLOCKED | 2026-09-26 | T14-output.txt, T14-blocked.md | 격리 HOME에 권한 허용 규칙이 없어 `-p` 자식의 resolver 호출 8회가 전부 승인 대기로 거부, 팩 미생성. resolver 단위 출력 source=env, 실제 기본 vault `find -newer` 비어 있음. 자식이 /tmp·리포 안에 vault 즉흥 생성 시도(거부) → SKILL.md에 금지 명시. 복합 명령 호출은 절대경로 한 줄로 교체 |
| T15 | PASS | 2026-09-27 | T15-prompt-observation.md, T15-transcript.md, T15-candidates.json | #20 실측(브랜치 st-20-vault-location, Claude Code 2.1.283, default 권한 모드, 격리 `CLAUDE_CONFIG_DIR`, 가짜 `HOME` + XDG 변수 제거). ⑤에 후보 3개(안 쓰는 기본 vault `nearly-empty`, 리포 30개 작업 폴더 `workspace-root`, 이름 신호만 있는 진짜 보관소)와 새로 만들기·직접 입력이 자동 선택 없이 떴다. 3번 선택 → `<보관소>/smartthink/`, `.gitignore`에 `smartthink/packs/`, 포인터 `~/.config/smartthink/vault-pointer`(가짜 홈), `Edit(~/<보관소>/smartthink/**)` 설치. 새 세션 무장에서 armorer의 pack.md Write가 프롬프트 없이 성공(vault Write/Edit 프롬프트 0회). Bash 프롬프트 12회(heredoc으로 쓴 5·6절·manifest.json 포함)는 #21 소관으로 기록만 |
