"""Policy Timeline API routes."""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import List, Optional
from datetime import date

from app.models.schemas import (
    IndustryType, TimelineEvent, TimelineResponse, TimelineExtractRequest
)
from app.services.timeline_extractor import get_timeline_service

router = APIRouter(prefix="/timeline", tags=["Policy Timeline"])


@router.get("/", response_model=TimelineResponse)
async def get_upcoming_events(
    days_ahead: int = Query(90, ge=1, le=365),
    industries: Optional[List[IndustryType]] = Query(None),
    include_past: bool = Query(False)
):
    """Get upcoming policy timeline events.
    
    - **days_ahead**: Number of days to look ahead (default 90)
    - **industries**: Filter by affected industries
    - **include_past**: Include past events (default False)
    """
    service = get_timeline_service()
    return await service.get_upcoming_events(
        days_ahead=days_ahead,
        industries=industries,
        include_past=include_past
    )


@router.get("/range", response_model=List[TimelineEvent])
async def get_events_by_range(
    start_date: date = Query(...),
    end_date: date = Query(...),
    industries: Optional[List[IndustryType]] = Query(None)
):
    """Get timeline events within a date range.
    
    - **start_date**: Start of date range (YYYY-MM-DD)
    - **end_date**: End of date range (YYYY-MM-DD)
    - **industries**: Filter by affected industries
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    service = get_timeline_service()
    return await service.get_events_by_date_range(
        start_date=start_date,
        end_date=end_date,
        industries=industries
    )


@router.post("/extract/{document_id}", response_model=List[TimelineEvent])
async def extract_timeline(
    document_id: str,
    force_refresh: bool = Query(False)
):
    """Extract timeline events from a specific document.
    
    Uses GPT-4 to analyze the document and identify key dates,
    deadlines, and regulatory timelines.
    
    - **document_id**: The document to analyze
    - **force_refresh**: Re-extract even if events already exist
    """
    service = get_timeline_service()
    events = await service.extract_timeline_from_document(
        document_id=document_id,
        force_refresh=force_refresh
    )
    
    if not events:
        raise HTTPException(
            status_code=404,
            detail="Document not found or no timeline events could be extracted"
        )
    
    return events


@router.post("/process-all")
async def process_all_documents():
    """Process all unprocessed documents for timeline extraction.
    
    Scans all documents that haven't been analyzed yet and
    extracts timeline events. This may take a while for large databases.
    """
    service = get_timeline_service()
    processed = await service.process_all_documents()
    
    return {
        "status": "success",
        "documents_processed": processed
    }


@router.get("/critical", response_model=List[TimelineEvent])
async def get_critical_events(
    days_ahead: int = Query(30, ge=1, le=180),
    industries: Optional[List[IndustryType]] = Query(None)
):
    """Get critical upcoming events (deadlines with penalties, etc.)
    
    Returns only events marked as critical within the specified timeframe.
    """
    service = get_timeline_service()
    response = await service.get_upcoming_events(
        days_ahead=days_ahead,
        industries=industries,
        include_past=False
    )
    
    critical_events = [e for e in response.events if e.is_critical]
    
    return critical_events


@router.get("/export/ical")
async def export_ical(
    days_ahead: int = Query(90, ge=1, le=365),
    industries: Optional[List[IndustryType]] = Query(None)
):
    """Export timeline events as iCal format.
    
    Download a .ics file that can be imported into calendar applications
    like Google Calendar, Outlook, or Apple Calendar.
    """
    service = get_timeline_service()
    response = await service.get_upcoming_events(
        days_ahead=days_ahead,
        industries=industries,
        include_past=False
    )
    
    ical_content = await service.generate_ical(response.events)
    
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": "attachment; filename=fsc_policy_timeline.ics"
        }
    )


@router.get("/summary")
async def get_timeline_summary(
    industries: Optional[List[IndustryType]] = Query(None)
):
    """Get a summary of upcoming timeline events.
    
    Returns counts by event type and urgency level.
    """
    service = get_timeline_service()
    
    response_30 = await service.get_upcoming_events(
        days_ahead=30, industries=industries, include_past=False
    )
    response_90 = await service.get_upcoming_events(
        days_ahead=90, industries=industries, include_past=False
    )
    
    by_type_30: dict = {}
    by_type_90: dict = {}
    
    for event in response_30.events:
        t = event.event_type.value
        by_type_30[t] = by_type_30.get(t, 0) + 1
    
    for event in response_90.events:
        t = event.event_type.value
        by_type_90[t] = by_type_90.get(t, 0) + 1
    
    urgent_events = [e for e in response_30.events if e.days_remaining <= 7]
    
    return {
        "next_30_days": {
            "total": len(response_30.events),
            "critical": response_30.upcoming_critical,
            "by_type": by_type_30
        },
        "next_90_days": {
            "total": len(response_90.events),
            "critical": response_90.upcoming_critical,
            "by_type": by_type_90
        },
        "urgent_within_7_days": [
            {
                "event_id": e.event_id,
                "description": e.description,
                "event_date": e.event_date.isoformat(),
                "days_remaining": e.days_remaining,
                "is_critical": e.is_critical
            }
            for e in urgent_events
        ]
    }
