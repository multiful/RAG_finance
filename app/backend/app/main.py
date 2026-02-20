"""Main FastAPI application with Phase A/B Architecture."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.core.redis import RedisClient
from app.api.routes import router as main_router
from app.api.advanced_routes import router as advanced_router
from app.api.governance_routes import router as governance_router
from app.api.pipeline_routes import router as pipeline_router
from app.api.alert_routes import router as alert_router
from app.api.timeline_routes import router as timeline_router
from app.api.compliance_routes import router as compliance_router
from app.api.analytics_routes import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"[START] Starting {settings.APP_NAME}")
    print(f"[INFO] Phase A: Data Ingestion (LLM Ops)")
    print(f"[INFO] Phase B: Serving Service (FastAPI + Redis)")
    print(f"[INFO] LangSmith enabled: {bool(settings.LANGSMITH_API_KEY)}")
    print(f"[INFO] LlamaParse enabled: {bool(settings.LLAMAPARSE_API_KEY)}")
    
    # Check Redis
    redis_ok = RedisClient.ping()
    if redis_ok:
        print("[OK] Redis connection: OK")
    else:
        print("[FAIL] Redis connection: FAILED (Check REDIS_URL or Docker)")
    
    # Check OpenAI
    if not settings.OPENAI_API_KEY:
        print("[WARN] WARNING: OPENAI_API_KEY is missing. RAG and Topic Detection will fail.")
    else:
        print(f"[OK] OpenAI API: Configured (Model: {settings.OPENAI_MODEL})")
    
    yield
    # Shutdown
    print(f"[STOP] Shutting down {settings.APP_NAME}")
    RedisClient.close()


app = FastAPI(
    title=settings.APP_NAME,
    description="""
    # FSC Policy RAG System - Phase A/B Architecture
    
    ## Phase A: 데이터 인제스천 (LLM Ops)
    - **Collector**: 금융위 RSS 1일 4회 체크
    - **Parser**: LlamaParse API로 PDF/HWP → 마크다운 변환
    - **Chunker**: LangChain으로 문맥 보존 청킹 + 업권 메타데이터
    - **Embedder**: OpenAI로 벡터 변환 → Supabase(pgvector)
    
    ## Phase B: 서빙 서비스 (FastAPI + Redis)
    - **Cache Layer**: Upstash Redis로 동일 질문 캐싱
    - **Reasoning**: LangGraph Agent로 질문 유형 판단 + Query Expansion
    - **Retrieval**: Hybrid Search (BM25 + Vector)
    - **Reranker**: Cross-Encoder로 Top-k 재정렬
    - **Generation & Guardrail**: 근거 문단 태그 + 환각 체크
    
    ## 관측성 (Observability)
    - **LangSmith**: 답변 생성 전 과정 시각화
    - **Ragas**: Groundedness 등 수치화된 평가 지표
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(main_router, prefix=settings.API_V1_PREFIX)
app.include_router(advanced_router, prefix=f"{settings.API_V1_PREFIX}/advanced", tags=["Advanced"])
app.include_router(governance_router, prefix=f"{settings.API_V1_PREFIX}/advanced", tags=["Governance"])
app.include_router(pipeline_router, prefix=f"{settings.API_V1_PREFIX}/pipeline")
app.include_router(alert_router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(timeline_router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(compliance_router, prefix=f"{settings.API_V1_PREFIX}/compliance", tags=["Compliance"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Analytics"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "2.0.0",
        "architecture": {
            "phase_a": "Data Ingestion (LLM Ops)",
            "phase_b": "Serving Service (FastAPI + Redis)",
            "observability": "LangSmith + Ragas"
        },
        "features": [
            "LangGraph Agent Workflow",
            "LlamaParse Document Parsing",
            "Ragas Evaluation",
            "LangSmith Observability",
            "Hybrid Vector Search (BM25 + Embedding)",
            "Cross-Encoder Reranking",
            "Guardrail & Hallucination Detection",
            "Redis Caching Layer",
            "Smart Alert System",
            "Policy Timeline Tracker"
        ],
        "docs": "/docs",
        "endpoints": {
            "main": f"{settings.API_V1_PREFIX}",
            "advanced": f"{settings.API_V1_PREFIX}/advanced",
            "pipeline": f"{settings.API_V1_PREFIX}/pipeline",
            "alerts": f"{settings.API_V1_PREFIX}/alerts"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_ok = RedisClient.ping()
    openai_ok = bool(settings.OPENAI_API_KEY)
    
    # Check Supabase/Vector DB connection
    db_ok = False
    try:
        from app.core.database import get_db
        db = get_db()
        result = db.table("documents").select("document_id").limit(1).execute()
        db_ok = True
    except Exception:
        db_ok = False
    
    all_ok = redis_ok and openai_ok and db_ok
    
    return {
        "status": "healthy" if all_ok else "degraded" if (openai_ok and db_ok) else "warning",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": True,
            "redis": redis_ok,
            "supabase": db_ok,
            "openai": openai_ok,
            "langsmith": bool(settings.LANGSMITH_API_KEY),
            "llamaparse": bool(settings.LLAMAPARSE_API_KEY)
        },
        "components": {
            "rag_engine": {"status": "operational" if (openai_ok and db_ok) else "degraded", "label": "RAG 엔진"},
            "vector_db": {"status": "operational" if db_ok else "error", "label": "벡터 DB"},
            "llm_api": {"status": "operational" if openai_ok else "error", "label": "LLM API"},
            "cache": {"status": "operational" if redis_ok else "degraded", "label": "캐시"}
        },
        "phases": {
            "phase_a": "Data Ingestion Ready",
            "phase_b": "Serving Service Ready"
        }
    }
