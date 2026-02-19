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
            print(f"Maintenance Eval: {res}")
            
        background_tasks.add_task(run_eval)
        
        return {
            "status": "triggered",
            "tasks": ["rss_collection", "evaluation_batch"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
