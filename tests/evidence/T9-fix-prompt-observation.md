# T9 재실측 (#14 수정 후) - 백그라운드 Write 권한 프롬프트 관찰

실행일: 2026-09-27 00:55 ~ 01:50 (+09:00) | Claude Code 2.1.283, Opus 5.5 | 브랜치 `st-14-init-perm` (커밋 175b45a, 세션 5만 후속 커밋 포함) | 스킬 진입 `/smartthink:smartthink`(Base directory가 워크트리, `T9-fix-transcript.md` 첫머리)

## 판정

- **env vault(홈 밖 절대경로): PASS.** init이 `//` 형식 규칙을 격리 `CLAUDE_CONFIG_DIR`의 `settings.json`에 설치했고, 새 세션 무장에서 armorer의 vault Write 프롬프트는 0회였다.
- **기본 vault(`~/.claude/smartthink-vault`): 규칙 형식은 PASS, 프롬프트 제거는 BLOCKED.** init은 `Edit(~/.claude/smartthink-vault/**)`를 가짜 홈의 `settings.json`에 설치했지만, 새 세션 무장에서 Write 프롬프트가 2회 떴다. Claude Code가 `$HOME/.claude` 아래 쓰기를 민감 파일로 보고 허용 규칙과 무관하게 묻기 때문이다(아래 프로브). 규칙 형식으로는 풀 수 없고 vault 위치를 바꿔야 한다. 이에 맞춰 resolver가 `permission_rule_effective: false`를 내고 init이 효과 없는 규칙을 제안하지 않도록 고쳤다(세션 5에서 확인).

## 세션 조건

- 모든 세션: Orca 대화형 터미널, `claude --plugin-dir "$WT" --model opus --permission-mode default`, 설정 시작값 `{"permissions":{"defaultMode":"default"}}`, 상태줄 `⏸ manual mode on`(관찰 구간 전부, auto·bypass 전환 없음). 토큰은 `CLAUDE_CODE_OAUTH_TOKEN="$ANTHROPIC_OAUTH_TOKEN"`로 자식 env에만 주입.
- 세션 1·2: `CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG>`(mktemp -d), `SMARTTHINK_VAULT=<VAULT>`(mktemp -d, `/var/folders/...` 아래). resolver: `source=env`, `permission_rule=Edit(//var/folders/[REDACTED]/T/<VAULT_DIR>/**)`, `settings_path=<ISOLATED_CONFIG>/settings.json`.
- 세션 3·4: `HOME=<FAKE_HOME>`(mktemp -d), `SMARTTHINK_VAULT`·`CLAUDE_CONFIG_DIR` unset. 기동 전 `HOME=<FAKE_HOME> python3 scripts/resolve-vault.py`가 `<FAKE_HOME>/.claude/smartthink-vault`, `source=default`를 내는 것을 확인했다. 가짜 홈에서 인증·기동 정상.
- 세션 5: 새 가짜 홈 `<FAKE_HOME2>`, 조건은 세션 3과 같고 코드만 후속 커밋(`permission_rule_effective` 분기).
- 프롬프트 응답: 테스터가 `orca terminal read --screen`으로 20~30초 간격 폴링하며 원문을 기록하고 `1. Yes`(1회 허용)로만 답했다. 규칙을 만드는 선택지(don't ask again, always allow, session allow)는 고르지 않았다.
- 실제 `~/.claude/settings.json`: 시작 전 sha256 기록 후 종료 시 `shasum -c` OK(불변). 실제 vault는 읽지도 쓰지도 않았다.

## init 설치 대상과 규칙 (세션 1, 3)

| 세션 | 조건 | 설치 대상 | 설치 규칙 | 실제 `~/.claude/settings.json` 쓰기 프롬프트 |
|---|---|---|---|---|
| 1 | env vault, 격리 CLAUDE_CONFIG_DIR | `<ISOLATED_CONFIG>/settings.json` (백업 `settings.json.bak`) | `Edit(//var/folders/[REDACTED]/T/<VAULT_DIR>/**)` | 없음 |
| 3 | 기본 vault, 가짜 HOME | `<FAKE_HOME>/.claude/settings.json` (백업 `settings.json.bak`) | `Edit(~/.claude/smartthink-vault/**)` | 없음 |
| 5 | 기본 vault, 가짜 HOME2, 후속 커밋 | 설치 안 함(제안 생략, 이유 안내) | - | 없음 |

두 경우 모두 스킬이 `resolve-vault.py --permission-rule`을 실행해 그 값을 그대로 썼다(트랜스크립트 세션 1 첫 스냅샷). 기존 키(`defaultMode`, `theme`) 보존, `permissions.allow`에 1항목만 추가(`T9-fix-settings.diff`).

## 무장 중 vault Write 관찰 (세션 2, 4)

| 세션 | 규칙 | pack.md Write | manifest.json 작성 |
|---|---|---|---|
| 2 (새 세션, 설정 새로 로딩) | `Edit(//.../<VAULT_DIR>/**)` | **프롬프트 없음.** 서브에이전트 jsonl: Write 호출 16:14:00.786Z → `File created successfully` 16:14:00.807Z(21ms). 부모 화면 01:13:58·01:14:24 스냅샷에 create 프롬프트 없음 | Write 도구가 아니라 Bash heredoc으로 작성(Bash 프롬프트 1회, 아래) |
| 4 (새 세션) | `Edit(~/.claude/smartthink-vault/**)` | **프롬프트 뜸** 01:35:31 `Do you want to create pack.md?` (Write 호출 16:35:09Z → 결과 16:36:58Z, 응답 대기 109초) | **프롬프트 뜸** 01:37:58 `Do you want to create manifest.json?` (16:37:38Z → 16:38:01Z) |

세션 4 프롬프트 원문(두 파일 같은 형식):

```
 Do you want to create pack.md?
 ❯ 1. Yes
   2. Yes, and allow Claude to edit files in its ~/.claude folder for this session
   3. No
```

### Write 외 프롬프트 (판정 대상 아님, 기록)

- 두 무장 모두 armorer가 Bash로 vault를 만졌다: `mkdir -p <VAULT>/packs/<slug>/`, 모듈 원문 이어붙이기(`cat >> "$PACK"`), 세션 2의 manifest.json heredoc. Bash 호출은 `Edit(...)` 규칙 대상이 아니므로 default 모드에서는 매번 Bash 프롬프트가 뜬다(세션 2: armorer Bash 프롬프트 5회, 세션 4: 4회). #14 범위(권한 규칙 형식·설정 파일)가 아니라 armorer의 도구 선택 문제라 후속으로 넘긴다.
- 메인 세션의 resolver 실행(Bash)과 vault Read도 매번 묻는다. 규칙은 `Edit`만 허용하므로 정상이다.

## 원인 프로브 (기본 vault에서 프롬프트가 남는 이유)

`claude -p`(헤드리스는 승인이 필요하면 거부로 끝난다) + `--permission-mode default`, 모델 claude-sonnet-5, 프롬프트 "Write 도구로 파일 1개만 만들고 결과를 그대로 보고". 가짜 홈 `<PROBE_HOME>`.

| 프로브 | HOME / CLAUDE_CONFIG_DIR | 쓰기 경로 | 매칭 규칙 | 결과(원문) |
|---|---|---|---|---|
| P1 | `<PROBE_HOME>` / 없음 | `~/.claude/smartthink-vault/p1.txt` | `Edit(~/.claude/smartthink-vault/**)` | `WRITE_DENIED ... which is a sensitive file.` |
| P2 | 같음 | `~/notes/st/p2.txt` | `Edit(~/notes/st/**)` | `WRITE_OK` (파일 생성 확인) |
| P3 | 같음 | `~/.claude/smartthink-vault/sub/p3.txt` | `Edit(//<PROBE_HOME 앞 / 제거>/.claude/smartthink-vault/sub/**)` | `WRITE_DENIED ... which is a sensitive file.` |
| P4 | 같음 | `~/other/sub2/p4.txt` | 없음(음성 대조) | `WRITE_DENIED ... but you haven't granted it yet.` |
| P5 | `<PROBE_HOME>` / `<PROBE_HOME>/cfg` | `<PROBE_HOME>/cfg/vault/p5.txt` | `Edit(//.../cfg/vault/**)` | `WRITE_OK` |
| P6 | 같음 | `~/.claude/v6/p6.txt` | `Edit(//.../.claude/v6/**)` | `WRITE_DENIED ... which is a sensitive file.` |

### 가설과 판정

- **H1 `$HOME/.claude`는 민감 경로라 허용 규칙이 무시된다: 채택.** P1·P3·P6 거부 문구가 "sensitive file"로 P4(규칙 없음)와 다르다. `~/`·`//` 어느 형식으로도 풀리지 않는다. 세션 4 프롬프트의 2번 선택지도 `~/.claude` 폴더 전용이다.
- **H2 `~/` 규칙 확장이 HOME을 따르지 않는다: 기각.** P2가 같은 가짜 홈에서 `~/` 규칙으로 허용됐다.
- **H3 새 세션에서 규칙이 로드되지 않았다: 기각.** 같은 설치 방식의 세션 2(`//` 규칙)는 무프롬프트였고, P1~P6은 매 호출 새 프로세스다.
- **H4 보호가 `CLAUDE_CONFIG_DIR`을 따른다: 기각.** P5(설정 디렉터리 안 vault) 허용, P6(설정 디렉터리가 따로 있어도 `$HOME/.claude`) 거부.

## 결론과 후속

- #14의 두 결함(단일 `/` 규칙, `CLAUDE_CONFIG_DIR` 무시)은 해소됐다. `~/` 형식 자체도 P2로 동작이 확인됐다.
- 기본 vault가 `~/.claude` 아래인 한 default 모드의 팩 Write 프롬프트는 규칙으로 없앨 수 없다. 해소하려면 기본 vault 위치 변경(기존 사용자 이전 포함) 같은 제품 결정이 필요하다. 이번 수정은 init이 효과 없는 규칙을 설치하지 않고 이유와 대안(vault 이동, 세션 한정 허용)을 안내하는 데까지다.
## 코디네이터 개입 (기록)

- 세션 1: 테스터가 포그라운드 대기 중 Bash 승인 프롬프트(settings.json 검증·resolver·ls)가 138초 방치돼 코디네이터가 1회 승인으로 응답하고 입력창에 남은 `1`을 지웠다. 설정 쓰기 관련 프롬프트가 아니라 Bash 검증 명령이다.
- 세션 4: manifest.json Create 프롬프트가 134초 방치돼 코디네이터가 `1`(Yes, 1회)로 응답했고, 이어 뜬 armorer의 `check-structure --pack` Bash 프롬프트에도 `1`로 응답했다. 프롬프트 발생 사실(01:37:58 스냅샷)은 테스터가 먼저 기록했고, 응답 선택지가 1회 허용이라 규칙이 생기지 않아 관찰은 오염되지 않았다.
- 두 경우 모두 테스터와 코디네이터의 응답이 겹쳐 잉여 `1` 입력이 생겼다(아래).

- 세션 1 끝의 `❯ 1`은 테스터가 이미 닫힌 승인 프롬프트에 보낸 잉여 입력이다. 세션 4 게이트의 `'1'을 어떻게 해석할까요?` 질문도 같은 잉여 입력 때문이며, 테스터가 `리서치 끄고 A/B/C 모두 그대로 진행 (--nosearch)`로 답했다. 두 경우 모두 권한 관찰에는 영향이 없다.
