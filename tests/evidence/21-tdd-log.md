# #21 TDD log

사이클마다 red 출력 1~3줄. 경로의 홈은 `<HOME>`으로 치환했다.

## S4-1 조립 팩이 `--pack` H 5/5 PASS
- 테스트: `tests/test_assemble_pack.py::test_assembled_pack_passes_the_pack_gate`
- red:
  ```
  E       AssertionError: 2 != 0 : <HOME>/.cache/uv/builds-v0/.tmp0yldqy/bin/python: can't open file '<HOME>/workspace/smartthink-st-21-assemble-pack/scripts/assemble-pack.py': [Errno 2] No such file or directory
  ```
- green: `1 passed in 0.09s`

## S4-2 모듈이 아닌 이름(없는 파일, 9개 밖 레퍼런스, references/ 밖 경로)은 거부
- 테스트: `test_non_module_names_fail_and_leave_pack_untouched`
- 먼저 없는 파일만으로 쓴 판은 red가 나지 않았다(OSError 처리로 이미 exit 1). 그래서 실제 결함인 두 입력을 더해 red를 냈다.
- red:
  ```
  E               AssertionError: 0 == 0 : {"pack": ".../vault/packs/2026-09-27-fixture/pack.md", "modules": ["analysis-method.md"], "bytes": 35088, "est_tokens_pack": 15949}
  E               AssertionError: 0 == 0 : {"pack": ".../vault/packs/2026-09-27-fixture/pack.md", "modules": ["../SKILL.md"], "bytes": 48503, "est_tokens_pack": 22047}
  ```
- green: `2 passed, 3 subtests passed`

## S4-3 5절에 이미 내용이 있으면(두 번째 실행 포함) 거부
- 테스트: `test_section_five_with_content_is_refused`
- red:
  ```
  E       AssertionError: 0 == 0 : {"pack": ".../vault/packs/2026-09-27-fixture/pack.md", "modules": ["core-engines.md"], "bytes": 67390, "est_tokens_pack": 30632}
  ```
- green: `3 passed, 3 subtests passed`

## S4-4 팩 디렉터리 밖 경로(packs/ 아래가 아닌 디렉터리, 밖을 가리키는 pack.md 심링크) 거부
- 테스트: `test_paths_outside_a_pack_directory_are_refused`
- red:
  ```
  E       AssertionError: 0 == 0 : {"pack": ".../elsewhere/notes/pack.md", "modules": ["core-engines.md"], "bytes": 67390, "est_tokens_pack": 30632}
  ```
- green: `4 passed, 3 subtests passed`

## S4-5 `--permission-rule`가 자기 절대경로 Bash 규칙을 낸다(공백 경로는 effective=false)
- 테스트: `test_permission_rule_names_this_script_by_absolute_path`
- red:
  ```
  E       AssertionError: 2 != 0 : usage: assemble-pack.py [-h] [--pack-dir PACK_DIR] [--modules NAME [NAME ...]]
  E       assemble-pack.py: error: unrecognized arguments: --permission-rule
  ```
- green: `5 passed, 3 subtests passed`

## S5b-1 정의·폴백에 팩 파일로 직접 `printf ... >>`·`cat >>` 하는 지시가 있으면 D절 FAIL
- 테스트: `tests/test_check_structure_armorer.py::test_printf_append_into_the_pack_fails`(변조 임시 사본)
- red:
  ```
  E               AssertionError: 0 != 1 : PASS A. layout: required paths exist
  ```
- green: `1 passed, 2 subtests passed` (실제 리포는 이 시점에 새 검사 FAIL 10건, 문서 교체 전이라 예상대로)
- 5절 문서 교체 뒤 green: `2 passed, 2 subtests passed`, 실제 리포 `37 passed, 0 failed`

## S5b-2 변조 없는 사본은 새 검사와 마커 형식 검사를 PASS
- 테스트: `test_untampered_copy_passes`
- red(문서 교체 전):
  ```
  E       AssertionError: 1 != 0 : PASS A. layout: required paths exist
  ```
- green은 위 줄(armorer 정의·폴백의 Step E를 assemble-pack.py 호출로 교체, `{SCRIPTS_DIR}` Path Variable 추가).

## S5b-3 (#19) assemble-pack.py의 마커 템플릿이 SSOT와 어긋나면 D절 마커 형식 검사 FAIL
- 테스트: `test_assembler_marker_template_drift_fails`(템플릿 `sha256=`을 `sha=`로 변조한 사본)
- red:
  ```
  E       AssertionError: 0 != 1 : PASS A. layout: required paths exist
  ```
- green: `3 passed, 2 subtests passed`, 실제 리포 D절 마커 형식 검사 evidence에 `scripts/assemble-pack.py MODULE-BEGIN: <!-- MODULE-BEGIN: <file> sha256=<sha> -->` 등장
