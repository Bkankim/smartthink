# T14 실행 기록 (2026-09-26, 브랜치 fix/3.0.1)

## 판정: BLOCKED (쓰기 경로 미실행). 기본 vault 무변경은 확인

## 시도
1. `timeout 540 claude ...` - macOS에 `timeout`이 없어 exit 127. 실행 자체가 안 됨(시도로 세지 않음).
2. 격리 `HOME`(스크래치 디렉터리)에서 `claude --plugin-dir . -p` - `Not logged in · Please run /login`, exit 1.
3. 격리 `HOME` + `CLAUDE_CODE_OAUTH_TOKEN`(사용자 cct 브리지로 자식 env에만 주입, 출력 안 함) +
   `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`, 입력 끝에 비대화식 진행 1줄(#9 우회). exit 0.

## 관찰 (시도 3, 자식 트랜스크립트 기준)
- resolver 단위 확인: `{"path": "<ISO>/empty-vault", "source": "env"}`.
- 자식은 resolver를 8회 호출했으나 전부 "This command requires approval"로 거부됨. 격리 `HOME`에는
  권한 허용 규칙이 없고 `-p`는 승인을 물을 수 없다.
- 첫 호출은 SKILL.md가 안내한 `$(cd ... && pwd -P)` 복합 명령이었고 "multiple operations ... require
  approval"로 거부됨. 일반 권한 모드에서도 매번 승인이 필요한 형태라 SKILL.md를 절대경로 한 줄 호출로 고쳤다.
- resolver가 막히자 자식이 `/tmp/smartthink-vault-check`, 리포 안 `.smartthink-vault/packs`,
  `tmp-smartthink-pack/packs`에 vault를 즉흥 생성하려 함(모두 권한 거부). 이것도 폴백이므로 SKILL.md에
  "resolver 실패 시 다른 경로를 만들지 말고 파일 없이 인라인으로 대체"를 명시했다.
- 결국 팩 파일 없이 인라인 응답으로 무장 브리핑을 출력하고 턴 종료.

## 통과 기준 대비
- resolver 출력 source=env: 충족.
- 팩이 만들어지면 `$ST_EMPTY/packs/` 아래: 팩이 만들어지지 않아 판정 불가.
- 기본 vault `find -newer` 결과 비어 있음: 충족(실제 `~/.claude/smartthink-vault`와 격리 HOME 기본 vault 모두).

## 완전 실측에 필요한 조건
격리 `HOME`에 `Bash(python3 *resolve-vault.py*)`와 `Write`/`Edit(<빈 vault>/**)` 허용 규칙을 넣고,
실제 vault 경로 쓰기는 deny 규칙으로 막은 뒤 재실행. 단위 테스트(`tests/test_resolve_vault.py`,
`tests/test_migrate_target.py`)가 빈 env vault 사용과 기본 vault 비폴백을 매 실행 검증한다.
