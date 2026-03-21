## FSC Policy RAG System

금융위원회 정책·보도자료 문서를 대상으로 하는 RAG(Retrieval-Augmented Generation) 시스템입니다.  
RSS 기반 수집 → 문서 파싱 → 벡터 인덱싱 → 하이브리드 검색 → 근거가 명시된 답변까지 한 번에 제공하는 것을 목표로 합니다.

## 프로젝트 개요

- **문제의식**: 금융 규제·정책이 빠르게 바뀌지만, 공문·보도자료·정책자료 분량이 많아 현업이 내용을 따라잡기 어렵습니다.
- **목표**  
  - **정책 문서 자동 수집**: 금융위 RSS, 국제기구 RSS를 주기적으로 수집해 DB에 적재  
  - **근거 기반 QA**: 답변마다 출처 문단과 URL을 함께 제시  
  - **업권 영향·체크리스트**: 은행·보험·증권 등 업권별 영향 요약과 준수 항목(무엇을, 언제까지, 누구에게)을 추출

## 시스템 아키텍처 개요

아키텍처 상세는 `ARCHITECTURE.md`, `BACKEND_ADVANCED.md`를 참고합니다. 여기서는 상위 레벨만 요약합니다.

### Phase A: 데이터 인제스천 (LLM Ops)

- **수집**: 금융위 RSS, FSS 스크래핑, 국제기구(FSB, BIS) RSS 수집
- **파싱**: LlamaParse로 PDF/HWP를 마크다운 구조로 변환
- **청킹**: 문맥 보존 청킹(청크 크기 800, 오버랩 100) 및 업권 메타데이터 태깅
- **임베딩 저장**: OpenAI `text-embedding-3-small` → Supabase(PostgreSQL + `pgvector`)

### Phase B: 서빙 서비스 (FastAPI + Redis)

- **API 서버**: FastAPI 기반 백엔드, 기본 URL은 `/api/v1`
- **검색**: BM25/Trigram 키워드 검색 + 벡터 검색을 결합한 하이브리드 검색
- **리랭커**: SentenceTransformers CrossEncoder 기반 재정렬
- **캐시**: Redis를 이용한 질의 결과 캐싱 및 레이트 리밋
- **평가·관측성**: Ragas 기반 RAG 품질 평가, LangSmith 트레이싱

## 주요 기능

- **정책 문서 수집 파이프라인**: 금융위/FSS/국제기구 RSS 및 웹 페이지 수집
- **문서 파싱·청킹**: PDF/HWP 파싱, 표 구조 보존, 업권 태깅
- **RAG QA**: 정책·규제 관련 질의에 대해 근거 문단과 함께 답변
- **체크리스트 생성**: 의무, 대상, 기한, 제재 등 준수 항목 구조화
- **토픽 서지·알림**: 임베딩 기반 토픽 클러스터링과 규제 이슈 감지
- **RAG 평가**: Ragas를 이용한 Groundedness, Faithfulness 등 지표 산출

## 기술 스택

### Backend

- **애플리케이션**: `FastAPI`, `uvicorn`
- **데이터베이스**: Supabase (PostgreSQL + `pgvector`)
- **캐시**: Redis
- **LLM·RAG**: OpenAI API, `langchain`, `langgraph`
- **문서 파싱**: `llama-parse`, `llama-index`
- **평가·관측성**: `ragas`, `datasets`, `langsmith`
- **데이터 처리**: `pydantic`, `pydantic-settings`, `numpy`, `pandas`

### Frontend

- **프레임워크**: React 18 + Vite
- **언어**: TypeScript
- **스타일링**: Tailwind CSS
- **차트**: Recharts
- **API 클라이언트**: Axios (`app/src/lib/api.ts`)

## 로컬 개발 환경

### 1. 백엔드 실행 (FastAPI)

프로젝트 루트 기준 경로는 `app/backend` 입니다.

```bash
cd app/backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 의존성 설치 (constraints 함께 사용 권장)
pip install -r requirements.txt -c constraints.txt

# 환경 변수 파일 생성
cp .env.example .env  # Windows PowerShell에서는 copy .env.example .env

# 서버 실행 (프론트 프록시와 맞추기 위해 포트 8001 고정)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

필수 환경 변수는 `app/backend/.env` 에 설정합니다.

```ini
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_or_publishable_key
SUPABASE_SERVICE_KEY=your_service_role_key
OPENAI_API_KEY=sk-...
# 필요 시 Redis Cloud URL로 교체
REDIS_URL=redis://127.0.0.1:6379/0
```

추가로 `LLAMAPARSE_API_KEY`, `LANGSMITH_API_KEY` 등을 설정하면 문서 파싱·관측 기능이 활성화됩니다.

### 2. 프론트엔드 실행 (Vite)

```bash
cd app

npm install

# 로컬 개발 서버 실행 (기본 포트 5173)
npm run dev
```

프론트엔드는 `VITE_API_BASE_URL` 환경 변수를 통해 백엔드 주소를 주입받습니다.  
로컬에서는 기본값(`/api/v1`)을 사용하고, 배포 환경에서는 예시처럼 설정합니다.

```ini
# app/.env 또는 Vercel 환경 변수
# Render (기존)
VITE_API_BASE_URL=https://rag-finance-d2ho.onrender.com/api/v1

# Railway 백엔드를 쓸 때: 대시보드의 공개 도메인(HTTPS) + /api/v1
# 예: VITE_API_BASE_URL=https://ragfinance-production-xxxx.up.railway.app/api/v1
# ※ ragfinance.railway.internal 같은 주소는 내부망 전용이라 Vercel·브라우저에서 쓰면 안 됩니다.
```

## 배포 정보

- **백엔드 (Render, 기존 유지)**  
  - URL: `https://rag-finance-d2ho.onrender.com`  
  - 헬스: `GET /health`
- **백엔드 (Railway, 선택)**  
  - Vercel·프론트에 넣을 값은 **Networking → Public Networking** 에 나오는 `https://…up.railway.app` 형태의 주소입니다.  
  - `*.railway.internal` 은 같은 Railway 프로젝트 안의 다른 서비스끼리 통신할 때만 씁니다.
- **프론트엔드 (Vercel)**  
  - `VITE_API_BASE_URL` 을 쓸 백엔드(Render 또는 Railway 공개 URL)의 `/api/v1` 로 설정합니다.  
  - Railway를 쓰면 해당 백엔드의 Railway **Variables**에 `CORS_ORIGINS` 로 Vercel 도메인(쉼표 구분)을 추가해 CORS를 맞춥니다.

## 기본 확인 방법

- 브라우저
  - `https://rag-finance-d2ho.onrender.com/`  
  - `https://rag-finance-d2ho.onrender.com/docs`
- 명령줄

```bash
curl https://rag-finance-d2ho.onrender.com/health
```

## 라이선스 및 개발 정보

- **개발 기간**: 2026년 1월 ~ 2026년 2월  
- **라이선스**: MIT License  
- **주요 역할**: 금융 정책 RAG 설계 및 구현, RAG 평가·관측 파이프라인 구축
