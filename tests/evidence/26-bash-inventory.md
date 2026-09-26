# #26 세션 Bash 인벤토리 (SKILL.md·lifecycle.md)

- 작성: 2026-09-27, final-review 20260927-072558 후속(코디네이터 지시 "규칙 묶음 밖 Bash 지시를 모두 목록화하고 변환 또는 유지+사유").
- 방법: `scripts/check-structure.py`의 `_shell_commands`가 뽑는 코드 블록 줄·인라인 코드 전부(첫 단어가 셸 명령인 것)와 본문의 "Bash" 언급을 줄 단위로 훑었다. 같은 줄에 금지 문구(마라·말고·금지·않는다)가 있는 것은 지시가 아니라 금지라 목록에서 "금지 언급"으로만 센다.
- 규칙 묶음: `python3 {SCRIPTS_DIR}/resolve-vault.py ...`, `python3 {SCRIPTS_DIR}/assemble-pack.py ...`(init이 `bash_rules`로 설치), install.sh 설치의 `readlink {SKILL_DIR}`(실측 무프롬프트, T16-after 4절).
- 강제: check-structure D절 두 검사가 이 표를 기계로 지킨다. `SKILL.md arming Bash stays inside the rule bundle`(SKILL.md는 묶음만), `lifecycle.md Bash is the bundle or a recorded exception`(lifecycle.md는 묶음 + 아래 "유지" 4건만). 새 Bash 지시를 넣으면 변환하거나 이 표와 `LIFECYCLE_EXCEPTION_RE`에 사유와 함께 올려야 통과한다.

## SKILL.md (무장 경로, 목표: 프롬프트 0회)

| 줄 | 명령 | 처리 | 사유 |
|---|---|---|---|
| 35, 47 | `readlink {SKILL_DIR}` | 유지(묶음) | install.sh 설치에서만, 한 줄. T16-after 4절에서 무프롬프트 |
| 37, 47 | `python3 {SCRIPTS_DIR}/resolve-vault.py --ensure` | 유지(묶음) | resolver Bash 규칙 |
| 290 | `wc -c`(index.json 부재 폴백) | **변환** → `python3 {SCRIPTS_DIR}/resolve-vault.py --module-sizes <모듈...>` | 3b995c4, final-review 20260927-064432 (a)1 |
| 425 | `python3 {SCRIPTS_DIR}/assemble-pack.py --pack-dir ... --modules ...`(5b 인라인) | 유지(묶음) | assemble-pack Bash 규칙 |
| 622 | `uv`·`pip`(우아한 축소 표) | 유지(무장 측정 밖) | armorer의 리서치 의존성 설치 경로(`insane-search` 등)를 가리키는 한 단어 언급. 리서치 ON에서만 쓰이고 WebSearch·WebFetch와 함께 T16 측정 대상 밖이다 |
| 35, 46, 48, 129, 403, 409, 425 | `ls`·`cat`·`grep`·`head`·`test`·`cd`·`git show`·`git log`, Bash로 env 읽기 | 금지 언급 | 같은 줄이 쓰지 말라고 지시한다 |

## lifecycle.md (init·retain·status, 무장 경로 밖)

| 줄(대략) | 명령 | 처리 | 사유 |
|---|---|---|---|
| 31, 141, 192, 225, 230, 442 | `python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`·`--candidates`·`--permission-rule` | 유지(묶음) | resolver Bash 규칙 |
| 225 | `python3 {SCRIPTS_DIR}/assemble-pack.py ...` | 유지(묶음) | 설명 문장 |
| 77 | `git log --oneline -50`(init 사전 스캔) | 유지 | init 1회, 작업 디렉터리(사용자 프로젝트) 안 읽기, 무장 경로 아님. lifecycle.md에 1줄 기록 |
| 102 | `git log 50건 ...` | 해당 없음 | 사전 스캔 결과 예시 화면의 글자(명령 아님) |
| 171 | `mkdir` | 금지 언급 | 포인터는 Write가 디렉터리를 만든다 |
| 282 | `cp "<SETTINGS>" "<SETTINGS>.bak"`(init 설정 백업) | 유지 | init은 사용자가 settings 변경 자체를 승인하는 대화형 1회 절차이고, 대상이 `~/.claude` 아래면 Write 도구로 바꿔도 보호 경로 프롬프트가 뜬다. lifecycle.md에 1줄 기록(final-review 20260927-072558 (a)2) |
| 351 | `python3 {SCRIPTS_DIR}/migrate-evolution.py {VAULT}/evolution-state.md --write`(retain) | 유지(형식만 통일) | 무장 경로 밖이라 규칙 묶음에 넣지 않는다. lifecycle.md에 1줄 기록(final-review 20260927-064432 (a)2) |
| 483 | `python3 {SCRIPTS_DIR}/legacy-install.py detect`(status) | 유지(형식만 통일) | 위와 같다 |
| 485 | `test -w {VAULT}`(status vault 쓰기 가능) | **변환** → resolver `--permission-rule` 출력의 `vault_writable` | 가장 가까운 존재 조상 기준. final-review 20260927-072558 (a)1 |

## 복합 명령 검사 범위 확인 (final-review 20260927-072558 (c) 부기)

단독 `cd`, `$(...)`, 리다이렉션(`>`, `>>`)은 두 문서에서 지시로 쓰이는 곳이 없다(`cd`·`$(...)`·리다이렉션은 SKILL.md 48·425의 금지 언급뿐, lifecycle.md 0건). 그래서 `check_session_bash_single_commands`는 확장하지 않았다. 새로 쓰이면 위 두 인벤토리 검사가 그 줄을 묶음 밖 명령으로 먼저 잡는다.
