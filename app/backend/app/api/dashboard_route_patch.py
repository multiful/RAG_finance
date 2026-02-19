@router.get("/dashboard/quality")
async def get_quality_metrics(days: int = Query(7, ge=1, le=30)):
    """Get real-time quality metrics from evaluation pipeline."""
    try:
        db = pipeline.collector.db
        
        # Real aggregation query
        query = f"""
            SELECT 
                AVG(metric_groundedness) as avg_groundedness,
                AVG(metric_citation_precision) as avg_citation,
                AVG(metric_hallucination_rate) as avg_hallucination,
                COUNT(*) as count
            FROM eval_results
            WHERE created_at > NOW() - INTERVAL '{days} days'
        """
        
        result = db.rpc("exec_sql", {"sql": query}).execute()
        data = result.data[0] if result.data else {}
        
        return QualityMetrics(
            date=datetime.now(),
            groundedness=data.get("avg_groundedness") or 0.0,
            hallucination_rate=data.get("avg_hallucination") or 0.0,
            avg_response_time_ms=0, # Logged in DB but not aggregated yet
            citation_accuracy=data.get("avg_citation") or 0.0,
            unanswered_rate=0.0 # Placeholder until log analysis added
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
