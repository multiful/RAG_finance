# FSC Policy RAG System

Financial Services Commission Policy Document RAG (Retrieval-Augmented Generation) System

## 🎯 Project Overview

Rapid changes in financial regulations and policies require immediate adaptation in product operations, internal controls, and risk management. However, the volume of documentation often leads to delays in compliance. This project proposes an automated system that **ingests policy documents via RSS** and provides **structured impact analysis and compliance checklists** using a grounded RAG architecture.

### Core Objectives
- **Latency Reduction**: Real-time RSS ingestion accelerates the analysis pipeline from days to minutes.
- **Reliability**: Enforced citation mechanisms minimize hallucination by grounding every answer in retrieved document chunks.
- **Trend Detection**: Semantic clustering of document embeddings visualizes emerging regulatory topics (Topic Surge).

## 🏗️ System Architecture (Phased Implementation)

### Phase A: Data Ingestion & Preprocessing (LLM Ops)
- **Collector**: Scheduled ingestion of FSC RSS feeds (Press Releases, Notices, Card News).
- **Parser**: LlamaParse API converts unstructured PDF/HWP documents into structured Markdown.
- **Chunker**: Context-aware chunking strategies with industry-specific metadata enrichment.

### Phase B: Vector Indexing & Storage
- **Storage**: Supabase (PostgreSQL) utilized as the primary vector store.
- **Indexing**: `pgvector` extension enabled for high-dimensional vector operations.
- **Embeddings**: OpenAI `text-embedding-3-small` model (1536 dimensions).

### Phase C: Retrieval & Serving (RAG Pipeline)
- **Hybrid Search**: Combines BM25/Trigram keyword search with dense vector retrieval using Reciprocal Rank Fusion (RRF).
- **Reranker (Optional)**: Cross-Encoder based reranking for precision refinement (configurable via feature flags).
- **Grounded QA**: GPT-4 driven generation with strict citation constraints.

### Phase D: Optimization & Governance
- **Safe Parsing**: Robust handling of numeric data and LLM output formats.
- **Observability**: Integration hooks for tracing (LangSmith) and performance monitoring.
- **Guardrails**: Input/output validation to ensure answerability and policy adherence.

## 📊 Key Features

1. **Real-time Collection Monitor**: Dashboard for tracking ingestion status, indexing latency, and parsing errors.
2. **Topic Surge Map**: Visualization of document clusters to identify rising regulatory trends.
3. **Industry Impact Classification**: Automated probability scoring for Insurance, Banking, and Securities sectors.
4. **Grounded RAG QA**: Question answering interface that provides specific citations for every claim.
5. **Compliance Checklist Generator**: Extraction of actionable items (Duty, Target, Deadline, Penalty) from policy texts.
6. **Governance Dashboard**: Monitoring of system health, hallucination rates, and citation accuracy.

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (High-performance ASGI)
- **Database**: Supabase (PostgreSQL + pgvector)
- **Caching**: Redis (Query results and session management)
- **LLM**: OpenAI GPT-4 Turbo / Embedding-3-small

### Frontend
- **Library**: React 18 (Vite)
- **Language**: TypeScript (Strict typing)
- **Styling**: Tailwind CSS (Premium financial dashboard aesthetic)
- **Visualization**: Recharts (Interactive charts)

## 📋 Prerequisites

Before starting, ensure you have the following:
- **Python 3.10+** installed.
- **Node.js 18+** installed.
- **Supabase Project** created with `pgvector` enabled.
- **OpenAI API Key** with access to GPT-4 models.

## 🚀 Quickstart (5-Minute Setup)

### 1. Backend Setup
```bash
cd backend
# Create virtual environment
python -m venv venv
# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment
# Copy .env.example to .env and populate keys
cp .env.example .env

# Run Server (반드시 포트 8001로 실행 — 프론트 프록시와 일치)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```
**중요:** 프론트(Vite)는 `/api` 요청을 `http://127.0.0.1:8001`로 프록시합니다. 백엔드를 **8001**에서 실행하지 않으면 `ECONNREFUSED` 또는 프록시 에러가 납니다. 500 에러가 나면 `backend/.env`에 `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `REDIS_URL`이 올바른지 확인하세요.

### 2. Frontend Setup
```bash
cd app
# Install dependencies
npm install

# Start Development Server
npm run dev
```

### 3. Environment Variables (.env)
Ensure these variables are set in `backend/.env`:
```ini
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379/0
# Feature Flags
ENABLE_RERANKING=False
ENABLE_TRACING=False
```

## 🧪 Testing & Verification

### API Documentation
Once the backend is running (on port 8001), access the interactive API docs at:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### Windows CMD Testing Guide
**Note**: Windows CMD requires strict JSON escaping and URL encoding.

**1. Search Test (GET)**
```cmd
curl.exe "http://localhost:8000/api/v1/search?query=%EA%B8%88%EB%A6%AC%20%EC%9D%B8%ED%95%98&top_k=5"
```

**2. QA Test (POST)**
```cmd
curl.exe -X POST "http://localhost:8000/api/v1/qa" -H "Content-Type: application/json" -d "{\"question\":\"금리 인하에 따른 보험업계 영향은?\",\"top_k\":5}"
```

## 📈 Evaluation Metrics

The system is evaluated against the following targets:

| Metric | Description | Target |
|---|---|---|
| **Groundedness** | Percentage of sentences supported by retrieved citations. | > 90% |
| **Hallucination Rate** | Frequency of unsupported or fabricated claims. | < 5% |
| **Industry F1 Score** | Accuracy of sector classification (Banking/Insurance/Securities). | > 0.85 |
| **Checklist Recall** | Success rate in extracting mandatory compliance items. | > 90% |

## 📄 License & Team

- **Development Period**: Jan 2026 – Feb 2026
- **License**: MIT License
- **Team**: FSC RAG Research Team
