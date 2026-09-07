[English](README.md) | 한국어

# SmartThink

**천재적 사고 엔진 시스템** - [Claude Code](https://docs.anthropic.com/en/docs/claude-code)를 위한 전략적 사고 엔진.

9개 사고 프레임워크(81개 멘탈 모델, 12개 운영 엔진, TRIZ 발명 원리, 안티프래질 전략 등)와 Cynefin 상황 진단을 결합해 어떤 주제든 깊이 있는 창의적 분석을 제공합니다. 스킬 하나와 전용 서브에이전트 둘로 구성됩니다. 분석 본체는 자기 컨텍스트에서 돌고, 검색 정찰 에이전트가 현실 데이터를 공급합니다.

---

## 빠른 시작

### 1. 설치

```bash
git clone https://github.com/Bkankim/smartthink.git
cd smartthink
./install.sh
```

설치 스크립트는 심링크 3개(`~/.claude/skills/smartthink`, `~/.claude/agents/st-thinker.md`, `~/.claude/agents/st-searcher.md`)를 만들고 `~/.claude/smartthink-vault/`에 빈 진화 상태 파일을 시드합니다.

### 2. 새 Claude Code 세션 열기

```bash
claude
```

> **중요**: 설치 후 **새 세션**을 시작해야 스킬과 에이전트가 인식됩니다.

### 3. 실행

```
/smartthink 1인 기업의 확장 전략
```

`/st`는 짧은 별칭입니다. 주제를 진단하고, 프레임워크를 고르고, 검색 데이터를 모은 뒤 6~10개의 실행 가능한 아이디어가 담긴 분석을 돌려줍니다.

---

## 3가지 모드

| 플래그 | 모드 | 실행 위치 | 인터랙션 |
|------|------|----------|---------|
| (없음) | **Agent** (기본값) | `st-thinker` 서브에이전트 | 분석 중 없음, 반환 후 피드백 루프 |
| `--deep` | **Deep** | 메인 에이전트 | 결정 지점마다 확인 |
| `--lite` / `--light` | **Light** | 메인 에이전트, 레퍼런스 미로딩 | 없음 |

`--nosearch`는 어느 모드에서든 웹 검색을 건너뜁니다. 검색은 **모든 모드에서 기본 실행**됩니다.

### Agent 분석 (기본값)

분석 전체를 `st-thinker` 서브에이전트(STSA)에 위임합니다. 레퍼런스 모듈을 자기 컨텍스트에 로딩하므로 메인 세션은 가볍게 유지됩니다. 반환 후에도 백그라운드에 살아 있어서, 피드백을 주면 그 자리에서 수정하고 "확정"이라고 하면 최종본 기준으로 진화 상태를 기록합니다.

```
/smartthink AI 스타트업에서 네트워크 효과를 만드는 방법
```

### Deep 분석

메인 에이전트가 직접 분석하며 인터랙션 포인트마다 확인합니다. Cynefin 경계, 모듈 선택, 대량 레퍼런스 로딩 전 검색 데이터팩 확인이 그 지점입니다.

```
/smartthink --deep 1인 기업의 수익 모델 설계
```

### Light 분석

Cynefin 진단과 제1원리 분해만 사용하는 경량 분석입니다. 레퍼런스 모듈을 로딩하지 않습니다. `--nosearch`가 없으면 검색 정찰은 실행됩니다.

```
/smartthink --lite 사이드 프로젝트 아이디어
/smartthink --lite --nosearch 사이드 프로젝트 아이디어
```

레거시 접두어(`agent <주제>`, `light <주제>`, `search <주제>`)도 별칭으로 인식되지만, 정본은 `--` 플래그입니다.

---

## 동작 원리

```
입력: /smartthink [--deep|--lite] [--nosearch] 주제
         ↓
    ┌─────────────────────────────────────┐
    │  메인 에이전트                        │
    │  1. Cynefin 진단                     │
    │  2. 주제 분류 + 모듈 추천             │
    │  3. st-searcher 스폰 ──► 데이터팩     │  (2K 토큰 이내, 수치-출처 짝)
    │  4. 모드 분기                        │
    └──────────┬──────────────────────────┘
               ↓
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
  Agent       Deep          Light
  st-thinker  메인 에이전트   메인 에이전트
  (백그라운드  (인터랙티브)   (레퍼런스 없음)
   + 피드백
   루프)
```

- **st-searcher** (Sonnet): 원문 검색 결과를 자기 창에서 소화하고 압축 데이터팩만 반환합니다. 출처가 짝지어진 정량 테이블, 플레이어 목록, 트렌드와 반대 신호 1개 이상, 출처 URL. 원문 페이지는 메인 컨텍스트에 들어오지 않습니다.
- **st-thinker** (세션 모델 상속, 30턴 상한): `skill/references/analysis-method.md`의 파이프라인을 실행합니다. 자기점검, 모듈 로딩, 다층 분석, 교차 엔진 합성, 아이디어 생성, Top 3 유니콘 평가, Next Steps.

---

## 진화 시스템

SmartThink는 세션마다 학습합니다.

- 효과적이었던 사고 패턴은 **인사이트**로 저장 (최대 10슬롯)
- 부족했던 관점은 **갭**으로 추적 (최대 5슬롯)
- 모듈 다양성을 모니터링해 한 프레임워크 편식을 막음
- 자기점검 단계가 진화 상태가 결론을 선점하는 것을 막음

진화 데이터는 **리포 바깥** `~/.claude/smartthink-vault/evolution-state.md`에 저장됩니다(`SMARTTHINK_VAULT`로 변경 가능). 개인 인사이트가 clone한 리포에 기록되는 일은 없습니다. `skill/.data/evolution-state.md`는 설치 시 시드하는 빈 템플릿일 뿐입니다.

Agent 모드에서는 최종본을 확정한 뒤에만 vault를 갱신하므로, 피드백으로 결론이 바뀌었는데 수정 전 인사이트가 박제되는 일이 없습니다.

---

## 사고 모듈

| 모듈 | 핵심 프레임워크 |
|------|---------------|
| 핵심 엔진 | 제1원리, 비대칭 기회, 네트워크 효과, 시장 창조, 해자 구축, 반직관 검증, 가치 포착, 타이밍 인텔리전스, 복합 우위, 생태계 설계, 역전 사고, 롤라팔루자 감지 |
| 유니콘 플레이북 | $0→$1B 비즈니스 빌딩 (6단계) |
| 현실 왜곡 | 제약 역전, 카테고리 창조, 시간적 차익거래 |
| 인지 무기고 | 9개 분야 81개 멘탈 모델 |
| 패턴 합성 | 교차 도메인 패턴 인식, 약한 신호 감지 |
| 실행 속도 | OODA 루프, 의사결정 프레임워크, 블리츠스케일링 |
| 안티프래질 전략 | 바벨 전략, 옵셔널리티, 블랙 스완 포지셔닝 |
| TRIZ 혁신 | 40 발명 원리, 모순 해결 |
| 메타인지 | 재귀적 자기개선, Wardley 매핑, 사용자 프레임 편향 진단 |

주제 유형(아이디어 발굴, 전략 수립, 문제 해결, 의사 결정, 체계적 발명 등)에 따라 2~3개 모듈을 자동 선택합니다.

---

## 리포 구조

```
skill/            스킬 본체 (SKILL.md + references/) - ~/.claude/skills/smartthink 로 심링크
agents/           st-thinker.md, st-searcher.md      - ~/.claude/agents/ 로 심링크
scripts/          check-structure.py                 - 66항목 배선 검사 (skill <-> agents <-> prompt)
install.sh        심링크 생성 + vault 시드
uninstall.sh      심링크 제거, vault는 보존
```

`skill/`이나 `agents/`를 수정했으면 구조 검사를 돌리세요.

```bash
python3 scripts/check-structure.py             # 리포 사본 검사
python3 scripts/check-structure.py --installed # Claude Code가 실제로 로딩하는 경로 검사
```

---

## 요구사항

- 커스텀 에이전트를 지원하는 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- macOS 또는 Linux (Windows는 [WSL2](https://learn.microsoft.com/en-us/windows/wsl/))
- 선택: 일반 fetch를 차단하는 사이트용 `insane-search` 스킬. 없으면 `st-searcher`가 차단된 소스를 건너뜁니다.

## 삭제

```bash
cd smartthink
./uninstall.sh
```

진화 vault는 그대로 남습니다. 완전 초기화는 `~/.claude/smartthink-vault/`를 직접 삭제하세요.

## 라이선스

MIT
