# T9 재실측 - 백그라운드 Write 권한 프롬프트 관찰 (#8)

실행일: 2026-09-26 23:12 ~ 2026-09-27 00:16 (+09:00) | vault: `<VAULT>` (`mktemp -d`, 전 세션 공용) | 설정: 격리 `CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG>`, 시작 시 `settings.json` = `{}`

## 세션 조건

- 명령(Orca 대화형 터미널, 세션마다 새로 기동): `cd "$WT" && CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG> CLAUDE_CODE_OAUTH_TOKEN=[REDACTED] SMARTTHINK_VAULT=<VAULT> claude --plugin-dir "$WT" --model opus --permission-mode default`
- Claude Code 2.1.283, Opus 5.5. 상태줄 원문(관찰 구간 전부): `⏸ manual mode on · ? for shortcuts · ← for agents`. bypass·auto가 아니다.
- 사용자 레벨 정의·훅·허용 규칙 없음(격리 설정). 권한 프롬프트는 테스터가 `orca terminal read --screen`으로 원문을 기록한 뒤 `1. Yes`(1회 허용, 규칙 추가 없음)로만 응답했다. 실제 사용자 설정 쓰기 시도 1건만 `4. No`로 거절했다(아래).
- 실제 `~/.claude/settings.json` sha256은 전 과정 `829dbd9c...b909`로 불변. 실제 vault mtime 불변.

## 오염 구간 고지 (세션 1의 첫 리서치 무장)

- 세션 1 첫 무장(23:19 진행) 도중 상태줄이 `⏵⏵ auto mode on`으로 바뀐 것을 23:25경 발견했다. 테스터의 승인 키가 auto 모드 전환 제안에 들어갔거나 사람이 프롬프트를 눌렀다(코디네이터 통보: 이 시각 전후 BK가 프롬프트를 직접 누른 적이 있다). 테스터가 Shift+Tab으로 `⏸ manual mode on`으로 되돌렸고, 이 무장의 팩 Write(23:26~23:27)는 manual 모드에서 일어났지만 이 회차는 판정 근거에서 뺐다. 같은 조건(규칙 없음)을 **1차-b**(`--nosearch`, 같은 세션)로 다시 관찰했다.

## 관찰 표

| 회차 | 세션 | 규칙 상태 | pack.md Write | manifest.json Write |
|---|---|---|---|---|
| 1차-b (23:30~23:38) | 세션 1, init에서 설치 거절 | 규칙 없음 | **프롬프트 뜸** 23:37:16 `Do you want to create pack.md?` | **프롬프트 뜸** 23:37:54 `Do you want to create manifest.json?` |
| 2차 (23:46~23:54) | 세션 2(새 세션), init에서 설치 승인 직후 같은 세션 | `Edit(/var/folders/.../<VAULT>/**)` (스킬이 쓴 형식) | **프롬프트 뜸** 23:53:19 | **프롬프트 뜸** 23:53:52 |
| 3차 (23:59~00:05) | 세션 3(새 세션, 설정 새로 로딩) | 같은 규칙 | **프롬프트 뜸** 00:02:3x `Do you want to create pack.md?` | Write 도구 대신 Bash로 작성(Bash 프롬프트) |
| 4차 (00:09~00:16) | 세션 4(새 세션) | 테스터가 `Edit(//var/folders/.../<VAULT>/**)` 추가 | **프롬프트 없음** (subagent jsonl: Write 호출 15:14:49.814Z → `File created successfully` 15:14:49.831Z, 17ms) | Write 도구 미사용 |

프롬프트 원문(1차-b, `orca terminal read --screen` 발췌, 파일 미리보기 줄은 생략):

```
 Do you want to create pack.md?
 ❯ 1. Yes
   2. Yes, and switch to accept edits (auto-approve file edits and common file commands) for this session (shift+tab)
   3. No
 Esc to cancel · Tab to amend
```

- 도구·경로: 서브에이전트 jsonl에서 같은 시각의 호출은 `smartthink:st-armorer`(백그라운드)의 `Write(<VAULT>/packs/<슬러그>/pack.md)`, `Write(<VAULT>/packs/<슬러그>/manifest.json)`다. 같은 에이전트의 Bash·Fetch·WebSearch 프롬프트는 `Bash command · from the smartthink:st-armorer agent`처럼 출처가 헤더에 찍혀 부모 세션 화면에 떴다. 파일 생성 프롬프트의 헤더 줄은 미리보기가 길어 화면 캡처 범위(`tail`) 밖으로 밀려 원문을 남기지 못했다.
- 백그라운드 서브에이전트의 프롬프트는 부모 세션의 입력창 위에 떠서 응답할 때까지 서브에이전트가 멈춘다. 응답하지 않으면 무장이 진행되지 않는다.

## 결론 (4절 실측표 답)

1. **뜬다.** default 권한 모드, 허용 규칙 없음에서 armorer(백그라운드)의 vault Write마다 부모 세션에 `Do you want to create <파일>?` 프롬프트가 뜬다. vault 밖 경로 Bash·WebFetch·WebSearch도 각각 프롬프트가 뜬다.
2. **스킬이 설치하는 규칙 `Edit(<VAULT>/**)`는 이 프롬프트를 없애지 못했다**(같은 세션 재시도, 새 세션 재시도 모두 프롬프트 발생). Claude Code 권한 규칙에서 `/`로 시작하는 경로는 설정 파일 기준 상대경로이고, 절대경로는 `//`로 시작해야 한다. 테스터가 `Edit(//<VAULT>/**)`를 넣은 새 세션에서는 pack.md Write가 프롬프트 없이 17ms 만에 끝났다. 원인은 규칙 형식이다(가설 판정은 아래).
3. init의 설치 제안은 실제 사용자 설정 `~/.claude/settings.json`을 대상으로 고정돼 있다. `CLAUDE_CONFIG_DIR`로 뜬 세션에서도 `cp ~/.claude/settings.json ~/.claude/settings.json.bak && ...`를 실행하려 했고, 테스터가 `4. No`로 거절한 뒤 "이 세션의 사용자 설정은 `$CLAUDE_CONFIG_DIR/settings.json`"이라고 지시해 격리 설정에 설치됐다. 머지 자체는 규율대로였다: 백업(`settings.json.bak`), 기존 JSON 보존, `permissions.allow`에 한 항목만 추가.

## 가설 판정 (규칙 설치 뒤에도 프롬프트가 뜬 원인)

| 가설 | 근거 | 판정 |
|---|---|---|
| H1. 설정 변경이 실행 중 세션에 반영되지 않는다 | 설정을 새로 읽은 세션 3에서도 같은 규칙으로 프롬프트가 떴다 | 기각 |
| H2. `/var` → `/private/var` 심링크 때문에 경로가 불일치한다 | 세션 4의 `//var/...` 규칙(심링크 미해석 경로)으로 프롬프트가 사라졌다. 심링크 해석은 필요 없었다 | 기각 |
| H3. `Edit(...)` 규칙이 Write 도구를 덮지 못한다 | 세션 4에서 `Edit(//...)` 규칙만으로 Write가 무프롬프트 통과 | 기각 |
| H4. 단일 `/` 접두 절대경로는 설정 파일 기준 상대경로로 해석된다 | `Edit(/var/...)` 있음 → 프롬프트, `Edit(//var/...)` 추가 → 프롬프트 없음. 다른 조건은 같다 | **채택** |

범위 밖 스킬 결함(보고만, 수정하지 않음): `references/lifecycle.md`의 권한 규칙 절이 ① 규칙을 `Edit(<VAULT>/**)`(단일 `/`)로 쓰고 ② 대상 파일을 `~/.claude/settings.json`으로 고정한다. 실사용 기본 vault(`~/.claude/smartthink-vault`)에서도 ①은 같은 문제일 가능성이 높다(`Edit(~/.claude/smartthink-vault/**)` 또는 `Edit(//<절대경로>/**)` 형식 필요). 기본 vault 경로로는 실측하지 않았다.
