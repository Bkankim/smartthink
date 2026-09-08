# T2 실패 기록

- 실행일: 2026-09-08 02:11~02:19 (+09:00)
- 임시 vault: [REDACTED]/smartthink-v3-gates-20260908-020434
- 입력: `/st --budget 60000 공공 도서관의 예약 대기열 안내 화면을 개선하는 실행 계획을 설계해줘` (Skill "smartthink:smartthink")

## 실패한 체크 항목

"`pack.md`에 정확히 `## 1. 무장 브리핑`, `## 2. 작업 해석`, `## 3. 리서치 합성`, `## 4. 작업 적용 레이어`, `## 5. 레퍼런스 원문`, `## 6. 과거 인사이트와 프로필` 6개 절 제목이 있다."

## 실제 출력

```
$ grep -n '^## [0-9]\. ' pack.md | grep -v MODULE
7:## 1. 무장 브리핑
42:## 2. 작업 해석
60:## 4. 작업 적용 레이어
84:## 5. 레퍼런스 원문
2044:## 6. 과거 인사이트와 프로필
```
`## 3. 리서치 합성` 없음. manifest: `"research": false`, `"budget": "60000"`.

## 원인 (추정, 코드 미수정)

1. 5개 추천 모듈 합계(≈132K)가 `--budget 60000`을 크게 넘어 SKILL.md 4단계 절삭 순서를 적용했다. 순서 1이 "리서치 축소 → OFF"이므로 리서치가 먼저 꺼지고, 그 다음 순서 2로 모듈 3개(메타인지·실행 속도·인지 무기고)를 뺐다. 모듈 제외 후에는 핵심 엔진+TRIZ+리서치(≈58K)가 60K 안에 들어오지만, 절삭 순서에는 "여유가 생기면 앞 단계 절삭을 되돌린다"는 규칙이 없어 리서치는 OFF로 남았다.
2. SKILL.md 팩 명세와 st-armorer.md는 `Research=OFF`일 때 3절 생략을 지시하고, `check-structure.py --pack`도 `research=false`면 3절 부재를 허용한다(H. section titles PASS). 즉 팩은 스킬 계약을 지켰지만 T2 통과 기준(6절 고정)과 어긋난다.
3. 결과적으로 5개 모듈 추천 + `--budget 60000` 조합에서는 리서치 3K가 가장 싼 항목인데 항상 첫 번째로 잘린다. 테스트 시나리오가 전제한 "6절 팩"은 이 절삭 순서로는 나올 수 없다.

## 부수 관찰 (판정 외)

- `Agent(subagent_type: "st-armorer")`는 `--plugin-dir` 세션에서 "not found". `smartthink:st-armorer`로만 스폰된다. SKILL.md 5a를 문자 그대로 따르면 general-purpose 폴백으로 내려간다(T11에 재기록).
- armorer가 기록한 est_tokens.pack=61190은 예산 60000을 1.2K 넘겼다. armorer는 자체 판단으로 4절을 깎지 않았다고 보고했다.
- 증거 복사 후 `check-structure.py`(리포 전체)는 G. hygiene(em dash)에서 tests/evidence/T2-pack.md를 잡아 exit 1이 된다. 5절 원문의 레퍼런스 em dash가 원인이며 팩 계약 위반은 아니다.

## 사용한 명령 · 산출물

- `python3 scripts/check-structure.py --pack [REDACTED]/smartthink-v3-gates-20260908-020434/packs/2026-09-08-library-queue-notice-plan` → 1차 exit 0 (35 passed)
- 산출물: [REDACTED]/smartthink-v3-gates-20260908-020434/packs/2026-09-08-library-queue-notice-plan/{pack.md,manifest.json} → tests/evidence/T2-pack.md, T2-manifest.json (경로 치환)
