"""Compliance Task Tracker Service.

Tracks regulatory compliance tasks derived from alerts and policy documents.
Provides workflow management for compliance teams.
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone, date
from enum import Enum

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import IndustryType


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceTask:
    """Compliance task model."""
    
    def __init__(
        self,
        task_id: str,
        title: str,
        description: Optional[str] = None,
        document_id: Optional[str] = None,
        document_title: Optional[str] = None,
        alert_id: Optional[str] = None,
        industries: List[str] = None,
        due_date: Optional[date] = None,
        assigned_to: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        priority: TaskPriority = TaskPriority.MEDIUM,
        created_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.document_id = document_id
        self.document_title = document_title
        self.alert_id = alert_id
        self.industries = industries or []
        self.due_date = due_date
        self.assigned_to = assigned_to
        self.status = status
        self.priority = priority
        self.created_at = created_at or datetime.now(timezone.utc)
        self.completed_at = completed_at
    
    @property
    def days_until_due(self) -> Optional[int]:
        if not self.due_date:
            return None
        return (self.due_date - date.today()).days
    
    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        return self.due_date < date.today() and self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "alert_id": self.alert_id,
            "industries": self.industries,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "days_until_due": self.days_until_due,
            "is_overdue": self.is_overdue
        }


class ComplianceTrackerService:
    """Service for managing compliance tasks."""
    
    def __init__(self):
        self.db = get_db()
    
    async def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        document_id: Optional[str] = None,
        alert_id: Optional[str] = None,
        industries: Optional[List[str]] = None,
        due_date: Optional[date] = None,
        assigned_to: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> ComplianceTask:
        """Create a new compliance task."""
        
        document_title = None
        if document_id:
            doc_result = self.db.table("documents").select("title").eq(
                "document_id", document_id
            ).execute()
            if doc_result.data:
                document_title = doc_result.data[0]["title"]
        
        task_data = {
            "title": title,
            "description": description,
            "document_id": document_id,
            "alert_id": alert_id,
            "industries": industries or [],
            "due_date": due_date.isoformat() if due_date else None,
            "assigned_to": assigned_to,
            "status": TaskStatus.PENDING.value,
            "priority": priority.value
        }
        
        result = self.db.table("compliance_tasks").insert(task_data).execute()
        
        if result.data:
            task_id = result.data[0]["task_id"]
            return ComplianceTask(
                task_id=task_id,
                title=title,
                description=description,
                document_id=document_id,
                document_title=document_title,
                alert_id=alert_id,
                industries=industries or [],
                due_date=due_date,
                assigned_to=assigned_to,
                priority=priority
            )
        
        raise Exception("Failed to create task")
    
    async def create_tasks_from_alert(self, alert_id: str) -> List[ComplianceTask]:
        """Create compliance tasks from a smart alert's action items."""
        
        alert_result = self.db.table("smart_alerts").select("*").eq(
            "alert_id", alert_id
        ).execute()
        
        if not alert_result.data:
            return []
        
        alert = alert_result.data[0]
        action_items = json.loads(alert.get("action_items", "[]"))
        key_deadlines = json.loads(alert.get("key_deadlines", "[]"))
        industries = alert.get("industries", [])
        
        doc_result = self.db.table("documents").select("title").eq(
            "document_id", alert["document_id"]
        ).execute()
        document_title = doc_result.data[0]["title"] if doc_result.data else None
        
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW
        }
        task_priority = priority_map.get(alert["priority"], TaskPriority.MEDIUM)
        
        tasks = []
        
        for i, action in enumerate(action_items):
            # Find matching deadline
            due_date = None
            for deadline in key_deadlines:
                if deadline.get("date"):
                    try:
                        due_date = date.fromisoformat(deadline["date"])
                        break
                    except:
                        continue
            
            task = await self.create_task(
                title=action,
                description=f"[{document_title}] 관련 조치사항",
                document_id=alert["document_id"],
                alert_id=alert_id,
                industries=industries,
                due_date=due_date,
                priority=task_priority
            )
            tasks.append(task)
        
        return tasks
    
    async def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        industries: Optional[List[str]] = None,
        assigned_to: Optional[str] = None,
        include_overdue: bool = True,
        limit: int = 100
    ) -> List[ComplianceTask]:
        """Get compliance tasks with filters."""
        
        try:
            query = self.db.table("compliance_tasks").select(
                "*, documents(title)"
            ).order("due_date", nullsfirst=False).limit(limit)
            
            if status:
                query = query.eq("status", status.value)
            
            if assigned_to:
                query = query.eq("assigned_to", assigned_to)
            
            result = query.execute()
        except Exception as e:
            # Table might not exist yet
            import logging
            logging.warning(f"compliance_tasks table not found: {e}")
            return []
        
        if not result.data:
            return []
        
        tasks = []
        today = date.today()
        
        for item in result.data:
            # Filter by industries if specified
            item_industries = item.get("industries", [])
            if industries:
                if not any(ind in item_industries for ind in industries):
                    continue
            
            due_date = None
            if item.get("due_date"):
                try:
                    due_date = date.fromisoformat(item["due_date"])
                except:
                    pass
            
            # Check if overdue
            task_status = TaskStatus(item["status"])
            if due_date and due_date < today and task_status == TaskStatus.PENDING:
                task_status = TaskStatus.OVERDUE
                # Update status in DB
                self.db.table("compliance_tasks").update(
                    {"status": TaskStatus.OVERDUE.value}
                ).eq("task_id", item["task_id"]).execute()
            
            if not include_overdue and task_status == TaskStatus.OVERDUE:
                continue
            
            document_title = item["documents"]["title"] if item.get("documents") else None
            
            tasks.append(ComplianceTask(
                task_id=item["task_id"],
                title=item["title"],
                description=item.get("description"),
                document_id=item.get("document_id"),
                document_title=document_title,
                alert_id=item.get("alert_id"),
                industries=item_industries,
                due_date=due_date,
                assigned_to=item.get("assigned_to"),
                status=task_status,
                priority=TaskPriority(item.get("priority", "medium")),
                created_at=datetime.fromisoformat(item["created_at"]) if item.get("created_at") else None,
                completed_at=datetime.fromisoformat(item["completed_at"]) if item.get("completed_at") else None
            ))
        
        return tasks
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus
    ) -> Optional[ComplianceTask]:
        """Update task status."""
        
        update_data = {"status": status.value}
        
        if status == TaskStatus.COMPLETED:
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        result = self.db.table("compliance_tasks").update(update_data).eq(
            "task_id", task_id
        ).execute()
        
        if result.data:
            tasks = await self.get_tasks(limit=1000)
            for task in tasks:
                if task.task_id == task_id:
                    return task
        
        return None
    
    async def assign_task(
        self,
        task_id: str,
        assigned_to: str
    ) -> Optional[ComplianceTask]:
        """Assign task to a user."""
        
        result = self.db.table("compliance_tasks").update(
            {"assigned_to": assigned_to}
        ).eq("task_id", task_id).execute()
        
        if result.data:
            tasks = await self.get_tasks(limit=1000)
            for task in tasks:
                if task.task_id == task_id:
                    return task
        
        return None
    
    async def get_dashboard_stats(
        self,
        industries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get compliance dashboard statistics."""
        
        all_tasks = await self.get_tasks(industries=industries, limit=1000)
        
        stats = {
            "total_tasks": len(all_tasks),
            "by_status": {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "overdue": 0,
                "cancelled": 0
            },
            "by_priority": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "by_industry": {},
            "upcoming_due": [],
            "overdue_tasks": [],
            "completion_rate": 0.0
        }
        
        completed_count = 0
        non_cancelled_count = 0
        
        for task in all_tasks:
            stats["by_status"][task.status.value] = stats["by_status"].get(task.status.value, 0) + 1
            stats["by_priority"][task.priority.value] = stats["by_priority"].get(task.priority.value, 0) + 1
            
            for ind in task.industries:
                stats["by_industry"][ind] = stats["by_industry"].get(ind, 0) + 1
            
            if task.status == TaskStatus.COMPLETED:
                completed_count += 1
            
            if task.status != TaskStatus.CANCELLED:
                non_cancelled_count += 1
            
            if task.is_overdue:
                stats["overdue_tasks"].append(task.to_dict())
            elif task.days_until_due is not None and 0 <= task.days_until_due <= 7:
                stats["upcoming_due"].append(task.to_dict())
        
        if non_cancelled_count > 0:
            stats["completion_rate"] = round(completed_count / non_cancelled_count * 100, 1)
        
        # Sort upcoming by due date
        stats["upcoming_due"].sort(key=lambda x: x.get("due_date") or "9999-12-31")
        stats["overdue_tasks"].sort(key=lambda x: x.get("due_date") or "9999-12-31")
        
        return stats
    
    async def get_task_history(
        self,
        document_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get task completion history."""
        
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        query = self.db.table("compliance_tasks").select("*").gte(
            "created_at", cutoff
        )
        
        if document_id:
            query = query.eq("document_id", document_id)
        
        result = query.execute()
        
        if not result.data:
            return []
        
        # Group by date
        by_date: Dict[str, Dict[str, int]] = {}
        
        for item in result.data:
            created = item.get("created_at", "")[:10]
            status = item.get("status", "pending")
            
            if created not in by_date:
                by_date[created] = {"created": 0, "completed": 0}
            
            by_date[created]["created"] += 1
            
            if status == "completed":
                by_date[created]["completed"] += 1
        
        history = [
            {"date": d, "created": v["created"], "completed": v["completed"]}
            for d, v in sorted(by_date.items())
        ]
        
        return history


_compliance_service: Optional[ComplianceTrackerService] = None


def get_compliance_service() -> ComplianceTrackerService:
    """Get singleton compliance service instance."""
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceTrackerService()
    return _compliance_service
