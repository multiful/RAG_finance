"""유지보수·스케줄 작업 트리거 API."""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.pipeline.ingestion import get_ingestion_pipeline

router = APIRouter()
_log = logging.getLogger(__name__)
pipeline = get_ingestion_pipeline()


@router.post("/maintenance/daily-job")
async def trigger_daily_maintenance(background_tasks: BackgroundTasks):
    """Trigger daily maintenance tasks: RSS Ingestion + Eval Batch."""
    try:
        from app.evaluation.pipeline import pipeline as eval_pipeline

        # 1. Trigger RSS Collection
        background_tasks.add_task(pipeline.run_scheduled_collection)

        # 2. Trigger Evaluation Batch
        async def run_eval():
            res = await eval_pipeline.run_batch_evaluation()
            _log.info("Maintenance eval batch completed: %s", res)

        background_tasks.add_task(run_eval)

        return {
            "status": "triggered",
            "tasks": ["rss_collection", "evaluation_batch"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
