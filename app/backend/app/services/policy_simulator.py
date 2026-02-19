"""Policy Simulator Service."""
import json
from typing import List, Dict, Any
from app.core.config import settings
from app.core.database import get_db
from datetime import datetime
from app.models.schemas import PolicyDiffResponse, PolicyDiffItem
import openai

class PolicySimulator:
    """Simulate policy changes between two documents."""
    
    def __init__(self):
        self.db = get_db()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def simulate(self, old_doc_id: str, new_doc_id: str) -> PolicyDiffResponse:
        """Analyze differences between two policy documents."""
        # 1. Fetch metadata and content
        old_doc = self.db.table("documents").select("title").eq("document_id", old_doc_id).execute()
        new_doc = self.db.table("documents").select("title").eq("document_id", new_doc_id).execute()
        
        old_text = await self._get_doc_text(old_doc_id)
        new_text = await self._get_doc_text(new_doc_id)
        
        old_title = old_doc.data[0]["title"] if old_doc.data else "Old Policy"
        new_title = new_doc.data[0]["title"] if new_doc.data else "New Policy"

        if not old_text or not new_text:
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="low",
                summary="문서 내용을 찾을 수 없습니다.",
                generated_at=datetime.now()
            )

        # 2. LLM Analysis
        prompt = f"""Compare the two financial policy documents and create a detailed regulatory impact map.
Find EXACT changes in clauses, duties, and restrictions.

OLD DOCUMENT: {old_title}
CONTENT: {old_text[:4000]}

NEW DOCUMENT: {new_title}
CONTENT: {new_text[:4000]}

Output EXACT JSON:
{{
  "changes": [
    {{
      "clause": "조항 번호 또는 제목",
      "change_type": "added/modified/removed",
      "description": "변경 내용 요약 (한국어)",
      "risk_level": "high/medium/low",
      "impacted_process": "영향을 받는 업무 프로세스"
    }}
  ],
  "overall_risk": "high/medium/low",
  "summary": "전체 변경사항 요약 (한국어)"
}}
"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 금융 규제 준수(Compliance) 분석가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[PolicyDiffItem(**item) for item in data.get("changes", [])],
                overall_risk=data.get("overall_risk", "low"),
                summary=data.get("summary", ""),
                generated_at=datetime.now()
            )
        except Exception as e:
            print(f"Policy Diff Error: {e}")
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="low",
                summary=f"분석 중 오류 발생: {str(e)}",
                generated_at=datetime.now()
            )

    async def _get_doc_text(self, doc_id: str) -> str:
        res = self.db.table("chunks").select("chunk_text").eq("document_id", doc_id).limit(5).execute()
        return "\n".join([c["chunk_text"] for c in res.data]) if res.data else ""

simulator = PolicySimulator()
