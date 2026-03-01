"""Policy Simulator Service."""
import json
import logging
from typing import List, Dict, Any
from app.core.config import settings
from app.core.database import get_db
from datetime import datetime, timezone
from app.models.schemas import PolicyDiffResponse, PolicyDiffItem
import openai

logger = logging.getLogger(__name__)

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
            missing = []
            if not old_text:
                missing.append("문서 A(기준)")
            if not new_text:
                missing.append("문서 B(비교)")
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="medium",
                summary=f"{', '.join(missing)}에 수집·파싱된 본문이 없습니다. 설정에서 수집을 실행한 뒤, 파이프라인에서 파싱·인덱싱이 완료된 문서를 선택해 주세요.",
                generated_at=datetime.now(timezone.utc),
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
            def _norm_risk(v: str) -> str:
                r = (v or "medium").strip().lower()
                return r if r in ("high", "medium", "low") else "medium"

            raw_changes = data.get("changes") or []
            changes: List[PolicyDiffItem] = []
            for i, item in enumerate(raw_changes):
                if not isinstance(item, dict):
                    continue
                try:
                    changes.append(PolicyDiffItem(
                        clause=str(item.get("clause", "") or ""),
                        change_type=str(item.get("change_type", "modified") or "modified"),
                        description=str(item.get("description", "") or ""),
                        risk_level=_norm_risk(str(item.get("risk_level", "medium") or "medium")),
                        impacted_process=str(item.get("impacted_process", "") or ""),
                    ))
                except Exception as parse_err:
                    logger.debug("PolicyDiffItem skip item %s: %s", i, parse_err)
            risk = (data.get("overall_risk") or "low").strip().lower()
            if risk not in ("high", "medium", "low"):
                risk = "medium"
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=changes,
                overall_risk=risk,
                summary=str(data.get("summary") or ""),
                generated_at=datetime.now(timezone.utc),
            )
        except json.JSONDecodeError as e:
            logger.warning("Policy simulate JSON decode error: %s", e)
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="medium",
                summary=f"분석 결과 파싱 오류: {str(e)}",
                generated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.exception("Policy Diff Error: %s", e)
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="medium",
                summary=f"분석 중 오류 발생: {str(e)}",
                generated_at=datetime.now(timezone.utc),
            )

    async def _get_doc_text(self, doc_id: str) -> str:
        """실제 chunks 테이블에서 문서 본문 수집 (최대 30청크, 실제값 반영)."""
        res = self.db.table("chunks").select("chunk_text").eq("document_id", doc_id).order("chunk_index").limit(30).execute()
        if not res.data:
            return ""
        return "\n\n".join([c["chunk_text"] for c in res.data])

simulator = PolicySimulator()
