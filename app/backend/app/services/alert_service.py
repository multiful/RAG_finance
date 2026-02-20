"""Smart Alert Service for policy change notifications."""
import openai
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.schemas import (
    IndustryType, AlertPriority, AlertChannel,
    SmartAlertResponse, AlertSubscription, AlertStatsResponse
)


@dataclass
class UrgencyFactors:
    """Factors contributing to alert urgency."""
    deadline_proximity: float  # 0-30 points
    scope_breadth: float       # 0-25 points
    penalty_severity: float    # 0-20 points
    regulatory_weight: float   # 0-15 points
    industry_impact: float     # 0-10 points


class SmartAlertService:
    """Service for intelligent policy alert generation and notification."""
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def analyze_document_urgency(
        self,
        document_id: str,
        document_text: str,
        title: str
    ) -> Dict[str, Any]:
        """Analyze document for urgency factors using GPT-4."""
        
        analysis_prompt = f"""당신은 금융 규제 전문가입니다. 다음 금융위원회 문서를 분석하여 긴급도를 평가하세요.

문서 제목: {title}

문서 내용:
{document_text[:4000]}

다음 항목을 JSON 형식으로 평가하세요:

1. deadline_info: 시행일, 제출 기한 등 주요 일정 (날짜와 설명)
2. affected_industries: 영향받는 업권 (INSURANCE, BANKING, SECURITIES 중 해당되는 것)
3. scope: 적용 대상 범위 (전체 금융권/특정 업권/특정 기관)
4. penalties: 위반 시 제재 내용 (있는 경우)
5. key_changes: 핵심 변경 사항 (3개 이내)
6. action_items: 금융기관이 취해야 할 조치 (3개 이내)
7. affected_regulations: 관련/개정되는 규정명

출력 형식:
{{
    "deadline_info": [{{"date": "YYYY-MM-DD", "description": "설명", "type": "effective_date|deadline|grace_period"}}],
    "affected_industries": ["INSURANCE", "BANKING"],
    "scope": "전체 금융권",
    "penalties": "과태료 1000만원 이하",
    "key_changes": ["변경1", "변경2"],
    "action_items": ["조치1", "조치2"],
    "affected_regulations": ["규정1", "규정2"],
    "urgency_assessment": {{
        "deadline_proximity_score": 0-30,
        "scope_breadth_score": 0-25,
        "penalty_severity_score": 0-20,
        "regulatory_weight_score": 0-15,
        "industry_impact_score": 0-10,
        "reasoning": "평가 근거"
    }}
}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error analyzing document urgency: {e}")
            return {
                "deadline_info": [],
                "affected_industries": [],
                "scope": "unknown",
                "penalties": None,
                "key_changes": [],
                "action_items": [],
                "affected_regulations": [],
                "urgency_assessment": {
                    "deadline_proximity_score": 0,
                    "scope_breadth_score": 0,
                    "penalty_severity_score": 0,
                    "regulatory_weight_score": 0,
                    "industry_impact_score": 0,
                    "reasoning": "분석 실패"
                }
            }
    
    def _calculate_urgency_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate total urgency score from analysis."""
        assessment = analysis.get("urgency_assessment", {})
        
        total = (
            assessment.get("deadline_proximity_score", 0) +
            assessment.get("scope_breadth_score", 0) +
            assessment.get("penalty_severity_score", 0) +
            assessment.get("regulatory_weight_score", 0) +
            assessment.get("industry_impact_score", 0)
        )
        
        return min(100.0, max(0.0, total))
    
    def _determine_priority(self, urgency_score: float) -> AlertPriority:
        """Determine alert priority based on urgency score."""
        if urgency_score >= 75:
            return AlertPriority.CRITICAL
        elif urgency_score >= 50:
            return AlertPriority.HIGH
        elif urgency_score >= 25:
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW
    
    async def create_smart_alert(
        self,
        document_id: str
    ) -> Optional[SmartAlertResponse]:
        """Create a smart alert for a document."""
        
        doc_result = self.db.table("documents").select("*").eq(
            "document_id", document_id
        ).execute()
        
        if not doc_result.data:
            return None
        
        doc = doc_result.data[0]
        
        chunks_result = self.db.table("chunks").select("chunk_text").eq(
            "document_id", document_id
        ).order("chunk_index").execute()
        
        full_text = "\n".join([c["chunk_text"] for c in chunks_result.data]) if chunks_result.data else ""
        
        if not full_text:
            full_text = doc.get("raw_html", "")[:5000]
        
        analysis = await self.analyze_document_urgency(
            document_id=document_id,
            document_text=full_text,
            title=doc["title"]
        )
        
        urgency_score = self._calculate_urgency_score(analysis)
        priority = self._determine_priority(urgency_score)
        
        industries = [
            IndustryType(ind) for ind in analysis.get("affected_industries", [])
            if ind in [e.value for e in IndustryType]
        ]
        
        impact_summary = f"{analysis.get('scope', '해당 없음')}에 적용. "
        if analysis.get("penalties"):
            impact_summary += f"위반 시 {analysis['penalties']}."
        
        key_deadlines = analysis.get("deadline_info", [])
        
        alert_data = {
            "document_id": document_id,
            "priority": priority.value,
            "urgency_score": urgency_score,
            "industries": [i.value for i in industries],
            "impact_summary": impact_summary,
            "key_deadlines": json.dumps(key_deadlines),
            "action_items": json.dumps(analysis.get("action_items", [])),
            "affected_regulations": json.dumps(analysis.get("affected_regulations", [])),
            "analysis_raw": json.dumps(analysis),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = self.db.table("smart_alerts").insert(alert_data).execute()
        
        if not result.data:
            return None
        
        alert_id = result.data[0]["alert_id"]
        
        return SmartAlertResponse(
            alert_id=alert_id,
            document_id=document_id,
            document_title=doc["title"],
            published_at=doc["published_at"],
            priority=priority,
            urgency_score=urgency_score,
            industries=industries,
            impact_summary=impact_summary,
            key_deadlines=key_deadlines,
            action_items=analysis.get("action_items", []),
            affected_regulations=analysis.get("affected_regulations", []),
            generated_at=datetime.now(timezone.utc),
            notification_sent=False
        )
    
    async def process_new_documents(self) -> List[SmartAlertResponse]:
        """Process new documents and create alerts."""
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        
        docs_result = self.db.table("documents").select("document_id").gte(
            "ingested_at", cutoff
        ).execute()
        
        if not docs_result.data:
            return []
        
        existing_alerts = self.db.table("smart_alerts").select("document_id").execute()
        existing_doc_ids = {a["document_id"] for a in existing_alerts.data} if existing_alerts.data else set()
        
        alerts = []
        for doc in docs_result.data:
            if doc["document_id"] not in existing_doc_ids:
                alert = await self.create_smart_alert(doc["document_id"])
                if alert:
                    alerts.append(alert)
        
        return alerts
    
    async def get_alerts(
        self,
        industries: Optional[List[IndustryType]] = None,
        min_priority: Optional[AlertPriority] = None,
        limit: int = 50
    ) -> List[SmartAlertResponse]:
        """Get alerts with optional filters."""
        
        query = self.db.table("smart_alerts").select(
            "*, documents(title, published_at)"
        ).order("urgency_score", desc=True).limit(limit)
        
        result = query.execute()
        
        if not result.data:
            return []
        
        alerts = []
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3
        }
        
        for item in result.data:
            item_industries = [IndustryType(i) for i in item.get("industries", [])]
            item_priority = AlertPriority(item["priority"])
            
            if industries:
                if not any(ind in item_industries for ind in industries):
                    continue
            
            if min_priority:
                if priority_order[item_priority] > priority_order[min_priority]:
                    continue
            
            alerts.append(SmartAlertResponse(
                alert_id=item["alert_id"],
                document_id=item["document_id"],
                document_title=item["documents"]["title"] if item.get("documents") else "Unknown",
                published_at=item["documents"]["published_at"] if item.get("documents") else datetime.now(timezone.utc),
                priority=item_priority,
                urgency_score=item["urgency_score"],
                industries=item_industries,
                impact_summary=item.get("impact_summary", ""),
                key_deadlines=json.loads(item.get("key_deadlines", "[]")),
                action_items=json.loads(item.get("action_items", "[]")),
                affected_regulations=json.loads(item.get("affected_regulations", "[]")),
                generated_at=item["generated_at"],
                notification_sent=item.get("notification_sent", False)
            ))
        
        return alerts
    
    async def send_webhook_notification(
        self,
        alert: SmartAlertResponse,
        webhook_url: str
    ) -> bool:
        """Send alert to webhook URL."""
        import httpx
        
        payload = {
            "alert_id": alert.alert_id,
            "document_title": alert.document_title,
            "priority": alert.priority.value,
            "urgency_score": alert.urgency_score,
            "industries": [i.value for i in alert.industries],
            "impact_summary": alert.impact_summary,
            "action_items": alert.action_items,
            "key_deadlines": alert.key_deadlines,
            "generated_at": alert.generated_at.isoformat()
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Webhook notification failed: {e}")
            return False
    
    async def create_subscription(
        self,
        subscription: AlertSubscription
    ) -> AlertSubscription:
        """Create or update an alert subscription."""
        
        sub_data = {
            "user_email": subscription.user_email,
            "industries": [i.value for i in subscription.industries],
            "channels": [c.value for c in subscription.channels],
            "min_priority": subscription.min_priority.value,
            "webhook_url": subscription.webhook_url,
            "is_active": subscription.is_active
        }
        
        existing = self.db.table("alert_subscriptions").select("*").eq(
            "user_email", subscription.user_email
        ).execute()
        
        if existing.data:
            result = self.db.table("alert_subscriptions").update(sub_data).eq(
                "user_email", subscription.user_email
            ).execute()
        else:
            result = self.db.table("alert_subscriptions").insert(sub_data).execute()
        
        if result.data:
            subscription.subscription_id = result.data[0].get("subscription_id")
        
        return subscription
    
    async def get_subscriptions(
        self,
        user_email: Optional[str] = None
    ) -> List[AlertSubscription]:
        """Get alert subscriptions."""
        
        query = self.db.table("alert_subscriptions").select("*")
        
        if user_email:
            query = query.eq("user_email", user_email)
        
        result = query.execute()
        
        subscriptions = []
        if result.data:
            for item in result.data:
                subscriptions.append(AlertSubscription(
                    subscription_id=item.get("subscription_id"),
                    user_email=item["user_email"],
                    industries=[IndustryType(i) for i in item.get("industries", [])],
                    channels=[AlertChannel(c) for c in item.get("channels", [])],
                    min_priority=AlertPriority(item.get("min_priority", "medium")),
                    webhook_url=item.get("webhook_url"),
                    is_active=item.get("is_active", True)
                ))
        
        return subscriptions
    
    async def notify_subscribers(
        self,
        alert: SmartAlertResponse
    ) -> int:
        """Notify all matching subscribers about an alert."""
        
        subscriptions = await self.get_subscriptions()
        notified_count = 0
        
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3
        }
        
        for sub in subscriptions:
            if not sub.is_active:
                continue
            
            if not any(ind in sub.industries for ind in alert.industries):
                continue
            
            if priority_order[alert.priority] > priority_order[sub.min_priority]:
                continue
            
            for channel in sub.channels:
                success = False
                
                if channel == AlertChannel.WEBHOOK and sub.webhook_url:
                    success = await self.send_webhook_notification(alert, sub.webhook_url)
                elif channel == AlertChannel.IN_APP:
                    success = True
                
                if success:
                    notified_count += 1
        
        if notified_count > 0:
            self.db.table("smart_alerts").update(
                {"notification_sent": True}
            ).eq("alert_id", alert.alert_id).execute()
        
        return notified_count
    
    async def get_alert_stats(self) -> AlertStatsResponse:
        """Get alert statistics."""
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        
        alerts_result = self.db.table("smart_alerts").select("*").gte(
            "generated_at", cutoff
        ).execute()
        
        if not alerts_result.data:
            return AlertStatsResponse(
                total_alerts_24h=0,
                critical_alerts=0,
                high_alerts=0,
                by_industry={},
                avg_urgency_score=0.0,
                pending_notifications=0
            )
        
        alerts = alerts_result.data
        
        critical_count = sum(1 for a in alerts if a["priority"] == "critical")
        high_count = sum(1 for a in alerts if a["priority"] == "high")
        
        by_industry: Dict[str, int] = {}
        for alert in alerts:
            for ind in alert.get("industries", []):
                by_industry[ind] = by_industry.get(ind, 0) + 1
        
        avg_urgency = sum(a["urgency_score"] for a in alerts) / len(alerts)
        
        pending = sum(1 for a in alerts if not a.get("notification_sent", False))
        
        return AlertStatsResponse(
            total_alerts_24h=len(alerts),
            critical_alerts=critical_count,
            high_alerts=high_count,
            by_industry=by_industry,
            avg_urgency_score=round(avg_urgency, 2),
            pending_notifications=pending
        )


_alert_service: Optional[SmartAlertService] = None


def get_alert_service() -> SmartAlertService:
    """Get singleton alert service instance."""
    global _alert_service
    if _alert_service is None:
        _alert_service = SmartAlertService()
    return _alert_service
