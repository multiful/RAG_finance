"""Compliance Tracking API routes."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

from app.services.compliance_tracker import (
    get_compliance_service, TaskStatus, TaskPriority, ComplianceTask
)

router = APIRouter(prefix="/compliance", tags=["Compliance Tracking"])


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


@router.post("/tasks", response_model=dict)
async def create_task(request: CreateTaskRequest):
    """Create a new compliance task."""
    service = get_compliance_service()
    
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


@router.post("/tasks/from-alert/{alert_id}", response_model=List[dict])
async def create_tasks_from_alert(alert_id: str):
    """Create compliance tasks from a smart alert's action items.
    
    Automatically generates tasks from the alert's action_items field.
    """
    service = get_compliance_service()
    tasks = await service.create_tasks_from_alert(alert_id)
    
    if not tasks:
        raise HTTPException(
            status_code=404,
            detail="Alert not found or no action items to create tasks from"
        )
    
    return [task.to_dict() for task in tasks]


@router.get("/tasks", response_model=List[dict])
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
    service = get_compliance_service()
    
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    tasks = await service.get_tasks(
        status=task_status,
        industries=industries,
        assigned_to=assigned_to,
        include_overdue=include_overdue,
        limit=limit
    )
    
    return [task.to_dict() for task in tasks]


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task(task_id: str):
    """Get a specific task by ID."""
    service = get_compliance_service()
    tasks = await service.get_tasks(limit=1000)
    
    for task in tasks:
        if task.task_id == task_id:
            return task.to_dict()
    
    raise HTTPException(status_code=404, detail="Task not found")


@router.put("/tasks/{task_id}/status", response_model=dict)
async def update_task_status(task_id: str, request: UpdateStatusRequest):
    """Update task status."""
    service = get_compliance_service()
    
    try:
        status = TaskStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    task = await service.update_task_status(task_id, status)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@router.put("/tasks/{task_id}/assign", response_model=dict)
async def assign_task(task_id: str, request: AssignTaskRequest):
    """Assign task to a user."""
    service = get_compliance_service()
    
    task = await service.assign_task(task_id, request.assigned_to)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@router.get("/dashboard", response_model=dict)
async def get_dashboard_stats(
    industries: Optional[List[str]] = Query(None)
):
    """Get compliance dashboard statistics.
    
    Returns task counts by status, priority, and industry,
    plus upcoming due tasks and overdue tasks.
    """
    service = get_compliance_service()
    return await service.get_dashboard_stats(industries=industries)


@router.get("/history", response_model=List[dict])
async def get_task_history(
    document_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """Get task completion history.
    
    Returns daily counts of created and completed tasks.
    """
    service = get_compliance_service()
    return await service.get_task_history(document_id=document_id, days=days)
