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

- 첫 명령의 출력은 정확히 `v3`이어야 한다. 아니면 실행을 중단하고 브랜치 문제로 기록한다.
- 구조 검사와 인덱스 검사는 종료 코드 0이어야 한다. 둘 중 하나라도 실패하면 T1부터 실행하지 말고 실패 출력을 별도 보관한다.
- `tests/evidence/`가 존재하고 쓰기 가능한지 확인한다. 이 준비 단계에서 증거 파일을 미리 만들 필요는 없다.

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

임시 vault는 모든 증거를 옮기고 결과 요약표를 채운 뒤에만 정리한다. 대상 변수를 먼저 확인한 뒤 다음 명령을 쓴다. 빈 변수나 실제 vault에 이 명령을 적용하지 않는다.

```bash
test -n "$ST_VAULT" && test -d "$ST_VAULT" && rm -rf "$ST_VAULT"
test -n "$ST_VAULT_V2" && test -d "$ST_VAULT_V2" && rm -rf "$ST_VAULT_V2"
```

## 3. 게이트 T1~T13

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
  - `manifest.est_tokens.pack` 값이 20000 이하이고, `python3 scripts/check-structure.py --pack <팩경로>`가 종료 코드 0이다.
  - 브리핑에 5절이 원문이 아닌 증류본이라는 사실이 한 줄로 명시된다.
- **증거**: `T4-manifest.json`, `T4-pack.md`, `T4-transcript.md`, `T4-structure-check.txt`를 남긴다. 마지막 파일에는 검사 명령과 종료 코드 0을 포함한다.
- **실패 시 흔한 원인**: digest 팩에 원문 마커를 섞음, `est_tokens.pack`을 실제 pack 크기 기준으로 기록하지 않음, 20K 상한을 넘김.

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
- **증거**: `T7-transcript.md`, `T7-evolution.before.md`, `T7-evolution.after.md`, `T7-evolution-state.v2.bak.md`, `T7-evolution.diff`를 남긴다.
- **실패 시 흔한 원인**: 승인 전에 기록함, 백업 없이 변환함, v3 헤더의 필수 키가 빠짐.

### T8. armorer 정의 제거 폴백

- **목적**: `st-armorer` 정의가 없을 때 general-purpose 폴백 또는 인라인 경로가 명시된 비용 표기로 동작하는지 확인한다.
- **사전 조건**: T1 PASS, 다른 작업자가 같은 리포지터리를 사용하지 않는 시간, Agent 도구가 있는 세션이다. 먼저 `test -f agents/st-armorer.md`로 원본 존재를 확인한다.
- **입력**: 터미널에서 `mv agents/st-armorer.md "${TMPDIR:-/tmp}/st-armorer.md.gates"`를 실행하고 `/st 지역 박물관의 안내 표지 체계를 개선해줘`를 입력한다. 테스트 직후 `mv "${TMPDIR:-/tmp}/st-armorer.md.gates" agents/st-armorer.md`로 반드시 복원한다.
- **통과 기준**:
  - 게이트가 정상 표시되고 일반 경로와 같은 두 단위 예상 비용을 표시한다.
  - `st-armorer` 정의 없음이 관찰 가능하게 기록되고, general-purpose armorer 폴백이 성공하면 팩 한 쌍과 브리핑이 생성된다.
  - general-purpose 폴백도 실패하면 인라인 경로로 내려가며 게이트에 `이 환경에는 Agent 도구가 없어 리서치를 메인이 직접 수행합니다.`와 검색 원문이 메인 컨텍스트를 소모한다는 안내가 표시된다.
  - 어떤 경로든 팩을 만들었다면 절 구조와 manifest 계약을 지키고, 테스트 후 `agents/st-armorer.md`가 원래 위치로 복원되어 있다.
- **증거**: `T8-transcript.md`, 생성되었다면 `T8-manifest.json`과 `T8-pack.md`, `T8-restore-check.txt`를 남긴다. 마지막 파일에는 복원 확인 명령과 결과를 남긴다.
- **실패 시 흔한 원인**: 에이전트 정의를 복원하지 않음, 폴백 실패 후 인라인 경로로 전환하지 않음, 인라인 리서치 비용 안내가 누락됨.

### T9. 백그라운드 Write 권한

- **목적**: vault 쓰기 권한 프롬프트의 실제 발생 여부와 init의 승인형 허용 규칙 설치를 기록한다.
- **사전 조건**: `~/.claude/settings.json`이 존재하고 유효 JSON이며, 실행자가 이 사용자 설정 파일을 변경할 권한이 있다. 리포지터리 밖 설정을 바꾸므로 먼저 `cp ~/.claude/settings.json ~/.claude/settings.json.bak.smartthink-gates`로 백업한다.
- **입력**: 권한 규칙이 없는 새 임시 vault로 `/st init`을 실행해 권한 규칙 설치 제안을 거절한 뒤, `/st 지역 문화센터 수업 신청 흐름을 개선해줘`를 입력한다. 프롬프트 발생 여부를 기록한 뒤 `/st init`을 다시 실행해 `Edit(<VAULT>/**)` 설치를 승인하고 같은 무장 명령을 재실행한다.
- **통과 기준**:
  - 첫 init은 `Edit(<VAULT>/**)` 규칙 설치 여부를 묻고, 승인 전에는 `settings.json`을 바꾸지 않는다.
  - 첫 무장 중 백그라운드 Write 권한 프롬프트가 뜨는지 또는 뜨지 않는지가 관찰 결과로 명시된다. 어느 결과도 단독으로 FAIL은 아니다.
  - 승인 뒤에는 기존 JSON을 보존한 머지로 `permissions.allow`에 정확히 현재 vault를 가리키는 `Edit(<VAULT>/**)` 항목 하나만 추가하거나, 이미 있으면 중복 추가하지 않는다.
  - 재시도 결과와 프롬프트 발생 여부를 첫 시도와 비교해 기록한다.
- **증거**: `T9-settings.diff`, `T9-transcript.md`, `T9-prompt-observation.md`를 남긴다. diff에는 `permissions.allow` 관련 전후만 남기고 무관한 설정은 `[REDACTED]`로 처리한다.
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

- **목적**: 비대화식 실행에서 게이트가 자동 진행되고 120K 상한 및 절삭 기록이 적용되는지 확인한다.
- **사전 조건**: `claude -p` 사용 가능, 새 임시 vault, 리포지터리 루트에서 플러그인 디렉터리를 전달할 수 있다.
- **입력**: `SMARTTHINK_VAULT="$ST_VAULT" claude --plugin-dir . -p '/st --budget 200000 지역 도서관 예약 시스템의 장기 개선 전략을 검토해줘'`
- **통과 기준**:
  - 대화형 Enter나 예산 답을 기다리지 않고 무장 게이트를 자동 진행한다.
  - 출력에 헤드리스 상한 120K가 적용되었음이 드러난다. 전달한 `--budget 200000`이 120K보다 우선하지 않는다.
  - 추정치가 120K를 넘으면 리서치 축소 또는 OFF, ★ 낮은 모듈 제외, 적용 레이어 축약의 순서 중 실제 적용한 절삭과 이유가 출력에 남는다.
  - 절삭이 없어도 자동 진행 결과, 팩 경로, 브리핑, 턴 종료가 출력에 남는다.
- **증거**: `T12-output.txt`에 표준 출력과 표준 오류, `T12-manifest.json`과 `T12-pack.md`에 생성 산출물을 남긴다.
- **실패 시 흔한 원인**: 헤드리스가 사용자 입력을 대기함, 120K 대신 사용자가 준 더 큰 예산을 사용함, 절삭 결과를 출력에 남기지 않음.

### T13. Codex 인라인 경로

- **목적**: Agent 도구가 없는 Codex 환경에서 동등한 팩 명세와 브리핑을 만드는 인라인 경로를 별도로 실측한다.
- **사전 조건**: Codex에서 리포지터리 파일을 읽고 `$SMARTTHINK_VAULT`에 쓸 수 있는 별도 세션이다. Claude 전용 플러그인 진입이 Codex에 없으면 이 게이트는 `BLOCKED`로 남겨도 된다.
- **입력**: 터미널에서 `SMARTTHINK_VAULT="$ST_VAULT" codex`를 실행한 뒤, 새 Codex 세션에 `/smartthink 지역 보행자 안전 안내를 개선해줘`를 입력한다. 해당 호출이 등록되지 않았으면 실제 오류와 실행 환경을 기록하고 중단한다.
- **통과 기준**:
  - 실행 가능할 때 Agent 도구 부재가 감지되고 인라인 경로임과 리서치 비용이 메인 컨텍스트에 실린다는 게이트 안내가 표시된다.
  - 게이트 승인 뒤 `$SMARTTHINK_VAULT/packs/<날짜>-<슬러그>/pack.md`와 `manifest.json`이 생성된다.
  - 생성 팩은 T2의 6개 절 제목과 manifest의 11개 필드를 지키고, 1절 브리핑을 출력한 뒤 본 작업에 착수하지 않는다.
  - Codex가 호출 또는 스킬 로딩 자체를 지원하지 않으면 `BLOCKED`로 판정하고, 기능 FAIL로 오판하지 않는다.
- **증거**: 실행 시 `T13-transcript.md`, `T13-manifest.json`, `T13-pack.md`를 남긴다. 실행 불가 시 `T13-blocked.md`에 시도한 호출, 오류 원문, 필요한 Codex 통합 조건을 남긴다.

## 4. 실측 기록

아래 표는 실행 중 답이 나온 즉시 채운다. 추정이나 과거 지식으로 채우지 않는다.

| 질문 | 답이 나오는 게이트 | 결과 기입란 |
|---|---:|---|
| `plugin.json`에 agents 등록 필드가 필요한가 | T11 | |
| `/smartthink` 단축 호출이 되는가, 아니면 네임스페이스가 붙는가 | T11 | |
| 백그라운드 Write에서 권한 프롬프트가 뜨는가 | T9 | |
| SendMessage 재개가 동작하는가 | T10 | |
| 헤드리스에서 게이트 자동 진행이 되는가 | T12 | |

## 5. 결과 요약

| 게이트 번호 | 판정 | 실행일 | 증거 파일 | 비고 |
|---:|---|---|---|---|
| T1 | | | | |
| T2 | | | | |
| T3 | | | | |
| T4 | | | | |
| T5 | | | | |
| T6 | | | | |
| T7 | | | | |
| T8 | | | | |
| T9 | | | | |
| T10 | | | | |
| T11 | | | | |
| T12 | | | | |
| T13 | | | | |
