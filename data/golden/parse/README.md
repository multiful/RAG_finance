# data/golden/parse/README.md

> **파일명**: data/golden/parse/README.md  
> **최종 수정일**: 2026-04-07  
> **문서 해시**: SHA256:fd7e8850290f52dc29e9fe26ac6d785229bf71cbb1374729efdd630731256aec  
> **문서 역할**: Parse 단계 골든셋·실행 안내 (Exp-1 평가)  
> **문서 우선순위**: 93  
> **연관 문서**: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, EVALUATION_GUIDELINE.md, RAG_PIPELINE.md, app/evaluation/parse_golden.py  
> **참조 규칙**: 골든 스키마·지표 변경 시 본 문서와 `parse_golden.py`를 같은 PR에서 갱신한다.

---

# Parse 단계 골든셋 (Exp-1)

`paper_Indexing` / Exp-1(**Parse 개선**)용. **Retriever·생성은 범위 밖**이며, 파서 산출물만 평가한다.

## 파일

| 파일 | 설명 |
|------|------|
| `golden_parse.jsonl` | 한 줄 = JSON 한 객체(아래 스키마). 팀이 직접 채움. |
| `fixtures/` | 평가용 PDF/HTML 등(저작권·비밀 주의). Git에 넣지 않을 수 있음 — `.gitignore` 권장. |
| `example_item.json` | 스키마 예시(참고). |

### 한국 PDF 샘플 자동 수집

저장소 루트에서:

```bash
python scripts/download_kr_pdf_fixtures.py 8
```

- **기본(`--mode regulatory`)**: 국가법령정보센터 `flDownload`(행정규칙·안내 PDF) 1건 + 금융위 RSS **입법·정책(`0111`)·공고(`0114`)**에서 채용·공무원 공고를 제외하고 규제·금융 키워드로 정렬한 PDF. 부족 시 `0112`(금융소비자 유의)로 보완.
- **`--mode general`**: 금융위 보도·공고 PDF + 한국은행 보도 + 금감원 목록의 PDF(이전 혼합 수집).

`fixtures/`에 저장하고 `golden_parse.jsonl`을 덮어쓴다. 행정규칙 `flSeq` 목록은 `scripts/download_kr_pdf_fixtures.py` 상단 `_LAW_GO_KR_FL_SEQS`에서 확장할 수 있다.

## 스키마 요약 (`ParseGoldenItem`)

- `id`: 고유 ID  
- `file_path`: 저장소 루트 기준 상대 경로(예: `data/golden/parse/fixtures/foo.pdf`)  
- `file_type`: `pdf` \| `html`  
- `reading_order_anchors`: **정답 순서**로 등장해야 하는 부분 문자열(페이지 경계·절머리 검증용)  
- `table_gold`: 표 검증 — `min_rows`, `min_cols`, `header_substrings`(모두 포함되면 통과 후보)  
- `structure_checks`: `must_appear_before`: `[A, B]` → 파싱 전체 텍스트에서 A가 B보다 **먼저** 나와야 함  
- `chunk_quality_unit_groups`: 각 내부 리스트의 구문들이 **같은 청크**에 들어가야 이상적(다운스트림 청킹 민감도)

## 실행

저장소 루트에서:

```bash
cd app/backend
python ../../scripts/run_parse_golden_eval.py --golden ../../data/golden/parse/golden_parse.jsonl
```

결과는 JSON으로 stdout(또는 `--out`). **한 번에 파서 한 종류만** 바꿔서 비교하면 원인 분해에 유리하다.

## 지표 (코드와 동일 이름)

| 지표 | 의미 |
|------|------|
| `reading_order_pass_rate` | 앵커 순서 조건 만족 비율 |
| `table_preservation_rate` | `table_gold` 명세를 만족한 표 존재 비율 |
| `structure_check_pass_rate` | `structure_checks` 통과 비율 |
| `chunk_cohesion_rate` | 유닛 그룹이 단일 청크에 온전히 들어간 비율 |

---

골든셋은 **인간 라벨**이 정본이다. 수치는 도메인에 맞게 임계치를 `EVALUATION_GUIDELINE.md`에 고정할 것.
