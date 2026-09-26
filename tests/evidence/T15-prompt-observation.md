# T15 init vault 후보 제안: 권한 프롬프트 관찰과 판정

- 실행일: 2026-09-27, 브랜치 `st-20-vault-location`(9be45de 이후 작업 트리), Claude Code 2.1.283, `--model opus`.
- 환경: 격리 `CLAUDE_CONFIG_DIR=<ROOT>/cfg`, 가짜 `HOME=<ROOT>/home`, `XDG_DATA_HOME`·`XDG_CONFIG_HOME`·`SMARTTHINK_VAULT` 제거(`env -u`), 인증은 `CLAUDE_CODE_OAUTH_TOKEN`을 자식 env에만 주입(값 미기록). 호출은 `/smartthink:smartthink`(bare `/smartthink`는 메인 체크아웃 심링크라 쓰지 않음). 로딩된 SKILL.md Base directory는 워크트리(`T15-transcript.md` 2절 `SKILL` 줄).
- 권한 모드: 격리 settings.json에 `"defaultMode":"default"` 명시, 두 세션 모두 상태줄 `⏸ manual mode on` 확인. 프롬프트는 20~30초 간격 화면 읽기로 직접 기록·응답했다.
- 실제 홈 보호: 격리 settings.json deny에 실제 홈 절대경로로 옛 vault·새 기본값·포인터 디렉터리를 넣었다. 실행 전후 실제 `~/.config/smartthink`·`~/.local/share/smartthink`는 둘 다 없음(`ls` 결과 `No such file or directory`).
- 안전 규칙 메모: 이 게이트는 포인터 경로를 보려고 `SMARTTHINK_VAULT`를 지웠다. resolver의 `source: default`/`pointer`가 가리킨 경로는 모두 가짜 홈 아래(`<ROOT>/home/...`)임을 사전 실행으로 확인한 뒤 진행했다.

## 픽스처 (가짜 홈, 노트 보관소 3종 = 실제 사례 재현)

| 경로(가짜 홈 기준) | 구성 | 기대 |
|---|---|---|
| `~/Documents/Obsidian Vault` | `.obsidian/`, 파일 1개, Obsidian 등록 목록에 있음 | 후보 + `nearly-empty` |
| `~/workspace` | `.obsidian/`, 리포 30개(`repo-NN/.git`), 등록 목록에 있음 | 후보 + `workspace-root` |
| `~/workspace/vault` | 이름 신호만, 노트 40개, git 리포 | 후보, 경고 없음 |

등록 목록: `~/Library/Application Support/obsidian/obsidian.json`(두 항목). `--candidates` 출력은 `T15-candidates.json`(init 뒤 재실행이라 `~/workspace/vault`의 파일 수가 profile·.gitignore 추가분만큼 늘었을 수 있다).

## 격리 settings.json (실행 전 → init 승인 뒤)

```
{"permissions":{"defaultMode":"default","deny":["Read(/<HOME>/.claude/smartthink-vault/**)","Edit(/<HOME>/.claude/smartthink-vault/**)","Read(/<HOME>/.local/share/smartthink/**)","Edit(/<HOME>/.local/share/smartthink/**)","Edit(/<HOME>/.config/smartthink/**)"]}}

{"permissions":{"defaultMode":"default","allow":["Edit(~/workspace/vault/smartthink/**)"],"deny":["Read(/<HOME>/.claude/smartthink-vault/**)","Edit(/<HOME>/.claude/smartthink-vault/**)","Read(/<HOME>/.local/share/smartthink/**)","Edit(/<HOME>/.local/share/smartthink/**)","Edit(/<HOME>/.config/smartthink/**)"]}}
```

포인터 `~/.config/smartthink/vault-pointer`(가짜 홈) 내용:

```
<ROOT>/home/workspace/vault/smartthink
```

`~/workspace/vault/.gitignore`(승인 뒤 새로 생성): `smartthink/packs/`

## 프롬프트 기록 (발생 순서, 응답)

`init`: init 세션, `arm`: 새 세션 무장. `[armorer]`는 부모 세션에 `· from the smartthink:st-armorer agent`로 뜬 프롬프트.

```
init P1 Read lifecycle.md (plugin dir) -> 1 Yes
init P2 Bash readlink+ls scripts -> 1 Yes
init P3 Bash resolve-vault.py --ensure -> 1 Yes
init P4 Bash ls proj + ls ~/.claude/CLAUDE.md MEMORY.md -> 1 Yes
init P5 Bash resolve-vault.py --candidates -> 1 Yes
init P6 Read .data/profile.md template -> 1 Yes
init P7 Bash cd vault && git rev-parse; ls; cat .gitignore -> 1 Yes
init P8 Bash echo XDG/HOME; mkdir -p pointer dir -> 1 Yes
init P9 Write ~/.config/smartthink/vault-pointer (init, expected) -> 1 Yes
init P10 Bash resolve-vault.py --ensure (via pointer) -> 1 Yes
init P11 Write vault/profile.md (init, before rule install, expected) -> 1 Yes
init P12 Write ~/workspace/vault/.gitignore (approved, expected) -> 1 Yes
init P13 Bash resolve-vault.py --permission-rule; ls vault -> 1 Yes
init P14 Bash ls cfg/settings.json -> 1 Yes
init P15 Read cfg/settings.json -> 1 Yes
init P16 Bash cp settings.json settings.json.bak -> 1 Yes
init P17 Edit cfg/settings.json add allow rule (approved) -> 1 Yes
init P18 Bash python3 verify settings allow -> 1 Yes
--- arm session (new) ---
arm A1 Bash resolve-vault.py --ensure -> 1 Yes
arm A2 Bash ls vault; cat index.json -> 1 Yes
arm A3 [armorer] Bash cd refs && wc -c ...; ls packs -> 1 Yes
arm A4 [armorer] Read references/core-engines.md -> 2 allow reading references/ this session
arm A5 [armorer] Bash cd refs && wc -l (Read deny rule note) -> 1 Yes
arm A6 [armorer] Bash ls vault/packs; head profile.md -> 1 Yes
arm A7 [armorer] Bash head evolution-state.md; ls scripts -> 1 Yes
arm A8 [armorer] Bash mkdir -p packs/<slug> && date -> 1 Yes
arm OBS pack.md created 03:15 with NO Write prompt (file exists while no prompt was answered)
arm A9 [armorer] Bash heredoc append sections 5-6 to pack.md + grep/awk checks (Bash, #21) -> 1 Yes
arm A10 [armorer] Bash python heredoc edit pack.md briefing + check-structure --help (Bash, #21) -> 1 Yes
arm A11 [armorer] Bash heredoc write manifest.json + check-structure --pack (Bash, #21) -> 1 Yes
arm A12 [armorer] Bash check-structure --pack results + em dash count (Bash, #21) -> 1 Yes
arm A13 [main] Bash cd pack && ls; grep headings; cat manifest -> 1 Yes
```

## 판정: PASS

- ⑤에서 `resolve-vault.py --candidates` 결과 3개 후보가 신호·수정일·파일 수·git 여부·경고와 함께 번호 목록으로 떴고, "새로 만들기(기본값)"·"직접 입력"이 끝에 붙었다. 모델이 "이 문항은 제가 미리 골라 두지 않았습니다"라고 명시했고 Enter 수락 기본값이나 추천 표시가 없었다(`T15-transcript.md` 1절). 앞 두 후보에 경고가 붙었다.
- 3번 선택 → `suggested_vault` `~/workspace/vault/smartthink`를 확정, git 리포라서 `packs/`를 `.gitignore`에 넣을지 물었고 승인 뒤 한 줄 생성.
- 포인터가 가짜 홈의 `~/.config/smartthink/vault-pointer`에 기록됐고(P9), 재실행한 resolver가 `source: pointer`로 같은 경로를 냈다(P10, P13).
- 권한 규칙 `Edit(~/workspace/vault/smartthink/**)`를 `permission_rule_effective: true`로 제안, 승인 뒤 격리 settings.json에 보존 머지(P16~P17).
- **새 세션 무장에서 vault Write/Edit 도구 프롬프트 0회.** armorer의 `Write(<VAULT>/packs/2026-09-27-library-seat-reservation-guide/pack.md)` 1회가 프롬프트 없이 성공했다(`is_error=False`, 03:15 파일 생성 시점에 응답한 프롬프트 없음). 무장 세션에 Edit 도구 호출은 없었다.
- init 중 Write/Edit 프롬프트(P9 포인터, P11 profile.md, P12 .gitignore, P17 settings.json)는 규칙 설치 전 또는 vault 밖 쓰기라 판정 대상이 아니다.

## 기록만 (범위 밖)

- Bash 프롬프트: init 11회, 무장 12회(A1~A3, A5~A13). 특히 armorer가 팩 5·6절 추가(A9·A10)와 `manifest.json` 작성(A11)을 Bash heredoc으로 해서 Edit 규칙이 덮지 못한다. #21 소관.
- A3·A5·A13의 "Compound command contains cd with a relative file read while a Read() deny rule exists" 경고는 이 게이트가 넣은 실제 홈 보호 deny 규칙 때문이다.
- Read 프롬프트: 플러그인 디렉터리의 references·.data 읽기와 격리 settings.json 읽기(P1, P6, P15, A4).
- init이 사전 스캔 단계에서 `--ensure`를 먼저 실행해 가짜 홈 기본 위치(`~/.local/share/smartthink`)에 빈 `packs/`·`evolution-state.md`를 만들었고, 다른 곳을 고른 뒤 쓰이지 않는 폴더로 남았다. 이 관찰 뒤 lifecycle.md 공통 규약과 ⑤ 0번에 "init은 ⑤ 확정 전까지 `--ensure` 없이 실행"을 추가했다(수정 뒤 재실측은 하지 않음).

임시 디렉터리(`<ROOT>`: 가짜 홈·격리 설정·vault)는 증거 추출 뒤 삭제했다.
