# 43 - C2/C3 재현 (수정 전, origin/main 20750bd 코드)

명령(리포 루트, `$WT`): `python3 tests/evidence/43-repro.py`

Part 1(`probe:`)은 세 보조 함수를 직접 부른 결과이고, Part 2(`case:`)는 SKILL.md 사본 끝에 한 줄을 붙여 사본의 `scripts/check-structure.py`를 돌린 결과다. 리포 본체는 읽기만 한다.

## 가설 판정

C2 입력: `` `V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure` ``
- H1 (ValueError 폴백이 전체를 `split()`으로 되돌려 따옴표 값이 쪼개진다): 채택. `W=it's`의 닫히지 않은 `'`가 shlex ValueError를 내고, `_command_word`가 처음부터 `split()`으로 되돌아가 `V="my`는 할당으로 건너뛰지만 `vault"`를 명령어로 돌려준다(`_command_word='vault"'`).
- H2 (쪼개진 조각이 SHELL_COMMAND_WORDS에 없어 `_is_command`가 span을 버린다): 채택. `_is_command=False`라 `_shell_commands`가 인라인 span을 후보에서 뺀다. 같은 줄을 bash 펜스에 넣으면 모든 줄이 후보라 `_compound_operator`의 첫 토큰 `V="my`가 `V=`로 잡혀 FAIL이다(수정 전 이미 FAIL, 판정 유지 대상).
- H3 (rule bundle 검사도 같은 `_command_word`를 써서 함께 놓친다): 채택. 두 검사 모두 `_shell_commands`가 만든 후보를 쓰므로 인라인 span이 빠지면 "single commands"와 "rule bundle"이 함께 PASS한다(아래 case 원문).

C3 입력: `` `'V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure` ``
- H1 (`_compound_operator`가 원문 첫 토큰 `'V=1'`에 정규식을 적용해 놓친다): 채택. 첫 토큰이 따옴표로 시작해 `ASSIGNMENT_RE`에 안 맞고, 이어지는 연산자 스캔도 작은따옴표 안이라 아무것도 못 찾는다(`_compound_operator=None`).
- H2 (`_command_word`는 따옴표를 벗긴 뒤 판정해 할당으로 본다): 채택. shlex가 `'V=1'`을 `V=1`로 벗겨 할당으로 건너뛰고 `python3`를 돌려준다(`_command_word='python3'`, `_is_command=True`). 인라인 span은 후보가 되지만 `_compound_operator`가 None이라 "single commands"만 PASS, "rule bundle"(첫 단어가 `'V=1'`이라 BUNDLE_COMMAND_RE 불일치)만 FAIL한다. 두 함수의 할당 판정이 갈린다.
- 관찰: 이 입력은 펜스 경로에서도 `_compound_operator=None`이라 "single commands"가 수정 전에 PASS다. 인라인과 펜스가 같은 `_compound_operator`를 공유하므로 이 누락은 한 번의 수정으로 두 표면에서 함께 닫힌다(수정 후 기록은 43-tdd-log.md).

## 수정 전 (원문)
```
probe: C2 unclosed quote after an assignment: _command_word='vault"' _is_command=False _compound_operator='V='
probe: C3 quoted assignment word: _command_word='python3' _is_command=True _compound_operator=None
probe: control: quoted value with space (#37): _command_word='python3' _is_command=True _compound_operator='V='
probe: control: no assignment: _command_word='python3' _is_command=True _compound_operator=None
probe: control: fully unparseable: _command_word='vault' _is_command=False _compound_operator='V='
case: untampered
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline C2 unclosed quote after an assignment: `V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence  C2 unclosed quote after an assignment: V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command,
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline C3 quoted assignment word: `'V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  PASS D. wiring: session Bash instructions are single commands
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  41 passed, 1 failed, 5 skipped
case: fence  C3 quoted assignment word: 'V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  PASS D. wiring: session Bash instructions are single commands
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  41 passed, 1 failed, 5 skipped
case: inline control: quoted value with space (#37): `V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence  control: quoted value with space (#37): V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline control: no assignment: `python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence  control: no assignment: python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline control: fully unparseable: `V="my vault python3 x.py`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence  control: fully unparseable: V="my vault python3 x.py
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault python3 x.py); allow rules match one plain command, so run one command per call with no redire
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
```

## 수정 후 (원문)
```
probe: C2 unclosed quote after an assignment: _command_word='python3' _is_command=True _compound_operator='V='
probe: C3 quoted assignment word: _command_word='python3' _is_command=True _compound_operator='V='
probe: control: quoted value with space (#37): _command_word='python3' _is_command=True _compound_operator='V='
probe: control: no assignment: _command_word='python3' _is_command=True _compound_operator=None
probe: control: fully unparseable: _command_word='vault' _is_command=False _compound_operator='V='
case: untampered
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline C2 unclosed quote after an assignment: `V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command,
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence  C2 unclosed quote after an assignment: V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault" W=it's python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command,
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline C3 quoted assignment word: `'V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' ('V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run one co
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence  C3 quoted assignment word: 'V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' ('V=1' python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run one co
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline control: quoted value with space (#37): `V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:672 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: fence  control: quoted value with space (#37): V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault" python3 {SCRIPTS_DIR}/resolve-vault.py --ensure); allow rules match one plain command, so run
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
case: inline control: no assignment: `python3 {SCRIPTS_DIR}/resolve-vault.py --ensure`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence  control: no assignment: python3 {SCRIPTS_DIR}/resolve-vault.py --ensure
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: inline control: fully unparseable: `V="my vault python3 x.py`
  exit=0
  PASS D. wiring: session Bash instructions are single commands
  PASS D. wiring: SKILL.md arming Bash stays inside the rule bundle
  42 passed, 0 failed, 5 skipped
case: fence  control: fully unparseable: V="my vault python3 x.py
  exit=1
  FAIL D. wiring: session Bash instructions are single commands: 1 compound shell command(s)
  - skills/smartthink/SKILL.md:673 uses 'V=' (V="my vault python3 x.py); allow rules match one plain command, so run one command per call with no redire
  FAIL D. wiring: SKILL.md arming Bash stays inside the rule bundle: 1 Bash instruction(s) outside the rule bundle
  40 passed, 2 failed, 5 skipped
```

## 관찰
- C2 인라인: 수정 전 두 검사 PASS -> 수정 후 두 검사 FAIL(`uses 'V='`). `_command_word`가 `vault"` 대신 `python3`를 돌려준다.
- C3: 수정 전 인라인·펜스 모두 "single commands" PASS(rule bundle만 FAIL) -> 수정 후 둘 다 FAIL. 같은 `_compound_operator`를 두 표면이 공유하므로 펜스의 C3 누락도 함께 닫힌다. 이슈 제약("펜스 경로의 기존 판정을 바꾸지 않는다")이 지키려는 기존 FAIL 판정(C2 펜스, #37 따옴표 값 펜스, 완전 파싱 불가 펜스)은 전부 FAIL 그대로다.
- 대조군(할당 없음 정상 명령, 완전 파싱 불가 인라인)은 수정 전후 동일(PASS)이고 크래시 없음.
