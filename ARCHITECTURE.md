# FSC Policy RAG System - Architecture

## Phase A/B 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FSC Policy RAG System v2.0                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PHASE A: 데이터 인제스천                       │   │
│  │                         (LLM Ops Pipeline)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│    ┌──────────┐    ┌─────────┴────────┐    ┌──────────┐    ┌──────────┐   │
│    │ Collector│───▶│     Parser       │───▶│ Chunker  │───▶│ Embedder │   │
│    │ (RSS)    │    │ (LlamaParse API) │    │(LangChain│    │ (OpenAI) │   │
│    └──────────┘    └──────────────────┘    └──────────┘    └────┬─────┘   │
│         │                    │                    │               │        │
│         ▼                    ▼                    ▼               ▼        │
│    ┌──────────────────────────────────────────────────────────────────┐   │
│    │                    Supabase (PostgreSQL + pgvector)               │   │
│    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│    │  │documents │  │  chunks  │  │embeddings│  │ industry_labels  │  │   │
│    │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │   │
│    └──────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                              ┌─────────────┐                                │
│                              │  Guardrail  │                                │
│                              │  (품질검증)  │                                │
│                              └──────┬──────┘                                │
│                                     │                                       │
│  ┌──────────────────────────────────┼──────────────────────────────────┐   │
│  │                        PHASE B: 서빙 서비스                          │   │
│  │                      (FastAPI + Redis)                               │   │
│  └──────────────────────────────────┼──────────────────────────────────┘   │
│                                     │                                       │
│    ┌──────────┐    ┌───────────────┼────────────────┐    ┌──────────┐     │
│    │  Request │────┼───────────────┘                │    │ Response │     │
│    │ (User)   │    │                                 │    │ (User)   │     │
│    └──────────┘    ▼                                 │    └──────────┘     │
│              ┌──────────┐                            │                     │
│              │  Cache   │◀───────────────────────────┤                     │
│              │ (Redis)  │   Cache Hit?               │                     │
│              └────┬─────┘                            │                     │
│                   │ No                               │                     │
│                   ▼                                  │                     │
│              ┌──────────┐    ┌──────────┐    ┌──────┴─────┐               │
│              │ Reasoning│───▶│ Retrieval│───▶│ Reranker  │               │
│              │(LangGraph│    │(Hybrid  │    │(Cross-    │               │
│              │  Agent)  │    │ Search)  │    │ Encoder)  │               │
│              └──────────┘    └──────────┘    └─────┬─────┘               │
│                                                    │                      │
│              ┌─────────────────────────────────────┘                      │
│              ▼                                                             │
│              ┌─────────────────────────────────────────┐                   │
│              │     Generation & Guardrail              │                   │
│              │  - 근거 문단 태그 ([출처 N])             │                   │
│              │  - 환각 여부 셀프 체크                   │                   │
│              │  - Groundedness Score 계산              │                   │
│              └─────────────────────────────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase A: 데이터 인제스천 (LLM Ops)

### 1. Collector (RSS 수집기)

```python
class RSSCollector:
    """금융위 RSS 1일 4회 체크"""
    
    RSS_SOURCES = {
        "0111": "볏  도자료",
        "0112": "볏  도설명", 
        "0114": "공지사항",
        "0411": "카드뉴스"
    }
    
    # Schedule: 00:00, 06:00, 12:00, 18:00
```

**기능:**
- 금융위원회 RSS 피드 자동 수집
- 중복 체크 (hash 기반)
- 메타데이터 추출 (제목, 발행일, 부서, 카테고리)

**API:**
```bash
POST /api/v1/pipeline/collect
```

### 2. Parser (LlamaParse)

```python
class LlamaDocumentParser:
    """PDF/HWP → 마크다운 변환"""
    
    # LlamaParse API 사용 (로컬 자원 사용 0)
    # 표(Table) 데이터를 마크다운으로 완벽 복구
```

**기능:**
- PDF 텍스트 + 표 추출
- HWP 파일 지원 (PDF 변환 후 파싱)
- 마크다운 형식 출력
- 표 구조 보존

**API:**
```bash
POST /api/v1/advanced/parse/document?file_type=pdf
```

### 3. Chunker (LangChain)

```python
class ContextualChunker:
    """문맥 보존 청킹 + 업권 메타데이터"""
    
    # Chunk size: 800 tokens
    # Overlap: 100 tokens
    # 업권 태그: INSURANCE, BANKING, SECURITIES
```

**기능:**
- 문맥을 보존하며 문단 분할
- 업권 키워드 기반 자동 태깅
- 표 데이터 청크 연결

### 4. Embedder (OpenAI)

```python
class OpenAIEmbedder:
    """문장을 벡터로 변환 → Supabase(pgvector)"""
    
    # Model: text-embedding-3-small
    # Dimension: 1536
    # Batch processing 지원
```

**기능:**
- OpenAI Embedding API 호출
- 배치 처리로 효율화
- Supabase pgvector에 저장

**API:**
```bash
GET /api/v1/pipeline/status/{document_id}
GET /api/v1/pipeline/stats
```

---

## Phase B: 서빙 서비스 (FastAPI + Redis)

### 1. Cache Layer (Upstash Redis)

```python
class CacheLayer:
    """동일 질문 캐싱"""
    
    TTL: 3600 seconds (1 hour)
    Key format: query:{hash}
```

**기능:**
- 동일 질문 캐시 확인 (있으면 즉시 반환)
- 응답 결과 캐싱
- 문서 업데이트 시 관련 캐시 무효화

**API:**
```bash
GET /api/v1/pipeline/query/cache/stats
DELETE /api/v1/pipeline/query/cache
```

### 2. Reasoning (LangGraph Agent)

```python
class ReasoningEngine:
    """질문 유형 판단 + Query Expansion"""
    
    # Query Types:
    # - qa: 일반 질문응답
    # - checklist_extract: 준수 항목 추출
    # - industry_analysis: 업권 영향 분석
    # - topic_search: 토픽/이슈 검색
```

**기능:**
- 질문 의도 분류
- 검색 쿼리 최적화
- 관련 키워드 확장

### 3. Retrieval (Hybrid Search)

```python
class HybridRetriever:
    """키워드(BM25) + 의미(Vector) 검색"""
    
    # Reciprocal Rank Fusion (RRF)
    # combined_score = 0.7 * vector_score + 0.3 * keyword_score
```

**기능:**
- pgvector 벡터 유사도 검색
- PostgreSQL 전문검색 (BM25)
- RRF로 결과 융합
- 메타데이터 필터링 (날짜, 카테고리, 업권)

### 4. Reranker (Cross-Encoder)

```python
class Reranker:
    """Cross-Encoder 기반 재정렬"""
    
    # Model: ms-marco-MiniLM-L-6-v2
    # Top-k: 5 (after reranking)
```

**기능:**
- 쿼리-문서 관련성 재계산
- 정답 확률이 높은 순으로 재정렬

### 5. Generation & Guardrail

```python
class GuardrailChecker:
    """근거 문단 태그 + 환각 체크"""
    
    # 1. Generate answer with [출처 N] tags
    # 2. Check groundedness score
    # 3. Detect hallucination
```

**기능:**
- 근거 문단 번호 태그로 답변 생성
- Groundedness Score 계산
- 환각 여부 셀프 체크

**API:**
```bash
POST /api/v1/pipeline/query
{
  "query": "보험사 납입면제 제도는?",
  "use_cache": true,
  "top_k": 5
}
```

**Response:**
```json
{
  "query": "보험사 납입면제 제도는?",
  "query_type": "qa",
  "answer": "납입면제 제도는... [출처 1]",
  "citations": [...],
  "confidence": 0.92,
  "groundedness_score": 0.89,
  "hallucination_flag": false,
  "processing_time_ms": 1250,
  "cache_hit": false
}
```

---

## 데이터 흐름 다이어그램

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   금융위    │────▶│   RSS       │────▶│  Collector  │
│   RSS       │     │   Feed      │     │  (4회/일)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────┐
│  Supabase (PostgreSQL + pgvector)                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │
│  │documents│  │  chunks │  │embeddings│  │   topics  │  │
│  │  (Raw)  │  │(Chunked)│  │(Vectors) │  │(Clusters) │  │
│  └─────────┘  └─────────┘  └─────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────┘
                                                │
                    ┌───────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                    사용자 질의 (Query)                    │
└─────────────────────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌────────┐    ┌────────┐    ┌────────────┐
│ Cache  │    │Reasoning│    │  Retrieval │
│ (Redis)│    │(Agent) │    │(Hybrid)   │
└────┬───┘    └────┬───┘    └─────┬──────┘
     │             │              │
     │             └──────────────┘
     │                            │
     │         ┌──────────┐       │
     └────────▶│ Reranker │◀──────┘
               │(Cross-   │
               │ Encoder) │
               └────┬─────┘
                    │
                    ▼
            ┌───────────────┐
            │  Generation   │
            │  & Guardrail  │
            │  - [출처 N]   │
            │  - 환각 체크  │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │    사용자     │
            │   (Response)  │
            └───────────────┘
```

---

## 컴포넌트 상호작용

### 프론트엔드 ↔ 백엔드

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vite + React)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  SourceCard  │  │ComplianceTable│  │  TrendChart  │      │
│  │ (근거 문단)  │  │ (체크리스트)  │  │ (토픽 트렌드)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Pipeline   │  │    Query     │  │  Evaluation │      │
│  │   Routes     │  │   Engine     │  │   (Ragas)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## API 엔드포인트 요약

### Phase A: Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pipeline/collect` | RSS 수집 트리거 |
| POST | `/api/v1/pipeline/ingest/{doc_id}` | 문서 인제스천 |
| GET | `/api/v1/pipeline/status/{doc_id}` | 인제스천 상태 |
| GET | `/api/v1/pipeline/stats` | 파이프라인 통계 |

### Phase B: Serving

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pipeline/query` | 쿼리 처리 |
| GET | `/api/v1/pipeline/query/cache/stats` | 캐시 통계 |
| DELETE | `/api/v1/pipeline/query/cache` | 캐시 삭제 |

### Advanced

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/advanced/agent/query` | LangGraph 에이전트 |
| POST | `/api/v1/advanced/parse/document` | LlamaParse |
| POST | `/api/v1/advanced/evaluate/single` | Ragas 단일 평가 |
| POST | `/api/v1/advanced/evaluate/batch` | Ragas 배치 평가 |
| GET | `/api/v1/advanced/observability/stats` | LangSmith 통계 |

---

## 환경 변수

```bash
# Phase A: Ingestion
OPENAI_API_KEY=sk-...                    # Embeddings
LLAMAPARSE_API_KEY=llx-...               # Document parsing

# Phase B: Serving
REDIS_URL=redis://localhost:6379/0       # Cache layer
OPENAI_MODEL=gpt-4-turbo-preview         # LLM

# Observability
LANGSMITH_API_KEY=ls-...                 # Tracing
LANGSMITH_PROJECT=fsc-policy-rag

# Database
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...
```

---

## 성능 목표

| Metric | Target | Phase |
|--------|--------|-------|
| Ingestion Throughput | 100 docs/hour | A |
| Query Latency (p95) | < 2s | B |
| Cache Hit Rate | > 30% | B |
| Groundedness Score | > 0.90 | B |
| Hallucination Rate | < 5% | B |
