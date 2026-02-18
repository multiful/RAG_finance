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


class Citation(BaseModel):
    """Citation for answer."""
    chunk_id: str
    document_id: str
    document_title: str
    published_at: datetime
    snippet: str
    url: str


class QAResponse(BaseModel):
    """Question answering response."""
    answer: str
    summary: str
    industry_impact: Dict[str, float]
    checklist: Optional[List[Dict[str, Any]]] = None
    citations: List[Citation]
    confidence: float
    uncertainty_note: Optional[str] = None


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
