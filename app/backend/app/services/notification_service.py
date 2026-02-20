"""Notification service for compliance items."""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings


class NotificationService:
    """Sends notifications for compliance action items."""
    
    def __init__(self):
        # Safely get SLACK_WEBHOOK_URL from settings
        self.webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", None)

    async def send_action_item_notification(self, item: Dict[str, Any], event_type: str = "update") -> bool:
        """Sends notification to Slack (if configured)."""
        if not self.webhook_url:
            print(f"DEBUG: Notification skipped for {item.get('action_item_id')} (No Slack webhook configured)")
            return False
            
        try:
            action = item.get("action", "Compliance Task")
            status = item.get("status", "unknown")
            assigned_user = item.get("assigned_user_id", "Unassigned")
            
            message = {
                "text": f"🔔 Compliance Action Item {event_type.capitalize()}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Action Item:* {action}\n*Status:* {status}\n*Assigned to:* {assigned_user}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"Event time: {datetime.now().isoformat()}"}
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=message)
                return response.status_code == 200
                
        except Exception as e:
            print(f"ERROR: Failed to send Slack notification: {e}")
            return False
