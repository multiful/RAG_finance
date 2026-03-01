"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class IndustryType(str, Enum):
    """Industry types for classification."""
    INSURANCE = "INSURANCE"
    BANKING = "BANKING"
    SECURITIES = "SECURITIES"


class DocumentStatus(str, Enum):
    """Document processing status."""
    INGESTED = "ingested"
    PARSED = "parsed"
    INDEXED = "indexed"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


# ==================== Document Models ====================

class DocumentBase(BaseModel):
    """Base document model."""
    title: str
    published_at: datetime
    url: str
    category: Optional[str] = None
    department: Optional[str] = None


class DocumentCreate(DocumentBase):
    """Document creation model."""
    source_id: str
    raw_html: Optional[str] = None
    hash: str


class DocumentResponse(DocumentBase):
    """Document response model."""
    document_id: str
    status: DocumentStatus
    ingested_at: datetime
    fail_reason: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Document list response."""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ==================== Chunk Models ====================

class ChunkResponse(BaseModel):
    """Document chunk response."""
    chunk_id: str
    chunk_text: str
    chunk_index: int
    section_title: Optional[str] = None
    document_id: str
    document_title: str
    published_at: datetime


# ==================== Industry Classification Models ====================

class IndustryClassificationRequest(BaseModel):
    """Industry classification request."""
    document_id: Optional[str] = None
    text: Optional[str] = None


class IndustryClassificationResponse(BaseModel):
    """Industry classification response."""
    document_id: Optional[str] = None
    label_insurance: float = Field(..., ge=0, le=1)
    label_banking: float = Field(..., ge=0, le=1)
    label_securities: float = Field(..., ge=0, le=1)
    predicted_labels: List[IndustryType]
    explanation: str
    evidence_chunk_ids: List[str]


# ==================== RAG QA Models ====================

class QARequest(BaseModel):
    """Question answering request."""
    question: str
    industry_filter: Optional[List[IndustryType]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    top_k: int = 5
    compliance_mode: bool = False


class Citation(BaseModel):
    """Citation for answer."""
    chunk_id: str
    document_id: str
    document_title: str
    published_at: datetime
    snippet: str
    url: str
    parsing_source: Optional[str] = None  # e.g. "llamaparse_v1", "pdfplumber" (파싱 출처)


class QAResponse(BaseModel):
    """Question answering response."""
    answer: str
    summary: str
    industry_impact: Dict[str, float]
    checklist: Optional[List[Dict[str, Any]]] = None
    citations: List[Citation]
    confidence: float
    groundedness_score: float = 0.0
    citation_coverage: float = 0.0
    uncertainty_note: Optional[str] = None
    answerable: bool = True


# ==================== Topic/Alert Models ====================

class TopicResponse(BaseModel):
    """Topic response model."""
    topic_id: str
    topic_name: Optional[str] = None
    topic_summary: Optional[str] = None
    time_window_start: datetime
    time_window_end: datetime
    document_count: int
    surge_score: float
    representative_documents: List[Dict[str, Any]]


class TopicListResponse(BaseModel):
    """List of detected topics."""
    topics: List[TopicResponse]
    topics_detected: int


class AlertResponse(BaseModel):
    """Alert response model."""
    alert_id: str
    topic_id: str
    topic_name: Optional[str] = None
    surge_score: float
    severity: AlertSeverity
    industries: List[IndustryType]
    generated_at: datetime
    status: str


# ==================== Checklist Models ====================

class ChecklistItem(BaseModel):
    """Checklist item model."""
    action: str
    target: Optional[str] = None
    due_date_text: Optional[str] = None
    effective_date: Optional[datetime] = None
    scope: Optional[str] = None
    penalty: Optional[str] = None
    evidence_chunk_id: Optional[str] = None
    confidence: float


class ChecklistRequest(BaseModel):
    """Checklist generation request."""
    document_id: str


class ChecklistResponse(BaseModel):
    """Checklist generation response."""
    checklist_id: str
    document_id: str
    document_title: str
    items: List[ChecklistItem]
    generated_at: datetime


# ==================== Monitoring Models ====================

class CollectionStatus(BaseModel):
    """RSS collection status."""
    source_id: str
    source_name: str
    last_fetch: Optional[datetime] = None
    new_documents_24h: int
    total_documents: int
    success_rate_7d: float
    parsing_failures_24h: int


class QualityMetrics(BaseModel):
    """Quality metrics for RAG system."""
    date: datetime
    groundedness: float
    hallucination_rate: float
    avg_response_time_ms: int
    citation_accuracy: float
    unanswered_rate: float


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_documents: int
    documents_24h: int
    active_alerts: int
    high_severity_alerts: int
    collection_status: List[CollectionStatus]
    recent_topics: List[TopicResponse]
    quality_metrics: Optional[QualityMetrics] = None
    # 이번 주(7일) 신규 = 국내+국제 합산. 국내(FSC 등)/국제(FSB·BIS) 구분용.
    documents_this_week: Optional[int] = None
    domestic_this_week: Optional[int] = None
    international_this_week: Optional[int] = None


# ==================== Advanced/Governance Models ====================

class PolicySimulationRequest(BaseModel):
    """Request for policy comparison simulation."""
    old_document_id: str
    new_document_id: str


class PolicyDiffItem(BaseModel):
    """Individual change item in a policy diff."""
    clause: str
    change_type: str  # added | modified | removed
    description: str
    risk_level: str  # high | medium | low
    impacted_process: str


class PolicyDiffResponse(BaseModel):
    """Response containing policy delta analysis."""
    old_doc_title: str
    new_doc_title: str
    changes: List[PolicyDiffItem]
    overall_risk: str
    summary: str
    generated_at: datetime


class GovernanceMetricsResponse(BaseModel):
    """Aggregated governance performance metrics."""
    avg_groundedness: float
    avg_citation_accuracy: float
    avg_hallucination_rate: float
    sample_size: int
    last_updated: datetime


# ==================== Smart Alert Models ====================

class AlertPriority(str, Enum):
    """Alert priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertChannel(str, Enum):
    """Alert notification channels."""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    IN_APP = "in_app"


class AlertSubscription(BaseModel):
    """User subscription for alerts."""
    subscription_id: Optional[str] = None
    user_email: str
    industries: List[IndustryType]
    channels: List[AlertChannel]
    min_priority: AlertPriority = AlertPriority.MEDIUM
    webhook_url: Optional[str] = None
    is_active: bool = True


class AlertSubscriptionCreate(BaseModel):
    """Create alert subscription request."""
    user_email: str
    industries: List[IndustryType]
    channels: List[AlertChannel] = [AlertChannel.IN_APP]
    min_priority: AlertPriority = AlertPriority.MEDIUM
    webhook_url: Optional[str] = None


class SmartAlertResponse(BaseModel):
    """Enhanced alert response with urgency analysis."""
    alert_id: str
    document_id: str
    document_title: str
    published_at: datetime
    priority: AlertPriority
    urgency_score: float = Field(..., ge=0, le=100)
    industries: List[IndustryType]
    impact_summary: str
    key_deadlines: List[Dict[str, Any]]
    action_items: List[str]
    affected_regulations: List[str]
    generated_at: datetime
    notification_sent: bool = False


class AlertNotificationRequest(BaseModel):
    """Request to send alert notification."""
    alert_id: str
    channels: List[AlertChannel]
    recipients: Optional[List[str]] = None


class AlertStatsResponse(BaseModel):
    """Alert statistics response."""
    total_alerts_24h: int
    critical_alerts: int
    high_alerts: int
    by_industry: Dict[str, int]
    avg_urgency_score: float
    pending_notifications: int


# ==================== Policy Timeline Models ====================

class TimelineEventType(str, Enum):
    """Types of timeline events."""
    EFFECTIVE_DATE = "effective_date"
    DEADLINE = "deadline"
    GRACE_PERIOD_END = "grace_period_end"
    SUBMISSION_DUE = "submission_due"
    REVIEW_DATE = "review_date"


class TimelineEvent(BaseModel):
    """Policy timeline event."""
    event_id: str
    document_id: str
    document_title: str
    event_type: TimelineEventType
    event_date: datetime
    description: str
    target_entities: List[str]
    industries: List[IndustryType]
    days_remaining: int
    is_critical: bool = False


class TimelineResponse(BaseModel):
    """Timeline response with events."""
    events: List[TimelineEvent]
    total_events: int
    upcoming_critical: int


class TimelineExtractRequest(BaseModel):
    """Request to extract timeline from document."""
    document_id: str
    force_refresh: bool = False
