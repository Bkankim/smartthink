# T16-before: main 코드 무장 1회 권한 프롬프트 재현 (#26)

- 실행일: 2026-09-27 05:48 ~ 05:55 (+09:00), Claude Code 2.1.283, `--model opus`, `--permission-mode default`(상태줄 `⏸ manual mode on`).
- 코드: 브랜치 fix-26-main-bash-prompts 시작점 d3f4113(main, #14·#20·#21 머지 포함)을 `git archive HEAD`로 푼 사본 `<ROOT>/wt-main`. `--plugin-dir <ROOT>/wt-main`, 호출 `/smartthink:smartthink`. 세션 jsonl의 스킬 로드 줄: `Base directory for this skill: <ROOT>/wt-main/skills/smartthink`.
- 환경: `<ROOT>`는 `mktemp -d`의 실경로(`/private/var/folders/...`, 심링크 조상 없음). 격리 `CLAUDE_CONFIG_DIR=<ROOT>/cfg`, 가짜 `HOME=<ROOT>/home`, 작업 디렉터리는 가짜 홈의 `~/project`(실사용처럼 플러그인 디렉터리와 vault가 둘 다 작업 디렉터리 밖이다). `SMARTTHINK_VAULT`·`XDG_CONFIG_HOME`·`XDG_DATA_HOME` 제거, 가짜 홈 포인터 `~/.config/smartthink/vault-pointer` → `<ROOT>/home/notes/smartthink`(resolver `source: pointer`). 인증은 자식 env에만 주입(값 미기록).
- init 대체: main 코드의 init이 설치하는 규칙 2개(T15-rerun의 init diff와 같다)를 그 스크립트 출력 그대로 격리 settings에 미리 넣었다. vault 시드(`--ensure`)와 빈 템플릿 profile.md도 미리 둔다. Read·Glob·Grep·Bash는 사전 허용하지 않는다(측정 대상).
- 입력: `/smartthink:smartthink --nosearch 동네 체육관 수영 강습 대기자 배정 방식 개선` → 게이트에 `진행`. 프롬프트는 화면 폴링(3~5초)으로 원문을 기록하고 전부 `1`(Yes, 1회)로만 답했다.

## 격리 settings.json (시작값)

```json
{"permissions":{"defaultMode":"default","allow":["WebSearch","WebFetch","Skill","Agent","Edit(~/notes/smartthink/**)","Bash(python3 <ROOT>/wt-main/scripts/assemble-pack.py *)"],"deny":["Read(//<HOME>/workspace/vault/**)","Edit(//<HOME>/workspace/vault/**)","Read(//<HOME>/.config/smartthink/**)","Edit(//<HOME>/.config/smartthink/**)"]}}
```

## 결과: 권한 프롬프트 10회

| # | 주체 | 도구 | 대상 | 단계 |
|---|---|---|---|---|
| 1 | 메인 | Bash | `python3 <ROOT>/wt-main/scripts/resolve-vault.py --ensure` | 경로 규약({VAULT} 해석) |
| 2 | 메인 | Read | `<ROOT>/wt-main/skills/smartthink/references/index.json` | 3~4단계(게이트 비용 추정) |
| 3 | armorer | Read | `references/core-engines.md` | 5a Step A |
| 4 | armorer | Read | `references/cognitive-arsenal.md` | 5a Step A |
| 5 | armorer | Read | `references/triz-innovation.md` | 5a Step A |
| 6 | armorer | Read | `references/meta-cognition.md` | 5a Step A |
| 7 | armorer | Read | `references/execution-velocity.md` | 5a Step A |
| 8 | armorer | Read | `references/analysis-method.md` | 5a Step 0.5 |
| 9 | armorer | Read | `references/core-engines.md`(774~1173행) | 5a 이어 읽기 |
| 10 | armorer | Read | `references/cognitive-arsenal.md`(428~877행) | 5a 이어 읽기 |

프롬프트 없이 실행된 호출: 메인 Read `profile.md`·`evolution-state.md`·`packs/<팩>/pack.md`(vault, 작업 디렉터리 밖), armorer Write `pack.md`·`manifest.json`, armorer Bash `assemble-pack.py`(규칙 매칭).

## 도구 호출 전체 (세션 jsonl 추출, 시각 UTC)

```
== main 34a4cf2d-705a-4064-986c-f7b0746569e7.jsonl
SKILL Base directory for this skill: <ROOT>/wt-main/skills/smartthink
20:48:04 Bash: python3 <ROOT>/wt-main/scripts/resolve-vault.py --ensure
20:48:05 Read: <ROOT>/wt-main/skills/smartthink/references/index.json
20:49:01 Read: <ROOT>/home/notes/smartthink/profile.md
20:49:01 Read: <ROOT>/home/notes/smartthink/evolution-state.md
20:49:40 Agent: smartthink:st-armorer
20:54:55 Read: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-lesson-waitlist-allocation/pack.md
== armorer agent-a48a791da6a18668c.jsonl
20:49:43 Read: <ROOT>/wt-main/skills/smartthink/references/core-engines.md
20:49:44 Read: <ROOT>/wt-main/skills/smartthink/references/cognitive-arsenal.md
20:49:44 Read: <ROOT>/wt-main/skills/smartthink/references/triz-innovation.md
20:49:45 Read: <ROOT>/wt-main/skills/smartthink/references/meta-cognition.md
20:49:46 Read: <ROOT>/wt-main/skills/smartthink/references/execution-velocity.md
20:49:47 Read: <ROOT>/wt-main/skills/smartthink/references/analysis-method.md
20:50:37 Read: <ROOT>/wt-main/skills/smartthink/references/core-engines.md
20:50:38 Read: <ROOT>/wt-main/skills/smartthink/references/cognitive-arsenal.md
20:54:38 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-lesson-waitlist-allocation/pack.md
20:54:41 Bash: python3 <ROOT>/wt-main/scripts/assemble-pack.py --pack-dir "<ROOT>/home/notes/smartthink/packs/2026-09-27-swim-lesson-waitlist-allocation" --modules core-engines.md cognitive-arsenal.md triz-innovation.md meta-cognition.md executi
20:54:46 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-lesson-waitlist-allocation/manifest.json
```

## 프롬프트 원문 (대표 3개, 화면 캡처)

```
 Bash command
 Tip: auto mode handles these prompts for you — choose "switch to auto mode" below
   │ python3 <ROOT>/wt-main/scripts/resolve-vault.py
   │ --ensure
   Resolve SmartThink vault path
 This command requires approval
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, and don’t ask again for: python3 *
   3. Yes, and switch to auto mode · auto mode handles these prompts for you
   4. No

 Read file
  Read(<ROOT>/wt-main/skills/smartthink/references/ind
  ex.json)
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, allow reading from
      <ROOT>/wt-main/skills/smartthink/references during
      this session
   3. No

 Read file · from the smartthink:st-armorer agent
  Read(<ROOT>/wt-main/skills/smartthink/references/cor
  e-engines.md)
 Do you want to proceed?
 ❯ 1. Yes
   2. Yes, allow reading from
      <ROOT>/wt-main/skills/smartthink/references during
      this session
   3. No
```

## 가설 판정

| 가설 | 판정 | 근거 |
|---|---|---|
| H1 문서가 복합 명령을 시키거나 모델이 관성으로 만든다 | 문서: 기각 / 관성: 부분 채택 | main 문서의 코드 블록·인라인 명령은 새 검사(S1)에서 복합 명령 0건(PASS). 이번 런의 메인 Bash는 한 줄 명령 1개뿐이었다. 그러나 T15-rerun(7회)·T9(2회)에서는 같은 문서로 `ls ...; cat ...`, `readlink ...; ls ...`가 나왔다. 문서가 "확인하라"만 쓰고 도구를 정하지 않은 자리(0단계 `{VAULT}` 쓰기 확인, 반환 규약 확인, `{SCRIPTS_DIR}`의 readlink)에서 모델이 Bash 복합 명령을 고른다 |
| H2 존재·읽기 확인이 Bash로 간다 | 채택(간헐) | 위와 같은 자리. 이번 런은 Read만 썼지만 T9·T15에서는 Bash `ls`/`cat`/`grep`이었다. 같은 확인을 Read·Glob으로 하면 아래 H4 결과대로 vault는 프롬프트가 없다 |
| H3 스크립트 호출 규칙이 없다 | 채택 | 프롬프트 1: `resolve-vault.py --ensure`는 무장마다 도는데 init은 assemble-pack 규칙만 제안한다. 게다가 문서의 호출 모양이 `python3 "{SCRIPTS_DIR}/resolve-vault.py"`(따옴표)라 접두어 규칙을 만들어도 글자가 어긋난다 |
| H4 작업 디렉터리 밖 Read가 프롬프트를 낸다 | vault: 기각 / 플러그인 디렉터리: 채택(주원인) | vault의 Read 3회(profile·evolution-state·pack.md)는 `Edit(~/notes/smartthink/**)`만으로 프롬프트가 없었다(Edit 허용이 Read를 덮는다). 플러그인 `references/`의 Read는 메인 1회 + armorer 8회 전부 프롬프트였다. T9·T15는 Read를 사전 허용했거나 작업 디렉터리가 워크트리라서 드러나지 않았다 |

결론: 프롬프트 10회 중 9회가 플러그인 디렉터리 Read(H4), 1회가 resolver Bash(H3)다. 수정은 (1) init이 플러그인 스킬 디렉터리 Read 규칙과 resolver Bash 규칙을 assemble-pack 규칙과 한 묶음으로 제안하고 그 문자열을 스크립트가 결정적으로 내며, (2) 메인·armorer의 확인 절차를 Read·Glob과 절대경로 한 줄 스크립트 호출로 고정하는 것이다.
