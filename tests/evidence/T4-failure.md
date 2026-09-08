# T4 실패 기록

- 실행일: 2026-09-08 02:23~02:37 (+09:00)
- 임시 vault: [REDACTED]/smartthink-v3-gates-20260908-020434
- 입력: `/st --digest --budget 60000 지역 행사 자원봉사자 배치 방식을 검토해줘` (Skill "smartthink:smartthink", armorer = smartthink:st-armorer, Digest=true 전달)

## 실패한 체크 항목 (3/5)

| 기준 | 실제 | 결과 |
|---|---|---|
| 5절에 모듈마다 `<!-- MODULE-DIGEST: <파일명>.md -->` 마커 | 마커 0개. `### 5.1 인지 무기고 (cognitive-arsenal.md) 증류본` 식 소제목만 사용 | FAIL |
| 5절에 MODULE-BEGIN/sha256/MODULE-END 없음, 모드 혼합 없음 | 원문 마커 0개 (혼합 없음) | PASS |
| manifest.modules 문자열 배열, digest 전용 필드 없음 | 문자열 5개, 추가 필드 없음 (단 4번째 항목이 "핵심 엔진 (제1원리 분해 #1, 역전 사고 #11)"로 엔진 주석 포함) | PASS |
| est_tokens.pack ≤ 20000 이고 check-structure --pack exit 0 | est_tokens.pack = **32002**; `--pack` exit 1, `--pack --digest` exit 1 (MODULE-DIGEST 마커 부재) | FAIL |
| 브리핑(1절)에 증류본 사실 한 줄 명시 | 1절 본문에 없음. 팩 머리말(1절 밖) 2행에 "digest 모드"만 표기 → 메인이 1절만 그대로 출력하므로 사용자에게 보이지 않음 | FAIL |

## 실제 출력

```
$ python3 scripts/check-structure.py --pack <팩> --digest
FAIL H. pack: section 5 verbatim hash integrity: .../pack.md: --digest pack but section 5 has no '<!-- MODULE-DIGEST: <file> -->' marker
exit 1
```
manifest 발췌: `"est_tokens": { "pack": 32002, "agent": 175000 }`, pack.md 70,404바이트(5절 28,421바이트 ≈ 12.9K 토큰, 나머지 절 ≈ 19K 토큰).

## 원인 (추정, 코드 미수정)

1. **MODULE-DIGEST 마커 규격이 armorer에 배선돼 있지 않다.** 마커 형식은 `references/analysis-method.md` 458~463행과 `scripts/check-structure.py`에만 있고, `agents/st-armorer.md`(117행)는 "증류본으로 대체, 절 머리에 1줄 명시, 해시 면제"만 지시한다. armorer는 analysis-method.md를 Step 0.5(편향 점검)만 Read하므로 마커 규격을 볼 경로가 없다. SKILL.md의 `--digest` 절도 마커를 언급하지 않는다.
2. **20K 상한의 적용 범위가 갈린다.** SKILL.md·st-armorer.md는 "총 10~20K"를 5절 증류본 목표로 쓰고(5절 실측 ≈12.9K로 충족), 게이트 비용식도 5절만 15K로 잡는다. 반면 T4 기준과 `est_tokens.pack`은 pack.md 전체(1~6절)를 잰다. 리서치 ON에서 3절이 86행, 4절이 100행이면 전체가 20K를 넘는 것이 구조적이다.
3. **증류본 명시 위치.** armorer 지시는 "절 머리(5절)에 1줄 명시"이고, 1절 브리핑 구성 항목(활성 프레임/규칙/과거 인사이트/편향/다음 단계)에는 digest 표기 슬롯이 없다. SKILL.md `--digest` 절의 "브리핑에 1줄로 명시하라"와 armorer 정의가 어긋난다.

## 사용한 명령 · 산출물

- `python3 scripts/check-structure.py --pack [REDACTED]/smartthink-v3-gates-20260908-020434/packs/2026-09-08-event-volunteer-deployment-review [--digest]` → 둘 다 exit 1 (T4-structure-check.txt)
- 산출물: tests/evidence/T4-pack.md, T4-manifest.json (경로 치환)
