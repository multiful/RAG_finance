"""Main FastAPI application with Phase A/B Architecture."""
import asyncio
import logging
import re
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.core.redis import RedisClient
from app.core.log_masking import install_log_masking
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.routes import router as main_router
from app.api.advanced_routes import router as advanced_router
from app.api.governance_routes import router as governance_router
from app.api.pipeline_routes import router as pipeline_router
from app.api.alert_routes import router as alert_router
from app.api.timeline_routes import router as timeline_router
from app.api.compliance_routes import router as compliance_router
from app.api.analytics_routes import router as analytics_router
from app.api.evaluation_routes import router as evaluation_router
from app.api.gap_map_routes import router as gap_map_router
from app.api.sandbox_checklist_routes import router as sandbox_checklist_router
from app.api.sandbox_simulate_routes import router as sandbox_simulate_router
from app.api.references_routes import router as references_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    install_log_masking()  # 로그 마스킹: API 키·토큰 등 민감 정보 필터
    print(f"[START] Starting {settings.APP_NAME}")
    print(f"[INFO] Phase A: Data Ingestion (LLM Ops)")
    print(f"[INFO] Phase B: Serving Service (FastAPI + Redis)")
    langsmith_on = bool(settings.LANGSMITH_API_KEY) and getattr(settings, "LANGCHAIN_TRACING_V2", True)
    print(f"[INFO] LangSmith: {'enabled (tracing on)' if langsmith_on else 'key set but tracing off' if settings.LANGSMITH_API_KEY else 'disabled'}")
    print(f"[INFO] LlamaParse enabled: {bool(settings.LLAMAPARSE_API_KEY)}")
    
    # Check Redis (미연결 시 인메모리 폴백으로 서버는 정상 기동)
    redis_ok = RedisClient.ping()
    if redis_ok:
        print("[OK] Redis connection: OK")
    else:
        print("[WARN] Redis unavailable — using in-memory cache (REDIS_URL or Docker optional)")
    
    # Check OpenAI
    if not settings.OPENAI_API_KEY:
        print("[WARN] WARNING: OPENAI_API_KEY is missing. RAG and Topic Detection will fail.")
    else:
        print(f"[OK] OpenAI API: Configured (Model: {settings.OPENAI_MODEL})")

    # 일일 1회 자동 수집 (경량, 추가 디펜던시 없음)
    schedule_task = None
    if getattr(settings, "ENABLE_DAILY_COLLECTION", True):
        try:
            from app.scheduler import run_daily_collection_loop
            schedule_task = asyncio.create_task(run_daily_collection_loop())
            print("[OK] Daily collection schedule: enabled (1x/day)")
        except Exception as e:
            print(f"[WARN] Daily schedule not started: {e}")

    yield

    if schedule_task and not schedule_task.done():
        schedule_task.cancel()
        try:
            await schedule_task
        except asyncio.CancelledError:
            pass
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


# --- CORS 허용 목록 (미들웨어 등록 전에 계산: health·예외 핸들러와 동일 규칙) ---
_cors_origins = list(getattr(settings, "CORS_DEFAULT_ORIGINS", []))
if settings.CORS_ORIGINS:
    for o in settings.CORS_ORIGINS.split(","):
        o = o.strip()
        if o and o not in _cors_origins:
            _cors_origins.append(o)
_cors_vercel_regex = r"https://([a-z0-9][a-z0-9-]*\.)+vercel\.app"
_cors_vercel_rx = re.compile(_cors_vercel_regex)


def cors_headers_for_request(request: Request) -> dict:
    """Starlette ExceptionMiddleware는 CORSMiddleware 바깥이라, 예외 응답에 ACAO가 없으면 브라우저가 CORS 오류로 표시함."""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    if origin in _cors_origins:
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    if _cors_vercel_rx.fullmatch(origin):
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    return {}


# insert(0) 순서: 아래에서 먼저 등록한 미들웨어가 스택에서 안쪽 → CORS는 반드시 마지막에 add_middleware
@app.middleware("http")
async def health_head_compat_middleware(request: Request, call_next):
    """
    UptimeRobot Free 플랜은 HTTP method를 HEAD로 고정합니다.
    HEAD /health 요청을 405 대신 200으로 돌려주기 위해,
    라우터 진입 전에 특별 처리합니다.
    """
    if request.method == "HEAD" and request.url.path.rstrip("/") == "/health":
        return Response(status_code=200, headers=cors_headers_for_request(request))
    return await call_next(request)


app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_vercel_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(
    f"[INFO] CORS: explicit_origins={len(_cors_origins)}, "
    f"vercel_regex=on, sample_match=https://rag-finance-rho.vercel.app"
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
app.include_router(evaluation_router, prefix=f"{settings.API_V1_PREFIX}", tags=["Evaluation"])
app.include_router(gap_map_router, prefix=settings.API_V1_PREFIX)
app.include_router(sandbox_checklist_router, prefix=settings.API_V1_PREFIX)
app.include_router(sandbox_simulate_router, prefix=settings.API_V1_PREFIX)
app.include_router(references_router, prefix=settings.API_V1_PREFIX)


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
            "alerts": f"{settings.API_V1_PREFIX}/alerts",
            "references": f"{settings.API_V1_PREFIX}/references"
        }
    }


@app.head("/")
async def root_head():
    """Uptime 모니터 등 HEAD 요청 지원 (405 방지)."""
    return Response(status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint. 수집·벡터 건수 등 확장."""
    redis_ok = RedisClient.ping()
    openai_ok = bool(settings.OPENAI_API_KEY)

    db_ok = False
    documents_count = 0
    chunks_count = 0
    try:
        from app.core.database import get_db
        db = get_db()
        result = db.table("documents").select("document_id").limit(1).execute()
        db_ok = True
        cnt = db.table("documents").select("document_id", count="exact").execute()
        documents_count = getattr(cnt, "count", 0) or 0
        try:
            ch = db.table("chunks").select("chunk_id", count="exact").execute()
            chunks_count = getattr(ch, "count", 0) or 0
        except Exception:
            pass
    except Exception:
        pass

    last_collection = None
    last_collection_success = None
    try:
        from app.services.job_tracker import job_tracker
        last_collection = job_tracker.get_last_collection_run()
        lid = job_tracker.get_latest_job_id()
        if lid:
            job = job_tracker.get_job(lid)
            if job:
                last_collection_success = job.get("status") in ("success", "success_collect", "no_change")
    except Exception:
        pass

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
            "llamaparse": bool(settings.LLAMAPARSE_API_KEY),
        },
        "components": {
            "rag_engine": {"status": "operational" if (openai_ok and db_ok) else "degraded", "label": "RAG 엔진"},
            "vector_db": {"status": "operational" if db_ok else "error", "label": "벡터 DB"},
            "llm_api": {"status": "operational" if openai_ok else "error", "label": "LLM API"},
            "cache": {"status": "operational" if redis_ok else "degraded", "label": "캐시"},
        },
        "phases": {
            "phase_a": "Data Ingestion Ready",
            "phase_b": "Serving Service Ready",
        },
        "metrics": {
            "documents_count": documents_count,
            "chunks_count": chunks_count,
            "last_collection_run": last_collection,
            "last_collection_success": last_collection_success,
        },
    }


@app.head("/health")
async def health_check_head():
    """UptimeRobot 등 HEAD /health 모니터링 지원 (405 방지)."""
    return Response(status_code=200)


# ---------------------------------------------------------------------------
# 예외 응답에도 ACAO 부여 (ExceptionMiddleware가 CORS 바깥에 있어서 기본 500은 CORS 오류로 보임)
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_with_cors(request: Request, exc: HTTPException):
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
        headers=cors_headers_for_request(request),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_with_cors(request: Request, exc: RequestValidationError):
    return JSONResponse(
        {"detail": exc.errors()},
        status_code=422,
        headers=cors_headers_for_request(request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_with_cors(request: Request, exc: Exception):
    logging.exception("Unhandled error: %s", exc)
    return JSONResponse(
        {"detail": "Internal server error"},
        status_code=500,
        headers=cors_headers_for_request(request),
    )
