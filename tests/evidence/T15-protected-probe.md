# T15 보호 경로 탐침 (#20 final-review (a)1)

- 목적: vault가 `<repo>/.claude/`·`.git/`(와 비슷한 도구 폴더) 아래일 때 Claude Code가 허용 규칙과 무관하게 쓰기를 막는지 실측한다(#14 P1~P6 방식).
- 실행: 2026-09-27, Claude Code 2.1.283, 헤드리스 `claude --model sonnet -p`(권한 동작은 모델과 무관), 가짜 `HOME`(`<B>/home`), 임시 git 리포 `<B>/home/proj/repo`, `XDG_*`·`SMARTTHINK_VAULT` 제거, 탐침마다 새 격리 `CLAUDE_CONFIG_DIR`.
- 격리 settings.json: `{"permissions":{"defaultMode":"default","allow":["Edit(//<대상 디렉터리>/**)"]}}` 한 줄뿐(대상마다 그 경로만 허용). `-p`는 승인 프롬프트에 답할 수 없어 보호 경로면 거부로 끝난다.
- 입력: "Use the Write tool (not Bash) exactly once to create the file <대상>/probe.txt ... reply WRITE_OK or WRITE_DENIED + error text". 판정은 파일 존재 여부(`WRITTEN`/`NOT_WRITTEN`)와 응답 원문.
- 스크립트 원본은 scratchpad에 있었고 실행 뒤 임시 디렉터리와 함께 지웠다. `<B>`는 임시 루트다.

## 결과 원문 (summary.txt)

```
P1-repo-claude cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/proj/repo/.claude/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/proj/repo/.claude/vault/probe.txt which is a sensitive file. 
P2-repo-git cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/proj/repo/.git/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/proj/repo/.git/vault/probe.txt which is a sensitive file. 
P3-repo-notes cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/proj/repo/notes/vault/**)"]}} result=WRITTEN reply=WRITE_OK 
P4-home-claude cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/.claude/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/.claude/vault/probe.txt which is a sensitive file. 
P5-repo-claude-cwd-other cwd=other rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/proj/repo/.claude/vault2/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/proj/repo/.claude/vault2/probe.txt which is a sensitive file. 
P6-repo-git-cwd-other cwd=other rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/proj/repo/.git/vault2/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/proj/repo/.git/vault2/probe.txt which is a sensitive file. 
P7-plain-git-dir cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/other/notes/.git/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/other/notes/.git/vault/probe.txt which is a sensitive file. 
P8-claude-outside-repo cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/other/stuff/.claude/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/other/stuff/.claude/vault/probe.txt which is a sensitive file. 
P9-vscode cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/other/w/.vscode/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/other/w/.vscode/vault/probe.txt which is a sensitive file. 
P10-idea cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/other/w/.idea/vault/**)"]}} result=NOT_WRITTEN reply=WRITE_DENIED Claude requested permissions to edit <B>/home/other/w/.idea/vault/probe.txt which is a sensitive file. 
P11-dotnotes-control cwd=repo rule={"permissions":{"defaultMode":"default","allow":["Edit(/<B>/home/other/.notes/vault/**)"]}} result=WRITTEN reply=WRITE_OK 
```

## 판정

- 이름이 `.claude`·`.git`·`.vscode`·`.idea`인 폴더가 경로에 있으면 그 아래 Write는 `... which is a sensitive file.`로 거부됐다. 리포 안(P1·P2)이든 밖(P7 리포 아닌 `.git`, P8)이든, cwd가 그 리포든 다른 곳이든(P5·P6) 같았다. `~/.claude`(P4)는 기존 관찰과 같다.
- 대조군: 리포 안 일반 폴더(P3)와 숨김 폴더 `.notes`(P11)는 같은 규칙으로 무프롬프트 Write 성공. 규칙 형식 자체는 유효하다.
- 반영: `resolve-vault.py`의 `ineffective_reason`이 이 네 이름을 `protected-folder`로 판정해 `permission_rule_effective=false`를 낸다(사이클 16). 후보 탐지도 등록 목록이 이런 폴더를 가리키면 뺀다. init ⑤ 직접 입력 경고와 4절 안내, status 진단을 같은 목록으로 맞췄다.
- 한계: 탐침한 이름은 여섯 개(`.claude`·`.git`·`.vscode`·`.idea`·일반·`.notes`)뿐이다. Claude Code의 민감 경로 목록 전체는 확인하지 않았다.
