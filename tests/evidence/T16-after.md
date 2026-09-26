# T16-after: 수정 후 init 승인 → 새 세션 무장 2회 권한 프롬프트 0회 (#26)

- 실행일: 2026-09-27 06:01 ~ 06:37 (+09:00), Claude Code 2.1.283, `--model opus`, `--permission-mode default`(상태줄 `⏸ manual mode on`, 세 세션 모두).
- 코드: 워크트리 `<HOME>/workspace/smartthink-fix-26-main-bash-prompts`, 커밋 64a04f4(수정 커밋). `--plugin-dir <워크트리>`, 호출 `/smartthink:smartthink`. 세 세션 jsonl의 스킬 로드 줄이 모두 `Base directory for this skill: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink`다(아래 도구 목록의 `SKILL` 줄).
- 환경: T16-before와 같다. `<ROOT>`는 `mktemp -d`의 실경로, 격리 `CLAUDE_CONFIG_DIR=<ROOT>/cfg`, 가짜 `HOME=<ROOT>/home`, 작업 디렉터리 `~/project`(플러그인 디렉터리·vault 둘 다 밖). `SMARTTHINK_VAULT`·`XDG_*` 제거, 인증은 자식 env에만(값 미기록). 가짜 홈에 `~/notes/.obsidian`(노트 보관소 후보)만 두고 포인터·vault·규칙 없이 시작했다.
- 격리 settings allow는 측정 대상이 아닌 `WebSearch`·`WebFetch`·`Skill`·`Agent`만. Read·Glob·Grep·Bash는 사전 허용하지 않았다.
- 프롬프트는 3~5초 간격 화면 폴링으로 감지해 원문을 기록하고 `1`(Yes, 1회)로만 답했다(`don't ask again` 계열 미선택). 무장 두 세션에서는 감지된 프롬프트가 없어 기록 파일 자체가 생기지 않았다.

## 1. init (세션 1, 규칙 설치 전이라 프롬프트는 예상대로 뜬다)

입력: `/smartthink:smartthink init` → "①~④와 ⑥은 다 건너뛸게. ⑤ vault 경로만" → ⑤에서 `1`(`~/notes/smartthink`) → 프로필 승인 → 규칙 `전부`.

init 4절 제안 원문(화면 캡처, 한 번의 `resolve-vault.py --permission-rule` 출력에서 나온 네 규칙):

```
  마지막 단계: 권한 규칙
  무장할 때 vault에 쓰거나, 스킬 파일을 읽거나, 스크립트를 실행할 때마다 권한 확인 창이 뜹니다. 아래 허용 규칙을 설정
  파일 …/<ROOT 끝>/cfg/settings.json(이 세션이 읽는 설정 파일)에 넣을까요? 이 파일에는 아직 같은 역할의 규칙이
  없습니다.
  1) Edit(~/notes/smartthink/**)
       팩 파일 쓰기·수정 (vault 읽기도 이 규칙이 허용)
  2) Read(//<HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/**)
       스킬 레퍼런스 읽기 (게이트 비용표, 모듈 원문)
  3) Bash(python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/resolve-vault.py *)
       vault 경로 해석 스크립트 실행 (이 스크립트만, 인자와 무관하게 확인 없이 실행)
  4) Bash(python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/assemble-pack.py *)
       팩 5절 원문 조립 스크립트 실행 (이 스크립트만, 인자와 무관하게 확인 없이 실행)
  3·4번의 위험: 이 규칙이 있으면 그 경로의 두 스크립트는 인자와 상관없이 확인 없이 실행됩니다.
  ...
  전부 / 번호 골라서 / 넣지 않음 중에 골라주세요. 넣지 않아도 무장은 그대로 동작하고, 매번 확인 창이 뜰 뿐입니다.
```

settings.json 전후(`permissions` 원문):

```
before (settings.json.bak, init이 쓰기 전 백업)
{"permissions":{"defaultMode":"default","allow":["WebSearch","WebFetch","Skill","Agent"],"deny":["Read(//<HOME>/workspace/vault/**)","Edit(//<HOME>/workspace/vault/**)","Read(//<HOME>/.config/smartthink/**)","Edit(//<HOME>/.config/smartthink/**)"]}}
after
{"permissions":{"defaultMode":"default","allow":["WebSearch","WebFetch","Skill","Agent","Edit(~/notes/smartthink/**)","Read(//<HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/**)","Bash(python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/resolve-vault.py *)","Bash(python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/assemble-pack.py *)"],"deny":["Read(//<HOME>/workspace/vault/**)","Edit(//<HOME>/workspace/vault/**)","Read(//<HOME>/.config/smartthink/**)","Edit(//<HOME>/.config/smartthink/**)"]}}
```

기존 allow·deny 보존, 4항목 추가만. 포인터 `~/.config/smartthink/vault-pointer` = `<ROOT>/home/notes/smartthink`. 가짜 홈 기본 위치 `~/.local/share/smartthink`는 만들어지지 않았다(`~/.local/share`에는 Claude Code 자신의 `claude`만 있음).

init 중 프롬프트 13회(규칙 설치 전 단계, 측정 대상 아님): Read lifecycle.md, Bash resolver(무인자), Read 가짜 홈 `~/.claude/MEMORY.md`·`CLAUDE.md`(사전 스캔), Bash `--candidates`, Read `.data/profile.md`, Write 포인터, Bash `--ensure`, Write profile.md, Bash `--permission-rule`, Read settings.json, Bash `cp settings.json settings.json.bak`, Edit settings.json. 전부 한 줄 명령이었다(`;`·`&&`·파이프 없음, `mkdir` 없음).

## 2. 무장 결과

| 세션 | 입력 | 메인 프롬프트 | armorer 프롬프트 | 합계 | 팩 `--pack` 검사 |
|---|---|---|---|---|---|
| 2 | `/smartthink:smartthink --digest --nosearch 동네 도서관 스터디룸 예약 노쇼 줄이기` → `진행` | 0 | 0 | **0** | H 5/5 PASS(`--digest`) |
| 3 | `/smartthink:smartthink --nosearch 동네 체육관 수영 강습 대기자 배정 방식 개선` → `진행` | 0 | 0 | **0** | H 5/5 PASS |

도구별(두 세션 합계, 전부 무프롬프트):

| 도구 | 주체 | 횟수 | 대상 | 덮은 규칙 |
|---|---|---|---|---|
| Bash `resolve-vault.py --ensure` | 메인 | 2 | 스크립트 | `Bash(python3 <SCRIPTS_DIR>/resolve-vault.py *)` |
| Read `references/index.json` | 메인 | 2 | 스킬 디렉터리 | `Read(//<SKILL_DIR>/**)` |
| Read `profile.md`·`evolution-state.md`·`pack.md`·`manifest.json` | 메인 | 8 | vault | `Edit(~/notes/smartthink/**)` |
| Glob `*` (팩 디렉터리) | 메인 | 1 | vault | `Edit(~/notes/smartthink/**)` |
| Read 모듈·`analysis-method.md` | armorer | 17 | 스킬 디렉터리 | `Read(//<SKILL_DIR>/**)` |
| Bash `date +%Y-%m-%dT%H:%M:%S%z` | armorer | 2 | 경로 없음 | 읽기 전용 명령(규칙 불필요) |
| Write `pack.md`·`manifest.json` | armorer | 5 | vault | `Edit(~/notes/smartthink/**)` |
| Bash `assemble-pack.py --pack-dir ... --modules ...` | armorer | 1 | 스크립트 | `Bash(python3 <SCRIPTS_DIR>/assemble-pack.py *)` |

메인 세션의 Bash는 두 세션 모두 `resolve-vault.py --ensure` 한 줄뿐이었고 `readlink`·`ls`·`cat`·`grep`·복합 명령은 0회였다. 반환 확인은 Glob과 Read로 했다.

## 3. 도구 호출 전체 (세션 jsonl 추출, 시각 UTC)

```
== main 5d561d2a-6550-4976-ace4-09bc67912523.jsonl   (세션 2, --digest)
SKILL Base directory for this skill: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink
21:11:20 Bash: python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/resolve-vault.py --ensure
21:11:22 Read: <ROOT>/home/notes/smartthink/profile.md
21:11:23 Read: <ROOT>/home/notes/smartthink/evolution-state.md
21:11:23 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/index.json
21:12:33 Agent: smartthink:st-armorer
21:26:54 Read: <ROOT>/home/notes/smartthink/packs/2026-09-27-library-studyroom-noshow/pack.md
21:26:56 Glob: * path=<ROOT>/home/notes/smartthink/packs/2026-09-27-library-studyroom-noshow
21:26:58 Read: <ROOT>/home/notes/smartthink/packs/2026-09-27-library-studyroom-noshow/manifest.json
== armorer agent-afba6acd8d9d1d880.jsonl   (세션 2)
21:12:36 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/core-engines.md
21:12:36 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/cognitive-arsenal.md
21:12:37 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/pattern-synthesis.md
21:12:37 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/triz-innovation.md
21:12:38 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/execution-velocity.md
21:12:38 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/analysis-method.md
21:12:42 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/core-engines.md
21:12:43 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/cognitive-arsenal.md
21:12:51 Bash: date +%Y-%m-%dT%H:%M:%S%z
21:22:30 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-library-studyroom-noshow/pack.md
21:26:38 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-library-studyroom-noshow/pack.md
21:26:41 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-library-studyroom-noshow/manifest.json
== main a9a061ad-9d04-4255-ab8f-f66922d08ea6.jsonl   (세션 3, 원문)
SKILL Base directory for this skill: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink
21:31:11 Bash: python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/resolve-vault.py --ensure
21:31:12 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/index.json
21:31:13 Read: <ROOT>/home/notes/smartthink/profile.md
21:31:14 Read: <ROOT>/home/notes/smartthink/evolution-state.md
21:32:23 Agent: smartthink:st-armorer
21:37:35 Read: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-class-waitlist-allocation/manifest.json
21:37:36 Read: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-class-waitlist-allocation/pack.md
== armorer agent-aa5b72c93ac028a45.jsonl   (세션 3)
21:32:26 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/core-engines.md
21:32:26 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/cognitive-arsenal.md
21:32:27 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/triz-innovation.md
21:32:27 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/pattern-synthesis.md
21:32:28 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/anti-fragile-strategy.md
21:32:29 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/analysis-method.md
21:32:33 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/core-engines.md
21:32:33 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/cognitive-arsenal.md
21:32:36 Read: <HOME>/workspace/smartthink-fix-26-main-bash-prompts/skills/smartthink/references/cognitive-arsenal.md
21:35:43 Bash: date +%Y-%m-%dT%H:%M:%S%z
21:37:15 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-class-waitlist-allocation/pack.md
21:37:19 Bash: python3 <HOME>/workspace/smartthink-fix-26-main-bash-prompts/scripts/assemble-pack.py --pack-dir "<ROOT>/home/notes/smartthink/packs/2026-09-27-swim-class-waitlist-allocation/" --modules core-engines.md cognitive-arsenal.md triz-i
21:37:25 Write: <ROOT>/home/notes/smartthink/packs/2026-09-27-swim-class-waitlist-allocation/manifest.json
```

무장 마지막 화면(요지):

```
  팩: ~/notes/smartthink/packs/2026-09-27-library-studyroom-noshow/  |  모듈: 핵심 엔진, 인지 무기고, 패턴 합성, TRIZ,
  실행 속도  |  비용: 팩 ≈27K / 작업 ≈170K  |  리서치: OFF (사용자 지정)
  팩: ~/notes/smartthink/packs/2026-09-27-swim-class-waitlist-allocation/  |  모듈: 핵심 엔진, 인지 무기고, TRIZ, 패턴
  합성, 안티프래질  |  비용: 팩 ≈145K / 작업 ≈160K  |  리서치: OFF
```

## 판정: PASS

- init 승인 뒤 새 세션 무장 2회(`--digest` 1, 원문 1) 모두 권한 프롬프트 0회. T16-before의 10회(스킬 디렉터리 Read 9, resolver Bash 1)가 사라졌다.
- 남은 한계(범위 밖, 실측 안 함): install.sh 심링크 설치는 `{SKILL_DIR}`이 `~/.claude/skills/smartthink` 심링크라 `readlink` 한 줄이 남고, Read 규칙은 `{SCRIPTS_DIR}` 기준 실제 경로로 만들어진다. 그 조합의 프롬프트 여부는 재지 않았다. 리서치 ON의 WebSearch·WebFetch는 이번 측정에서 사전 허용했다(측정 대상 아님).
