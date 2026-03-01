"""
Evaluation & Advanced Agent API Routes
RAGAS 평가 및 LangGraph 에이전트 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import logging

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluationRequest(BaseModel):
    """평가 요청 모델"""
    sample_size: int = 16


class AgentQuestionRequest(BaseModel):
    """에이전트 질문 요청"""
    question: str
    use_agent: bool = True


@router.post("/run")
async def run_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks
):
    """
    RAGAS 평가 실행
    
    - 테스트 데이터셋으로 RAG 시스템 평가
    - Faithfulness, Relevancy, Precision, Recall 측정
    """
    try:
        from app.services.ragas_evaluator import ragas_evaluator
        
        result = await ragas_evaluator.evaluate_system(
            sample_size=request.sample_size
        )
        
        return {
            "status": "completed",
            "evaluation": {
                "faithfulness": result.faithfulness,
                "answer_relevancy": result.answer_relevancy,
                "context_precision": result.context_precision,
                "context_recall": result.context_recall,
                "overall_score": result.overall_score,
                "sample_size": result.sample_size,
                "evaluated_at": result.evaluated_at
            },
            "details": result.details
        }
    except Exception as e:
        logging.error(f"Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_evaluation_history(limit: int = Query(10, ge=1, le=50)):
    """평가 이력 조회"""
    try:
        from app.services.ragas_evaluator import ragas_evaluator
        history = await ragas_evaluator.get_evaluation_history(limit)
        return {"history": history}
    except Exception as e:
        logging.error(f"History fetch error: {e}")
        return {"history": []}


@router.get("/latest")
async def get_latest_evaluation():
    """최신 평가 결과 조회"""
    try:
        from app.services.ragas_evaluator import ragas_evaluator
        history = await ragas_evaluator.get_evaluation_history(1)
        
        if history:
            latest = history[0]
            return {
                "has_evaluation": True,
                "evaluation": latest
            }
        
        return {
            "has_evaluation": False,
            "message": "아직 평가가 실행되지 않았습니다."
        }
    except Exception as e:
        logging.error(f"Latest evaluation error: {e}")
        return {"has_evaluation": False, "error": str(e)}


@router.post("/agent/ask")
async def agent_ask_question(request: AgentQuestionRequest):
    """
    LangGraph 멀티 에이전트로 질문 처리
    
    에이전트 파이프라인:
    1. Planner: 질문 분석 및 검색 전략
    2. Retriever: 관련 문서 검색
    3. Analyzer: 답변 초안 작성
    4. Verifier: 답변 검증
    5. Synthesizer: 최종 답변 생성
    """
    try:
        from app.services.langgraph_agent import regulation_agent

        result = await regulation_agent.process_question(request.question)
        raw_citations = result.get("citations") or []

        def norm_citation(c: dict) -> dict:
            pub = c.get("published_at")
            if hasattr(pub, "isoformat"):
                pub = pub.isoformat()
            return {
                "chunk_id": str(c.get("chunk_id", "")),
                "document_id": str(c.get("document_id", "")),
                "document_title": str(c.get("document_title", "")),
                "snippet": str(c.get("snippet", ""))[:500],
                "published_at": str(pub) if pub else "",
                "url": str(c.get("url", "")),
            }

        citations = [norm_citation(x) for x in raw_citations if isinstance(x, dict)]

        return {
            "answer": result.get("answer", ""),
            "citations": citations,
            "confidence": float(result.get("confidence", 0)),
            "groundedness_score": float(result.get("groundedness_score", 0)),
            "citation_coverage": float(result.get("citation_coverage", 0)),
            "metadata": {
                "question_type": str(result.get("question_type", "")),
                "agent_iterations": int(result.get("agent_iterations", 1)),
                "processed_at": str(result.get("processed_at", "")),
                "engine": "langgraph_multi_agent",
            },
        }
    except Exception as e:
        logging.exception("Agent error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    공모전용 성능 지표 요약
    
    Returns:
        시스템 전체 성능 지표 및 벤치마크 비교
    """
    try:
        from app.services.ragas_evaluator import ragas_evaluator
        from app.services.rss_collector import RSSCollector
        
        rss_collector = RSSCollector()
        collection_stats = await rss_collector.get_collection_stats()
        
        eval_history = await ragas_evaluator.get_evaluation_history(5)
        
        if eval_history:
            avg_faithfulness = sum(e.get("faithfulness", 0) for e in eval_history) / len(eval_history)
            avg_relevancy = sum(e.get("answer_relevancy", 0) for e in eval_history) / len(eval_history)
            avg_precision = sum(e.get("context_precision", 0) for e in eval_history) / len(eval_history)
            avg_recall = sum(e.get("context_recall", 0) for e in eval_history) / len(eval_history)
            avg_overall = sum(e.get("overall_score", 0) for e in eval_history) / len(eval_history)
            # 환각률 = 1 - faithfulness (목표 5% 미만)
            hallucination_rate_recent = round((1.0 - avg_faithfulness) * 100, 2)

            rag_metrics = {
                "avg_faithfulness": round(avg_faithfulness, 4),
                "avg_answer_relevancy": round(avg_relevancy, 4),
                "avg_context_precision": round(avg_precision, 4),
                "avg_context_recall": round(avg_recall, 4),
                "avg_overall_score": round(avg_overall, 4),
                "evaluation_count": len(eval_history),
                "hallucination_rate_recent_pct": hallucination_rate_recent,
                "hallucination_goal_pct": 5.0,
            }
        else:
            rag_metrics = {
                "avg_faithfulness": 0,
                "avg_answer_relevancy": 0,
                "avg_context_precision": 0,
                "avg_context_recall": 0,
                "avg_overall_score": 0,
                "evaluation_count": 0,
                "hallucination_rate_recent_pct": None,
                "hallucination_goal_pct": 5.0,
                "note": "평가 데이터 없음 - /evaluation/run 실행 필요",
            }
        
        return {
            "system_name": "RegTech RAG Platform",
            "version": "2.0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_metrics": {
                "total_documents": collection_stats.get("total_documents", 0),
                "documents_24h": collection_stats.get("documents_24h", 0),
                "collection_success_rate": collection_stats.get("success_rate_7d", 100),
                "data_sources": 4
            },
            "rag_metrics": rag_metrics,
            "technology_stack": {
                "llm": "GPT-4o Mini",
                "embedding": "text-embedding-3-small",
                "vector_db": "Supabase pgvector",
                "agent_framework": "LangGraph",
                "evaluation": "RAGAS"
            },
            "features": [
                "멀티 에이전트 RAG (LangGraph)",
                "자동 품질 평가 (RAGAS)",
                "실시간 규제 수집 (RSS)",
                "업권별 영향도 분석",
                "출처 추적 시스템"
            ]
        }
    except Exception as e:
        logging.error(f"Metrics summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
