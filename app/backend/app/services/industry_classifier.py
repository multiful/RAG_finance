"""Industry classification service."""
import openai
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import (
    IndustryClassificationRequest,
    IndustryClassificationResponse,
    IndustryType
)


class IndustryClassifier:
    """Industry classification using LLM + embeddings."""
    
    # Keywords for weak labeling
    INDUSTRY_KEYWORDS = {
        IndustryType.INSURANCE: [
            "보험", "생명보험", "손해보험", "보험료", "보험금", "계약자", "피보험자",
            "보험사", "보험상품", "보험계약", "보장", "보험가입", "보험설계사"
        ],
        IndustryType.BANKING: [
            "은행", "예금", "대출", "이자", "금리", "대출금리", "예금금리",
            "은행권", "시중은행", "지방은행", "특수은행", "금융지주", "캐피탈"
        ],
        IndustryType.SECURITIES: [
            "증권", "주식", "채권", "펀드", "투자", "투자자", "증권사",
            "코스피", "코스닥", "주식시장", "증시", "자산운용", "자산관리"
        ]
    }
    
    def __init__(self):
        self.db = get_db()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _keyword_based_classification(self, text: str) -> Dict[str, float]:
        """Weak labeling using keywords."""
        text_lower = text.lower()
        scores = {}
        
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            scores[industry.value] = min(1.0, count / 3)  # Normalize
        
        return scores
    
    async def _llm_classification(self, text: str) -> Dict[str, Any]:
        """LLM-based classification with explanation."""
        
        prompt = f"""다음 금융정책 문서를 분석하여 영향을 받는 업권을 분류하세요.

문서 내용:
{text[:2000]}

응답 형식 (JSON):
{{
    "insurance": 0.0-1.0,
    "banking": 0.0-1.0,
    "securities": 0.0-1.0,
    "predicted_labels": ["INSURANCE", "BANKING", ...],
    "explanation": "분류 근거 설명",
    "key_phrases": ["관련 문구1", "관련 문구2"]
}}

참고: 값은 0.0~1.0 사이의 신뢰도, 복수 업권 영향 가능"""

        model = (settings.OPENAI_MODEL_CLASSIFICATION or settings.OPENAI_MODEL).strip() or settings.OPENAI_MODEL
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "당신은 금융정책·규제 문서의 업권(보험/은행/증권) 영향 분류 전문가입니다. JSON 형식만 출력하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"LLM classification error: {e}")
        
        return {
            "insurance": 0.0,
            "banking": 0.0,
            "securities": 0.0,
            "predicted_labels": [],
            "explanation": "분류 실패",
            "key_phrases": []
        }
    
    async def classify(
        self,
        request: IndustryClassificationRequest
    ) -> IndustryClassificationResponse:
        """Classify document by industry impact."""
        
        # Get text
        if request.text:
            text = request.text
        elif request.document_id:
            # Fetch document from DB; 본문은 raw_text 우선, 없으면 chunks에서 수집(실제 데이터)
            result = self.db.table("documents").select("*").eq(
                "document_id", request.document_id
            ).execute()
            
            if not result.data:
                return IndustryClassificationResponse(
                    document_id=request.document_id,
                    label_insurance=0.0,
                    label_banking=0.0,
                    label_securities=0.0,
                    predicted_labels=[],
                    explanation="문서를 찾을 수 없습니다.",
                    evidence_chunk_ids=[]
                )
            
            doc = result.data[0]
            text = doc.get("raw_text") or doc.get("raw_html", "")
            if not text or not text.strip():
                chunks_res = self.db.table("chunks").select("chunk_text").eq(
                    "document_id", request.document_id
                ).order("chunk_index").limit(25).execute()
                if chunks_res.data:
                    text = "\n\n".join([c["chunk_text"] for c in chunks_res.data])
            if not text or not text.strip():
                return IndustryClassificationResponse(
                    document_id=request.document_id,
                    label_insurance=0.0,
                    label_banking=0.0,
                    label_securities=0.0,
                    predicted_labels=[],
                    explanation="문서 본문이 없습니다. 파이프라인에서 파싱·청킹이 완료된 문서를 사용하세요.",
                    evidence_chunk_ids=[]
                )
        else:
            return IndustryClassificationResponse(
                label_insurance=0.0,
                label_banking=0.0,
                label_securities=0.0,
                predicted_labels=[],
                explanation="입력 텍스트 또는 문서 ID가 필요합니다.",
                evidence_chunk_ids=[]
            )
        
        # Get LLM classification
        llm_result = await self._llm_classification(text)
        
        # Get keyword scores for hybrid approach
        keyword_scores = self._keyword_based_classification(text)
        
        # Combine scores (weighted average)
        combined = {
            "insurance": llm_result.get("insurance", 0) * 0.7 + keyword_scores.get("INSURANCE", 0) * 0.3,
            "banking": llm_result.get("banking", 0) * 0.7 + keyword_scores.get("BANKING", 0) * 0.3,
            "securities": llm_result.get("securities", 0) * 0.7 + keyword_scores.get("SECURITIES", 0) * 0.3
        }
        
        # Determine predicted labels (threshold 0.3)
        predicted = []
        for key, score in combined.items():
            if score >= 0.3:
                predicted.append(IndustryType(key.upper()))
        
        # If no labels above threshold, take highest
        if not predicted and combined:
            max_key = max(combined, key=combined.get)
            predicted.append(IndustryType(max_key.upper()))
        
        # Find evidence chunks
        evidence_chunks = []
        key_phrases = llm_result.get("key_phrases", [])
        
        if key_phrases and request.document_id:
            # Search for chunks containing key phrases
            for phrase in key_phrases[:2]:
                chunks_result = self.db.table("chunks").select("chunk_id").eq(
                    "document_id", request.document_id
                ).ilike("chunk_text", f"%{phrase}%").limit(3).execute()
                
                if chunks_result.data:
                    evidence_chunks.extend([c["chunk_id"] for c in chunks_result.data])
        
        # Save classification result
        if request.document_id:
            self.db.table("industry_labels").upsert({
                "document_id": request.document_id,
                "label_insurance": combined["insurance"],
                "label_banking": combined["banking"],
                "label_securities": combined["securities"],
                "predicted_labels": [p.value for p in predicted],
                "model_version": "llm_hybrid_v1",
                "explanation_chunk_ids": evidence_chunks[:5]
            }).execute()
        
        return IndustryClassificationResponse(
            document_id=request.document_id,
            label_insurance=combined["insurance"],
            label_banking=combined["banking"],
            label_securities=combined["securities"],
            predicted_labels=predicted,
            explanation=llm_result.get("explanation", ""),
            evidence_chunk_ids=evidence_chunks[:5]
        )
    
    async def batch_classify(self, document_ids: List[str]) -> List[IndustryClassificationResponse]:
        """Classify multiple documents."""
        results = []
        for doc_id in document_ids:
            request = IndustryClassificationRequest(document_id=doc_id)
            result = await self.classify(request)
            results.append(result)
        return results
