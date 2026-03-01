"""Advanced API routes with LangGraph, LlamaParse, Ragas, and LangSmith."""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import tempfile
import os

from app.agents.policy_agent import run_policy_agent
from app.parsers.llama_parser import parse_and_chunk_document
from app.evaluation.ragas_evaluator import get_evaluator, calculate_groundedness, calculate_hallucination_rate
from app.observability.langsmith_tracer import get_tracer, trace_function
from app.services.vector_store import get_vector_store
from app.services.rag_service import RAGService
from app.core.config import settings

router = APIRouter()

# Initialize services
vector_store = get_vector_store()
rag_service = RAGService()
evaluator = get_evaluator()
tracer = get_tracer()


# ============ LangGraph Agent Routes ============

@router.post("/agent/query")
async def agent_query(data: dict):
    """Execute LangGraph agent workflow.
    
    Implements: 분류 -> 추출 -> 검증 (Classification -> Extraction -> Verification)
    
    Request:
        {
            "query": "사용자 질문",
            "document_id": "optional-doc-id"
        }
    
    Response:
        {
            "query_type": "qa|industry_classification|compliance_extract",
            "answer": "...",
            "confidence": 0.85,
            "verification_status": "passed",
            "iterations": 2,
            "retrieved_chunks": [...]
        }
    """
    try:
        query = data.get("query")
        document_id = data.get("document_id")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Trace with LangSmith
        start_time = datetime.now()
        
        # Run agent
        result = await run_policy_agent(query, document_id)
        
        # Calculate latency
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Trace the pipeline
        tracer.trace_rag_pipeline(
            query=query,
            query_type=result.get("query_type", "unknown"),
            retrieved_chunks=result.get("retrieved_chunks", []),
            answer=result.get("answer", ""),
            confidence=result.get("confidence", 0),
            latency_ms=latency_ms
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/trace/{run_id}")
async def get_agent_trace(run_id: str):
    """Get LangSmith trace details."""
    try:
        if not tracer.is_enabled():
            return {"error": "LangSmith tracing not enabled"}
        
        # Get run details from LangSmith
        stats = tracer.get_run_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ LlamaParse Routes ============

@router.post("/parse/document")
async def parse_document(
    file: UploadFile = File(...),
    file_type: str = Query(..., description="File type: pdf, hwp, hwpx")
):
    """PDF/HWP 업로드 → LlamaParse(API 키 있음) 또는 pdfplumber/olefile fallback.
    
    **플로우**: 업로드 파일 임시 저장 → parse_and_chunk_document() → 마크다운·테이블 추출·청킹.
    LLAMAPARSE_API_KEY가 설정되어 있으면 LlamaParse API로 파싱하고, 없으면 로컬 fallback 사용.
    반환 chunks의 metadata.parser에 'llamaparse' | 'pdfplumber' 등 파싱 출처가 포함됨.
    
    Returns:
        filename, file_type, text(전체), chunks(청크 목록), total_chunks, parsing_source(사용된 파서)
    """
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Parse document
            chunks = await parse_and_chunk_document(tmp_path, file_type)
            
            # Combine all text
            full_text = "\n\n".join([c["chunk_text"] for c in chunks])
            
            parsing_source = (
                chunks[0].get("metadata", {}).get("parser", "unknown")
                if chunks else "unknown"
            )
            return {
                "filename": file.filename,
                "file_type": file_type,
                "text": full_text,
                "chunks": chunks,
                "total_chunks": len(chunks),
                "parsing_source": parsing_source,
            }
            
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse/document/{document_id}/index")
async def index_parsed_document(
    document_id: str,
    data: dict,
    background_tasks: BackgroundTasks
):
    """Index parsed document chunks to vector store."""
    try:
        chunks = data.get("chunks", [])
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks provided")
        
        # Generate embeddings and index
        # This would be done in background
        background_tasks.add_task(_index_chunks, document_id, chunks)
        
        return {
            "message": "Indexing started",
            "document_id": document_id,
            "chunk_count": len(chunks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _index_chunks(document_id: str, chunks: List[dict]):
    """Background task to index chunks."""
    from app.services.rag_service import RAGService
    
    rag = RAGService()
    
    # Generate embeddings for each chunk
    chunk_ids = []
    embeddings = []
    
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        text = chunk.get("chunk_text", "")
        
        if chunk_id and text:
            embedding = await rag._get_embedding(text)
            chunk_ids.append(chunk_id)
            embeddings.append(embedding)
    
    # Store embeddings
    if chunk_ids and embeddings:
        await vector_store.add_embeddings(chunk_ids, embeddings)


# ============ Ragas Evaluation Routes ============

@router.post("/evaluate/single")
async def evaluate_single(data: dict):
    """Evaluate a single QA pair using Ragas.
    
    Request:
        {
            "question": "...",
            "answer": "...",
            "contexts": ["context1", "context2"],
            "ground_truth": "expected answer"
        }
    
    Response:
        {
            "groundedness": 0.85,
            "faithfulness": 0.90,
            "answer_relevancy": 0.88,
            "context_precision": 0.82,
            "context_recall": 0.79,
            "overall_score": 0.85
        }
    """
    try:
        question = data.get("question")
        answer = data.get("answer")
        contexts = data.get("contexts", [])
        ground_truth = data.get("ground_truth", "")
        
        if not question or not answer:
            raise HTTPException(status_code=400, detail="Question and answer are required")
        
        # Run evaluation
        scores = await evaluator.evaluate_single(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth=ground_truth
        )
        
        return scores
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/batch")
async def evaluate_batch(data: dict):
    """Evaluate a batch of QA pairs.
    
    Request:
        {
            "test_cases": [
                {
                    "question_id": "q1",
                    "question": "...",
                    "answer": "...",
                    "contexts": [...],
                    "ground_truth": "..."
                },
                ...
            ]
        }
    
    Response:
        {
            "run_id": "run_123",
            "total_questions": 10,
            "avg_groundedness": 0.85,
            "avg_faithfulness": 0.90,
            ...
            "results": [...],
            "suggestions": [...]
        }
    """
    try:
        test_cases = data.get("test_cases", [])
        
        if not test_cases:
            raise HTTPException(status_code=400, detail="No test cases provided")
        
        # Run batch evaluation
        summary = await evaluator.evaluate_batch(test_cases)
        
        return {
            "run_id": summary.run_id,
            "total_questions": summary.total_questions,
            "avg_groundedness": summary.avg_groundedness,
            "avg_faithfulness": summary.avg_faithfulness,
            "avg_answer_relevancy": summary.avg_answer_relevancy,
            "avg_context_precision": summary.avg_context_precision,
            "avg_context_recall": summary.avg_context_recall,
            "avg_overall_score": summary.avg_overall_score,
            "results": [
                {
                    "question_id": r.question_id,
                    "groundedness": r.groundedness,
                    "faithfulness": r.faithfulness,
                    "answer_relevancy": r.answer_relevancy,
                    "context_precision": r.context_precision,
                    "context_recall": r.context_recall,
                    "overall_score": r.overall_score
                }
                for r in summary.results
            ],
            "suggestions": summary.suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/compare")
async def compare_systems(data: dict):
    """Compare multiple system variants.
    
    Request:
        {
            "test_cases": [...],
            "variants": ["baseline", "rag_v1", "rag_v2"]
        }
    """
    try:
        test_cases = data.get("test_cases", [])
        variants = data.get("variants", [])
        
        if not test_cases or not variants:
            raise HTTPException(status_code=400, detail="Test cases and variants required")
        
        results = await evaluator.compare_systems(test_cases, variants)
        
        return {
            variant: {
                "avg_groundedness": summary.avg_groundedness,
                "avg_overall_score": summary.avg_overall_score
            }
            for variant, summary in results.items()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluate/metrics/{run_id}")
async def get_evaluation_metrics(run_id: str):
    """Get detailed metrics for an evaluation run."""
    try:
        db = evaluator.db
        
        # Get run info
        run = db.table("eval_runs").select("*").eq("run_id", run_id).execute()
        
        # Get results
        results = db.table("eval_results").select("*").eq("run_id", run_id).execute()
        
        return {
            "run": run.data[0] if run.data else None,
            "results": results.data or []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ LangSmith Observability Routes ============

@router.get("/observability/status")
async def get_observability_status():
    """Get LangSmith observability status."""
    return {
        "enabled": tracer.is_enabled(),
        "project": settings.LANGSMITH_PROJECT if tracer.is_enabled() else None,
        "endpoint": settings.LANGSMITH_ENDPOINT if tracer.is_enabled() else None
    }


@router.get("/observability/stats")
async def get_observability_stats(
    hours: int = Query(24, ge=1, le=168)
):
    """Get LangSmith run statistics."""
    try:
        if not tracer.is_enabled():
            return {"error": "LangSmith not enabled"}
        
        from datetime import timedelta
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        stats = tracer.get_run_stats(start_time, end_time)
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observability/traces/export")
async def export_traces(
    hours: int = Query(24, ge=1, le=168)
):
    """Export traces to JSON."""
    try:
        if not tracer.is_enabled():
            return {"error": "LangSmith not enabled"}
        
        from datetime import timedelta
        import tempfile
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as tmp:
            tracer.export_traces(tmp.name, start_time, end_time)
            
            return {
                "message": "Traces exported",
                "file_path": tmp.name
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/observability/feedback/{run_id}")
async def add_feedback(run_id: str, data: dict):
    """Add feedback to a traced run.
    
    Request:
        {
            "key": "user_rating",
            "score": 5,
            "comment": "Good answer"
        }
    """
    try:
        if not tracer.is_enabled():
            return {"error": "LangSmith not enabled"}
        
        tracer.add_feedback(
            run_id=run_id,
            key=data.get("key"),
            score=data.get("score"),
            comment=data.get("comment")
        )
        
        return {"message": "Feedback added"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Vector Store Routes ============

@router.post("/vector/search")
async def vector_search(data: dict):
    """Hybrid vector + keyword search.
    
    Request:
        {
            "query": "search text",
            "top_k": 10,
            "vector_weight": 0.7,
            "keyword_weight": 0.3,
            "filters": {
                "date_from": "2024-01-01",
                "date_to": "2024-12-31",
                "category": "press_release"
            }
        }
    """
    try:
        query = data.get("query")
        top_k = data.get("top_k", 10)
        vector_weight = data.get("vector_weight", 0.7)
        keyword_weight = data.get("keyword_weight", 0.3)
        filters = data.get("filters")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Get query embedding
        embedding = await rag_service._get_embedding(query)
        
        # Hybrid search
        results = await vector_store.hybrid_search(
            query=query,
            query_embedding=embedding,
            top_k=top_k,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            filters=filters
        )
        
        return {
            "query": query,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "chunk_text": r.chunk_text[:500],
                    "document_title": r.document_title,
                    "published_at": r.published_at,
                    "url": r.url,
                    "similarity": r.similarity
                }
                for r in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vector/rerank")
async def rerank_results(data: dict):
    """Rerank search results using cross-encoder."""
    try:
        query = data.get("query")
        results_data = data.get("results", [])
        top_k = data.get("top_k", 5)
        
        if not query or not results_data:
            raise HTTPException(status_code=400, detail="Query and results required")
        
        # Convert to SearchResult objects
        from app.services.vector_store import SearchResult
        
        results = [
            SearchResult(
                chunk_id=r.get("chunk_id", ""),
                document_id=r.get("document_id", ""),
                chunk_text=r.get("chunk_text", ""),
                chunk_index=0,
                document_title=r.get("document_title", ""),
                published_at=r.get("published_at", ""),
                url=r.get("url", ""),
                similarity=r.get("similarity", 0),
                metadata={}
            )
            for r in results_data
        ]
        
        # Rerank
        reranked = await vector_store.rerank(query, results, top_k)
        
        return {
            "query": query,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_title": r.document_title,
                    "similarity": r.similarity
                }
                for r in reranked
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector/stats")
async def get_vector_stats():
    """Get vector store statistics."""
    try:
        stats = await vector_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
