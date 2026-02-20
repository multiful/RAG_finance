"""Main API routes (legacy + new combined)."""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging
import traceback

from app.core.config import settings
from app.models.schemas import (
    DocumentListResponse, DocumentResponse,
    QARequest, QAResponse,
    IndustryClassificationRequest, IndustryClassificationResponse,
    TopicResponse, TopicListResponse, AlertResponse,
    ChecklistRequest, ChecklistResponse,
    DashboardStats, QualityMetrics, CollectionStatus
)
from app.services.rss_collector import RSSCollector
from app.services.rag_service import RAGService
from app.services.industry_classifier import IndustryClassifier
from app.services.topic_detector import TopicDetector
from app.services.checklist_service import ChecklistService
from app.services.fss_scraper import fss_scraper
from app.observability.langsmith_tracer import get_tracer

router = APIRouter()

# Initialize services
rss_collector = RSSCollector()
rag_service = RAGService()
industry_classifier = IndustryClassifier()
topic_detector = TopicDetector()
checklist_service = ChecklistService()
tracer = get_tracer()


# ==================== Document Routes ====================

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    days: Optional[int] = None
):
    """List documents with pagination and filtering."""
    try:
        db = rss_collector.db
        query = db.table("documents").select("*", count="exact")
        
        if category:
            query = query.eq("category", category)
        
        if days:
            since = datetime.now() - timedelta(days=days)
            query = query.gte("published_at", since.isoformat())
        
        # Order and paginate
        query = query.order("published_at", desc=True)
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)
        
        result = query.execute()
        
        documents = [
            DocumentResponse(
                document_id=d["document_id"],
                title=d["title"],
                published_at=d["published_at"],
                url=d["url"],
                category=d.get("category"),
                department=d.get("department"),
                status=d["status"],
                ingested_at=d["ingested_at"],
                fail_reason=d.get("fail_reason")
            )
            for d in (result.data or [])
        ]
        
        return DocumentListResponse(
            documents=documents,
            total=result.count if hasattr(result, 'count') else len(documents),
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get a single document by ID."""
    try:
        db = rss_collector.db
        result = db.table("documents").select("*").eq("document_id", document_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        d = result.data[0]
        return DocumentResponse(
            document_id=d["document_id"],
            title=d["title"],
            published_at=d["published_at"],
            url=d["url"],
            category=d.get("category"),
            department=d.get("department"),
            status=d["status"],
            ingested_at=d["ingested_at"],
            fail_reason=d.get("fail_reason")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Collection Routes ====================

async def _run_all_collection(job_id: str):
    """Run both FSC RSS and FSS scraping."""
    # First collect FSC RSS
    await rss_collector.collect_all(job_id=job_id)
    # Then collect FSS (금감원)
    try:
        await fss_scraper.collect_all()
    except Exception as e:
        logging.error(f"FSS scraping failed: {e}")


@router.post("/collection/trigger")
async def trigger_collection(background_tasks: BackgroundTasks):
    """Trigger RSS collection (FSC + FSS) in background with job tracking."""
    try:
        from app.services.job_tracker import job_tracker
        job_id = job_tracker.create_job()
        if not job_id:
            raise HTTPException(status_code=503, detail="Redis connection failed. Job tracking unavailable.")
        
        background_tasks.add_task(_run_all_collection, job_id)
        
        return {
            "message": "Collection started (FSC + FSS)",
            "job_id": job_id,
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collection/trigger-fss")
async def trigger_fss_collection(background_tasks: BackgroundTasks):
    """Trigger FSS (금융감독원) scraping only."""
    try:
        background_tasks.add_task(fss_scraper.collect_all)
        return {
            "message": "FSS scraping started",
            "status": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/jobs/latest")
async def get_latest_job():
    """Get status of the most recent collection job."""
    from app.services.job_tracker import job_tracker
    job_id = job_tracker.get_latest_job_id()
    if not job_id:
        return {"message": "No jobs found"}
    
    job = job_tracker.get_job(job_id)
    if not job:
        return {"message": "Job details not found"}
    return job


@router.get("/collection/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific collection job."""
    from app.services.job_tracker import job_tracker
    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/collection/status")
async def get_collection_status():
    """Get RSS collection status."""
    try:
        stats = await rss_collector.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/recent")
async def get_recent_documents(hours: int = Query(24, ge=1, le=168)):
    """Get documents collected in recent hours."""
    try:
        documents = await rss_collector.get_recent_documents(hours)
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Retrieval Routes ====================

@router.get("/search")
async def search_documents(
    query: str = Query(..., min_length=2),
    top_k: int = Query(5, ge=1, le=20),
    category: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    """Basic retrieval search (Hybrid)."""
    try:
        # Get query embedding
        query_embedding = await rag_service._get_embedding(query)
        
        # Build filters
        filters = {}
        if category: filters["category"] = category
        if date_from: filters["date_from"] = date_from.isoformat()
        if date_to: filters["date_to"] = date_to.isoformat()
        
        # Perform hybrid search
        results = await rag_service.vector_store.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters
        )
        
        return {
            "query": query,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "title": r.document_title,
                    "url": r.url,
                    "published_at": r.published_at,
                    "snippet": r.chunk_text[:300],
                    "score": r.similarity,
                    "metadata": r.metadata
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RAG QA Routes ====================

@router.post("/qa", response_model=QAResponse)
async def answer_question(request: QARequest):
    """Answer question using RAG."""
    try:
        start_time = datetime.now()
        
        response = await rag_service.answer_question(request)
        
        # Trace with LangSmith
        if tracer.is_enabled():
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tracer.trace_rag_pipeline(
                query=request.question,
                query_type="qa",
                retrieved_chunks=[
                    {
                        "chunk_id": c.chunk_id,
                        "document_title": c.document_title,
                        "snippet": c.snippet,
                        "url": c.url
                    }
                    for c in response.citations
                ],
                answer=response.answer,
                confidence=response.confidence,
                latency_ms=latency_ms
            )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa/stream")
async def answer_question_stream(request: QARequest):
    """Answer question using RAG with streaming."""
    from fastapi.responses import StreamingResponse
    try:
        return StreamingResponse(
            rag_service.stream_answer(request),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Industry Classification Routes ====================

@router.post("/classify", response_model=IndustryClassificationResponse)
async def classify_industry(request: IndustryClassificationRequest):
    """Classify document by industry impact."""
    try:
        response = await industry_classifier.classify(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/industry")
async def get_document_industry_classification(document_id: str):
    """Get industry classification for a document."""
    try:
        request = IndustryClassificationRequest(document_id=document_id)
        response = await industry_classifier.classify(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Topic/Alert Routes ====================

@router.get("/topics", response_model=TopicListResponse)
async def list_topics(
    days: int = Query(7, ge=1, le=30),
    detect: bool = Query(False)
):
    """List detected topics."""
    try:
        if detect:
            # Run detection first
            topics = await topic_detector.detect_surging_topics(days)
        else:
            # Get from database
            db = topic_detector.db
            since = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = db.table("topics").select("*").gte(
                "time_window_start", since.isoformat()
            ).order("created_at", desc=True).execute()
            
            topics = []
            if result.data:
                for t in result.data:
                    # Get document count
                    count_result = db.table("topic_memberships").select(
                        "count", count="exact"
                    ).eq("topic_id", t["topic_id"]).execute()
                    
                    # Get representative documents
                    docs_result = db.table("topic_memberships").select(
                        "documents(document_id, title, url, published_at)"
                    ).eq("topic_id", t["topic_id"]).limit(3).execute()
                    
                    rep_docs = []
                    if docs_result.data:
                        for d in docs_result.data:
                            doc = d.get("documents", {})
                            if doc:
                                rep_docs.append({
                                    "document_id": doc.get("document_id"),
                                    "title": doc.get("title"),
                                    "url": doc.get("url"),
                                    "published_at": doc.get("published_at")
                                })
                    
                    # Fetch surge score from alerts if available
                    alert_res = db.table("alerts").select("surge_score").eq("topic_id", t["topic_id"]).execute()
                    surge_score = alert_res.data[0]["surge_score"] if alert_res.data else 0.0

                    topics.append(TopicResponse(
                        topic_id=t["topic_id"],
                        topic_name=t.get("topic_name"),
                        topic_summary=t.get("topic_summary"),
                        time_window_start=t["time_window_start"],
                        time_window_end=t["time_window_end"],
                        document_count=count_result.count if hasattr(count_result, 'count') else 0,
                        surge_score=surge_score,
                        representative_documents=rep_docs
                    ))
        
        return TopicListResponse(topics=topics, topics_detected=len(topics))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = "open"
):
    """List alerts."""
    try:
        db = topic_detector.db
        query = db.table("alerts").select("*, topics(topic_name)")
        
        if severity:
            query = query.eq("severity", severity)
        if status:
            query = query.eq("status", status)
        
        result = query.order("surge_score", desc=True).execute()
        
        alerts = []
        if result.data:
            for item in result.data:
                alerts.append(AlertResponse(
                    alert_id=item["alert_id"],
                    topic_id=item["topic_id"],
                    topic_name=item.get("topics", {}).get("topic_name"),
                    surge_score=item["surge_score"],
                    severity=item["severity"],
                    industries=item.get("industries", []),
                    generated_at=item["generated_at"],
                    status=item["status"]
                ))
        
        return alerts
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/detect", response_model=TopicListResponse)
async def detect_topics(days: int = Query(7, ge=1, le=30)):
    """Manually trigger topic detection."""
    try:
        topics = await topic_detector.detect_surging_topics(days)
        return TopicListResponse(topics=topics, topics_detected=len(topics))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Checklist Routes ====================

@router.post("/checklists", response_model=ChecklistResponse)
async def generate_checklist(request: ChecklistRequest):
    """Generate compliance checklist for document."""
    try:
        # Check if exists
        existing = await checklist_service.get_checklist_by_document(request.document_id)
        if existing:
            return existing
        
        # Generate new
        response = await checklist_service.extract_checklist(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/checklist", response_model=ChecklistResponse)
async def get_document_checklist(document_id: str):
    """Get checklist for a document."""
    try:
        checklist = await checklist_service.get_checklist_by_document(document_id)
        if not checklist:
            # Generate new
            request = ChecklistRequest(document_id=document_id)
            checklist = await checklist_service.extract_checklist(request)
        return checklist
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/checklist/export")
async def export_checklist(document_id: str, format: str = Query("json")):
    """Export checklist in various formats."""
    try:
        checklist = await checklist_service.get_checklist_by_document(document_id)
        if not checklist:
            raise HTTPException(status_code=404, detail="Checklist not found")
        
        content = checklist_service.export_checklist(checklist, format)
        
        from fastapi.responses import PlainTextResponse
        
        content_type = "application/json" if format == "json" else "text/plain"
        return PlainTextResponse(content=content, media_type=content_type)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Dashboard Routes ====================

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics."""
    from app.models.schemas import CollectionStatus
    try:
        db = rss_collector.db
        
        # Collection stats (total docs, documents_24h, success_rate_7d)
        collection_stats = await rss_collector.get_collection_stats()
        
        # Active alerts
        alerts_result = db.table("alerts").select("*", count="exact").eq(
            "status", "open"
        ).execute()
        active_alerts_count = (alerts_result.count if hasattr(alerts_result, 'count') else 0) or 0
        
        high_severity_res = db.table("alerts").select("*", count="exact").eq(
            "status", "open"
        ).eq("severity", "high").execute()
        high_severity_count = (high_severity_res.count if hasattr(high_severity_res, 'count') else 0) or 0
        
        # Recent topics (last 7 days)
        since_topic = datetime.now(timezone.utc) - timedelta(days=7)
        topics_result = db.table("topics").select("*").gte(
            "time_window_start", since_topic.isoformat()
        ).order("created_at", desc=True).limit(5).execute()
        
        topics = []
        if topics_result.data:
            for t in topics_result.data:
                # Get document count for each topic
                count_res = db.table("topic_memberships").select("count", count="exact").eq("topic_id", t["topic_id"]).execute()
                
                # Check for alert to get surge score if available
                alert_res = db.table("alerts").select("surge_score").eq("topic_id", t["topic_id"]).execute()
                surge_score = alert_res.data[0]["surge_score"] if alert_res.data else 0.0

                topics.append(TopicResponse(
                    topic_id=t["topic_id"],
                    topic_name=t.get("topic_name") or "New Topic",
                    topic_summary=t.get("topic_summary"),
                    time_window_start=t["time_window_start"],
                    time_window_end=t["time_window_end"],
                    document_count=(count_res.count if hasattr(count_res, 'count') else 0) or 0,
                    surge_score=surge_score,
                    representative_documents=[]
                ))
        
        # Collection status per source (defined in FSC_RSS_FIDS)
        sources = []
        # Get actual source records to get their UUIDs
        sources_records = db.table("sources").select("*").in_("fid", settings.FSC_RSS_FIDS).execute()
        
        # Pre-calculate timestamps
        now_utc = datetime.now(timezone.utc)
        since_24h = (now_utc - timedelta(hours=24)).isoformat()
        since_7d = (now_utc - timedelta(days=7)).isoformat()

        for source_rec in (sources_records.data or []):
            source_id = source_rec["source_id"]
            fid = source_rec.get("fid")
            
            # Count from DB
            source_docs = db.table("documents").select("*", count="exact").eq(
                "source_id", source_id
            ).execute()
            
            recent = db.table("documents").select("*", count="exact").eq(
                "source_id", source_id
            ).gte("ingested_at", since_24h).execute()
            
            # Calculate success rate
            source_week = db.table("documents").select("status").eq(
                "source_id", source_id
            ).gte("ingested_at", since_7d).execute()
            
            total_week = len(source_week.data) if source_week.data else 0
            failed_week = sum(1 for d in source_week.data if d.get("status") == "failed") if source_week.data else 0
            success_rate = (total_week - failed_week) / total_week * 100 if total_week > 0 else 100.0

            sources.append(CollectionStatus(
                source_id=fid,
                source_name=source_rec.get("name") or f"Source {fid}",
                last_fetch=now_utc,
                new_documents_24h=(recent.count if hasattr(recent, 'count') else 0) or 0,
                total_documents=(source_docs.count if hasattr(source_docs, 'count') else 0) or 0,
                success_rate_7d=success_rate,
                parsing_failures_24h=0
            ))
        
        return DashboardStats(
            total_documents=collection_stats["total_documents"] or 0,
            documents_24h=collection_stats["documents_24h"] or 0,
            active_alerts=active_alerts_count,
            high_severity_alerts=high_severity_count,
            collection_status=sources,
            recent_topics=topics,
            quality_metrics=None
        )
    
    except Exception as e:
        logging.error(f"Error in get_dashboard_stats: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Dashboard stats error: {str(e)}")


@router.get("/dashboard/hourly-stats")
async def get_hourly_collection_stats(hours: int = Query(24, ge=1, le=168)):
    """Get hourly document collection statistics for charts."""
    try:
        db = rss_collector.db
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get documents with timestamps
        docs_result = db.table("documents").select(
            "document_id, ingested_at, source_id, status"
        ).gte("ingested_at", since.isoformat()).execute()
        
        # Group by hour
        hourly_data = {}
        for i in range(hours):
            hour_key = (datetime.now(timezone.utc) - timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
            hourly_data[hour_key] = {"hour": hour_key, "count": 0, "success": 0, "failed": 0}
        
        for doc in (docs_result.data or []):
            ingested = doc.get("ingested_at")
            if ingested:
                hour_key = datetime.fromisoformat(ingested.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:00")
                if hour_key in hourly_data:
                    hourly_data[hour_key]["count"] += 1
                    if doc.get("status") == "completed":
                        hourly_data[hour_key]["success"] += 1
                    else:
                        hourly_data[hour_key]["failed"] += 1
        
        # Get source distribution
        sources_result = db.table("sources").select("source_id, name").execute()
        source_names = {s["source_id"]: s["name"] for s in (sources_result.data or [])}
        
        source_counts = {}
        for doc in (docs_result.data or []):
            sid = doc.get("source_id")
            name = source_names.get(sid, "Unknown")
            source_counts[name] = source_counts.get(name, 0) + 1
        
        return {
            "hourly": sorted(hourly_data.values(), key=lambda x: x["hour"]),
            "by_source": [{"name": k, "count": v} for k, v in source_counts.items()],
            "total": len(docs_result.data or []),
            "period_hours": hours
        }
    except Exception as e:
        logging.error(f"Error in hourly stats: {str(e)}")
        return {"hourly": [], "by_source": [], "total": 0, "period_hours": hours}


@router.get("/dashboard/quality")
async def get_quality_metrics(days: int = Query(7, ge=1, le=30)):
    """Get quality metrics for RAG system from actual QA logs."""
    try:
        db = rss_collector.db
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get QA logs from database
        qa_result = db.table("qa_logs").select("*").gte(
            "created_at", since.isoformat()
        ).execute()
        
        qa_logs = qa_result.data or []
        
        if not qa_logs:
            # Return baseline metrics if no logs yet
            return QualityMetrics(
                date=datetime.now(timezone.utc),
                groundedness=0.0,
                hallucination_rate=0.0,
                avg_response_time_ms=0,
                citation_accuracy=0.0,
                unanswered_rate=0.0
            )
        
        # Calculate actual metrics
        total_queries = len(qa_logs)
        
        groundedness_scores = [log.get("groundedness_score", 0) or 0 for log in qa_logs]
        avg_groundedness = sum(groundedness_scores) / total_queries if total_queries > 0 else 0
        
        response_times = [log.get("response_time_ms", 0) or 0 for log in qa_logs]
        avg_response_time = int(sum(response_times) / total_queries) if total_queries > 0 else 0
        
        citation_scores = [log.get("citation_coverage", 0) or 0 for log in qa_logs]
        avg_citation = sum(citation_scores) / total_queries if total_queries > 0 else 0
        
        # Calculate hallucination rate (confidence < 0.4)
        low_confidence = sum(1 for log in qa_logs if (log.get("confidence", 1) or 1) < 0.4)
        hallucination_rate = low_confidence / total_queries if total_queries > 0 else 0
        
        # Calculate unanswered rate
        unanswered = sum(1 for log in qa_logs if log.get("status") == "failed" or not log.get("answer"))
        unanswered_rate = unanswered / total_queries if total_queries > 0 else 0
        
        return QualityMetrics(
            date=datetime.now(timezone.utc),
            groundedness=round(avg_groundedness, 2),
            hallucination_rate=round(hallucination_rate, 2),
            avg_response_time_ms=avg_response_time,
            citation_accuracy=round(avg_citation, 2),
            unanswered_rate=round(unanswered_rate, 2)
        )
        
    except Exception as e:
        logging.error(f"Error calculating quality metrics: {str(e)}")
        # Return zeros instead of mock data on error
        return QualityMetrics(
            date=datetime.now(timezone.utc),
            groundedness=0.0,
            hallucination_rate=0.0,
            avg_response_time_ms=0,
            citation_accuracy=0.0,
            unanswered_rate=0.0
        )
