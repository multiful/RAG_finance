"""Compliance Hub API routes."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from uuid import UUID

from app.services.compliance_service import ComplianceService
from app.models.compliance_schemas import (
    ComplianceDocumentResponse,
    ComplianceChecklistResponse,
    ComplianceActionItemResponse,
    ComplianceActionItemUpdate,
    ComplianceActionItemAuditResponse
)

router = APIRouter()

# Dependency for service
def get_compliance_service() -> ComplianceService:
    return ComplianceService()


# (A) Compliance Documents
@router.post("/documents", response_model=ComplianceDocumentResponse)
async def get_or_create_compliance_document(
    original_document_id: UUID,
    user_id: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_service)
):
    """Create or get a compliance document entry for a RAG document."""
    try:
        return await service.get_or_create_compliance_document(str(original_document_id), user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create compliance document: {str(e)}")


@router.get("/documents/{compliance_doc_id}", response_model=ComplianceDocumentResponse)
async def get_compliance_document(
    compliance_doc_id: UUID,
    service: ComplianceService = Depends(get_compliance_service)
):
    """Fetch compliance document details."""
    result = service.db.table("compliance_documents").select("*").eq(
        "compliance_doc_id", str(compliance_doc_id)
    ).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Compliance document not found")
        
    return ComplianceDocumentResponse.model_validate(result.data[0])


# (B) Compliance Checklists
@router.post("/checklists/generate", response_model=ComplianceChecklistResponse)
async def generate_compliance_checklist(
    original_document_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_service)
):
    """
    Generate a full compliance checklist from an original document.
    Triggers RAG extraction and initial risk scoring.
    """
    try:
        # Generate the checklist (this includes initial scoring in our service implementation)
        checklist = await service.generate_checklist_from_original(str(original_document_id), user_id)
        
        # We can also add extra background tasks if needed
        # background_tasks.add_task(...)
        
        return checklist
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/checklists/{checklist_id}", response_model=ComplianceChecklistResponse)
async def get_compliance_checklist(
    checklist_id: UUID,
    service: ComplianceService = Depends(get_compliance_service)
):
    """Fetch detailed checklist with action items."""
    try:
        return await service.get_compliance_checklist(str(checklist_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/checklists", response_model=List[ComplianceChecklistResponse])
async def list_checklists(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_service)
):
    """List compliance checklists with optional filtering."""
    return await service.list_compliance_checklists(skip, limit, status, risk_level)


# (C) Action Items
@router.put("/action-items/{action_item_id}", response_model=ComplianceActionItemResponse)
async def update_action_item(
    action_item_id: UUID,
    item_update: ComplianceActionItemUpdate,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_service)
):
    """Update action item status, assignee, or notes."""
    try:
        # Update (triggers risk recalculation and notification in the service)
        return await service.update_action_item(str(action_item_id), item_update, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/action-items/{action_item_id}/audit", response_model=List[ComplianceActionItemAuditResponse])
async def get_action_item_audit(
    action_item_id: UUID,
    service: ComplianceService = Depends(get_compliance_service)
):
    """Fetch audit trail for a specific action item."""
    return await service.get_action_item_audit_log(str(action_item_id))


# (D) Risk
@router.post("/action-items/{action_item_id}/recalculate-risk")
async def recalculate_risk(
    action_item_id: UUID,
    background_tasks: BackgroundTasks,
    service: ComplianceService = Depends(get_compliance_service)
):
    """Manually trigger background risk recalculation for an item."""
    # Add to background tasks as requested
    background_tasks.add_task(service.risk_service.recalculate_action_item_risk, str(action_item_id))
    return {"message": "Recalculation enqueued", "action_item_id": action_item_id}
