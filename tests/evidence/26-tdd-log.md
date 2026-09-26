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
