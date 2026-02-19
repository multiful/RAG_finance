"""Policy Simulator Service."""
import json
from typing import List, Dict, Any
from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import PolicySimulationResponse
import openai

class PolicySimulator:
    """Simulate policy changes between two documents."""
    
    def __init__(self):
        self.db = get_db()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def simulate(self, old_doc_id: str, new_doc_id: str) -> PolicySimulationResponse:
        """Analyze differences between two policy documents."""
        # 1. Fetch chunks for both
        old_chunks = await self._get_doc_text(old_doc_id)
        new_chunks = await self._get_doc_text(new_doc_id)
        
        if not old_chunks or not new_chunks:
            return PolicySimulationResponse(
                added_duties=[],
                removed_restrictions=[],
                modified_requirements=["Document content not found"],
                risk_level="unknown",
                confidence=0.0
            )

        # 2. LLM Analysis
        prompt = f"""Compare the following two policy documents and identify regulatory changes.

OLD POLICY (Summary):
{old_chunks[:3000]}

NEW POLICY (Summary):
{new_chunks[:3000]}

Output JSON:
{{
  "added_duties": ["List of new obligations"],
  "removed_restrictions": ["List of lifted bans"],
  "modified_requirements": ["List of requirements that were changed"],
  "risk_level": "low/medium/high",
  "confidence": 0.0-1.0
}}
"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return PolicySimulationResponse(**data)
        except Exception as e:
            return PolicySimulationResponse(
                added_duties=[],
                removed_restrictions=[],
                modified_requirements=[f"Error: {str(e)}"],
                risk_level="unknown",
                confidence=0.0
            )

    async def _get_doc_text(self, doc_id: str) -> str:
        res = self.db.table("chunks").select("chunk_text").eq("document_id", doc_id).limit(5).execute()
        return "\n".join([c["chunk_text"] for c in res.data]) if res.data else ""

simulator = PolicySimulator()
