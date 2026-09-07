# `.data/` - vault 시드 템플릿

이 디렉터리의 파일은 **플러그인에 동봉되는 빈 시드 템플릿**이다. 실제 사용자 상태는 여기가 아니라
`{VAULT}`에 산다. `st init`(또는 vault가 없는 상태에서의 첫 무장)이 vault를 만들 때 이 템플릿을
복사해 쓴다.

> **`.data/`를 사용자 상태 저장소로 쓰지 않는다.** 플러그인 디렉터리는 업데이트 때 통째로 교체될 수
> 있고, 여러 프로젝트가 같은 플러그인을 공유한다. 사용자 데이터가 여기 있으면 조용히 사라지거나
> 남의 것과 섞인다. 읽고 쓰는 대상은 언제나 `{VAULT}` 아래의 사본이다.

동봉 파일:

| 파일 | 역할 |
|---|---|
| `profile.md` | D25 6블록 프로필의 빈 템플릿. 사용자 편집 가능 |
| `evolution-state.md` | v3 진화 상태의 빈 시드(YAML 헤더 + 본문). 자동 관리, 수동 편집 금지 |
| `README.md` | 이 문서 |

---

## `{VAULT}` 레이아웃

```
<VAULT>/
├── profile.md                  D25 6블록. YAML 헤더(version, updated) + 본문
├── evolution-state.md          YAML 헤더(routing_weights, sessions, diversity_h) + 본문
├── evolution-state.v2.bak.md   첫 retain 시 v2 원본 백업
└── packs/<날짜>-<슬러그>/{pack.md, manifest.json}
```

## `{VAULT}` 해석 규칙

우선순위대로 확인한다.

1. `st init`에서 사용자가 지정한 경로
2. 환경 변수 `$SMARTTHINK_VAULT`
3. 기본값 `~/.claude/smartthink-vault`

기존에 쓰던 vault(Obsidian 등)가 있으면 그 안의 `smartthink/` 하위 디렉터리를 쓴다(D29).
이때 **기존 vault를 훼손하지 않는다.** 기존 파일·디렉터리 구조는 그대로 두고 `profile.md`와
`packs/`만 추가한다. 이름이 겹치는 파일을 덮어쓰지 않으며, 겹치면 사용자에게 묻는다.

## 팩 보관 규칙

- 팩은 `packs/<날짜>-<슬러그>/`에 `pack.md` + `manifest.json` 한 쌍으로 저장된다.
- **최근 20개를 유지한다.**
- 20개를 넘으면 **삭제 안내만 하고 자동으로 지우지 않는다.** 어떤 팩이 오래됐는지 알려주고,
  지울지 말지는 사용자가 정한다. 팩은 `--pack <경로>`로 재장전할 수 있는 자산이다.

## v2 → v3 변환

v2의 진화 상태는 YAML 헤더 없는 산문 형식이다. 읽기는 그대로 되고, **첫 `st retain` 때 v3 스키마로
자동 변환된다**(D28).

- 변환 전 원본을 `evolution-state.v2.bak.md`로 백업한다.
- 파일명 `evolution-state.md`는 그대로 유지한다.
- 변환 스크립트: `scripts/migrate-evolution.py`. 기본값은 dry-run이라 인자 없이 실행해도 파일이
  바뀌지 않는다. 실제 쓰기는 `--write`가 있을 때만 일어난다.

## 쓰기 권한

백그라운드 에이전트가 vault에 Write할 때 권한 프롬프트가 부모 세션에 뜰 수 있다. 그래서
`st init`이 `~/.claude/settings.json`에 `Edit(<VAULT>/**)` 허용 규칙을 추가할지 **묻는다**.
**승인했을 때만 기록한다**(D31). 거절해도 무장은 동작하며, 매번 권한 프롬프트가 뜰 뿐이다.

## 프라이버시

- `st init`의 사전 스캔(D23)은 **로컬 읽기 전용이다. 외부로 아무것도 전송하지 않는다.**
- 스캔 범위: 프로젝트 루트(`AGENTS.md`, `CLAUDE.md`, `SOUL.md`, `DESIGN.md`, `.claude/`),
  `~/.claude`(`CLAUDE.md`, `MEMORY.md`), git log 50건, 사용자가 지정한 노트 디렉터리.
- **타 런타임의 설정 디렉터리(`~/.codex` 등)는 스캔 대상이 아니다.**
- 스캔 결과는 `profile.md`에 요약으로만 남고, 원문을 복사해 오지 않는다.
