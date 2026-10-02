# #43 TDD 로그

시임: `scripts/check-structure.py`의 `_command_word`, `_compound_operator`, 그리고 둘이 공유하게 된 `_leading_word`·`_leading_assignments`. 테스트는 `tests/test_check_structure_bash.py`의 `test_assignment_prefix_matrix_in_inline_and_fence`(5개 입력 x 인라인·bash 펜스 = 10 subTest)와 `test_assignment_judges_do_not_crash_on_unparseable_text`(12개 파싱 불가 입력, 세 함수 직접 호출).

## 설계 판단
- `_leading_word(text)`: shlex로 첫 단어 하나만 읽고 나머지 텍스트를 함께 돌려준다. ValueError면 그 지점부터 공백 단어로 내려간다(앞에서 이미 읽은 단어는 건드리지 않는다). 처음부터 `split()`으로 되돌리던 옛 폴백이 H1의 원인이었다.
- `_leading_assignments(command)`: 앞쪽 `VAR=` 단어를 위 함수로 하나씩 건너뛰고 (이름 목록, 명령어가 시작되는 나머지)를 돌려준다. `_compound_operator`와 `_command_word`가 이것만 쓴다. 원문 첫 토큰 + `ASSIGNMENT_RE`는 사라졌고, 그 정규식은 호출처가 없어져 같이 지웠다.
- 크래시 방지: 닫히지 않은 따옴표·끝의 역슬래시 등은 모두 ValueError -> 공백 단어 폴백으로 처리된다. 크래시 테스트가 12개 입력으로 고정한다.

## 수정 전 red (옛 check-structure.py로 새 테스트 실행, 원문)
`python3 -m unittest tests.test_check_structure_bash.SessionBashCheckTest.test_assignment_prefix_matrix_in_inline_and_fence tests.test_check_structure_bash.SessionBashCheckTest.test_assignment_judges_do_not_crash_on_unparseable_text`
```
FAIL: test_assignment_prefix_matrix_in_inline_and_fence (case='C2 unclosed quote after an assignment', surface='inline')
AssertionError: False is not true : want FAIL: PASS D. wiring: session Bash instructions are single commands
FAIL: test_assignment_prefix_matrix_in_inline_and_fence (case='C3 quoted assignment word', surface='inline')
AssertionError: False is not true : want FAIL: PASS D. wiring: session Bash instructions are single commands
FAIL: test_assignment_prefix_matrix_in_inline_and_fence (case='C3 quoted assignment word', surface='bash fence')
AssertionError: False is not true : want FAIL: PASS D. wiring: session Bash instructions are single commands
Ran 2 tests in 0.819s
FAILED (failures=3)
```
크래시 테스트는 수정 전에도 green이다(옛 폴백도 예외를 삼켰다). 새 구현이 같은 보장을 유지하는지 지키는 회귀 가드다.

## 수정 후 green (원문)
`python3 -m unittest -v <위 두 테스트>`
```
test_assignment_prefix_matrix_in_inline_and_fence (tests.test_check_structure_bash.SessionBashCheckTest.test_assignment_prefix_matrix_in_inline_and_fence) ... ok
test_assignment_judges_do_not_crash_on_unparseable_text (tests.test_check_structure_bash.SessionBashCheckTest.test_assignment_judges_do_not_crash_on_unparseable_text) ... ok
Ran 2 tests in 0.878s
OK
```

## 펜스 경로 판정 비교 (옛 vs 새, 전수)
`git show origin/main:scripts/check-structure.py > <old>` 후 `python3 tests/evidence/43-differential.py <old>`: 세션 문서가 보여 주는 모든 명령, 리포 모든 md의 코드 펜스 줄, 합성 접두 x 본문 곱을 같은 입력으로 두 구현에 넣어 `_compound_operator`·`_command_word`·`_is_command`를 비교했다.
```
inputs=1611 differing=35
```
- 차이 35건은 전부 합성 입력이다. 문서의 실제 명령에는 차이가 0건이다.
- 차이의 종류 3가지(전부 옛 쪽이 누락): (1) 따옴표로 싼 할당 단어 `'V=1'`·`"V=1"`(C3, 의도한 변화), (2) 탭으로 구분된 접두 `V=1<TAB>cmd`(옛 코드는 공백 하나로만 첫 토큰을 잘랐다), (3) 이스케이프한 `V\=1`(셸에서는 명령어 이름이지만 `'V=1'`과 같은 방식으로 접두 위반으로 본다 - 이슈의 C3 목표와 같은 보수적 판정).
- 옛 판정이 이미 FAIL이던 펜스 입력이 PASS로 바뀐 경우는 0건이다(옛 쪽이 연산자를 달리 보고한 `"V=1" cat > f` 같은 입력은 어느 쪽이든 FAIL이고, 보고되는 연산자 이름만 `>`에서 `V=`로 바뀐다).

## 문서 3건 (수정 후 원문 인용)

### analysis-method.md 84행 (풀 3)
```
   - **풀 3 - 작업 해석 유래**: 게이트에서 답한 목표가 있으면 그 목표를 익숙한 다른 작업으로 바꿔 읽어 목표·성공 기준에서 벗어나는 것. 그 답이 없을 때만 예상 작업 A/B/C 중 익숙한 하나로 조기 수렴하는 것, 또는 주제만 온 경우 사용자의 실제 의도를 넘겨짚는 것.
```

### SKILL.md 382행 (이름 해석 규칙)
```
목록을 볼 수 없는 런타임에서만 아래 순서를 따른다. `smartthink:<이름>`이 not found면 bare `<이름>`으로 **1회만** 재시도하고, 그래도 실패해야 `general-purpose` 폴백으로 내려가라. 접두어 없는 설치(install.sh 심링크처럼 `~/.claude/agents/`에 놓는 사용자 레벨 설치)에서는 bare 이름이 정본이기 때문이다. not found가 아닌 다른 스폰 오류는 bare 재시도 없이 바로 `general-purpose` 폴백으로 간다.
```

### SKILL.md 421행 (5a 폴백 1항)
```
1. 세션 목록에 두 이름이 모두 없으면 → 재시도 없이 바로 폴백이다(반드시 실패할 bare 호출을 던지지 마라). 목록을 볼 수 없어 던진 `smartthink:st-armorer` 스폰이 not found면 → 위 이름 해석 규칙대로 bare `st-armorer`로 1회만 재시도하고, **두 이름이 모두 실패**(정의 부재 포함)해야 폴백이다. not found가 아닌 다른 스폰 오류는 bare 재시도 없이 바로 `general-purpose` 폴백으로 간다. 폴백으로 갈 때는 → `{SKILL_DIR}/references/armorer-prompt.md`(폴백 SSOT)를 Read해 그 전문 끝에 위 Input 블록을 붙인 것을 prompt로 써서 `subagent_type: "general-purpose"`로 스폰하라. 전문을 요약하거나 다시 쓰지 마라. **git 이력(`git show`, `git log` 등)이나 다른 설치본에서 정의를 복구하지 마라** - git이 없는 설치(복사본·플러그인 캐시)에서도 동작해야 하고, 폴백 파일이 정의 본문의 동기화 사본이다. 백그라운드로 뜨면 위 대기 규칙이 그대로 적용된다.
```

### SKILL.md 629행 (결핍 표 armorer 행)
```
| `smartthink:st-armorer` 정의 없음 | 목록에 두 이름이 모두 없으면 즉시 `general-purpose` + `armorer-prompt.md` 폴백. 목록을 볼 수 없을 때만 bare 1회 재시도 후 실패하면 같은 폴백(git 이력 복구 금지). 폴백 파일이 없거나 `general-purpose` 폴백 자체가 실패하면 인라인 |
```

382행과 421행은 같은 문장 "not found가 아닌 다른 스폰 오류는 bare 재시도 없이 바로 `general-purpose` 폴백으로 간다."를 쓴다. st-armorer.md와 armorer-prompt.md에는 이 문구가 없어(grep 확인) 동기화 대상 문구를 건드리지 않았다.

## 최종 검증 (원문)
`python3 scripts/check-structure.py` (관련 PASS 줄과 요약)
```
check exit=0
PASS D. wiring: plugin namespace on spawns and the /st alias
PASS D. wiring: st-thinker definition and fallback prompt in sync
PASS D. wiring: st-armorer definition and fallback prompt in sync
PASS D. wiring: session Bash instructions are single commands
PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
PASS D. wiring: headless gate signals and branches
PASS E. schema: run goal asked at the gate, not in init
42 passed, 0 failed, 5 skipped
pack: 0 passed, 0 failed, 5 skipped
```
`python3 -m unittest discover -s tests -p 'test_*.py'`
```
----------------------------------------------------------------------
Ran 121 tests in 13.987s
OK
```

새 테스트 2개가 더해져 119 -> 121.
