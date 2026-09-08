# T13 BLOCKED 기록 - Codex 인라인 경로

- 실행일: 2026-09-08 02:23~02:24 (+09:00)
- 환경: codex-cli 0.153.4 (`~/.local/bin/codex`), model gpt-5.6-terra, approval never, sandbox danger-full-access, cwd = 리포 루트. `SMARTTHINK_VAULT="$ST_VAULT"` 지정.
- 이 세션(Claude Code)에서 대화형 `codex`를 열 수 없어 비대화 `codex exec`로 슬래시 등록 여부만 탐침했다.

## 시도한 호출

```
$ SMARTTHINK_VAULT="$ST_VAULT" codex exec --skip-git-repo-check "/smartthink 지역 보행자 안전 안내를 개선해줘"
```

## 관찰 (오류 원문·발췌)

1. Codex는 `/smartthink`를 스킬·명령으로 인식하지 않았다. 첫 응답이 프롬프트를 자유 텍스트로 해석한 것이었다:
```
codex
지역 보행자 안전 안내 화면을 살펴본 뒤, 실제 사용자 흐름과 시각적 완성도를 함께 개선하겠습니다. 프런트엔드 변경이므로 관련 UI 작업 지침을 먼저 확인하고 진행합니다.
```
   이어서 무관한 Codex 플러그인 스킬(`~/.codex/plugins/cache/sisyphuslabs/omo/4.19.3/skills/frontend/SKILL.md`)을 읽었다. `~/.codex/skills/`·`~/.codex/agents/`·`~/.codex/config.toml`에 smartthink 등록 없음(확인 명령: `ls ~/.codex/skills`, `grep smartthink ~/.codex/config.toml` → 프로젝트 trust 항목만).
2. 리포 루트가 cwd라서 Codex가 탐색 중 `./skills/smartthink/SKILL.md`를 발견해 스스로 읽었고(`sed -n '1,320p' skills/smartthink/SKILL.md && sed -n '1,240p' commands/st.md ...`), 그 지시를 따라 `━━ SmartThink 무장 게이트 ━━` 6항목을 출력했다. 게이트에는 "메인에 실릴 팩 ≈ 131K / 서브에이전트 작업 ≈ 144K"가 표시됐고, 인라인 경로 안내문("이 환경에는 Agent 도구가 없어 리서치를 메인이 직접 수행합니다")은 **표시되지 않았다**. 비대화 실행이라 Enter 대기에서 턴이 끝났고 팩은 생성되지 않았다(`$ST_VAULT/packs/`에 T13 팩 없음). 종료 코드 0, tokens used 51,873.
3. 게이트 출력 전문은 아래에 첨부한다.

## 판정

**BLOCKED** - Codex에 `/smartthink` 호출(스킬 로딩)이 등록돼 있지 않다. 리포 파일 자체 탐색으로 게이트까지 도달한 것은 스킬 진입이 아니라 우연한 파일 읽기이며, 문서 기준(호출 미등록 시 오류·환경 기록 후 중단)에 따라 기능 FAIL로 판정하지 않는다.

## 다음에 필요한 Codex 통합 조건

- `~/.codex/skills/smartthink` → 리포 `skills/smartthink` 심링크(또는 Codex 스킬 설치 절차)로 스킬 등록. 대화형 세션에서 `/smartthink` 슬래시가 스킬을 여는지 확인.
- 등록 후 인라인 경로 게이트 안내문(Agent 도구 부재·리서치 비용 메인 부담) 표시 여부와 팩 생성(6절·manifest 11필드)을 대화형으로 재실측.
- 참고: 등록 없이도 cwd가 리포 루트면 Codex가 SKILL.md를 읽어 게이트를 흉내 낼 수 있으므로, 등록 여부는 리포 밖 cwd에서 판정해야 한다.

## 첨부: Codex가 출력한 게이트 (원문)

```
━━ SmartThink 무장 게이트 ━━

1. 입력 해석  
   지역 보행자 안전 안내를 더 쉽게 이해하고, 실제 위험 상황에서 행동으로 이어지도록 개선합니다.

2. 진단  
   Cynefin: 복합(Complex) - 복잡(Complicated) 경계 | 분류: 문제 해결

3. 추천 모듈 (5개, ★ = 주력)  
   ★ 핵심 엔진 - 안내의 목적을 “정보 제공”이 아닌 “위험 인지와 안전 행동 유도”로 재정의합니다.  
   ★ 인지 무기고 - 보행자의 주의 한계, 위험 지각, 익숙함 편향을 안내 구조에 반영합니다.  
   ★ 패턴 합성 - 통학로, 교차로, 골목, 야간 등 지역별 반복 위험 신호를 안내 체계로 묶습니다.  
   TRIZ 혁신 시스템 - 눈에 띄되 과밀하지 않고, 공통 안내이되 장소 맥락에 맞는 모순을 풉니다.  
   실행 속도 - 작은 현장 실험과 관찰로 안내 개선안을 빠르게 검증하는 루프를 설계합니다.

4. 예상 비용 (추정치)  
   메인에 실릴 팩 ≈ 131K 토큰  
   서브에이전트 작업 ≈ 144K 토큰  
   ※ 두 값 모두 추정이며 실제와 다를 수 있습니다.

5. 리서치: ON  
   지역·보행자 안전 현황과 검증된 안내 원칙을 함께 조사합니다.

6. 조작  
   Enter: 진행  
   숫자: 예산 상한 지정 (예: `60000`)  
   모듈 조정: 예: “TRIZ 빼고 안티프래질 넣어”  
   `--nosearch`: 리서치 끄기
```

## 첨부: 실행 헤더
```
Reading additional input from stdin...
OpenAI Codex v0.153.4
--------
workdir: [REDACTED]
model: gpt-5.6-terra
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: high
reasoning summaries: none
session id: 01a07ce5-48e2-73f0-99d5-4c62505966e3
--------
user
```
