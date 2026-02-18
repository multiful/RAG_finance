# FSC Policy RAG System - Backend Advanced Features

## 🚀 고도화된 백엔드 아키텍처

### 추가된 프레임워크

| 프레임워크 | 역할 | 고도화 포인트 |
|-----------|------|--------------|
| **LangGraph** | 에이전트 워크플로우 | 단순 QA를 넘어 '분류→추출→검증'의 자율 판단 루프 구현 |
| **LlamaParse** | 첨부파일 파싱 | HWP/PDF 내 표(Table) 데이터를 마크다운으로 완벽 복구 |
| **Ragas** | RAG 정량 평가 | Groundedness 등 수치화된 지표로 논문의 객관성 확보 |
| **LangSmith** | 관측성(Observability) | 답변 생성 전 과정을 시각화하여 모델 거버넌스 증명 |

---

## 📁 디렉토리 구조

```
backend/
├── app/
│   ├── agents/
│   │   └── policy_agent.py          # LangGraph 에이전트 워크플로우
│   ├── api/
│   │   ├── routes.py                 # 기본 API 라우트
│   │   └── advanced_routes.py        # 고급 API 라우트
│   ├── core/
│   │   ├── config.py                 # 설정 (LangSmith, LlamaParse 추가)
│   │   ├── database.py               # Supabase 연결
│   │   └── redis.py                  # Redis 캐시
│   ├── evaluation/
│   │   └── ragas_evaluator.py        # Ragas 평가 시스템
│   ├── models/
│   │   └── schemas.py                # Pydantic 모델
│   ├── observability/
│   │   └── langsmith_tracer.py       # LangSmith 트레이싱
│   ├── parsers/
│   │   └── llama_parser.py           # LlamaParse 통합
│   ├── services/
│   │   ├── checklist_service.py      # 체크리스트 추출
│   │   ├── industry_classifier.py    # 업권 분류
│   │   ├── rag_service.py            # RAG 서비스
│   │   ├── rss_collector.py          # RSS 수집
│   │   ├── topic_detector.py         # 토픽 탐지
│   │   └── vector_store.py           # 최적화된 벡터 스토어
│   └── main.py                       # FastAPI 앱
├── requirements.txt                   # 업데이트된 의존성
└── .env.example                       # 환경 변수 예시
```

---

## 🔗 LangGraph 에이전트 워크플로우

### 분류 → 추출 → 검증 루프

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   사용자    │────▶│ Query        │────▶│  라우터     │
│   질문      │     │ Classifier   │     │  (Router)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
           ┌────────────────────────────────────┼────────────────────┐
           │                                    │                    │
           ▼                                    ▼                    ▼
    ┌─────────────┐                    ┌──────────────┐    ┌──────────────┐
    │  RAG QA     │                    │   Industry   │    │  Checklist   │
    │  (일반 QA)  │                    │ Classification│   │  Extraction  │
    └──────┬──────┘                    └──────┬───────┘    └──────┬───────┘
           │                                  │                    │
           └──────────────────────────────────┼────────────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │ Verification │
                                       │   (검증)     │
                                       └──────┬───────┘
                                              │
                              ┌───────────────┴───────────────┐
                              │                                 │
                              ▼                                 ▼
                       ┌─────────────┐                 ┌─────────────┐
                       │  passed     │                 │ needs_retry │
                       │  (종료)     │                 │ (재시도)    │
                       └─────────────┘                 └─────────────┘
```

### API 엔드포인트

```bash
POST /api/v1/advanced/agent/query
```

**Request:**
```json
{
  "query": "보험사 납입면제 제도 변경사항은?",
  "document_id": "optional-doc-id"
}
```

**Response:**
```json
{
  "query_type": "qa",
  "answer": "...",
  "confidence": 0.85,
  "verification_status": "passed",
  "iterations": 2,
  "retrieved_chunks": [...]
}
```

---

## 📄 LlamaParse 문서 파싱

### 기능

- **PDF 파싱**: 텍스트 + 표 + 구조 추출
- **HWP 파싱**: 한글 문서 지원 (PDF 변환 후 파싱)
- **표 복구**: 마크다운 테이블 형식으로 변환
- **청킹**: 표 구조를 보존하며 청킹

### API 엔드포인트

```bash
POST /api/v1/advanced/parse/document?file_type=pdf
Content-Type: multipart/form-data

file: <uploaded_file>
```

**Response:**
```json
{
  "filename": "policy.pdf",
  "file_type": "pdf",
  "text": "# Full markdown text...",
  "chunks": [
    {
      "chunk_index": 0,
      "chunk_text": "...",
      "tables": [
        {
          "headers": ["항목", "내용"],
          "rows": [["A", "내용A"], ["B", "내용B"]]
        }
      ]
    }
  ],
  "total_chunks": 5
}
```

---

## 📊 Ragas 평가 시스템

### 평가 지표

| 지표 | 설명 | 목표값 |
|-----|------|-------|
| **Groundedness** | 근거일치율 | > 0.90 |
| **Faithfulness** | 충실도 | > 0.90 |
| **Answer Relevancy** | 답변 관련성 | > 0.85 |
| **Context Precision** | 컨텍스트 정확도 | > 0.80 |
| **Context Recall** | 컨텍스트 재현율 | > 0.80 |
| **Overall Score** | 종합 점수 | > 0.85 |

### API 엔드포인트

#### 단일 평가
```bash
POST /api/v1/advanced/evaluate/single
```

```json
{
  "question": "보험사 납입면제 제도는?",
  "answer": "납입면제 제도는...",
  "contexts": ["context1", "context2"],
  "ground_truth": "정답"
}
```

#### 배치 평가
```bash
POST /api/v1/advanced/evaluate/batch
```

```json
{
  "test_cases": [
    {
      "question_id": "q1",
      "question": "...",
      "answer": "...",
      "contexts": [...],
      "ground_truth": "..."
    }
  ]
}
```

**Response:**
```json
{
  "run_id": "run_123",
  "total_questions": 10,
  "avg_groundedness": 0.87,
  "avg_faithfulness": 0.90,
  "avg_answer_relevancy": 0.88,
  "avg_context_precision": 0.82,
  "avg_context_recall": 0.79,
  "avg_overall_score": 0.85,
  "suggestions": [
    "근거일치율이 낮습니다. 리랭커를 개선하세요."
  ]
}
```

---

## 👁️ LangSmith 관측성

### 기능

- **파이프라인 트레이싱**: Query → Retrieval → Generation 전 과정 추적
- **에이전트 워크플로우 트레이싱**: Iteration별 상태 추적
- **피드백 수집**: 사용자 피드백 연결
- **통계 분석**: Latency, Error rate 등

### API 엔드포인트

```bash
# 상태 확인
GET /api/v1/advanced/observability/status

# 통계 조회
GET /api/v1/advanced/observability/stats?hours=24

# 트레이스 나이스포트
GET /api/v1/advanced/observability/traces/export

# 피드백 추가
POST /api/v1/advanced/observability/feedback/{run_id}
{
  "key": "user_rating",
  "score": 5,
  "comment": "Good answer"
}
```

---

## 🔍 최적화된 벡터 검색

### 하이브리드 검색 (BM25 + Vector)

```python
# Reciprocal Rank Fusion (RRF) 사용
combined_score = vector_weight / (k + vector_rank) + keyword_weight / (k + keyword_rank)
```

### API 엔드포인트

```bash
POST /api/v1/advanced/vector/search
```

```json
{
  "query": "보험사 규제 변경",
  "top_k": 10,
  "vector_weight": 0.7,
  "keyword_weight": 0.3,
  "filters": {
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "category": "press_release"
  }
}
```

### 리랭킹 (Cross-Encoder)

```bash
POST /api/v1/advanced/vector/rerank
```

```json
{
  "query": "보험사 규제 변경",
  "results": [...],
  "top_k": 5
}
```

---

## ⚙️ 환경 변수 설정

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# LangSmith (Observability)
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=fsc-policy-rag
LANGCHAIN_TRACING_V2=true

# LlamaParse (Document Parsing)
LLAMAPARSE_API_KEY=llx-...

# Supabase
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## 🚀 실행 방법

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 4. 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. API 문서 확인
open http://localhost:8000/docs
```

---

## 📈 성능 최적화

### pgvector 인덱스

```sql
-- IVFFlat 인덱스 (빠른 근사 검색)
CREATE INDEX idx_embeddings_ivfflat 
ON embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- HNSW 인덱스 (더 높은 정확도)
CREATE INDEX idx_embeddings_hnsw 
ON embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 캐싱 전략

```python
# Redis 캐싱
@cache(ttl=3600)
async def get_embedding(text: str) -> List[float]:
    ...

@cache(ttl=1800)
async def search_similar(query: str) -> List[SearchResult]:
    ...
```

---

## 📝 논문 작성 팁

### Ragas 결과 활용

```
Table 1: RAG System Evaluation Results

| Metric | Baseline | RAG (Basic) | RAG + Rerank | RAG + Guardrails |
|--------|----------|-------------|--------------|------------------|
| Groundedness | 0.72 | 0.81 | 0.87 | 0.91 |
| Faithfulness | 0.75 | 0.84 | 0.89 | 0.93 |
| Answer Relevancy | 0.78 | 0.85 | 0.88 | 0.90 |
| Context Precision | 0.70 | 0.78 | 0.85 | 0.88 |
| Context Recall | 0.68 | 0.76 | 0.82 | 0.86 |
| **Overall Score** | **0.73** | **0.81** | **0.86** | **0.90** |
```

### LangSmith 트레이스 활용

논문에 첨부할 수 있는 트레이스 예시:
- Query Classification 단계
- Retrieval 결과 (Top-k chunks)
- LLM Generation 과정
- Verification 결과

---

## 🔗 참고 자료

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LlamaParse Documentation](https://docs.llamaindex.ai/en/latest/llama_cloud/llama_parse/)
- [Ragas Documentation](https://docs.ragas.io/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
