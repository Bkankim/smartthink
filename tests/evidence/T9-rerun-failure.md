# T9 재실측 FAIL 기록 (#8)

실행일: 2026-09-26~27 | 세부: `T9-rerun-prompt-observation.md`, `T9-rerun-settings.diff`, `T9-rerun-transcript.md`

## 실패한 통과 기준

1. **"승인 뒤에는 ... 정확히 현재 vault를 가리키는 `Edit(<VAULT>/**)` 항목"** - init이 쓴 항목은 `Edit(/var/folders/[REDACTED]/<VAULT_DIR>/**)`(단일 `/` 절대경로)다. Claude Code는 `/`로 시작하는 규칙 경로를 설정 파일 기준 상대경로로 해석한다. 실측: 이 규칙만 있는 상태에서 같은 세션 재시도(2차)와 설정을 새로 읽은 새 세션(3차) 모두 armorer의 `pack.md` Write에 `Do you want to create pack.md?` 프롬프트가 떴다. 테스터가 `Edit(//var/folders/[REDACTED]/<VAULT_DIR>/**)`를 추가한 새 세션(4차)에서는 Write가 프롬프트 없이 17ms 만에 끝났다.
2. **설치 대상 파일** - 세션이 `CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG>`로 떠 있는데도 init은 실제 사용자 설정을 대상으로 `cp ~/.claude/settings.json ~/.claude/settings.json.bak && grep -n -A3 '"permissions"' ~/.claude/settings.json`을 실행하려 했다(권한 프롬프트 원문: `Claude requested permissions to write to /Users/[REDACTED]/.claude/settings.json, but you haven't granted it yet.`). 테스터가 `4. No`로 거절하고 격리 설정을 지시한 뒤에야 올바른 파일에 설치됐다. 실제 `~/.claude/settings.json`은 sha256 불변.

## 충족한 기준

- 첫 init은 설치 여부를 묻고, 거절 시 격리 `settings.json`이 `{}` 그대로다.
- 첫 무장의 백그라운드 Write 프롬프트 발생이 관찰 결과로 명시됐다(뜬다).
- 승인 시 머지 규율: `settings.json.bak` 백업, 기존 JSON 보존, `permissions.allow` 신설 후 1항목만 추가.
- 재시도(같은 세션·새 세션)와 첫 시도의 프롬프트 발생을 비교 기록했다.

## 원인 위치 (스킬, 이 이슈 범위 밖이라 수정하지 않음)

- `skills/smartthink/references/lifecycle.md` 권한 규칙 절(161~178행 부근): 규칙 형식 `Edit(<VAULT>/**)`와 대상 `~/.claude/settings.json`이 고정돼 있다. 371행 표도 같다.
- 수정 방향(제안): 절대경로 vault는 `Edit(//<VAULT>/**)`로, 홈 아래면 `Edit(~/...)`로 쓰고, `CLAUDE_CONFIG_DIR`가 있으면 그 안의 `settings.json`을 대상으로 한다. 기본 vault(`~/.claude/smartthink-vault`)로는 실측하지 않았다.

## 사용한 명령

`cd "$WT" && CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG> CLAUDE_CODE_OAUTH_TOKEN=[REDACTED] SMARTTHINK_VAULT=<VAULT> claude --plugin-dir "$WT" --model opus --permission-mode default` (세션 1~4 각각 새로 기동)
