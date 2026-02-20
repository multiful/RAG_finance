"""Smart Alert API routes."""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional

from app.models.schemas import (
    IndustryType, AlertPriority, AlertChannel,
    SmartAlertResponse, AlertSubscription, AlertSubscriptionCreate,
    AlertNotificationRequest, AlertStatsResponse
)
from app.services.alert_service import get_alert_service

router = APIRouter(prefix="/alerts", tags=["Smart Alerts"])


@router.post("/process", response_model=List[SmartAlertResponse])
async def process_new_documents(background_tasks: BackgroundTasks):
    """Process new documents and create smart alerts.
    
    Scans documents from the last 24 hours that haven't been processed
    and generates alerts with urgency analysis.
    """
    service = get_alert_service()
    alerts = await service.process_new_documents()
    
    for alert in alerts:
        if alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]:
            background_tasks.add_task(service.notify_subscribers, alert)
    
    return alerts


@router.post("/analyze/{document_id}", response_model=SmartAlertResponse)
async def analyze_document(document_id: str):
    """Analyze a specific document and create an alert.
    
    Performs urgency analysis on the specified document and
    generates a smart alert with priority, deadlines, and action items.
    """
    service = get_alert_service()
    alert = await service.create_smart_alert(document_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Document not found or analysis failed")
    
    return alert


@router.get("/", response_model=List[SmartAlertResponse])
async def get_alerts(
    industries: Optional[List[IndustryType]] = Query(None),
    min_priority: Optional[AlertPriority] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Get smart alerts with optional filters.
    
    - **industries**: Filter by affected industries
    - **min_priority**: Minimum priority level (critical, high, medium, low)
    - **limit**: Maximum number of alerts to return
    """
    service = get_alert_service()
    return await service.get_alerts(
        industries=industries,
        min_priority=min_priority,
        limit=limit
    )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats():
    """Get alert statistics for the last 24 hours.
    
    Returns counts by priority and industry, average urgency score,
    and pending notification count.
    """
    service = get_alert_service()
    return await service.get_alert_stats()


@router.get("/{alert_id}", response_model=SmartAlertResponse)
async def get_alert(alert_id: str):
    """Get a specific alert by ID."""
    service = get_alert_service()
    alerts = await service.get_alerts(limit=1000)
    
    for alert in alerts:
        if alert.alert_id == alert_id:
            return alert
    
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/notify", response_model=dict)
async def send_notification(request: AlertNotificationRequest):
    """Manually trigger notification for an alert.
    
    Sends notifications through specified channels to matching subscribers.
    """
    service = get_alert_service()
    
    alerts = await service.get_alerts(limit=1000)
    target_alert = None
    for alert in alerts:
        if alert.alert_id == request.alert_id:
            target_alert = alert
            break
    
    if not target_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    notified = await service.notify_subscribers(target_alert)
    
    return {
        "alert_id": request.alert_id,
        "notifications_sent": notified,
        "status": "success" if notified > 0 else "no_subscribers_matched"
    }


# ==================== Subscription Endpoints ====================

@router.post("/subscriptions", response_model=AlertSubscription)
async def create_subscription(subscription: AlertSubscriptionCreate):
    """Create or update an alert subscription.
    
    Subscriptions define which alerts a user wants to receive,
    filtered by industry and priority, delivered through specified channels.
    """
    service = get_alert_service()
    
    full_subscription = AlertSubscription(
        user_email=subscription.user_email,
        industries=subscription.industries,
        channels=subscription.channels,
        min_priority=subscription.min_priority,
        webhook_url=subscription.webhook_url
    )
    
    return await service.create_subscription(full_subscription)


@router.get("/subscriptions", response_model=List[AlertSubscription])
async def get_subscriptions(user_email: Optional[str] = Query(None)):
    """Get alert subscriptions.
    
    - **user_email**: Filter by specific user email
    """
    service = get_alert_service()
    return await service.get_subscriptions(user_email=user_email)


@router.delete("/subscriptions/{user_email}")
async def delete_subscription(user_email: str):
    """Deactivate a subscription (soft delete)."""
    service = get_alert_service()
    
    subscriptions = await service.get_subscriptions(user_email=user_email)
    if not subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription = subscriptions[0]
    subscription.is_active = False
    await service.create_subscription(subscription)
    
    return {"status": "deactivated", "user_email": user_email}
