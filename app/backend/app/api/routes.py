"""Main API routes (legacy + new combined)."""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.schemas import (
    DocumentListResponse, DocumentResponse,
    QARequest, QAResponse,
    IndustryClassificationRequest, IndustryClassificationResponse,
    TopicResponse, AlertResponse,
    ChecklistRequest, ChecklistResponse,
    DashboardStats, QualityMetrics
)
from app.services.rss_collector import RSSCollector
from app.services.rag_service import RAGService
from app.services.industry_classifier import IndustryClassifier
from app.services.topic_detector import TopicDetector
from app.services.checklist_service import ChecklistService
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

@router.post("/collection/trigger")
async def trigger_collection(background_tasks: BackgroundTasks):
    """Trigger RSS collection in background."""
    try:
        background_tasks.add_task(rss_collector.collect_all)
        return {"message": "Collection started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

@router.get("/topics", response_model=List[TopicResponse])
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
            since = datetime.now() - timedelta(days=days)
            
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
                            rep_docs.append({
                                "document_id": doc.get("document_id"),
                                "title": doc.get("title"),
                                "url": doc.get("url"),
                                "published_at": doc.get("published_at")
                            })
                    
                    topics.append(TopicResponse(
                        topic_id=t["topic_id"],
                        topic_name=t.get("topic_name"),
                        topic_summary=t.get("topic_summary"),
                        time_window_start=t["time_window_start"],
                        time_window_end=t["time_window_end"],
                        document_count=count_result.count if hasattr(count_result, 'count') else 0,
                        surge_score=0.0,
                        representative_documents=rep_docs
                    ))
        
        return topics
    
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


@router.post("/topics/detect")
async def detect_topics(days: int = Query(7, ge=1, le=30)):
    """Manually trigger topic detection."""
    try:
        topics = await topic_detector.detect_surging_topics(days)
        return {"topics_detected": len(topics), "topics": topics}
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


@router.get("/documents/{document_id}/checklist")
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
    try:
        db = rss_collector.db
        
        # Collection stats
        collection_stats = await rss_collector.get_collection_stats()
        
        # Active alerts
        alerts_result = db.table("alerts").select("count", count="exact").eq(
            "status", "open"
        ).execute()
        
        high_severity = db.table("alerts").select("count", count="exact").eq(
            "status", "open"
        ).eq("severity", "high").execute()
        
        # Recent topics
        since = datetime.now() - timedelta(days=7)
        topics_result = db.table("topics").select("*").gte(
            "time_window_start", since.isoformat()
        ).order("created_at", desc=True).limit(5).execute()
        
        topics = []
        if topics_result.data:
            for t in topics_result.data:
                topics.append(TopicResponse(
                    topic_id=t["topic_id"],
                    topic_name=t.get("topic_name"),
                    topic_summary=t.get("topic_summary"),
                    time_window_start=t["time_window_start"],
                    time_window_end=t["time_window_end"],
                    document_count=0,
                    surge_score=0.0,
                    representative_documents=[]
                ))
        
        # Collection status per source
        sources = []
        for fid in ["0111", "0112", "0114"]:
            source_docs = db.table("documents").select("count", count="exact").eq(
                "source_id", f"FSC_RSS_{fid}"
            ).execute()
            
            recent = db.table("documents").select("count", count="exact").eq(
                "source_id", f"FSC_RSS_{fid}"
            ).gte("ingested_at", (datetime.now() - timedelta(hours=24)).isoformat()).execute()
            
            sources.append({
                "source_id": f"FSC_RSS_{fid}",
                "source_name": rss_collector.RSS_URLS.get(fid, fid),
                "last_fetch": datetime.now(),
                "new_documents_24h": recent.count if hasattr(recent, 'count') else 0,
                "total_documents": source_docs.count if hasattr(source_docs, 'count') else 0,
                "success_rate_7d": 95.0,
                "parsing_failures_24h": 0
            })
        
        return DashboardStats(
            total_documents=collection_stats["total_documents"],
            documents_24h=collection_stats["documents_24h"],
            active_alerts=alerts_result.count if hasattr(alerts_result, 'count') else 0,
            high_severity_alerts=high_severity.count if hasattr(high_severity, 'count') else 0,
            collection_status=sources,
            recent_topics=topics,
            quality_metrics=None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/quality")
async def get_quality_metrics(days: int = Query(7, ge=1, le=30)):
    """Get quality metrics for RAG system."""
    try:
        # This would be calculated from qa_logs in production
        # For now, return mock data
        return QualityMetrics(
            date=datetime.now(),
            groundedness=0.87,
            hallucination_rate=0.08,
            avg_response_time_ms=2500,
            citation_accuracy=0.92,
            unanswered_rate=0.05
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
