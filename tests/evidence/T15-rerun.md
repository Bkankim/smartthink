# T15 재실측 (final-review 20260927-032439 (a)3)

- 실행일: 2026-09-27, 브랜치 st-20-vault-location(1b01df4, origin/main #21 병합 d104727 포함), Claude Code 2.1.283, `--model opus`, default 권한 모드(상태줄 `⏸ manual mode on`).
- 환경: 격리 `CLAUDE_CONFIG_DIR=<ROOT>/cfg`, 가짜 `HOME=<ROOT>/home`, `XDG_DATA_HOME`·`XDG_CONFIG_HOME`·`SMARTTHINK_VAULT` 제거, 인증은 자식 env에만 주입(값 미기록). 호출은 `/smartthink:smartthink`, Base directory는 워크트리(아래 도구 목록의 `SKILL` 줄).
- 픽스처: 첫 실측과 같다(안 쓰는 기본 vault 1파일 + 리포 30개 작업 폴더, 둘 다 Obsidian 등록 목록. 진짜 보관소는 이름 신호만 있는 git 리포 `~/workspace/notes`).
- 프롬프트는 20~30초 간격 화면 읽기로 직접 기록·응답했다. 코디네이터 개입 없음.

## 사전 허용 목록 (격리 settings.json 초기 원문)

```json
{
  "permissions": {
    "defaultMode": "default",
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "WebSearch",
      "WebFetch",
      "Skill",
      "Agent",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(head:*)",
      "Bash(wc:*)",
      "Bash(test:*)",
      "Bash(python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py:*)",
      "Bash(python3 \"<HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py\":*)",
      "Bash(python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/check-structure.py:*)",
      "Bash(python3 \"<HOME>/workspace/smartthink-st-20-vault-location/scripts/check-structure.py\":*)"
    ],
    "deny": [
      "Read(/<HOME>/.claude/smartthink-vault/**)",
      "Edit(/<HOME>/.claude/smartthink-vault/**)",
      "Read(/<HOME>/.local/share/smartthink/**)",
      "Edit(/<HOME>/.local/share/smartthink/**)",
      "Edit(/<HOME>/.config/smartthink/**)"
    ]
  }
}```

init 승인 뒤 `permissions.allow`에 추가된 두 줄(설정 파일 diff 요지):

```
+ Edit(~/workspace/notes/smartthink/**)
+ Bash(python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/assemble-pack.py *)
```

포인터(가짜 홈 `~/.config/smartthink/vault-pointer`):

```
<ROOT>/home/workspace/notes/smartthink
```

가짜 홈 기본 위치 `~/.local/share/smartthink`는 init 뒤에도 없다(`ls: ... No such file or directory`). ⑤ 0번 수정대로 init이 경로 확정 전에 `--ensure`를 하지 않았다(첫 실측의 빈 폴더 잔존 해소).

## ⑤ 후보 제시 화면 (터미널 캡처 원문)

```
  ⑤ vault 경로. 프로필과 팩을 저장할 곳입니다. 탐지된 후보를 보여 드리니 하나를 골라 주세요. 미리 골라 둔 항목은
  없습니다. 탐색은 끝까지 마쳤습니다.
  1) ~/Documents/Obsidian Vault
     근거: Obsidian 등록 목록, .obsidian 폴더, 이름에 "vault"  |  최근 수정 2026-09-26  |  파일 약 1개  |  git 아님
     ⚠ 파일이 거의 없음 (쓰지 않는 기본 vault일 수 있음)
     → 저장 위치: ~/Documents/Obsidian Vault/smartthink/
  2) ~/workspace
     근거: Obsidian 등록 목록, .obsidian 폴더  |  최근 수정 2026-09-26  |  파일 약 72개  |  git 아님
     ⚠ 코드 리포 여러 개를 담은 작업 폴더의 루트
     → 저장 위치: ~/workspace/smartthink/
  3) ~/workspace/notes
     근거: 폴더 이름 "notes"  |  최근 수정 2026-09-26  |  파일 약 40개  |  git 리포
     경고 없음
     → 저장 위치: ~/workspace/notes/smartthink/
  4) 새로 만들기 (기본값)  ~/.local/share/smartthink/
  5) 직접 입력 (절대경로)
  기존 보관소를 고르면 그 안에 smartthink/ 폴더만 새로 만듭니다. 이미 있는 파일은 건드리지 않습니다. 이 문항을 건너뛰면
  4번 새로 만들기가 됩니다.
  ⑥ 리서치 기본값. 무장할 때마다 웹 리서치를 켤까요? (Enter = 켜기) 끄면 매번 --nosearch를 붙인 것처럼 동작합니다.
```

## 프롬프트 기록 (발생 순서, 응답)

```
init P1 Bash compound readlink; ls scripts (compound, not pre-allowed) -> 1
init P2 Bash compound pre-scan ls; ls ~/.claude; git log (git not pre-allowed) -> 1
init P3 Bash ls <fake default vault> 2>&1 (ls outside cwd prompts despite Bash(ls:*)) -> 1
init OBS --candidates ran without prompt (pre-allowed)
init P4 Bash git -C notes rev-parse; ls -a (git not pre-allowed) -> 1
init P5 Bash echo env; ls ~/.config/smartthink; date (compound+expansion) -> 1
init P6 Bash mkdir -p ~/.config/smartthink -> 1
init P7 Write ~/.config/smartthink/vault-pointer (init, expected) -> 1
init P8 Write vault/profile.md (init, before rule, expected) -> 1
init P9 Write notes/.gitignore (approved B, expected) -> 1
init P10 Bash compound resolve --permission-rule; assemble-pack --permission-rule; ls vault (compound, assemble-pack not pre-allowed) -> 1
init P11 Bash cat settings | python3 -m json.tool (pipe) -> 1
init P12 Bash cp settings.json .bak -> 1
init P13 Edit settings.json add 2 allow rules (approved) -> 1
init P14 Bash python3 -m json.tool validate -> 1
--- arm session (new) ---
arm A1 [main] Bash compound readlink; ls scripts -> 1
arm A2 [main] Bash compound ls vault; cat index.json -> 1
arm A3 [armorer] Bash compound ls scripts; ls packs -> 1
arm OBS pack.md created 03:58 by Write with NO prompt
arm OBS manifest.json created and pack.md rewritten 04:03 with NO prompt
arm A4 Bash compound ls pack; grep headings (verification read) -> 1
--- arm run 2 (same session, no --digest, exercises assemble-pack) ---
arm2 A5 [armorer] Bash compound grep; ls packs (read) -> 1
arm2 A6 [armorer] Bash compound ls scripts; grep check-structure (read) -> 1
arm2 A7 [main] Bash compound ls pack; grep headings (verification read) -> 1
```

## 판정: PASS

- ⑤: 후보 3개(경고 2개 포함)와 새로 만들기·직접 입력이 떴고, 모델이 "미리 골라 둔 항목은 없습니다"라고 밝혔다. `--candidates`는 사전 허용 규칙으로 프롬프트 없이 실행됐다.
- 3번 선택 → `~/workspace/notes/smartthink/`, `.gitignore`에 `smartthink/packs/`, 포인터 기록, 권한 규칙 두 개(`Edit(~/workspace/notes/smartthink/**)`, `Bash(python3 <WT>/scripts/assemble-pack.py *)`) 승인 설치.
- **새 세션 무장 2회에서 vault 쓰기 관련 프롬프트 0회.**
  - 1회차(`--nosearch --digest`): armorer의 pack.md Write 2회, manifest.json Write 1회가 모두 무프롬프트(파일 생성 시각 03:58·04:03, 응답한 프롬프트 없음).
  - 2회차(`--nosearch`, 예산 60000으로 원문 모듈 1개): pack.md Write, `assemble-pack.py` Bash 1회(5절 원문 조립), manifest.json Write가 모두 무프롬프트.
- init 중 Write/Edit 프롬프트(P7 포인터, P8 profile.md, P9 .gitignore, P13 settings.json)는 규칙 설치 전이거나 vault 밖 쓰기라 판정 대상이 아니다.

## 남은 프롬프트 (종류·원인)

- 무장 7회(A1~A7)는 모두 읽기용 Bash이고 vault 쓰기와 무관하다.
  - 원인: 일곱 번 모두 `;`로 이은 복합 명령(`readlink ...; ls ...`, `ls ...; cat ...`, `ls ...; grep ...`)이고 작업 디렉터리 밖 경로를 읽는다. Claude Code는 복합 명령의 각 부분이 모두 허용돼야 통과시키는데 `readlink`·`grep`은 사전 허용 목록에 없고, `Bash(ls:*)`·`Bash(cat:*)`가 있어도 cwd 밖 읽기는 따로 묻는다(선택지 "allow reading from <dir>").
- init 10회(P1~P6, P10~P12, P14)도 같은 두 원인(복합 명령, cwd 밖 읽기, `git`·`mkdir`·`cp`·파이프 `python3 -m json.tool` 미허용)이다.
- 줄이는 방법은 모델이 단일 명령·Read 도구를 쓰게 하는 지침이나 읽기 명령 사전 허용이며, 이 이슈 범위 밖이다.

## 도구 호출 목록 (세션 jsonl에서 추출)

`=== ...jsonl` 순서: init 세션, 무장 세션 메인, 무장 세션의 armorer 2개. `ERROR`는 도구 오류 결과(기본 위치가 아직 없어서 난 `ls` 실패 1건).

```
=== 0a4af937-608d-4732-a254-2236b0364d27.jsonl
SKILL Base directory for this skill: <HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/lifecycle.md"}
TOOL Bash {"command": "readlink <HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink; ls <HOME>/workspace/smartthink-st-20-vault-location/scripts"}
TOOL Bash {"command": "ls -la <ROOT>/proj; ls ~/.claude/CLAUDE.md ~/."}
TOOL Bash {"command": "python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py"}
TOOL Bash {"command": "ls -la <ROOT>/home/.local/share/smartthink 2>&"}
ERROR Exit code 1 ls: <ROOT>/home/.local/s
TOOL Bash {"command": "python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py --candidates"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/.data/profile.md"}
TOOL Bash {"command": "git -C \"<ROOT>/home/workspace/notes\" rev-parse"}
TOOL Bash {"command": "echo \"XDG_CONFIG_HOME=$XDG_CONFIG_HOME SMARTTHINK_VAULT=$SMARTTHINK_VAULT HOME=$HOME\"; ls -la ~/.config/smartthink 2>&1; date -Iseconds"}
TOOL Bash {"command": "mkdir -p ~/.config/smartthink"}
TOOL Write {"file_path": "<ROOT>/home/.config/smartthink/vault-pointer"}
TOOL Bash {"command": "python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py --ensure"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/smartthink/profile.md"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/.gitignore"}
TOOL Bash {"command": "python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py --permission-rule; python3 <HOME>/workspace/smartthink-st-20-vault-location/sc"}
TOOL Bash {"command": "cat <ROOT>/cfg/settings.json 2>&1 | python3 -m"}
TOOL Bash {"command": "cp \"<ROOT>/cfg/settings.json\" \"/private/tmp/cl"}
TOOL Read {"file_path": "<ROOT...>"}
TOOL Edit {"file_path": "<ROOT>/cfg/settings.json"}
TOOL Bash {"command": "python3 -m json.tool \"<ROOT>/cfg/settings.json"}
=== 0591c49f-bfee-4907-815c-b188d7d725a5.jsonl
SKILL Base directory for this skill: <HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink
TOOL Bash {"command": "readlink <HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink; ls <HOME>/workspace/smartthink-st-20-vault-location/scripts/"}
TOOL Bash {"command": "python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/resolve-vault.py --ensure"}
TOOL Bash {"command": "ls -la <ROOT>/home/workspace/notes/smartthink "}
TOOL Read {"file_path": "<ROOT...>"}
TOOL Read {"file_path": "<ROOT...>"}
TOOL Agent {"subagent_type": "smartthink:st-armorer", "description": "SmartThink 무장 팩 생성"}
TOOL Bash {"command": "ls <ROOT>/home/workspace/notes/smartthink/pack"}
TOOL Read {"file_path": "<ROOT...>"}
SKILL Base directory for this skill: <HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink
TOOL Agent {"subagent_type": "smartthink:st-armorer", "description": "SmartThink 무장 팩 생성"}
TOOL Bash {"command": "ls <ROOT>/home/workspace/notes/smartthink/pack"}
TOOL Read {"file_path": "<ROOT...>"}
=== agent-a9c0f597b0511ba30.jsonl
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/core-engines.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/cognitive-arsenal.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/triz-innovation.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/meta-cognition.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/execution-velocity.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/analysis-method.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/core-engines.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/cognitive-arsenal.md"}
TOOL Bash {"command": "ls <HOME>/workspace/smartthink-st-20-vault-location/scripts/ ; ls \"<ROOT...>"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/scripts/check-structure.py"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/scripts/check-structure.py"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/scripts/check-structure.py"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/index.json"}
TOOL Bash {"command": "date +%Y-%m-%dT%H:%M:%S%z"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/smartthink/packs/2026-09-27-library-seat-reservation-guide/pack.md"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/smartthink/packs/2026-09-27-library-seat-reservation-guide/pack.md"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/smartthink/packs/2026-09-27-library-seat-reservation-guide/manifest.json"}
=== agent-adabd439f5162c3ad.jsonl
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/core-engines.md"}
TOOL Bash {"command": "grep -n \"Step 0.5\" <HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/analysis-method.md; ls <ROOT...>"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/core-engines.md"}
TOOL Read {"file_path": "<HOME>/workspace/smartthink-st-20-vault-location/skills/smartthink/references/analysis-method.md"}
TOOL Bash {"command": "ls <HOME>/workspace/smartthink-st-20-vault-location/scripts/; grep -n \"3\\. 리서치\\|research\\|생략\" <HOME>/workspace/smartthink-st-20-vault-location/scripts/check-str"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/smartthink/packs/2026-09-27-sports-center-waitlist-guide/pack.md"}
TOOL Bash {"command": "python3 <HOME>/workspace/smartthink-st-20-vault-location/scripts/assemble-pack.py --pack-dir \"<ROOT...>"}
TOOL Write {"file_path": "<ROOT>/home/workspace/notes/smartthink/packs/2026-09-27-sports-center-waitlist-guide/manifest.json"}
```
