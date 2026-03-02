"""Compliance Tracking & Compliance Hub API routes."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from datetime import date
from uuid import UUID
from pydantic import BaseModel

from app.services.compliance_tracker import (
    get_compliance_service as get_tracker_service, TaskStatus, TaskPriority, ComplianceTask
)
from app.services.compliance_service import ComplianceService
from app.models.compliance_schemas import (
    ComplianceDocumentResponse,
    ComplianceChecklistResponse,
    ComplianceActionItemResponse,
    ComplianceActionItemUpdate,
    ComplianceActionItemAuditResponse
)

router = APIRouter()


# ============================================
# Request Models for Task Management
# ============================================

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    document_id: Optional[str] = None
    alert_id: Optional[str] = None
    industries: Optional[List[str]] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    priority: str = "medium"


class UpdateStatusRequest(BaseModel):
    status: str


class AssignTaskRequest(BaseModel):
    assigned_to: str


# ============================================
# Dependency for Compliance Hub Service
# ============================================

def get_compliance_hub_service() -> ComplianceService:
    return ComplianceService()


# ============================================
# (A) Task Management Endpoints (Smart Alert Integration)
# ============================================

@router.post("/tasks", response_model=dict, tags=["Compliance Tasks"])
async def create_task(request: CreateTaskRequest):
    """Create a new compliance task."""
    service = get_tracker_service()
    
    priority_map = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW
    }
    
    task = await service.create_task(
        title=request.title,
        description=request.description,
        document_id=request.document_id,
        alert_id=request.alert_id,
        industries=request.industries,
        due_date=request.due_date,
        assigned_to=request.assigned_to,
        priority=priority_map.get(request.priority, TaskPriority.MEDIUM)
    )
    
    return task.to_dict()


@router.post("/tasks/from-alert/{alert_id}", response_model=List[dict], tags=["Compliance Tasks"])
async def create_tasks_from_alert(alert_id: str):
    """Create compliance tasks from a smart alert's action items.
    
    Automatically generates tasks from the alert's action_items field.
    """
    service = get_tracker_service()
    tasks = await service.create_tasks_from_alert(alert_id)
    
    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or no action items to create tasks from"
        )
    
    return [task.to_dict() for task in tasks]


@router.get("/tasks", response_model=List[dict], tags=["Compliance Tasks"])
async def get_tasks(
    status: Optional[str] = Query(None),
    industries: Optional[List[str]] = Query(None),
    assigned_to: Optional[str] = Query(None),
    include_overdue: bool = Query(True),
    limit: int = Query(100, ge=1, le=500)
):
    """Get compliance tasks with filters.
    
    - **status**: Filter by task status (pending, in_progress, completed, overdue, cancelled)
    - **industries**: Filter by affected industries
    - **assigned_to**: Filter by assignee
    - **include_overdue**: Include overdue tasks (default True)
    """
    service = get_tracker_service()
    
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    try:
        tasks = await service.get_tasks(
            status=task_status,
            industries=industries,
            assigned_to=assigned_to,
            include_overdue=include_overdue,
            limit=limit
        )
        
        return [task.to_dict() for task in tasks]
    except Exception as e:
        # Return empty list if table doesn't exist
        return []


@router.get("/tasks/{task_id}", response_model=dict, tags=["Compliance Tasks"])
async def get_task(task_id: str):
    """Get a specific task by ID."""
    service = get_tracker_service()
    tasks = await service.get_tasks(limit=1000)
    
    for task in tasks:
        if task.task_id == task_id:
            return task.to_dict()
    
    raise HTTPException(status_code=404, detail="Task not found")


@router.put("/tasks/{task_id}/status", response_model=dict, tags=["Compliance Tasks"])
async def update_task_status(task_id: str, request: UpdateStatusRequest):
    """Update task status."""
    service = get_tracker_service()
    
    try:
        status = TaskStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    task = await service.update_task_status(task_id, status)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@router.put("/tasks/{task_id}/assign", response_model=dict, tags=["Compliance Tasks"])
async def assign_task(task_id: str, request: AssignTaskRequest):
    """Assign task to a user."""
    service = get_tracker_service()
    
    task = await service.assign_task(task_id, request.assigned_to)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@router.get("/dashboard", response_model=dict, tags=["Compliance Tasks"])
async def get_dashboard_stats(
    industries: Optional[List[str]] = Query(None)
):
    """Get compliance dashboard statistics.
    
    Returns task counts by status, priority, and industry,
    plus upcoming due tasks and overdue tasks.
    """
    try:
        service = get_tracker_service()
        return await service.get_dashboard_stats(industries=industries)
    except Exception:
        # Return empty dashboard if table doesn't exist
        return {
            "total_tasks": 0,
            "by_status": {},
            "by_priority": {},
            "by_industry": {},
            "upcoming_due": [],
            "overdue": []
        }


@router.get("/history", response_model=List[dict], tags=["Compliance Tasks"])
async def get_task_history(
    document_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """Get task completion history.
    
    Returns daily counts of created and completed tasks.
    """
    try:
        service = get_tracker_service()
        return await service.get_task_history(document_id=document_id, days=days)
    except Exception:
        return []


# ============================================
# (B) Compliance Hub - Document Management
# ============================================

@router.post("/documents", response_model=ComplianceDocumentResponse, tags=["Compliance Hub"])
async def get_or_create_compliance_document(
    original_document_id: UUID,
    user_id: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """Create or get a compliance document entry for a RAG document."""
    try:
        return await service.get_or_create_compliance_document(str(original_document_id), user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create compliance document: {str(e)}")


@router.get("/documents/{compliance_doc_id}", response_model=ComplianceDocumentResponse, tags=["Compliance Hub"])
async def get_compliance_document(
    compliance_doc_id: UUID,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """Fetch compliance document details."""
    result = service.db.table("compliance_documents").select("*").eq(
        "compliance_doc_id", str(compliance_doc_id)
    ).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Compliance document not found")
        
    return ComplianceDocumentResponse.model_validate(result.data[0])


# ============================================
# (C) Compliance Hub - Checklists
# ============================================

@router.post("/checklists/generate", response_model=ComplianceChecklistResponse, tags=["Compliance Hub"])
async def generate_compliance_checklist(
    original_document_id: UUID,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """
    Generate a full compliance checklist from an original document.
    Triggers RAG extraction and initial risk scoring.
    """
    try:
        checklist = await service.generate_checklist_from_original(str(original_document_id), user_id)
        return checklist
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/checklists/{checklist_id}", response_model=ComplianceChecklistResponse, tags=["Compliance Hub"])
async def get_compliance_checklist(
    checklist_id: UUID,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """Fetch detailed checklist with action items."""
    try:
        return await service.get_compliance_checklist(str(checklist_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/checklists", response_model=List[ComplianceChecklistResponse], tags=["Compliance Hub"])
async def list_checklists(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """List compliance checklists with optional filtering."""
    return await service.list_compliance_checklists(skip, limit, status, risk_level)


# ============================================
# (D) Compliance Hub - Action Items
# ============================================

@router.put("/action-items/{action_item_id}", response_model=ComplianceActionItemResponse, tags=["Compliance Hub"])
async def update_action_item(
    action_item_id: UUID,
    item_update: ComplianceActionItemUpdate,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """Update action item status, assignee, or notes."""
    try:
        return await service.update_action_item(str(action_item_id), item_update, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/action-items/{action_item_id}/audit", response_model=List[ComplianceActionItemAuditResponse], tags=["Compliance Hub"])
async def get_action_item_audit(
    action_item_id: UUID,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """Fetch audit trail for a specific action item."""
    return await service.get_action_item_audit_log(str(action_item_id))


# ============================================
# (E) Compliance Hub - Risk Management
# ============================================

@router.post("/action-items/{action_item_id}/recalculate-risk", tags=["Compliance Hub"])
async def recalculate_risk(
    action_item_id: UUID,
    background_tasks: BackgroundTasks,
    service: ComplianceService = Depends(get_compliance_hub_service)
):
    """Manually trigger background risk recalculation for an item."""
    background_tasks.add_task(service.risk_service.recalculate_action_item_risk, str(action_item_id))
    return {"message": "Recalculation enqueued", "action_item_id": action_item_id}
