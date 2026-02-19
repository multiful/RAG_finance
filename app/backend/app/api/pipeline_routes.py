"""Pipeline API Routes - Phase A/B Architecture."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.pipeline.ingestion import get_ingestion_pipeline
from app.serving.query_engine import get_query_engine
from app.observability.langsmith_tracer import get_tracer

router = APIRouter()

# Initialize services
pipeline = get_ingestion_pipeline()
query_engine = get_query_engine()
tracer = get_tracer()


# ============ Phase A: Data Ingestion Routes ============

@router.post("/ingest/{document_id}")
async def ingest_document(document_id: str, background_tasks: BackgroundTasks):
    """Run full ingestion pipeline for a document.
    
    Pipeline: Collector → Parser → Chunker → Embedder → Supabase
    """
    try:
        # Run in background for long-running tasks
        background_tasks.add_task(pipeline.run_full_pipeline, document_id)
        
        return {
            "message": "Ingestion started",
            "document_id": document_id,
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect")
async def trigger_collection(background_tasks: BackgroundTasks):
    """Trigger scheduled RSS collection (runs 4 times/day) with job tracking."""
    try:
        from app.services.job_tracker import job_tracker
        job_id = job_tracker.create_job()
        if not job_id:
            raise HTTPException(status_code=503, detail="Redis connection failed. Job tracking unavailable.")
        
        background_tasks.add_task(pipeline.run_scheduled_collection, job_id=job_id)
        
        return {
            "message": "Collection started",
            "job_id": job_id,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-failed")
async def retry_failed_documents(background_tasks: BackgroundTasks):
    """Retry processing for all failed documents."""
    try:
        db = pipeline.collector.db
        result = db.table("documents").select("document_id").eq("status", "failed").execute()
        
        doc_ids = [d["document_id"] for d in (result.data or [])]
        
        if not doc_ids:
            return {"message": "No failed documents found"}
            
        async def process_batch(ids):
            for doc_id in ids:
                await pipeline.run_full_pipeline(doc_id)
                
        background_tasks.add_task(process_batch, doc_ids)
        
        return {
            "message": f"Retry started for {len(doc_ids)} documents",
            "document_ids": doc_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-pending")
async def index_pending_documents(background_tasks: BackgroundTasks):
    """Process all documents with 'ingested' status."""
    try:
        db = pipeline.collector.db
        result = db.table("documents").select("document_id").eq("status", "ingested").execute()
        
        doc_ids = [d["document_id"] for d in (result.data or [])]
        
        if not doc_ids:
            return {"message": "No pending documents found"}
            
        async def process_batch(ids):
            for doc_id in ids:
                await pipeline.run_full_pipeline(doc_id)
                
        background_tasks.add_task(process_batch, doc_ids)
        
        return {
            "message": f"Processing started for {len(doc_ids)} pending documents",
            "document_ids": doc_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{document_id}")
async def get_ingestion_status(document_id: str):
    """Get document ingestion status."""
    try:
        db = pipeline.collector.db
        
        doc = db.table("documents").select("*").eq("document_id", document_id).execute()
        chunks = db.table("chunks").select("*", count="exact").eq("document_id", document_id).execute()
        embeddings = db.table("embeddings").select("*", count="exact").eq("chunk_id", 
            db.table("chunks").select("chunk_id").eq("document_id", document_id)
        ).execute()
        
        if not doc.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "document_id": document_id,
            "status": doc.data[0].get("status"),
            "title": doc.data[0].get("title"),
            "chunks_count": chunks.count if hasattr(chunks, 'count') else 0,
            "embeddings_count": embeddings.count if hasattr(embeddings, 'count') else 0,
            "ingested_at": doc.data[0].get("ingested_at"),
            "parsed_at": doc.data[0].get("parsed_at"),
            "indexed_at": doc.data[0].get("indexed_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_pipeline_stats():
    """Get ingestion pipeline statistics."""
    try:
        db = pipeline.collector.db
        
        # Document counts by status
        total = db.table("documents").select("*", count="exact").execute()
        ingested = db.table("documents").select("*", count="exact").eq("status", "ingested").execute()
        parsed = db.table("documents").select("*", count="exact").eq("status", "parsed").execute()
        indexed = db.table("documents").select("*", count="exact").eq("status", "indexed").execute()
        failed = db.table("documents").select("*", count="exact").eq("status", "failed").execute()
        
        # Recent documents (24h)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        recent = db.table("documents").select("*", count="exact").gte(
            "ingested_at", since.isoformat()
        ).execute()
        
        return {
            "total_documents": total.count if hasattr(total, 'count') else 0,
            "by_status": {
                "ingested": ingested.count if hasattr(ingested, 'count') else 0,
                "parsed": parsed.count if hasattr(parsed, 'count') else 0,
                "indexed": indexed.count if hasattr(indexed, 'count') else 0,
                "failed": failed.count if hasattr(failed, 'count') else 0
            },
            "recent_24h": recent.count if hasattr(recent, 'count') else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Phase B: Serving Routes ============

@router.post("/query")
async def process_query(data: dict):
    """Process user query through serving pipeline.
    
    Pipeline: Request → Cache → Reasoning → Retrieval → Reranker → Generation & Guardrail
    """
    try:
        query = data.get("query")
        use_cache = data.get("use_cache", True)
        top_k = data.get("top_k", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Trace with LangSmith
        start_time = datetime.now(timezone.utc)
        
        # Process query
        result = await query_engine.process_query(
            query=query,
            use_cache=use_cache,
            top_k=top_k
        )
        
        # Calculate latency
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Trace
        if tracer.is_enabled():
            tracer.trace_rag_pipeline(
                query=query,
                query_type=result.query_type,
                retrieved_chunks=[
                    {
                        "chunk_id": c.chunk_id,
                        "document_title": c.document_title,
                        "snippet": c.chunk_text[:200]
                    }
                    for c in []  # Would need to pass actual chunks
                ],
                answer=result.answer,
                confidence=result.confidence,
                latency_ms=latency_ms
            )
        
        return {
            "query": result.query,
            "query_type": result.query_type,
            "answer": result.answer,
            "citations": result.citations,
            "confidence": result.confidence,
            "groundedness_score": result.groundedness_score,
            "hallucination_flag": result.hallucination_flag,
            "processing_time_ms": result.processing_time_ms,
            "cache_hit": result.cache_hit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def stream_query(data: dict):
    """Stream query processing (for real-time UI updates)."""
    # TODO: Implement SSE streaming
    pass


@router.get("/query/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        redis = query_engine.cache.redis
        
        # Get Redis info
        info = redis.info()
        
        # Count query cache keys
        keys = redis.keys("query:*")
        
        return {
            "total_cached_queries": len(keys),
            "redis_used_memory": info.get("used_memory_human", "N/A"),
            "redis_connected_clients": info.get("connected_clients", 0),
            "ttl_seconds": query_engine.cache.ttl_seconds
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/query/cache")
async def clear_cache():
    """Clear query cache."""
    try:
        redis = query_engine.cache.redis
        keys = redis.keys("query:*")
        
        if keys:
            redis.delete(*keys)
        
        return {
            "message": "Cache cleared",
            "deleted_keys": len(keys)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Architecture Overview ============

@router.get("/architecture")
async def get_architecture():
    """Get system architecture overview."""
    return {
        "name": "FSC Policy RAG System",
        "version": "2.0.0",
        "phases": {
            "phase_a": {
                "name": "Data Ingestion (LLM Ops)",
                "components": [
                    {
                        "name": "Collector",
                        "description": "금융위 RSS 1일 4회 체크",
                        "technology": "Python + feedparser"
                    },
                    {
                        "name": "Parser",
                        "description": "PDF/HWP를 마크다운으로 변환",
                        "technology": "LlamaParse API"
                    },
                    {
                        "name": "Chunker",
                        "description": "문맥 보존 청킹 + 업권 메타데이터",
                        "technology": "LangChain"
                    },
                    {
                        "name": "Embedder",
                        "description": "문장을 벡터로 변환",
                        "technology": "OpenAI + Supabase(pgvector)"
                    }
                ]
            },
            "phase_b": {
                "name": "Serving Service (FastAPI + Redis)",
                "components": [
                    {
                        "name": "Cache Layer",
                        "description": "동일 질문 캐싱",
                        "technology": "Upstash Redis"
                    },
                    {
                        "name": "Reasoning",
                        "description": "질문 유형 판단 + Query Expansion",
                        "technology": "LangGraph Agent"
                    },
                    {
                        "name": "Retrieval",
                        "description": "Hybrid Search (BM25 + Vector)",
                        "technology": "Supabase pgvector"
                    },
                    {
                        "name": "Reranker",
                        "description": "Top-k 재정렬",
                        "technology": "Cross-Encoder"
                    },
                    {
                        "name": "Generation & Guardrail",
                        "description": "근거 문단 태그 + 환각 체크",
                        "technology": "OpenAI GPT-4"
                    }
                ]
            }
        },
        "observability": {
            "langsmith": tracer.is_enabled(),
            "tracing": [
                "Query Classification",
                "Retrieval Steps",
                "LLM Calls",
                "Verification Loops"
            ]
        }
    }
