# #20 TDD 로그

각 사이클의 red 출력 1~3줄. 테스트는 모두 가짜 HOME(+ XDG 변수 제거 또는 가짜 경로)에서 돈다. 임시 경로는 `<TMP>`로 줄였다.

## 사이클 1 (S1): 기본값이 `~/.local/share/smartthink`로 옮겨진다 (+S3 기본값 규칙 기대값)

```
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_default_when_nothing_is_set
E       AssertionError: {'path': '<TMP>/home/.claude/smartthink-vault', 'source': 'default'} != {'path': '<TMP>/home/.local/share/smartthink', 'source': 'default'}
4 failed, 18 passed in 0.64s
```

## 사이클 2 (S1): 포인터는 `~/.config/smartthink/vault-pointer`에서 읽고, 옛 `~/.claude/smartthink-vault/vault-pointer`는 무시한다

(사이클 1 구현 뒤 옛 위치 포인터 테스트는 이미 통과했다. 새 위치 포인터가 red.)

```
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_pointer_is_used_when_env_is_unset
E       AssertionError: {'path': '<TMP>/home/.local/share/smartthink', 'source': 'default'} != {'path': '<TMP>/notes/smartthink', 'source': 'pointer'}
```

## 사이클 3 (S1): `XDG_DATA_HOME`·`XDG_CONFIG_HOME`을 존중한다 (상대값은 XDG 규약대로 무시)

```
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_default_follows_xdg_data_home
E       AssertionError: {'path': '<TMP>/home/.local/share/smartthink', 'source': 'default'} != {'path': '<TMP>/xdg-data/smartthink', 'source': 'default'}
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_pointer_follows_xdg_config_home
```

## 사이클 4 (S2): `--candidates`가 빈 가짜 홈에서 "새로 만들기" 기본값 항목만 낸다

```
E   resolve-vault.py: error: unrecognized arguments: --candidates
FAILED tests/test_resolve_vault.py::CandidatesTest::test_empty_home_offers_only_the_new_default
```

## 사이클 5 (S2): `.obsidian`·`.logseq`·`dendron.yml`·`.foam` 표시 파일이 후보가 되고 제안 경로는 `<후보>/smartthink`

```
E       AssertionError: Items in the second set but not the first:
FAILED tests/test_resolve_vault.py::CandidatesTest::test_marker_files_make_candidates
```

## 사이클 6 (S2): 이름에 vault·notes·second-brain이 든 폴더가 후보가 된다 (대소문자·`_`·공백 무시)

```
E       AssertionError: Items in the second set but not the first:
FAILED tests/test_resolve_vault.py::CandidatesTest::test_folder_names_are_a_signal
```

## 사이클 7 (S2): Obsidian 등록 목록(macOS·Linux)이 신호가 되고, 표시 파일과 같은 곳이면 한 후보로 합친다

```
E       AssertionError: Items in the second set but not the first:
FAILED tests/test_resolve_vault.py::CandidatesTest::test_obsidian_registries_are_a_signal_and_merge_with_markers
```

## 사이클 8 (S2): 깊이 3 초과, `Library`·`node_modules`·`.git`·`.Trash`·`~/.claude`, 리포 안 `.claude`는 후보가 아니다 (등록 목록이 가리켜도)

```
E       AssertionError: Items in the first set but not the second:
E       '<TMP>/home/Library/Mobile Documents/Vault'
E       '<TMP>/home/.claude/notes'
```

## 사이클 9 (S2): 후보별 마지막 수정일·대략 파일 수·git 리포 여부·경고(`stale`·`nearly-empty`·`workspace-root`), 자동 선택 필드 없음(키 집합 고정)

```
E       AssertionError: {'path': ..., 'signals': ['marker:.obsidian'], 'suggested_vault': ...} != {'path': ..., 'last_modified': '2026-09-26', 'file_count': ...}
FAILED tests/test_resolve_vault.py::CandidatesTest::test_candidate_fields_and_warnings
```

## 사이클 10 (S2): 실제 사례 픽스처 (등록 목록 = 안 쓰는 기본 vault + 리포 30개 작업 폴더, 진짜 보관소는 이름 신호만)

red 없음: 사이클 7~9 구현으로 첫 실행에 통과했다. 이슈가 요구한 회귀 픽스처로 남긴다.

```
33 passed in 0.98s
```

## 사이클 11 (S2): 탐색 범위(`scan`)를 보고하고 시간 상한에서 멈춘다, 최상위 키에도 선택 표시가 없다

```
E   resolve-vault.py: error: unrecognized arguments: --time-limit 0
FAILED tests/test_resolve_vault.py::CandidatesTest::test_scan_reports_its_bounds_and_stops_at_the_time_limit
```

## S3: 새 기본값의 `permission_rule`은 `Edit(~/.local/share/smartthink/**)`, `permission_rule_effective=true`

red는 사이클 1에 함께 기록했다(`test_rule_for_default_vault_is_home_relative`가 옛 기본값 규칙 `Edit(~/.claude/smartthink-vault/**)`을 내서 실패). `XDG_DATA_HOME`이 홈 밖이면 `Edit(//...)`를 내는 회귀 테스트(`test_rule_follows_the_xdg_default`)는 사이클 3 구현 뒤 추가해 첫 실행에 통과했다.

## 사이클 12 (S5a): check-structure가 규약 문서·스크립트·설치기에 남은 옛 기본 vault 경로를 FAIL로 잡는다

`tests/test_check_structure_vault.py`는 리포 임시 사본을 변조해 CLI exit code와 출력 줄을 본다. 네 케이스를 한 파일에 적었고 검사가 없어 전부 red였다(아래는 설치기 변조 케이스).

```
E       AssertionError: 'FAIL E. vault: no pre-#20 default vault path in the conventions' not found in 'PASS A. layout: required paths exist\n...36 passed, 0 failed, 5 skipped...'
FAILED tests/test_check_structure_vault.py::OldVaultPathCheckTest::test_old_path_in_an_installer_fails
4 failed
```

green: `check_no_old_default_vault` 추가 뒤 변조 케이스 2개(설치기, 동등 표기 `$HOME/.claude/smartthink-vault`·`".claude" / "smartthink-vault"`)는 바로 통과, 깨끗한 사본·이력 허용 케이스 2개는 규약 문서·스크립트·설치기의 옛 경로 16건(README 2종, uninstall.sh, .gitignore, .data/README.md, SKILL.md 경로 규약, lifecycle.md)을 새 규약으로 고친 뒤 통과했다.

```
FAIL E. vault: no pre-#20 default vault path in the conventions: 16 mention(s) of the pre-#20 default vault
(문서 정리 뒤)
PASS E. vault: no pre-#20 default vault path in the conventions
57 passed in 2.58s
```

## 완료 기준 출력 (최종 커밋 직전 작업 트리)

```
$ python3 scripts/check-structure.py; echo "exit=$?"
PASS A. layout: required paths exist
PASS A. layout: plugin.json is valid and complete
PASS A. layout: st-searcher.md removed
PASS A. layout: st-armorer.md and st-thinker.md exist
PASS B. references: 9 mental-model modules exist
PASS B. references: index.json sha256 matches file bytes
PASS B. references: index.json est_tokens recomputes
PASS C. agents: frontmatter parses and name matches filename
PASS C. agents: no model field (session inheritance)
PASS C. agents: no skills preload
PASS C. agents: st-thinker effort/maxTurns
PASS C. agents: st-armorer effort/maxTurns
PASS C. agents: st-armorer owns the web tools
PASS C. agents: st-thinker has no web tools
PASS D. wiring: 6 pack section titles shared verbatim
PASS D. wiring: 11 manifest fields described on both sides
PASS D. wiring: spawned sub-agent names resolve to agents/
PASS D. wiring: plugin namespace on spawns and the /st alias
PASS D. wiring: referenced references/ files exist
PASS D. wiring: st-thinker definition and fallback prompt in sync
PASS D. wiring: thinker-prompt substitution variables
PASS D. wiring: st-armorer definition and fallback prompt in sync
PASS D. wiring: section 5 module marker forms match the SSOT
PASS D. wiring: headless gate signals and branches
PASS E. schema: evolution-state.md v3 header
PASS E. schema: profile.md v3 header
PASS E. schema: profile.md six blocks in order
PASS E. schema: shipped .data is a blank seed
PASS E. vault: {VAULT} comes from resolve-vault.py
PASS E. vault: permission rule is ~/ or // in the resolved settings
PASS E. vault: no pre-#20 default vault path in the conventions
PASS F. v2: no --deep mode in SKILL.md
PASS F. v2: SKILL.md frontmatter has no effort/argument-hint
PASS F. v2: no legacy prefix alias mapping
PASS F. v2: no live st-searcher wiring
PASS G. hygiene: no em dash in editable files
PASS G. hygiene: no private information
SKIP H. pack: pack.md and manifest.json exist: no --pack given
SKIP H. pack: manifest schema and boolean research: no --pack given
SKIP H. pack: section titles present and ordered: no --pack given
SKIP H. pack: section 5 verbatim hash integrity: no --pack given
SKIP H. pack: module markers scoped to section 5: no --pack given

37 passed, 0 failed, 5 skipped
pack: 0 passed, 0 failed, 5 skipped
exit=0

$ uv run --with pytest pytest -q tests; echo "exit=$?"
.........................................................                [100%]
57 passed in 2.39s
exit=0

$ git diff main -- . ':!tests/evidence' | grep '^+' | grep -c <em dash>   # 기존 289건은 바이트 불변 9개 모듈 원문(main과 동일)
0

$ 토큰 흔적 grep (git diff main에서 Anthropic 키 접두어 또는 토큰 변수에 리터럴 값 대입, 완료 기준의 정규식) | wc -l
0

$ git grep -n 'smartthink-vault' -- . ':!tests/evidence' | cut -c1-90
CHANGELOG.md:28:  `~/.claude/smartthink-vault/vault-pointer` file > the default. The same 
tests/gates.md:260:  - 사용자 레벨 정의와 CLAUDE.md·훅을 배제하려고 격리 `CLAUDE_CONFIG_DIR`에서 돌릴 때는 그 디렉터리
tests/gates.md:346:| 백그라운드 Write에서 권한 프롬프트가 뜨는가 | T9 | **뜬다.** default 권한 모드(상태줄 `⏸ manual
tests/gates.md:368:| T9 | PASS | 2026-09-27 | T9-fix-prompt-observation.md, T9-fix-setting
tests/test_check_structure_vault.py:16:OLD_PATH = "~/.claude/" + "smartthink-vault"
tests/test_check_structure_vault.py:63:        self.append("skills/smartthink/references/l
tests/test_check_structure_vault.py:64:        self.append("scripts/migrate-evolution.py",
tests/test_resolve_vault.py:31:        self.old_vault = self.home / ".claude" / "smartthin
tests/test_resolve_vault.py:383:        self.make_store(".claude/smartthink-vault")
```

남은 `smartthink-vault` 언급: CHANGELOG.md(이력), gates.md 260행(T12 예시의 옛 위치 보호 deny, "옛 위치(메인테이너 머신 잔존)" 표기), gates.md 346·368행(T9 기록, 다른 워커 소유라 미수정), tests/의 회귀 픽스처(옛 위치를 무시하는지·check가 잡는지 검증하는 입력).

---

# final-review 20260927-032439 후속 (Spec MISSING 판정 반영)

## 사이클 13 (c)2: `--time-limit`이 후보 기술(`describe`)까지 포함한 전체 스캔에 걸린다, 초과 시 `partial` 경고와 부분 결과

```
E       AssertionError: 3000 not less than 3000
FAILED tests/test_resolve_vault.py::CandidatesTest::test_time_limit_also_bounds_describing_candidates
```

## 사이클 14 (a)2 #23-1: vault 경로에 규칙·glob 문법 문자(`[ ] * ? { } ( )`)가 있으면 `permission_rule_effective=false`, `permission_rule_reason="special-characters"`

```
E       KeyError: 'permission_rule_reason'
E               AssertionError: True is not false
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_rule_syntax_characters_make_the_rule_ineffective
```

## 사이클 15 (a)2 #23-2: 상대 `CLAUDE_CONFIG_DIR`면 `settings_path=null`과 stderr 경고

```
E       AssertionError: '<TMP>/rel-config/settings.json' is not None
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_relative_claude_config_dir_leaves_settings_path_empty
```

## 사이클 16 (a)1: `.claude`·`.git`·`.vscode`·`.idea` 폴더 아래 vault는 `permission_rule_effective=false`, `permission_rule_reason="protected-folder"`

헤드리스 탐침(T15-protected-probe.md) 11회로 보호 경로를 먼저 실측한 뒤 쓴 테스트다.

```
E               AssertionError: True is not false
FAILED tests/test_resolve_vault.py::ResolveVaultTest::test_rule_under_protected_folders_is_not_effective
```
