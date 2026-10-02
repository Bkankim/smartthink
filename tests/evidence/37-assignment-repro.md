# 37 - 할당 값 파싱 재현 (수정 전 / 수정 후)

명령(리포 루트): `python3 tests/evidence/37-assignment-repro.py`. 각 케이스는 SKILL.md 사본 끝에 한 줄을 붙이고 사본의 `scripts/check-structure.py`를 돌린다.

## 가설 판정
- H1 (`split()`이 따옴표 안 공백을 쪼갠다): 채택. 인라인 코드 경로는 `_is_command`가 `_command_word`의 `split()` 결과 `vault"`를 보고 명령이 아니라고 판정해 D절 검사 대상에서 빠진다(수정 전 PASS).
- H2 (`ASSIGNMENT_RE`의 `\S*`가 따옴표 값을 거부): 기각. 쪼개진 첫 토큰 `V="my`는 `\S*`에 맞는다. 다만 shlex로 따옴표를 벗기면 값에 공백이 생겨 `\S*$`가 거부하므로, `_command_word`는 접두 `VAR=`만 보는 `ASSIGNMENT_WORD_RE`를 쓴다. `_compound_operator`가 쓰는 `ASSIGNMENT_RE`는 그대로.
- H3 (`_compound_operator`가 먼저 `V=`를 잡아 경로가 갈린다): 부분 채택. bash/sh 펜스 경로는 모든 줄이 명령 후보이므로 `_compound_operator`의 첫 단어 `V="my`가 `V=`로 잡혀 수정 전에도 FAIL이다. 인라인 경로는 `_is_command`가 먼저 걸러 `_compound_operator`에 닿지 못한다. 그래서 펜스 판정은 수정 대상이 아니고, 수정 전후 동일해야 한다.

## 수정 전 (원문)
```
case: untampered
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline  double-quoted value with space: `V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline  single-quoted value with space: `V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline  value without space: `V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run on
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline  several assignments: `A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline  unclosed quote: `V="my vault python3 x.py`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence   double-quoted value with space: V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   single-quoted value with space: V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   value without space: V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run on
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   several assignments: A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'A=' (A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   unclosed quote: V="my vault python3 x.py
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault python3 x.py); allow rules match one plain command, so run one command per call with no redire
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
```

## 수정 후 (원문)
```
case: untampered
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline  double-quoted value with space: `V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline  single-quoted value with space: `V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline  value without space: `V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run on
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline  several assignments: `A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'A=' (A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline  unclosed quote: `V="my vault python3 x.py`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence   double-quoted value with space: V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   single-quoted value with space: V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V='my vault' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   value without space: V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V=myvault python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run on
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   several assignments: A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'A=' (A=1 V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence   unclosed quote: V="my vault python3 x.py
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault python3 x.py); allow rules match one plain command, so run one command per call with no redire
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
```

## 관찰
- 수정 전 PASS였던 인라인 3건(큰따옴표, 작은따옴표, 할당 여러 개)이 수정 후 FAIL. 펜스 5건은 수정 전후 동일(전부 FAIL).
- 인라인 닫히지 않은 따옴표(`V="my vault python3 x.py`)는 수정 전후 모두 PASS이며 크래시 없음(traceback 없음, 요약 줄 출력). shlex가 ValueError를 내면 옛 공백 분리 규칙으로 되돌아가므로 이 입력의 판정은 바뀌지 않는다. 쉘도 이 입력을 실행하지 못한다.
