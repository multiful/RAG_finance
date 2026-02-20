"""Pydantic models for Compliance Hub."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


class ActionItemStatus(str, Enum):
    """Status for compliance action items."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


class RiskLevelEnum(str, Enum):
    """Risk levels for compliance items."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceDocumentBase(BaseModel):
    """Base model for compliance documents."""
    original_document_id: UUID
    title: str
    version: str = "1.0"
    status: str = "active"


class ComplianceDocumentCreate(ComplianceDocumentBase):
    """Model for creating compliance documents."""
    created_by_user_id: Optional[str] = None


class ComplianceDocumentResponse(ComplianceDocumentBase):
    """Response model for compliance documents."""
    compliance_doc_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ComplianceActionItemBase(BaseModel):
    """Base model for compliance action items."""
    action: str
    target: Optional[str] = None
    due_date: Optional[datetime] = None
    status: ActionItemStatus = ActionItemStatus.PENDING
    priority: str = "medium"
    risk_level: RiskLevelEnum = RiskLevelEnum.LOW
    risk_score: float = 0.0
    assigned_user_id: Optional[str] = None
    notes: Optional[str] = None
    evidence_chunk_id: Optional[UUID] = None
    llm_confidence: float = 0.0


class ComplianceActionItemUpdate(BaseModel):
    """Model for updating compliance action items."""
    status: Optional[ActionItemStatus] = None
    assigned_user_id: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: Optional[str] = None


class ComplianceActionItemResponse(ComplianceActionItemBase):
    """Response model for compliance action items."""
    action_item_id: UUID
    checklist_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ComplianceChecklistBase(BaseModel):
    """Base model for compliance checklists."""
    compliance_doc_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"


class ComplianceChecklistResponse(ComplianceChecklistBase):
    """Response model for compliance checklists."""
    checklist_id: UUID
    risk_score: float
    risk_level: RiskLevelEnum
    created_at: datetime
    updated_at: datetime
    action_items: List[ComplianceActionItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class ComplianceActionItemAuditResponse(BaseModel):
    """Response model for action item audit logs."""
    audit_id: UUID
    action_item_id: UUID
    changed_by_user_id: Optional[str] = None
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    changed_fields: List[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
