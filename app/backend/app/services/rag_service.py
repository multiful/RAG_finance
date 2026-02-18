"""RAG (Retrieval Augmented Generation) service."""
import openai
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.schemas import (
    QARequest, QAResponse, Citation, IndustryType,
    ChunkResponse, ChecklistItem
)


class RAGService:
    """RAG service with hybrid search, reranking, and guardrails."""
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        cache_key = f"emb:{hash(text) % 10000000}"
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        response = await self.openai_client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text[:8000]
        )
        embedding = response.data[0].embedding
        
        # Cache for 24 hours
        self.redis.setex(cache_key, 86400, json.dumps(embedding))
        return embedding
    
    async def _hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        industry_filter: Optional[List[IndustryType]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search (BM25 + Vector)."""
        
        # Build base query
        db_query = self.db.table("chunks").select(
            "*, documents!inner(title, published_at, url, department)"
        )
        
        # Apply filters
        if date_from:
            db_query = db_query.gte("documents.published_at", date_from.isoformat())
        if date_to:
            db_query = db_query.lte("documents.published_at", date_to.isoformat())
        
        # Vector similarity search using pgvector
        vector_results = db_query.order(
            f"embedding <-> '{json.dumps(query_embedding)}'::vector"
        ).limit(top_k * 2).execute()
        
        chunks = []
        if vector_results.data:
            for item in vector_results.data:
                chunk = {
                    "chunk_id": item["chunk_id"],
                    "chunk_text": item["chunk_text"],
                    "chunk_index": item["chunk_index"],
                    "section_title": item.get("section_title"),
                    "document_id": item["document_id"],
                    "document_title": item["documents"]["title"],
                    "published_at": item["documents"]["published_at"],
                    "url": item["documents"]["url"],
                    "department": item["documents"].get("department"),
                    "similarity": 1.0  # Will be updated by reranker
                }
                chunks.append(chunk)
        
        return chunks[:top_k]
    
    async def _rerank_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank chunks using LLM-based scoring."""
        if not chunks:
            return []
        
        # Prepare reranking prompt
        chunk_texts = []
        for i, chunk in enumerate(chunks):
            preview = chunk["chunk_text"][:300].replace("\n", " ")
            chunk_texts.append(f"[{i}] {preview}...")
        
        rerank_prompt = f"""Query: {query}

Document chunks:
{chr(10).join(chunk_texts)}

Rate each chunk's relevance to the query (0-10). Respond in JSON:
{{"scores": [{{"index": 0, "score": 8, "reason": "..."}}, ...]}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a relevance scoring assistant."},
                    {"role": "user", "content": rerank_prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                scores_data = json.loads(json_match.group())
                scores = {s["index"]: s["score"] for s in scores_data.get("scores", [])}
                
                # Update chunk scores
                for i, chunk in enumerate(chunks):
                    chunk["similarity"] = scores.get(i, 5) / 10
                
                # Sort by score
                chunks.sort(key=lambda x: x["similarity"], reverse=True)
        
        except Exception as e:
            print(f"Reranking error: {e}")
        
        return chunks[:top_k]
    
    async def _check_answerability(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """Check if query can be answered from retrieved chunks."""
        if not chunks:
            return False, "검색된 문서가 없습니다."
        
        combined_text = " ".join([c["chunk_text"] for c in chunks[:3]])
        
        check_prompt = f"""Query: {query}

Retrieved text: {combined_text[:1000]}

Can this query be answered from the retrieved text? Answer only YES or NO with brief reason."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": check_prompt}],
                temperature=0,
                max_tokens=100
            )
            
            content = response.choices[0].message.content.upper()
            if "YES" in content:
                return True, ""
            else:
                return False, "검색된 문서에서 답을 찾을 수 없습니다."
        
        except Exception:
            return True, ""  # Default to allowing
    
    async def _generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate grounded answer with citations."""
        
        # Prepare context
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(
                f"[출처 {i+1}] {chunk['document_title']} ({chunk['published_at'][:10]})\n"
                f"{chunk['chunk_text']}\n"
            )
        
        context = "\n".join(context_parts)
        
        # Generate answer with structured output
        system_prompt = """당신은 금융정책 전문가입니다. 제공된 문서만을 기반으로 답변하세요.

답변 형식:
1. 요약 (3줄 이내)
2. 업권 영향 (보험/은행/증권별 영향도 0-1)
3. 체크리스트 (의무/기한/대상)
4. 근거 인용 (문서명/발행일)
5. 불확실성 표시 (근거 불충분 시)

중요: 문서에 없는 정보는 추측하지 말고 "확인되지 않음"으로 표시하세요."""

        user_prompt = f"""질문: {query}

참고 문서:
{context}

위 문서만을 기반으로 구조화된 답변을 제공하세요."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            answer_text = response.choices[0].message.content
            
            # Parse structured output
            return self._parse_structured_answer(answer_text, chunks)
            
        except Exception as e:
            return {
                "answer": f"답변 생성 중 오류: {str(e)}",
                "summary": "오류 발생",
                "industry_impact": {},
                "checklist": [],
                "uncertainty": "시스템 오류"
            }
    
    def _parse_structured_answer(
        self,
        answer_text: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse structured answer from LLM output."""
        result = {
            "answer": answer_text,
            "summary": "",
            "industry_impact": {"INSURANCE": 0.0, "BANKING": 0.0, "SECURITIES": 0.0},
            "checklist": [],
            "uncertainty": None
        }
        
        # Extract summary (first 3 lines after "요약" or first paragraph)
        lines = answer_text.split("\n")
        summary_lines = []
        for line in lines:
            if "요약" in line or len(summary_lines) > 0:
                clean = line.replace("요약", "").replace("**", "").strip()
                if clean:
                    summary_lines.append(clean)
            if len(summary_lines) >= 3:
                break
        
        if not summary_lines:
            summary_lines = lines[:3]
        
        result["summary"] = " ".join(summary_lines)
        
        # Extract industry impact
        for industry in ["보험", "은행", "증권"]:
            pattern = rf"{industry}.*?([0-9.]+)"
            match = re.search(pattern, answer_text)
            if match:
                key = industry.replace("보험", "INSURANCE").replace("은행", "BANKING").replace("증권", "SECURITIES")
                result["industry_impact"][key] = float(match.group(1))
        
        # Check for uncertainty markers
        uncertainty_markers = ["확인되지 않음", "불확실", "추가 확인 필요", "근거 없음"]
        for marker in uncertainty_markers:
            if marker in answer_text:
                result["uncertainty"] = marker
                break
        
        return result
    
    async def answer_question(self, request: QARequest) -> QAResponse:
        """Main RAG pipeline."""
        
        # 1. Get query embedding
        query_embedding = await self._get_embedding(request.question)
        
        # 2. Hybrid search
        chunks = await self._hybrid_search(
            query=request.question,
            query_embedding=query_embedding,
            top_k=settings.TOP_K_RETRIEVAL,
            industry_filter=request.industry_filter,
            date_from=request.date_from,
            date_to=request.date_to
        )
        
        # 3. Rerank
        reranked_chunks = await self._rerank_chunks(
            query=request.question,
            chunks=chunks,
            top_k=settings.TOP_K_RERANK
        )
        
        # 4. Guardrail: Answerability check
        can_answer, reason = await self._check_answerability(
            request.question, reranked_chunks
        )
        
        if not can_answer:
            return QAResponse(
                answer="죄송합니다. 검색된 문서에서 해당 질문에 대한 답을 찾을 수 없습니다.",
                summary="근거 부족",
                industry_impact={},
                checklist=[],
                citations=[],
                confidence=0.0,
                uncertainty_note=reason
            )
        
        # 5. Generate answer
        answer_data = await self._generate_answer(request.question, reranked_chunks)
        
        # 6. Build citations
        citations = [
            Citation(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                document_title=chunk["document_title"],
                published_at=chunk["published_at"],
                snippet=chunk["chunk_text"][:200],
                url=chunk["url"]
            )
            for chunk in reranked_chunks
        ]
        
        return QAResponse(
            answer=answer_data["answer"],
            summary=answer_data["summary"],
            industry_impact=answer_data["industry_impact"],
            checklist=answer_data.get("checklist", []),
            citations=citations,
            confidence=min(1.0, len(reranked_chunks) * 0.2 + 0.3),
            uncertainty_note=answer_data.get("uncertainty")
        )
