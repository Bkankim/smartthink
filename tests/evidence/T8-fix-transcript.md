# T8-fix 실측 - git 없는 설치의 armorer 폴백 (#15)

생성: 2026-09-27 00:54~01:04 (+09:00) | 코드: 브랜치 `st-15-armorer-fallback` 커밋 f1ff5bc | Claude Code 2.1.283, Opus 5.5 | 판정: **PASS**

## 실행 조건

- git 없는·정의 없는 플러그인 사본: `cp -R "$WT" <TMP>/plugin && rm -rf <TMP>/plugin/.git <TMP>/plugin/.fablize && rm <TMP>/plugin/agents/st-armorer.md`. 확인: `ls <TMP>/plugin/agents` = `st-thinker.md`뿐, `.git` 0개. 작업 디렉터리 `<TMP>/work`는 `git rev-parse` = `fatal: not a git repository`.
- 격리 `CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG>`: 사용자 레벨 agents/skills/commands 없음(사용자 레벨 `st-armorer` 심링크 배제). settings.json allow 규칙 + 실제 vault deny 규칙, `.claude.json`은 온보딩 완료 플래그와 작업 폴더 신뢰만.
- 임시 vault: `SMARTTHINK_VAULT=<VAULT>`(`mktemp -d`). 사전 확인 `resolve-vault.py` = `{"path": "<VAULT>", "source": "env"}`.
- 명령(Orca 대화형 터미널, 비대화 권한): `cd <TMP>/work && CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG> SMARTTHINK_VAULT=<VAULT> CLAUDE_CODE_OAUTH_TOKEN="$ANTHROPIC_OAUTH_TOKEN" claude --dangerously-skip-permissions --plugin-dir <TMP>/plugin --model opus`. 시작 시 폴더 신뢰 확인과 bypass 확인에 "Yes"로 응답했다.
- 입력: `/smartthink:smartthink 동네 도서관의 청소년 이용률을 높이는 방안` → 게이트 → `진행`.
- 스킬 Base directory: `<TMP>/plugin/skills/smartthink`(git 없는 사본 코드, 메인 체크아웃 심링크가 아님).

## 화면 원문 (`orca terminal read --screen`)

게이트 5항목 일부:

```
  - 이 환경에는 전용 무장 에이전트(st-armorer)가 등록돼 있지 않습니다. 그래서 범용 에이전트(general-purpose)에 무장
    지시문 전문(armorer-prompt.md)을 넣어 대신 실행합니다.
```

`진행` 직후(스폰 90초 뒤):

```
❯ 진행
⏺ smartthink:st-armorer(SmartThink 무장 팩 생성)
  ⎿  Initializing…
  ⎿  Error: Agent type 'smartthink:st-armorer' not found. Available agents: claude, claude-code-guide, Explore,
     general-purpose, Plan, smartthink:st-thinker, statusline-setup
⏺ st-armorer(SmartThink 무장 팩 생성)
  ⎿  Initializing…
  ⎿  Error: Agent type 'st-armorer' not found. Available agents: claude, claude-code-guide, Explore, general-purpose,
     Plan, smartthink:st-thinker, statusline-setup
  Read 1 file
⏺ Agent(SmartThink 무장 팩 생성)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)
⏺ 무장 팩을 만드는 중입니다(범용 에이전트로 대체 실행, 백그라운드). 완료 알림이 오면 브리핑을 출력합니다.
✻ Waiting for 1 background agent to finish
```

완료 뒤 마지막 화면(브리핑 말미):

```
  팩: <VAULT>/packs/2026-09-27-teen-library-usage/  |  모듈:
  핵심 엔진, 인지 무기고, 패턴 합성, 현실 왜곡, 실행 속도  |  비용: 팩 ≈137K / 작업 ≈165K  |  리서치: ON (출처 13개,
  접근 실패 2건: 403 차단 1건, PDF 판독 실패 1건)
  ※ 비용이 게이트 추정보다 늘었습니다. 팩은 126K에서 137K로(+11K), 작업은 139K에서 165K로(+26K) 커졌습니다.
  ※ 전용 무장 에이전트(st-armorer)가 등록돼 있지 않아 범용 에이전트(general-purpose)로 대체 실행했습니다. 팩 구조 검사는
  5/5 통과했습니다.
  프로필이 없습니다. /st init으로 프로필을 만들면 다음 무장부터 모듈이 사용자에게 맞게 골라집니다.
  무장 완료. 이제 작업을 지시하세요.
  깊은 작업이라면 /effort xhigh 를 먼저 실행하는 것을 권장합니다.
✻ Worked for 7m 14s · done 1:04 AM
```

## 판정 근거 (세션 jsonl 실측)

| 기준 | 결과 | 근거 |
|---|---|---|
| `smartthink:st-armorer` not found → bare not found → general-purpose | PASS | 아래 타임라인 15:56:57, 15:56:59, 15:58:06 |
| 폴백 브리핑 원천 = `references/armorer-prompt.md` Read | PASS | 15:57:01 `Read <TMP>/plugin/skills/smartthink/references/armorer-prompt.md`. general-purpose prompt(10968자)가 파일의 `---` 아래 본문을 **그대로 포함**(부분문자열 일치 True)하고 끝에 `## Input` 블록(9858자 위치)을 붙였다 |
| git 호출 0회 | PASS | 메인 jsonl Bash 명령 중 `git` 0건, 서브에이전트 jsonl 0건(명령 문자열을 정규식 `(^\|[;&\|\s(])git\s`로 셌다) |
| 백그라운드 여부 | 백그라운드 | tool_use 입력 키 = `subagent_type, description, prompt`(run_in_background 없음), 결과 `Async agent launched successfully`, 화면 `Backgrounded agent` |
| 대기 규칙 준수 | PASS | 스폰(15:58:06) 뒤 메인 출력은 1줄 상태 고지(15:58:08)뿐. 완료 알림(16:03:42.859) 전 메인 도구 호출 0건. 첫 팩 접근은 알림 뒤 16:03:46(절 구조 확인 + 1절 출력) |
| 팩 6절 | PASS | `## 1. 무장 브리핑`(7행) ~ `## 6. 과거 인사이트와 프로필`(4222행), `T8-fix-pack.md` |
| manifest 11필드 | PASS | 11개 키, `research` = true(boolean), `T8-fix-manifest.json` |
| `python3 scripts/check-structure.py --pack <팩>` | exit 0 | 워크트리 검사기, 40 passed + pack 5/5, `T8-fix-structure-check.txt` |

참고: 사본의 `scripts/check-structure.py`로 같은 팩을 돌리면 H 5/5 PASS지만 exit 1이다. `agents/st-armorer.md`를 일부러 지운 사본이라 A·C·D절이 정의 부재를 FAIL로 잡기 때문이다(기대 동작). 판정은 워크트리 검사기로 한다.

## 메인 세션 타임라인 (jsonl 렌더링, 게이트 이후. 경로 치환: `<TMP>` 임시 사본, `<VAULT>`, `<SESSION_TMP>`. 도구 결과·긴 입력은 잘림. 도구 결과 안의 em dash는 하이픈으로 치환됨)

```
[2026-09-26T15:56:49.791Z] USER: 진행
[2026-09-26T15:56:57.915Z] TOOL Agent: {"subagent_type": "smartthink:st-armorer", "description": "SmartThink 무장 팩 생성", "prompt": "## Input\n- **Task/Topic**: 동네 도서관의 청소년 이용률을 높이는 방안\n- **Interpretation**: 주제만 입력됨. 예상 작업 A: 청소년 이용률 저하 원인 진단 + 우선 개입점 도출 / B: 공간·프로그램·운영·홍보 개선안 포트폴리오 + 소규모 파일럿·측정지표 설계 / C: 예산·인력 제약 하 구청·운영위 제출용 제안서 작성. 사용자 미지정 → 팩 2절에 셋 다 남김\n- **Cynefin Domain**: Complex (예산·공간 설계에 C ...[잘림]
[2026-09-26T15:56:57.925Z]   -> Agent type 'smartthink:st-armorer' not found. Available agents: claude, claude-code-guide, Explore, general-purpose, Plan, smartthink:st-thinker, statusline-setup
[2026-09-26T15:56:59.605Z] TOOL Agent: {"subagent_type": "st-armorer", "description": "SmartThink 무장 팩 생성", "prompt": "(retry) see input"}
[2026-09-26T15:56:59.610Z]   -> Agent type 'st-armorer' not found. Available agents: claude, claude-code-guide, Explore, general-purpose, Plan, smartthink:st-thinker, statusline-setup
[2026-09-26T15:57:01.705Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/armorer-prompt.md"}
[2026-09-26T15:57:01.734Z]   -> 1	# SmartThink 무장 폴백 프롬프트 (armorer-prompt)
2	
3	> **용도**: `smartthink:st-armorer`(접두어 없는 설치에서는 bare `st-armorer`) 에이전트 정의가
4	> 어느 이름으로도 해석되지 않는 환경에서 5a armorer 경로를 살리기 위한 폴백 SSOT.
5	> SKILL.md 5a 폴백이 이 파일을 Read하고, `---` 구분선 아래 전문 끝에 5a의 **Input 블록**(치환
6	> 완료 상태)을 붙여 Agent 도구의 `prompt` 파라미터로 `subage
[2026-09-26T15:58:06.671Z] TOOL Agent: {"subagent_type": "general-purpose", "description": "SmartThink 무장 팩 생성", "prompt": "## 폴백 스폰 추가 규율 (정의 파일의 frontmatter 대체)\n\n- 너는 general-purpose로 스폰됐지만 아래 st-armorer 임무만 수행한다.\n- 도구는 **Read, Grep, Glob, WebSearch, WebFetch, Write, Bash, Skill**만 쓴다. Agent 도구로 하위\n  에이전트를 띄우지 마라.\n- 사고 깊이는 effort high 수준으로 유지하고, 턴 예산 40턴을 스스로 센다.\n- git 명령으로 정의를 찾거나 복구하지 마라 ...[잘림]
[2026-09-26T15:58:06.679Z]   -> Async agent launched successfully. (This tool result is internal metadata - never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: <ID> (internal ID - do not mention to user. Use SendMessage with to: '<ID>', summary: '<5-10 word recap>' to continue this
[2026-09-26T15:58:08.022Z] MAIN TEXT: 무장 팩을 만드는 중입니다(범용 에이전트로 대체 실행, 백그라운드). 완료 알림이 오면 브리핑을 출력합니다.
[2026-09-26T16:03:42.859Z] USER: <task-notification>
<task-id>a49e960147ed6e8f5</task-id>
<tool-use-id>toolu_014nTpjE9vdcDyMZWiKthA89</tool-use-id>
<output-file><SESSION_TMP></ou
[2026-09-26T16:03:46.205Z] TOOL Bash: {"command": "P=<VAULT>/packs/2026-09-27-teen-library-usage/pack.md; grep -n '^## [1-6]\\. ' $P; awk '/^## 1\\. 무장 브리핑/{f=1} /^## 2\\. 작업 해석/{f=0} f' $P", "description": "Check pack sections and print briefing section"}
[2026-09-26T16:03:46.291Z]   -> 7:## 1. 무장 브리핑
38:## 2. 작업 해석
56:## 3. 리서치 합성
135:## 4. 작업 적용 레이어
225:## 5. 레퍼런스 원문
235:## 1. 제1원리 분해 엔진 (First Principles Decomposition Engine)
310:## 2. 비대칭 기회 탐지 엔진 (Asymmetric Opportunity Detection Engine)
395:## 3. 네트워크 효과 설계 엔진 (Network Effects Architecture Engine)
483:## 4. 시장 창조 엔진 (Market C
[2026-09-26T16:04:03.952Z] MAIN TEXT: ## 1. 무장 브리핑

**활성 프레임 3**
1. **제1원리 분해 (핵심 엔진 #1)** - "청소년은 도서관에 안 온다"를 기저 진실(시간·자리·소음 허용·동행·비용·거리)로 쪼갭니다. 관습(정숙 규범, 운영시간, 자료실 배치)과 물리적 제약(면적, 예산, 사서 1인당 이용자 약 3.7만 명)을 가르는 칼 역할입니다.
2. **역전 사고 (핵심 엔진 #11)** - "청소년이 절대 오지 않을 도서관을 만들려면?"에서 실패 모드 10개 이상을 뽑고 상위 5개를 제거하는 방식으로 개선안 포트폴리오를 거릅니다. 파일럿의 킬 기준도 여기서 나옵니다.
3. **시장 창조 + 이상 징후 채굴 (핵심 엔진 #4, 패턴 합성 §3)** - 청소년이 도서관을 '고용'하는 진짜 일(JTBD)과, 도서관 밖에서 이미 벌어지는 이상 징후(스터디카페 62배 증가, 마포 공공 스터디카페 좌석 초과 방문)를 연결해 경쟁 프레임을 다시 정합니다.

**이 작업에 적용할 규칙**
- 어떤 개선안이든 먼저 "관습인가 물리 제약인가"로 분류하고, 관습만 바꾸는 안을 비용이 드는 안보다 먼저 검토하십시오.
- 개선안을 내기 전에 실패 모드 카탈로그(10개 이상)부터 작성하고, 확률 높음×영향 치명적인 항목부터 제거하십시오.
- 경쟁자를 '다른 도서관'이 아니라 스터디카페·집·학원 자습실·PC방 같은 청소년의 실제 대안으로 정의하고, 이들이 이기는 차원(시간, 소
...(이하 1절 브리핑 출력, 화면 원문 절 참고)
```

## 서브에이전트(general-purpose 폴백) 도구 호출 전체

```
[2026-09-26T15:58:09.886Z] TOOL Bash: {"command": "cd \"<TMP>/plugin/skills/smartthink/references\" && wc -c *.md && ls <VAULT>/packs 2>/dev/null | wc -l", "description": "List reference file sizes and pack count"}
[2026-09-26T15:58:12.044Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/core-engines.md"}
[2026-09-26T15:58:12.574Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/pattern-synthesis.md"}
[2026-09-26T15:58:13.354Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/reality-distortion.md"}
[2026-09-26T15:58:14.054Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/execution-velocity.md"}
[2026-09-26T15:58:17.052Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/core-engines.md", "offset": 774}
[2026-09-26T15:58:18.314Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/cognitive-arsenal.md"}
[2026-09-26T15:58:22.312Z] TOOL Read: {"file_path": "<TMP>/plugin/skills/smartthink/references/cognitive-arsenal.md", "offset": 428}
[2026-09-26T15:58:24.032Z] TOOL Bash: {"command": "cd \"<TMP>/plugin/skills/smartthink/references\" && grep -n \"Step 0.5\\|원문 무결성\" analysis-method.md | head", "description": "Locate Step 0.5 and integrity rule sections"}
[2026-09-26T15:58:27.122Z] TOOL Bash: {"command": "cd \"<TMP>/plugin/skills/smartthink/references\" && sed -n 36,110p analysis-method.md && echo ------ && sed -n 399,460p analysis-method.md", "description": "Read Step 0.5 and integrity rule sections"}
[2026-09-26T15:58:29.532Z] TOOL ToolSearch: {"query": "select:WebSearch,WebFetch", "max_results": 2}
[2026-09-26T15:58:31.142Z] TOOL WebSearch: {"query": "국민독서실태조사 2025 청소년 도서관 이용률 학생 독서율"}
[2026-09-26T15:58:32.202Z] TOOL WebSearch: {"query": "공공도서관 청소년 전용공간 틴즈 라운지 이용자 증가 사례"}
[2026-09-26T15:58:32.601Z] TOOL WebSearch: {"query": "teen library use decline study cafes gaming YALSA teen space research 2024"}
[2026-09-26T15:58:54.363Z] TOOL WebFetch: {"url": "https://www.readingnews.kr/news/articleView.html?idxno=20548", "prompt": "2025년 기준 전국 공공도서관 통계 수치를 모두 추출: 도서관 수, 방문자 수, 1관당 봉사대상 인구, 대출, 자료구입비, 사서 수, 청소년 관련 수치, 연도별 증감. 수치와 해당 문장을 정확히."}
[2026-09-26T15:58:55.692Z] TOOL WebFetch: {"url": "https://www.tandfonline.com/doi/full/10.1080/13467581.2025.2455025", "prompt": "Extract: sample size, key findings on which design factors Korean adolescents prefer in library teen spaces, any statistics about teen library usage decline in Korea, re ...[잘림]
[2026-09-26T15:58:56.213Z] TOOL WebSearch: {"query": "스터디카페 수 전국 2024 2025 청소년 이용 증가 통계"}
[2026-09-26T15:59:17.743Z] TOOL WebFetch: {"url": "https://www.publishersweekly.com/pw/by-topic/industry-news/libraries/article/95383-the-quiet-crisis-facing-u-s-public-libraries.html", "prompt": "Extract key numbers (visits decline, collection size, programming attendance) and the author's argument ...[잘림]
[2026-09-26T15:59:18.173Z] TOOL WebSearch: {"query": "청소년 공공도서관 이용하지 않는 이유 설문 조용해야 해서 이연옥 2025 부산 청소년 558명"}
[2026-09-26T15:59:40.805Z] TOOL WebFetch: {"url": "https://journal.kci.go.kr/kslis/archive/articlePdf?artiId=ART003307545", "prompt": "청소년이 공공도서관을 어떻게 인식하는지(현재 이미지 vs 바라는 이미지), 이용하지 않는 이유, 스터디카페/학원 등 대체재 언급, 주요 수치나 인용 발언을 추출. 저자·연도·표본 포함."}
[2026-09-26T16:00:17.842Z] TOOL Bash: {"command": "mkdir -p <VAULT>/packs/2026-09-27-teen-library-usage/ && ls <VAULT>/packs/ | wc -l; ls <VAULT>/; head -5 <VAULT>/profile.md 2>/dev/null; date +%Y-%m-%dT%H:%M:%S%z", "description": "Create pack directory and check vault state"}
[2026-09-26T16:03:08.031Z] TOOL Write: {"file_path": "<VAULT>/packs/2026-09-27-teen-library-usage/pack.md", "content": "# Armory Pack: 동네 도서관의 청소년 이용률을 높이는 방안\n\n- 생성: 2026-09-27 / Cynefin: Complex (예산·공간 설계는 Complicated 성격 혼재) / 분류: 전략 수립\n- 모듈: ★ 핵심 엔진(주력 #1 제1원리 분해, #11 역전 사고, #4 시장 창조), ★ 인지 무기고 ...[잘림]
[2026-09-26T16:03:20.333Z] TOOL Bash: {"command": "set -e\nREF=\"<TMP>/plugin/skills/smartthink/references\"\nPACK=\"<VAULT>/packs/2026-09-27-teen-library-usage/pack.md\"\nfor f in core-engines.md cognitive-arsenal.md pattern-synthesis.md reality-distortion.md execution-velocity.md; do\n  SRC=\"$REF ...[잘림]
[2026-09-26T16:03:27.343Z] TOOL Bash: {"command": "PACK=\"<VAULT>/packs/2026-09-27-teen-library-usage/pack.md\"\ngrep -n 'MODULE-' \"$PACK\" | awk -F: '$1<225 || $1>4221'; echo \"outside-check done\"\nS=$(find <TMP>/plugin -name 'check-structure.py' | head -1); echo \"$S\"\n[ -n \"$S\" ] && python3  ...[잘림]
[2026-09-26T16:03:36.454Z] TOOL Bash: {"command": "D=\"<VAULT>/packs/2026-09-27-teen-library-usage\"\nREF=\"<TMP>/plugin/skills/smartthink/references\"\nPB=$(wc -c < \"$D/pack.md\"); RB=$(cat $REF/core-engines.md $REF/cognitive-arsenal.md $REF/pattern-synthesis.md $REF/reality-distortion.md $REF/exe ...[잘림]
```

모듈 5개 전문 Read(긴 파일 2개는 offset으로 이어 읽기), Step 0.5와 원문 무결성 절 확인, 리서치 뒤 팩 작성. git·Agent 호출 없음.
