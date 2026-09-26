# T9-bash 권한 프롬프트 관찰 (#21)

실행일: 2026-09-27 02:45 ~ 02:58 (+09:00) | Claude Code 2.1.283, Opus 5.5 | 브랜치 st-21-assemble-pack, 커밋 88631f8(파일 모드 수정 전, 조립 로직은 최종과 같음).
환경: 격리 `CLAUDE_CONFIG_DIR`(`<CFG_DIR>`), `SMARTTHINK_VAULT`는 `~/.claude` 밖 임시 디렉터리(`<VAULT_DIR>`), `claude --plugin-dir "$WT" --model opus --permission-mode default`, 상태줄 `⏸ manual mode on`(세션 1·2 모두). 격리 `settings.json` 시작값: `defaultMode: default` + 실제 vault Read·Edit deny 2줄, allow 없음.
프롬프트는 20초 간격 화면 폴링으로 원문을 기록한 뒤 전부 `1`(Yes, 1회)로만 답했다(`don't ask again` 계열 미선택). 도구 호출 목록은 격리 설정의 세션 jsonl과 서브에이전트 jsonl에서 추출했다.

워크트리 코드 증명: 세션 jsonl의 스킬 로드 메시지 `Base directory for this skill: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink`(2회, 세션 1·2). 서브에이전트 meta `{'agentType': 'smartthink:st-armorer', 'requestShape': 'background'}`. 격리 설정이라 사용자 레벨 심링크 정의(bare `st-armorer`)는 로드되지 않고, `smartthink:st-armorer`는 `--plugin-dir "$WT"`의 `agents/st-armorer.md`다.

## 결론

| 구간 | 프롬프트 | 종류 |
|---|---|---|
| 무장 중 armorer의 vault 쓰기(Write pack.md, Bash assemble-pack.py, Write manifest.json) | **0회** | - |
| 무장 중 armorer의 기타 도구 | 0회 | Read 8회(레퍼런스, 원래 작업 디렉터리 안) |
| 메인 세션, 무장 전 | 2회 | Bash `resolve-vault.py --ensure`(vault 해석·시드, `python3` 규칙 없음), Bash `ls -la <VAULT> ...; cat evolution-state.md`(vault 읽기) |
| 메인 세션, armorer 완료 뒤 | 1회 | Bash `ls <팩>/; grep -n '^## [0-9]\. ' pack.md`(반환 규약 확인용 vault 읽기) |

- **목표(vault 쓰기 관련 프롬프트 0회)는 armorer 구간에서 충족.** armorer가 vault에 쓴 호출 3개(Write·Bash·Write)가 모두 프롬프트 없이 실행됐다. `Bash(python3 <스크립트 절대경로> *)` 규칙이 `python3 <HOME>/.../scripts/assemble-pack.py --pack-dir ... --modules ...` 명령과 매칭됐다. 팩 디렉터리는 pack.md Write가 만들었다(armorer의 mkdir 호출 없음).
- 이전 T9-fix(#14)에서 armorer 구간에 뜬 Bash 프롬프트(mkdir·heredoc·printf/cat 이어 붙이기, `check-structure --pack`)는 이번 런에서 0회다.
- **남은 3회는 전부 메인 세션 Bash이고 armorer 밖이다.** 1회는 `resolve-vault.py --ensure`(vault가 없을 때 packs/·시드를 만드는 명령, 이번 런에서는 이미 있어 쓰기 없음), 2회는 vault 읽기 확인(`ls`·`cat`·`grep`). 원인: 이 명령들은 SKILL.md 경로 규약·반환 규약 확인 절차가 부르는 것이고 init이 제안하는 규칙(Edit 1개 + assemble-pack Bash 1개) 밖이다. 읽기 확인은 Read/Glob으로 대체할 수 있고, resolver는 별도 규칙이 필요하다. 이번 이슈 소유 범위(armorer·5b·init 4절) 밖이라 후속으로 넘긴다.
- 리서치는 게이트에서 `--nosearch`로 껐다(#14 T9-fix와 같은 조건). WebSearch·WebFetch 프롬프트는 이번 런에서 관찰 대상이 아니다.
- 산출 팩은 `check-structure.py --pack` H 5/5 PASS(아래). 관찰 부산물: 조립된 pack.md의 파일 모드가 `0600`이었다(스크립트의 mkstemp 기본값). 이후 TDD 사이클 S4-6으로 원래 모드를 유지하도록 고쳤다(`tests/evidence/21-tdd-log.md`).

## armorer·메인 도구 호출 (세션 2, jsonl 추출, 시각은 UTC)

```
## main session (세션 2)
- 17:50:32 Bash: python3 <HOME>/workspace/smartthink-st-21-assemble-pack/scripts/resolve-vault.py --ensure
    -> {"path": "<VAULT>", "source": "env"}
- 17:50:33 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/index.json
    -> 1	{ 2	  "generated": "2026-09-07T14:09:50.259792Z", 3	  "modules": { 4	    "anti-fragile-strategy.md": { 5	      "bytes": 43271, 6	      "est_tokens": 19669, 7	
- 17:50:53 Bash: ls -la <VAULT> <VAULT>/packs; cat <VAULT>/evolution-state.md
    -> <VAULT>: total 16 drwx------@    5 bkan  staff     160 Sep 27 02:49 . drwx------@ 6341 bkan  staff  2029
- 17:50:56 Read: <VAULT>/profile.md
    -> 1	--- 2	version: 3 3	updated: 2026-09-27T02:48:37+09:00 4	--- 5	 6	# SmartThink 사용자 프로필 7	 8	> **이 파일은 사용자가 직접 편집할 수 있다.** (D21 ①) 진화 상태(`evolution-state.md`)와 
- 17:52:04 Agent: smartthink:st-armorer
    -> Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing
- 17:57:08 Bash: ls <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/; grep -n '^## [0-9]\. ' <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/pack.md
    -> manifest.json pack.md 3:## 1. 무장 브리핑 36:## 2. 작업 해석 76:## 4. 작업 적용 레이어 182:## 5. 레퍼런스 원문 192:## 1. 제1원리 분해 엔진 (First Principles Decomposition Engine) 267:## 2. 
- 17:57:14 Read: <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/pack.md
    -> 1	# SmartThink 무장 팩 - 지역 문화센터 수업 신청 흐름 개선 2	 3	## 1. 무장 브리핑 4	 5	**활성 프레임 3** 6	1. **TRIZ 물리적 모순 + 분리 원칙** - "신청 창구는 모든 주민에게 넓게 열려 있어야 하면서 동시에 폭주·매크로에는 닫혀 있어야 한
## armorer 서브에이전트
- 17:52:06 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/core-engines.md
    -> 1	# 천재적 사고 운영 엔진 (Core Thinking Engines) 2	 3	> 이 문서의 12개 엔진은 추상적 채점표가 아니라 **실행 가능한 운영 절차**다. 4	> 각 엔진은 독립적으로 사용 가능하며, 복수 엔진을 **곱셈적으로 조합**하면 통찰의 품질이 기하급수적으로 상승한
- 17:52:06 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/cognitive-arsenal.md
    -> 1	# 인지 무기고 (Cognitive Arsenal) 2	 3	> 81개의 멘탈 모델을 원천 도메인별로 조직화하고, 비즈니스 전장에 무기화한 사고 도구 라이브러리. 4	> 평범한 사고와 천재적 전략을 가르는 것은 도구의 수가 아니라 도구를 꺼내는 타이밍이다. 5	> Charlie Mu
- 17:52:06 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/triz-innovation.md
    -> 1	# TRIZ 체계적 혁신 엔진 (TRIZ Systematic Innovation Engine) 2	 3	> TRIZ(발명 문제 해결 이론, Theory of Inventive Problem Solving)는 인류 역사상 **유일한 알고리즘적(Algorithmic) 혁신 방법론**이다
- 17:52:07 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/pattern-synthesis.md
    -> 1	# 패턴 합성 시스템 (Pattern Synthesis System) 2	 3	> 도메인을 넘나드는 패턴 인식과 돌파적 통찰 합성을 위한 체계적 프레임워크. 4	> 천재는 남들이 보지 못하는 연결을 본다. 이 문서는 그 연결을 보는 법을 체계화한다. 5	 6	--- 7	 8	## 핵
- 17:52:08 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/execution-velocity.md
    -> 1	# 실행 속도 (Execution Velocity) 2	 3	> 통찰을 현실로 전환하는 최대 속도 시스템. 4	> 스타트업에서 속도는 전략적 선택이 아니라 생존 조건이다. 5	> "First mover advantage"는 신화지만, "Fastest learner advantage"
- 17:52:09 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/analysis-method.md
    -> 1	# SmartThink 분석 방법론 (Analysis Methodology) 2	 3	> **SSOT**. Deep(인라인) 및 Agent(서브에이전트) 모드 공통 참조. 4	> 템플릿 변수 없음. 방법론만 기술. 실행 모드별 차이는 INTERACTION POINT에서 분기. 5	 
- 17:52:12 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/core-engines.md
    -> 774	- **복합 우위 + 데이터 생태계(#10)**: 생태계 참여자들의 데이터가 플라이휠을 가속 775	 776	### 안티패턴 (하지 말아야 할 것) 777	 778	- **감소하는 우위에 투자**: 가격 경쟁은 복합하지 않는다. 경쟁자가 항상 더 낮출 수 있다 779	- **플라
- 17:52:13 Read: <HOME>/workspace/smartthink-st-21-assemble-pack/skills/smartthink/references/cognitive-arsenal.md
    -> 428	### 41. 네트워크 이론 (Network Theory) 429	 430	**핵심**: 노드(Node), 엣지(Edge), 허브(Hub). 네트워크의 가치는 노드 수의 제곱에 비례한다(Metcalfe's Law). 431	**비즈니스 적용**: 소셜 네트워크, 마켓플레이스, 플
- 17:56:51 Write: <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/pack.md
    -> File created successfully at: <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/pack.md (file st
- 17:56:54 Bash: python3 <HOME>/workspace/smartthink-st-21-assemble-pack/scripts/assemble-pack.py --pack-dir <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/ --modules core-engines.md cognitive-arsenal.md triz-innovation.md pat
    -> {"pack": "<VAULT>/packs/2026-09-27-culture-center-class-signup-flow/pack.md", "modules": ["core-engines.
- 17:57:00 Write: <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/manifest.json
    -> File created successfully at: <VAULT>/packs/2026-09-27-culture-center-class-signup-flow/manifest.json (f
```

## 세션 2 권한 프롬프트 원문 (화면 폴링)

```
[스냅샷 02:50:49]
 Bash command
 Tip: auto mode handles these prompts for you — choose "switch to auto mode" below
   │ python3 <HOME>/workspace/smartthink-st-21-assemble-pack/scripts/resolve-vault.py --ensure
   Resolve SmartThink vault path
 This command requires approval
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, and don’t ask again for: python3 *
   3. Yes, and switch to auto mode · auto mode handles these prompts for you
   4. No
 Esc to cancel · Tab to amend

[스냅샷 02:50:54]
 Bash command
 Tip: auto mode handles these prompts for you — choose "switch to auto mode" below
   │ ls -la /var/folders/[REDACTED]/T/<VAULT_DIR>
   │ /var/folders/[REDACTED]/T/<VAULT_DIR>/packs; cat
   │ /var/folders/[REDACTED]/T/<VAULT_DIR>/evolution-state.md
   List vault contents and show evolution state
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, allow reading from /private/var/folders/[REDACTED]/T/<VAULT_DIR> from this project
   3. Yes, and switch to auto mode · auto mode handles these prompts for you
   4. No
 Esc to cancel · Tab to amend

=== 게이트 응답 이후 ===
[스냅샷 02:57:11]
 Bash command
 Tip: auto mode handles these prompts for you — choose "switch to auto mode" below
   │ ls /var/folders/[REDACTED]/T/<VAULT_DIR>/packs/2026-09-27-culture-center-class-signup-flow/; grep -n '^## [0-9]\. ' /var/folders/[REDACTED]/T/<VAULT_DIR>/packs/2026-09-27-culture-center-class-signup-flow/pack.md
   Check pack files and section headings
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, allow reading from /private/var/folders/[REDACTED]/T/<VAULT_DIR>/packs/2026-09-27-culture-center-class-signup-flow from this project
   3. Yes, and switch to auto mode · auto mode handles these prompts for you
   4. No
 Esc to cancel · Tab to amend

```

## 산출 팩 검사

`python3 scripts/check-structure.py --pack <VAULT>/packs/2026-09-27-culture-center-class-signup-flow` (exit 0):

```
PASS H. pack: pack.md and manifest.json exist
PASS H. pack: manifest schema and boolean research
PASS H. pack: section titles present and ordered
PASS H. pack: section 5 verbatim hash integrity
PASS H. pack: module markers scoped to section 5
42 passed, 0 failed, 0 skipped
pack: 5 passed, 0 failed, 0 skipped
```
