"""
Evaluation & Advanced Agent API Routes
RAGAS 평가 및 LangGraph 에이전트 엔드포인트
KAI(핵심 성과 지표) 목표치는 competition 문서 page_29 기준.
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging

from app.constants.kai_targets import get_kai_targets_summary, check_kai_pass, KAI_TARGETS
from app.core.config import settings

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluationRequest(BaseModel):
    """평가 요청 모델 — 기본 10건(골든 소규모). RAGAS·LLM 비용·시간 고려."""
    sample_size: int = Field(default=10, ge=1, le=30, description="평가 샘플 수 (권장 10)")


class AgentQuestionRequest(BaseModel):
    """에이전트 질문 요청"""
    question: str
    use_agent: bool = True


def _run_ragas_in_thread(sample_size: int) -> None:
    """별도 스레드에서 새 이벤트 루프를 만들어 RAGAS 평가 실행 (메인 서버 루프 블로킹 방지)."""
    import asyncio
    import threading
    from app.services.ragas_evaluator import ragas_evaluator
    cap = min(sample_size, getattr(settings, "RAGAS_TEST_SIZE", 10), 30)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ragas_evaluator.evaluate_system(sample_size=cap))
    except Exception as e:
        logging.error(f"RAGAS background evaluation error: {e}")
    finally:
        loop.close()


@router.post("/run")
async def run_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
):
    """
    RAGAS 평가 실행.
    장시간 소요 시 타임아웃을 피하기 위해 백그라운드 스레드에서 실행하고 202를 반환합니다.
    결과는 GET /evaluation/latest 로 폴링하거나, 설정 화면 새로고침으로 확인하세요.
    """
    import threading
    from fastapi.responses import JSONResponse

    def _start_thread():
        t = threading.Thread(target=_run_ragas_in_thread, args=(request.sample_size,), daemon=True)
        t.start()

    background_tasks.add_task(_start_thread)
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "평가가 백그라운드에서 실행 중입니다. 1~2분 후 설정 화면을 새로고침하거나, 평가 이력에서 결과를 확인하세요.",
            "evaluation": None,
            "details": None,
        },
    )


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


@router.get("/kai-targets")
async def get_kai_targets():
    """
    KAI(핵심 성과 지표) 목표치 조회.
    competition 문서 page_29 파일럿 검증 계획 기준: Hallucination <5%, 정확도 >95%, 응답 <3초, 만족도 >4.0
    """
    return get_kai_targets_summary()


@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    공모전용 성능 지표 요약
    
    Returns:
        시스템 전체 성능 지표 및 벤치마크 비교
    """
    from app.core.cache_helper import cache_get, cache_set, CACHE_TTL_METRICS_SUMMARY
    _mk = "evaluation:metrics_summary:v1"
    _mc = cache_get(_mk)
    if _mc is not None and isinstance(_mc, dict):
        return _mc
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

            # KAI 목표 충족 여부 (page_29: Hallucination <5%, 정확도 >95% 등)
            kai_hallucination_pass = hallucination_rate_recent is not None and check_kai_pass(hallucination_rate_recent, "hallucination_rate_pct")
            accuracy_pct = (avg_faithfulness * 100) if avg_faithfulness else None
            kai_accuracy_pass = accuracy_pct is not None and check_kai_pass(accuracy_pct, "accuracy_pct")

            rag_metrics = {
                "avg_faithfulness": round(avg_faithfulness, 4),
                "avg_answer_relevancy": round(avg_relevancy, 4),
                "avg_context_precision": round(avg_precision, 4),
                "avg_context_recall": round(avg_recall, 4),
                "avg_overall_score": round(avg_overall, 4),
                "evaluation_count": len(eval_history),
                "hallucination_rate_recent_pct": hallucination_rate_recent,
                "hallucination_goal_pct": 5.0,
                "kai": {
                    "hallucination_target_met": kai_hallucination_pass,
                    "accuracy_pct": round(accuracy_pct, 2) if accuracy_pct is not None else None,
                    "accuracy_target_met": kai_accuracy_pass,
                },
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
                "kai": {
                    "hallucination_target_met": None,
                    "accuracy_pct": None,
                    "accuracy_target_met": None,
                },
                "note": "평가 데이터 없음 - /evaluation/run 실행 필요",
            }
        
        payload = {
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
        try:
            cache_set(_mk, payload, CACHE_TTL_METRICS_SUMMARY)
        except Exception:
            pass
        return payload
    except Exception as e:
        logging.error(f"Metrics summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
