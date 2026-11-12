# smartthink 에이전트 지침

이 파일이 리포 지침의 실물이다. `CLAUDE.md`는 이 파일을 임포트하는 한 줄이다.
구조·절차·결정은 여기에 옮겨 적지 않고 `README.md`, `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`에 둔다.

## 목표

SmartThink는 Claude Code 세션을 그 작업의 전문가로 무장시키는 플러그인이다(`/st`).
레퍼런스 원문을 그대로 싣고(요약하지 않음), 고른 모듈만 싣고, 브리핑에서 턴을 끝낸다.
변경을 고를 때는 이 세 원칙을 깨지 않는지 먼저 본다(`docs/ARCHITECTURE.md` 2절).

## 확인 명령

- `python3 scripts/check-structure.py`
- `python3 -m unittest discover -s tests -p 'test_*.py'`
- `python3 scripts/check-structure.py --strict`

## README 길잡이

`README.md`는 자동으로 실리지 않는다. 아래 일을 하기 전에 해당 절을 직접 읽는다.
- 설치·제거 경로를 건드릴 때: "Install", "Alternative: `install.sh`", "Uninstall"
- 서브커맨드·플래그를 바꿀 때: "Usage", "Subcommands", "Flags"
- 게이트·armorer·브리핑 흐름을 바꿀 때: "How a run goes"
- 팩 절 제목이나 manifest를 바꿀 때: "What a pack is"
- 진화 상태·retain을 바꿀 때: "Evolution"
- 도구가 없을 때의 폴백을 바꿀 때: "Environment differences (graceful degradation)"
- 요구 환경이 바뀔 때: "Requirements"

## 코드가 오해를 부르는 곳

- `skills/smartthink/references/`의 모듈 9개는 내용이 얼어 있다. 한 바이트라도 바꾸면 `references/index.json`의 SHA-256과 기존 팩 검증이 깨진다.
  바꿔야 하면 `python3 scripts/build-index.py`로 색인을 같은 변경에서 다시 만든다. 한국어 모듈을 번역하지 않는다.
  같은 폴더의 `analysis-method.md`, `lifecycle.md`, `thinker-prompt.md`, `armorer-prompt.md`는 모듈이 아닌 절차 문서라 고쳐도 된다.
- 일부 지시는 일부러 두 파일에 중복돼 있다. 한쪽을 고치면 다른 쪽도 같은 변경에서 고친다(`CONTRIBUTING.md` "Wiring contracts" 표).
  예: 팩 절 제목과 manifest 필드는 `skills/smartthink/SKILL.md`와 `agents/st-armorer.md`, 보고서 폴백은 `agents/st-thinker.md`와 `references/thinker-prompt.md`.
- 방법론 공식·스키마는 `references/analysis-method.md` 한 곳에만 쓴다. 다른 파일에 다시 적지 않는다.
- `skills/smartthink/.data/`는 빈 시드 템플릿이다. 채운 `profile.md`, `evolution-state.md`를 커밋하지 않는다. 실제 상태는 리포 밖 vault에 있다.
- `SKILL.md`, `references/lifecycle.md`에 새 Bash 지시를 넣으면 `check-structure.py` D절이 막는다.
  규칙 묶음(resolve-vault, assemble-pack)으로 바꾸거나, 예외면 `tests/evidence/26-bash-inventory.md`와 `LIFECYCLE_EXCEPTION_RE`에 사유와 함께 등록한다.
- `migrate-evolution.py`는 기본이 dry-run이고 `--write`에서만 쓴다.

## 공개 리포 규칙

- 이 리포는 공개다. `check-structure.py` G절이 리포의 `.md`·`.py`에서 em dash와 사적 패턴(절대 홈 경로, 개인 vault 경로, 사설 호스트명)을 잡는다. 이 파일도 대상이다.
- 사용자 문구를 바꾸면 `README.md`와 `README.ko.md`를 함께 고친다. 두 파일은 절 구성이 같아야 한다.
- 시험은 임시 `HOME`과 임시 `SMARTTHINK_VAULT`로 돌린다. 실제 vault와 실제 `~/.claude`를 건드리지 않는다.

## 설치본과 작업 트리

- `install.sh`는 스킬·에이전트·커맨드를 `~/.claude/` 아래에 이 리포를 가리키는 심링크로 건다. 그래서 설치된 `/st`는 그 체크아웃의 현재 브랜치 코드를 돈다.
  워크트리에서 바꾼 코드를 시험할 때는 `claude --plugin-dir <워크트리>`로 띄우고 `/smartthink:smartthink`로 부른다. 이름 없는(bare) `/smartthink`와 `st-armorer`는 심링크가 가리키는 체크아웃 코드를 탈 수 있다.
- 행동 시험 시나리오와 판정 기준은 `tests/gates.md`, 증거 파일은 `tests/evidence/`에 둔다.
