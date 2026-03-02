from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from app.models.schemas import (
    PolicySimulationRequest, 
    PolicyDiffResponse, 
    GovernanceMetricsResponse
)
from datetime import datetime

router = APIRouter()

@router.get("/dashboard/quality", response_model=GovernanceMetricsResponse)
async def get_quality(days: int = Query(7, ge=1, le=30)):
    """Get real-time quality metrics from evaluation results."""
    try:
        from app.evaluation.pipeline import pipeline as eval_pipeline
        db = eval_pipeline.db
        sql = f"""
            SELECT 
                AVG(metric_groundedness) as g, 
                AVG(metric_citation_precision) as c, 
                AVG(metric_hallucination_rate) as h, 
                COUNT(*) as s 
            FROM eval_results 
            WHERE created_at > NOW() - INTERVAL '{days} days'
        """
        # Execute query via exec_sql RPC
        res = db.rpc("exec_sql", {"sql": sql}).execute()
        d = res.data[0] if res.data else {}
        return {
            "avg_groundedness": d.get("g") or 0.0,
            "avg_citation_accuracy": d.get("c") or 0.0,
            "avg_hallucination_rate": d.get("h") or 0.0,
            "sample_size": d.get("s") or 0,
            "last_updated": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/daily-job")
async def daily_job(background_tasks: BackgroundTasks):
    """Trigger RSS ingestion and pending evaluation batch."""
    try:
        from app.pipeline.ingestion import get_ingestion_pipeline
        from app.evaluation.pipeline import pipeline as eval_pipeline
        
        ingest = get_ingestion_pipeline()
        # Trigger ingestion in background
        background_tasks.add_task(ingest.run_scheduled_collection)
        # Trigger evaluation pipeline in background
        background_tasks.add_task(eval_pipeline.run_batch_evaluation)
        return {
            "message": "Maintenance started in background",
            "tasks": ["rss_ingestion", "evaluation_pipeline"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/policy/simulate", response_model=PolicyDiffResponse)
async def simulate_policy(req: PolicySimulationRequest):
    """두 정책 문서(실제 DB 문서) 간 규제 변경 영향 시뮬레이션."""
    try:
        from app.core.database import get_db
        db = get_db()
        for doc_id, label in [(req.old_document_id, "기준 문서"), (req.new_document_id, "비교 문서")]:
            r = db.table("documents").select("document_id").eq("document_id", doc_id).execute()
            if not r.data:
                raise HTTPException(status_code=404, detail=f"{label}(ID: {doc_id})를 찾을 수 없습니다. 문서 목록을 새로고침하세요.")
        from app.services.policy_simulator import simulator
        return await simulator.simulate(req.old_document_id, req.new_document_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
