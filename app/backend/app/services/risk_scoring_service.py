"""Risk scoring service for compliance items."""
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from uuid import UUID

from app.core.database import get_db
from app.models.compliance_schemas import RiskLevelEnum, ActionItemStatus


class RiskScoringService:
    """Calculates risk scores for compliance action items and checklists."""
    
    def __init__(self):
        self.db = get_db()

    async def recalculate_action_item_risk(self, action_item_id: str) -> Tuple[float, RiskLevelEnum]:
        """Recalculates risk for a single action item."""
        result = self.db.table("compliance_action_items").select("*").eq(
            "action_item_id", action_item_id
        ).execute()
        
        if not result.data:
            return 0.0, RiskLevelEnum.LOW
            
        item = result.data[0]
        score, level = self._calculate_risk_for_item(item)
        
        # Update DB
        self.db.table("compliance_action_items").update({
            "risk_score": score,
            "risk_level": level.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("action_item_id", action_item_id).execute()
        
        # Also trigger checklist recalculation
        if item.get("checklist_id"):
            await self.recalculate_checklist_risk(item["checklist_id"])
            
        return score, level

    async def recalculate_checklist_risk(self, checklist_id: str) -> Tuple[float, RiskLevelEnum]:
        """Recalculates aggregate risk for a checklist based on its items."""
        items_result = self.db.table("compliance_action_items").select("risk_score").eq(
            "checklist_id", checklist_id
        ).execute()
        
        if not items_result.data:
            return 0.0, RiskLevelEnum.LOW
            
        scores = [item["risk_score"] for item in items_result.data]
        # Aggregate score: average of top 3 most risky items or simple average?
        # Let's use weighted average or just max risk? 
        # Requirement: "Clamp 0-100 and map to low/medium/high/critical"
        
        if not scores:
            avg_score = 0.0
        else:
            # We take the average but bias towards higher risks
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            # Combine average and max for a more conservative risk profile
            final_score = (avg_score * 0.4) + (max_score * 0.6)
            avg_score = min(100.0, final_score)
            
        level = self._map_score_to_level(avg_score)
        
        # Update DB
        self.db.table("compliance_checklists").update({
            "risk_score": avg_score,
            "risk_level": level.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("checklist_id", checklist_id).execute()
        
        return avg_score, level

    def _calculate_risk_for_item(self, item: Dict[str, Any]) -> Tuple[float, RiskLevelEnum]:
        """Core risk calculation logic."""
        score = 0.0
        
        # 1. Deadline proximity (30%)
        due_date = item.get("due_date")
        if due_date and item.get("status") != ActionItemStatus.COMPLETED:
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            
            now = datetime.now(timezone.utc)
            days_left = (due_date - now).days
            
            if days_left < 0:
                score += 30.0 # Overdue
            elif days_left < 7:
                score += 20.0 # Urgent
            elif days_left < 30:
                score += 10.0 # Coming up
        
        # 2. Penalty severity keyword rules (Korean) (30%)
        penalty = item.get("penalty", "") or ""
        severity_keywords = {
            r"영업정지": 30.0,
            r"등록취소": 30.0,
            r"징역": 25.0,
            r"과징금": 20.0,
            r"벌칙": 15.0,
            r"과태료": 10.0,
            r"주의": 5.0
        }
        
        penalty_score = 0.0
        for kw, s in severity_keywords.items():
            if re.search(kw, penalty):
                penalty_score = max(penalty_score, s)
        score += penalty_score
        
        # 3. LLM Confidence & Uncertainty (20%)
        # (1 - confidence) * weight
        confidence = item.get("llm_confidence", 0.5)
        score += (1.0 - confidence) * 20.0
        
        # 4. Priority & Status modifiers (20%)
        priority = item.get("priority", "medium")
        priority_map = {"urgent": 20.0, "high": 15.0, "medium": 10.0, "low": 5.0}
        score += priority_map.get(priority, 10.0)
        
        # Status reduction
        status = item.get("status", ActionItemStatus.PENDING)
        if status == ActionItemStatus.COMPLETED:
            score *= 0.1 # Completed items have 90% reduced risk
        elif status == ActionItemStatus.IN_PROGRESS:
            score *= 0.8 # In progress has 20% reduction
            
        final_score = min(100.0, score)
        return final_score, self._map_score_to_level(final_score)

    def _map_score_to_level(self, score: float) -> RiskLevelEnum:
        if score >= 80:
            return RiskLevelEnum.CRITICAL
        if score >= 60:
            return RiskLevelEnum.HIGH
        if score >= 30:
            return RiskLevelEnum.MEDIUM
        return RiskLevelEnum.LOW
