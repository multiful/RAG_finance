"""Compliance checklist extraction service."""
import openai
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import ChecklistRequest, ChecklistResponse, ChecklistItem


class ChecklistService:
    """Extract compliance checklist items from documents."""
    
    def __init__(self):
        self.db = get_db()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def extract_checklist(self, request: ChecklistRequest) -> ChecklistResponse:
        """Extract checklist from document."""
        
        # Get document
        doc_result = self.db.table("documents").select("*").eq(
            "document_id", request.document_id
        ).execute()
        
        if not doc_result.data:
            return ChecklistResponse(
                checklist_id="",
                document_id=request.document_id,
                document_title="",
                items=[],
                generated_at=datetime.now()
            )
        
        doc = doc_result.data[0]
        
        # Get chunks
        chunks_result = self.db.table("chunks").select("*").eq(
            "document_id", request.document_id
        ).order("chunk_index").execute()
        
        if not chunks_result.data:
            return ChecklistResponse(
                checklist_id="",
                document_id=request.document_id,
                document_title=doc["title"],
                items=[],
                generated_at=datetime.now()
            )
        
        # Combine chunks
        full_text = "\n".join([c["chunk_text"] for c in chunks_result.data])
        
        # Extract checklist using LLM
        items = await self._extract_with_llm(full_text, chunks_result.data)
        
        # Save checklist
        checklist_result = self.db.table("checklists").insert({
            "document_id": request.document_id,
            "generated_by_model": settings.OPENAI_MODEL,
            "model_version": "v1"
        }).execute()
        
        checklist_id = checklist_result.data[0]["checklist_id"] if checklist_result.data else ""
        
        # Save items
        for item in items:
            self.db.table("checklist_items").insert({
                "checklist_id": checklist_id,
                "action": item.action,
                "target": item.target,
                "due_date_text": item.due_date_text,
                "effective_date": item.effective_date,
                "scope": item.scope,
                "penalty": item.penalty,
                "evidence_chunk_id": item.evidence_chunk_id,
                "confidence": item.confidence
            }).execute()
        
        return ChecklistResponse(
            checklist_id=checklist_id,
            document_id=request.document_id,
            document_title=doc["title"],
            items=items,
            generated_at=datetime.now()
        )
    
    async def _extract_with_llm(
        self,
        text: str,
        chunks: List[Dict[str, Any]]
    ) -> List[ChecklistItem]:
        """Extract checklist items using LLM."""
        
        prompt = f"""다음 금융정책 문서에서 준수 체크리스트 항목을 추출하세요.

문서 내용:
{text[:4000]}

각 항목을 다음 JSON 형식으로 추출:
{{
    "checklist": [
        {{
            "action": "해야 할 일 (필수)",
            "target": "대상 (예: 보험사, 은행 등)",
            "due_date_text": "기한/시행일 (예: 2024년 3월 31일까지)",
            "scope": "적용 범위",
            "penalty": "위반 시 제재 (언급된 경우)"
        }}
    ]
}}

주의사항:
- 문서에 명시된 내용만 추출
- 추측하지 말 것
- 근거가 명확한 항목만 포함
- 없으면 빈 배열 반환"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "금융 규제 준수 전문가"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                checklist_data = data.get("checklist", [])
                
                items = []
                for item_data in checklist_data:
                    # Find evidence chunk
                    evidence_chunk_id = await self._find_evidence_chunk(
                        item_data.get("action", ""),
                        chunks
                    )
                    
                    # Parse effective date
                    effective_date = None
                    due_text = item_data.get("due_date_text", "")
                    date_match = re.search(r'(\d{4})[년.-]\s*(\d{1,2})[월.-]\s*(\d{1,2})', due_text)
                    if date_match:
                        try:
                            effective_date = datetime(
                                int(date_match.group(1)),
                                int(date_match.group(2)),
                                int(date_match.group(3))
                            )
                        except ValueError:
                            pass
                    
                    items.append(ChecklistItem(
                        action=item_data.get("action", ""),
                        target=item_data.get("target"),
                        due_date_text=due_text,
                        effective_date=effective_date,
                        scope=item_data.get("scope"),
                        penalty=item_data.get("penalty"),
                        evidence_chunk_id=evidence_chunk_id,
                        confidence=0.8 if evidence_chunk_id else 0.5
                    ))
                
                return items
        
        except Exception as e:
            print(f"Checklist extraction error: {e}")
        
        return []
    
    async def _find_evidence_chunk(
        self,
        action_text: str,
        chunks: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find chunk containing evidence for action."""
        
        # Extract key phrases from action
        key_phrases = re.findall(r'[가-힣]{2,}', action_text)
        
        best_chunk = None
        best_score = 0
        
        for chunk in chunks:
            chunk_text = chunk.get("chunk_text", "")
            score = sum(1 for phrase in key_phrases if phrase in chunk_text)
            
            if score > best_score:
                best_score = score
                best_chunk = chunk
        
        return best_chunk["chunk_id"] if best_chunk and best_score >= 2 else None
    
    async def get_checklist_by_document(
        self,
        document_id: str
    ) -> Optional[ChecklistResponse]:
        """Get existing checklist for document."""
        
        result = self.db.table("checklists").select("*").eq(
            "document_id", document_id
        ).order("created_at", desc=True).limit(1).execute()
        
        if not result.data:
            return None
        
        checklist = result.data[0]
        
        # Get items
        items_result = self.db.table("checklist_items").select("*").eq(
            "checklist_id", checklist["checklist_id"]
        ).execute()
        
        items = []
        if items_result.data:
            for item in items_result.data:
                items.append(ChecklistItem(
                    action=item["action"],
                    target=item.get("target"),
                    due_date_text=item.get("due_date_text"),
                    effective_date=item.get("effective_date"),
                    scope=item.get("scope"),
                    penalty=item.get("penalty"),
                    evidence_chunk_id=item.get("evidence_chunk_id"),
                    confidence=item.get("confidence", 0.5)
                ))
        
        # Get document title
        doc_result = self.db.table("documents").select("title").eq(
            "document_id", document_id
        ).execute()
        
        doc_title = doc_result.data[0]["title"] if doc_result.data else ""
        
        return ChecklistResponse(
            checklist_id=checklist["checklist_id"],
            document_id=document_id,
            document_title=doc_title,
            items=items,
            generated_at=checklist["created_at"]
        )
    
    def export_checklist(
        self,
        checklist: ChecklistResponse,
        format: str = "json"
    ) -> str:
        """Export checklist to various formats."""
        
        if format == "markdown":
            lines = [
                f"# 준수 체크리스트: {checklist.document_title}",
                "",
                "| 항목 | 대상 | 기한 | 적용범위 | 제재 |",
                "|------|------|------|----------|------|"
            ]
            
            for item in checklist.items:
                lines.append(
                    f"| {item.action} | {item.target or '-'} | "
                    f"{item.due_date_text or '-'} | {item.scope or '-'} | "
                    f"{item.penalty or '-'} |"
                )
            
            return "\n".join(lines)
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["항목", "대상", "기한", "적용범위", "제재", "신뢰도"])
            
            for item in checklist.items:
                writer.writerow([
                    item.action,
                    item.target or "",
                    item.due_date_text or "",
                    item.scope or "",
                    item.penalty or "",
                    item.confidence
                ])
            
            return output.getvalue()
        
        else:  # json
            return json.dumps({
                "document_id": checklist.document_id,
                "document_title": checklist.document_title,
                "generated_at": checklist.generated_at.isoformat(),
                "items": [
                    {
                        "action": item.action,
                        "target": item.target,
                        "due_date_text": item.due_date_text,
                        "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                        "scope": item.scope,
                        "penalty": item.penalty,
                        "confidence": item.confidence
                    }
                    for item in checklist.items
                ]
            }, ensure_ascii=False, indent=2)
