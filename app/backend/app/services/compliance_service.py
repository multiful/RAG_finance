"""Main compliance hub service."""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from uuid import UUID

from app.core.database import get_db
from app.services.checklist_service import ChecklistService
from app.services.risk_scoring_service import RiskScoringService
from app.services.notification_service import NotificationService
from app.models.compliance_schemas import (
    ComplianceDocumentResponse, 
    ComplianceChecklistResponse, 
    ComplianceActionItemResponse,
    ComplianceActionItemUpdate,
    ComplianceActionItemAuditResponse,
    ActionItemStatus,
    RiskLevelEnum
)
from app.models.schemas import ChecklistRequest


class ComplianceService:
    """Manages compliance documents, checklists, and action items."""
    
    def __init__(self):
        self.db = get_db()
        self.checklist_service = ChecklistService()
        self.risk_service = RiskScoringService()
        self.notif_service = NotificationService()

    async def get_or_create_compliance_document(
        self, 
        original_document_id: str, 
        created_by_user_id: Optional[str] = None
    ) -> ComplianceDocumentResponse:
        """Fetch or create compliance document based on original_document_id."""
        
        # Check if already exists
        result = self.db.table("compliance_documents").select("*").eq(
            "original_document_id", original_document_id
        ).execute()
        
        if result.data:
            return ComplianceDocumentResponse.model_validate(result.data[0])
            
        # Create new entry: Fetch original doc info first
        doc_result = self.db.table("documents").select("*").eq(
            "document_id", original_document_id
        ).execute()
        
        if not doc_result.data:
            raise ValueError(f"Original document {original_document_id} not found")
            
        doc = doc_result.data[0]
        
        new_doc = {
            "original_document_id": original_document_id,
            "title": doc["title"],
            "version": "1.0",
            "status": "active",
            "created_by_user_id": created_by_user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        insert_result = self.db.table("compliance_documents").insert(new_doc).execute()
        
        if not insert_result.data:
            raise RuntimeError("Failed to create compliance document")
            
        return ComplianceDocumentResponse.model_validate(insert_result.data[0])

    async def create_compliance_checklist(
        self, 
        compliance_doc_id: str, 
        extracted_checklist: List[Any], 
        created_by_user_id: Optional[str] = None
    ) -> ComplianceChecklistResponse:
        """Create compliance checklist and its action items from extracted data."""
        
        # 1. Create the checklist row
        new_checklist = {
            "compliance_doc_id": compliance_doc_id,
            "title": "Compliance Review",
            "description": "Auto-generated from policy document",
            "status": "draft",
            "created_by_user_id": created_by_user_id,
            "risk_score": 0.0,
            "risk_level": "low",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        checklist_result = self.db.table("compliance_checklists").insert(new_checklist).execute()
        
        if not checklist_result.data:
            raise RuntimeError("Failed to create compliance checklist")
            
        checklist_id = checklist_result.data[0]["checklist_id"]
        
        # 2. Batch insert action items
        action_items_to_insert = []
        for item in extracted_checklist:
            # Map ChecklistItem to compliance_action_item
            action_items_to_insert.append({
                "checklist_id": checklist_id,
                "action": item.action,
                "target": item.target,
                "due_date": item.effective_date.isoformat() if item.effective_date else None,
                "status": "pending",
                "priority": "medium",
                "risk_score": 0.0,
                "risk_level": "low",
                "notes": f"Extract from document (Evidence chunk: {item.evidence_chunk_id})",
                "evidence_chunk_id": item.evidence_chunk_id,
                "llm_confidence": item.confidence,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            
        if action_items_to_insert:
            self.db.table("compliance_action_items").insert(action_items_to_insert).execute()
            
        # 3. Calculate initial risk for the checklist (which triggers item risks)
        # We need to do this after items are inserted
        items_in_db = self.db.table("compliance_action_items").select("*").eq(
            "checklist_id", checklist_id
        ).execute()
        
        for db_item in items_in_db.data:
             await self.risk_service.recalculate_action_item_risk(db_item["action_item_id"])
             
        # Return full response
        return await self.get_compliance_checklist(checklist_id)

    async def generate_checklist_from_original(
        self, 
        original_document_id: str, 
        created_by_user_id: Optional[str] = None
    ) -> ComplianceChecklistResponse:
        """Workflow: Get/Create Doc -> Extract -> Create Checklist."""
        
        # Get or create compliance doc
        comp_doc = await self.get_or_create_compliance_document(original_document_id, created_by_user_id)
        
        # Use existing extraction service
        extracted = await self.checklist_service.extract_checklist(ChecklistRequest(document_id=original_document_id))
        
        # Create new compliance checklist
        return await self.create_compliance_checklist(
            str(comp_doc.compliance_doc_id), 
            extracted.items, 
            created_by_user_id
        )

    async def get_compliance_checklist(self, checklist_id: str) -> ComplianceChecklistResponse:
        """Fetch detailed checklist with all action items."""
        result = self.db.table("compliance_checklists").select("*").eq(
            "checklist_id", checklist_id
        ).execute()
        
        if not result.data:
            raise ValueError(f"Checklist {checklist_id} not found")
            
        checklist_data = result.data[0]
        
        # Fetch action items
        items_result = self.db.table("compliance_action_items").select("*").eq(
            "checklist_id", checklist_id
        ).execute()
        
        checklist_data["action_items"] = items_result.data
        
        return ComplianceChecklistResponse.model_validate(checklist_data)

    async def list_compliance_checklists(
        self, 
        skip: int = 0, 
        limit: int = 10, 
        status: Optional[str] = None, 
        risk_level: Optional[str] = None
    ) -> List[ComplianceChecklistResponse]:
        """List checklists with optional filtering."""
        query = self.db.table("compliance_checklists").select("*").range(skip, skip + limit - 1)
        
        if status:
            query = query.eq("status", status)
        if risk_level:
            query = query.eq("risk_level", risk_level)
            
        result = query.execute()
        
        checklists = []
        for row in result.data:
            # We can't afford too many individual queries, 
            # but for a small list it's okay. In real production use joins or a nested view.
            items_result = self.db.table("compliance_action_items").select("*").eq(
                "checklist_id", row["checklist_id"]
            ).execute()
            row["action_items"] = items_result.data
            checklists.append(ComplianceChecklistResponse.model_validate(row))
            
        return checklists

    async def update_action_item(
        self, 
        action_item_id: str, 
        item_update: ComplianceActionItemUpdate, 
        updated_by_user_id: Optional[str] = None
    ) -> ComplianceActionItemResponse:
        """Update an action item and log changes in audit trail."""
        
        # 1. Fetch current item
        old_result = self.db.table("compliance_action_items").select("*").eq(
            "action_item_id", action_item_id
        ).execute()
        
        if not old_result.data:
            raise ValueError(f"Action item {action_item_id} not found")
            
        old_item = old_result.data[0]
        
        # 2. Prepare update data
        update_data = item_update.model_dump(exclude_unset=True)
        
        # Auto-set completed_at if status changed to completed
        if update_data.get("status") == ActionItemStatus.COMPLETED and old_item.get("status") != ActionItemStatus.COMPLETED:
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        elif update_data.get("status") and update_data.get("status") != ActionItemStatus.COMPLETED:
             update_data["completed_at"] = None
             
        # 3. Write Audit Trail
        changed_fields = []
        old_values = {}
        new_values = {}
        
        for key, val in update_data.items():
             # Basic value comparison (for simple types)
             old_val = old_item.get(key)
             # Stringify if it's a date/uuid for comparison
             if str(old_val) != str(val):
                  changed_fields.append(key)
                  old_values[key] = old_val
                  new_values[key] = val
                  
        if changed_fields:
             audit_log = {
                 "action_item_id": action_item_id,
                 "changed_by_user_id": updated_by_user_id,
                 "old_values": old_values,
                 "new_values": new_values,
                 "changed_fields": changed_fields,
                 "created_at": datetime.now(timezone.utc).isoformat()
             }
             self.db.table("compliance_action_item_audits").insert(audit_log).execute()
             
             # Apply update
             self.db.table("compliance_action_items").update(update_data).eq("action_item_id", action_item_id).execute()
             
             # 4. Trigger Recalculations and Notifications
             # Re-fetch the item to get full state
             updated_result = self.db.table("compliance_action_items").select("*").eq(
                 "action_item_id", action_item_id
             ).execute()
             new_item = updated_result.data[0]
             
             # Risk recalculation if status or due_date changed
             if "status" in changed_fields or "due_date" in changed_fields:
                  await self.risk_service.recalculate_action_item_risk(action_item_id)
                  
             # Notifications if status or assigned_user changed
             if "status" in changed_fields or "assigned_user_id" in changed_fields:
                  await self.notif_service.send_action_item_notification(new_item, "update")
                  
             return ComplianceActionItemResponse.model_validate(new_item)
             
        return ComplianceActionItemResponse.model_validate(old_item)

    async def get_action_item_audit_log(self, action_item_id: str) -> List[ComplianceActionItemAuditResponse]:
        """Fetch audit log for an action item."""
        result = self.db.table("compliance_action_item_audits").select("*").eq(
            "action_item_id", action_item_id
        ).order("created_at", desc=True).execute()
        
        return [ComplianceActionItemAuditResponse.model_validate(row) for row in result.data]
