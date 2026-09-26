# #26 TDD 로그

사이클마다 실패(red) 출력 1~3줄을 남긴다. 시임은 S1(`scripts/check-structure.py` 세션 Bash 단일 명령 검사)과
S2(`scripts/resolve-vault.py --permission-rule` 규칙 묶음)뿐이다.

## S1-1 SKILL.md 코드 블록의 복합 명령이 D를 FAIL시킨다

`uv run --with pytest pytest -q tests/test_check_structure_bash.py`

```
SUBFAILED(block='```bash\nls -la "{VAULT}"; cat "{VAULT}/evolution-state.md"\n```') tests/test_check_structure_bash.py::SessionBashCheckTest::test_compound_code_block_in_skill_md_fails
    self.assertEqual(result.returncode, 1, result.stdout)
5 failed, 1 passed in 0.34s
```

### S1 추가 케이스 (첫 실행 green)

`test_untampered_copy_passes`, `test_compound_inline_command_fails_in_every_session_doc`(lifecycle.md·st-armorer.md·armorer-prompt.md 인라인),
`test_operators_inside_quotes_or_prose_pass`(따옴표 안 연산자·산문 속 `&&` 오탐 방지)는 S1-1 구현이 이미 덮어 첫 실행에 통과했다(red 없음).
`4 passed, 9 subtests passed in 0.72s`. main 문서 원본도 이 검사를 통과한다(가설 H1 "문서가 복합 명령을 시킨다" 기각 근거).

## S2-1 resolver --permission-rule이 스크립트 Bash 규칙 묶음을 낸다(심링크 조상, 호출 경로 그대로)

`uv run --with pytest pytest -q tests/test_permission_bundle.py`

```
E       KeyError: 'command_prefixes'
tests/test_permission_bundle.py:67: KeyError
1 failed in 0.04s
```

## S2-2 resolver가 스킬 디렉터리 Read 규칙을 낸다(홈 아래 `~/`, 밖은 `//`, 호출 경로 그대로)

```
E       KeyError: 'read_rule'
tests/test_permission_bundle.py:85: KeyError
1 failed, 1 passed in 0.06s
```

## S2-3 문서가 시키는 스크립트 호출이 규칙 접두어로 시작한다

```
SUBFAILED(doc='skills/smartthink/SKILL.md', call='python3 "{SCRIPTS_DIR}/resolve-vault.py" --ensure') tests/test_permission_bundle.py::PermissionBundleTest::test_every_documented_script_call_starts_with_its_rule_prefix
SUBFAILED(doc='skills/smartthink/references/lifecycle.md', call='python3 "{SCRIPTS_DIR}/resolve-vault.py" --candidates') tests/test_permission_bundle.py::PermissionBundleTest::test_every_documented_script_call_starts_with_its_rule_prefix
4 failed, 3 passed, 9 subtests passed in 0.13s
```

## green 확인

- S1: `check_session_bash_single_commands`(D절) 추가 뒤 `4 passed, 9 subtests passed`.
- S2-1·S2-2: `resolve-vault.py`에 `script_rules()`(`command_prefixes`·`bash_rules`·`bash_rules_effective`·`read_rule`·`read_rule_effective`) 추가 뒤 green.
- S2-3: SKILL.md·lifecycle.md의 `python3 "{SCRIPTS_DIR}/resolve-vault.py"`(따옴표) 4곳을 `python3 {SCRIPTS_DIR}/resolve-vault.py`로 바꾼 뒤 `3 passed, 15 subtests passed in 0.11s`.
- 전체: `uv run --with pytest pytest -q tests` → `94 passed, 51 subtests passed in 6.89s`, `python3 scripts/check-structure.py` exit=0.

## final-review 20260927-064432 후속

### S2-4 resolver --module-sizes가 index.json 부재 폴백의 `wc -c`를 대신한다 ((a)1)

```
E       AssertionError: 2 != 0 : usage: resolve-vault.py [-h] [--ensure] [--permission-rule] [--candidates]
E       resolve-vault.py: error: unrecognized arguments: --module-sizes core-engines.md meta-cognition.md
1 failed, 3 deselected in 0.04s
```

### S1-2 SKILL.md의 규칙 묶음 밖 Bash 지시(`wc -c`, `ls -la`, 다른 스크립트)가 D를 FAIL시킨다 ((a)1)

```
E               AssertionError: 0 != 1 : PASS A. layout: required paths exist
E               39 passed, 0 failed, 5 skipped
tests/test_check_structure_bash.py:108: AssertionError
```

### S2-5 read_rules가 install.sh 링크 경로(~/.claude/skills/smartthink, $CLAUDE_CONFIG_DIR/skills/smartthink)를 더한다 ((c))

```
E       KeyError: 'read_rules'
tests/test_permission_bundle.py:115: KeyError
2 failed
```

## final-review 20260927-072558 후속

### S2-6 resolver --permission-rule이 vault_writable을 낸다(status의 `test -w` 대체, (a)1)

```
E       KeyError: 'vault_writable'
tests/test_permission_bundle.py:139: KeyError
1 failed, 6 deselected in 0.04s
```

### S1-3 lifecycle.md의 인벤토리 밖 Bash(`test -w`, `ls -la`)가 D를 FAIL시킨다(재발 방지)

```
E               AssertionError: 0 != 1 : PASS A. layout: required paths exist
E               40 passed, 0 failed, 5 skipped
E               pack: 0 passed, 0 failed, 5 skipped
```

## final-review 20260927-073516 후속 (마지막)

리뷰가 남긴 미커밋 패치 01~03을 역순으로 되돌린 뒤 사이클마다 red부터 다시 했다.

### S2-7 `--ensure`·`--permission-rule`이 `bash_rules_effective`와 `bash_rules_reason`을 낸다(#1)

```
E               KeyError: 'bash_rules_reason'
tests/test_permission_bundle.py:76: KeyError
2 failed, 1 passed, 7 deselected in 0.07s
```

### S2-8 `--ensure`가 `vault_writable`을 내고, 루트와 packs/ 둘 다 쓰기 가능해야 true다(#2)

```
E       KeyError: 'vault_writable'
tests/test_permission_bundle.py:189: KeyError
1 failed, 8 deselected in 0.04s
```

### S2-9 `read_rule_effective`가 `read_rules`의 링크 경로까지 본다(#3)

```
E       AssertionError: True is not False
tests/test_permission_bundle.py:163: AssertionError
1 failed, 9 deselected in 0.07s
```

### S2-10 `--module-sizes`가 없는 이름은 null과 경고로 내고 나머지를 계속 잰다, exit 0(#5)

```
E               AssertionError: 1 != 0 : error: not a file in <ROOT>/plugin/skills/smartthink/references: ../scripts/resolve-vault.py
tests/test_permission_bundle.py:253: AssertionError
E               AssertionError: 1 != 0 : error: not a file in <ROOT>/plugin/skills/smartthink/references: missing.md
```

### green 확인 (마지막 후속)

- S2-7~S2-10 구현 뒤 `uv run --with pytest pytest -q tests` → `104 passed, 66 subtests passed`, `python3 scripts/check-structure.py` exit 0.
- `tests/test_resolve_vault.py`의 `--ensure` 정확 일치 테스트는 의도된 출력 확장(`bash_rules_effective`·`bash_rules_reason`·`vault_writable`)을 포함하도록 갱신했다.
- #4(readlink 조건 일반화)·#6(규율 문장의 묶음 명령 나열)은 문서 변경이라 테스트 대상이 아니다. check-structure D 세 검사가 새 문장을 통과한다.
