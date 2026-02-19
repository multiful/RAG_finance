"""RAG (Retrieval Augmented Generation) service."""
import openai
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.services.vector_store import get_vector_store
from app.models.schemas import (
    QARequest, QAResponse, Citation, IndustryType,
    ChunkResponse, ChecklistItem
)


class RAGService:
    """RAG service with hybrid search, reranking, and guardrails."""
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
        self.vector_store = get_vector_store()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"emb:{text_hash}"
        cached = self.redis.get(cache_key)
        
        if cached:
            print(f"DEBUG: Using cached query embedding for '{text[:20]}...'")
            return json.loads(cached)
        
        print(f"DEBUG: Calling OpenAI for query embedding (model={settings.OPENAI_EMBEDDING_MODEL})")
        response = await self.openai_client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text[:8000]
        )
        embedding = response.data[0].embedding
        
        # Cache for 24 hours
        self.redis.setex(cache_key, 86400, json.dumps(embedding))
        print(f"DEBUG: Successfully generated embedding (dims={len(embedding)})")
        return embedding
    
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
        """Parse structured answer from LLM output with robust numeric handling."""
        result = {
            "answer": answer_text,
            "summary": "",
            "industry_impact": {"INSURANCE": 0.0, "BANKING": 0.0, "SECURITIES": 0.0},
            "checklist": [],
            "uncertainty_note": None
        }
        
        def safe_float(val_str: Any) -> float:
            """Robustly converts inputs to float in range [0, 1]."""
            if val_str is None:
                return 0.0
            try:
                s = str(val_str).strip().replace(',', '.')
                match = re.search(r"[-+]?\d*\.\d+|\d+", s)
                if not match:
                    return 0.0
                val = float(match.group())
                return max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                return 0.0

        # 1. Extract Summary
        lines = [l.strip() for l in answer_text.split("\n") if l.strip()]
        summary_lines = []
        for line in lines:
            if "요약" in line or len(summary_lines) > 0:
                clean = re.sub(r'요약|[*:#]', '', line).strip()
                if clean:
                    summary_lines.append(clean)
            if len(summary_lines) >= 3:
                break
        
        if summary_lines:
            result["summary"] = " ".join(summary_lines)
        else:
            result["summary"] = " ".join(lines[:3]) if lines else "No summary available"

        # 2. Extract Industry Impact
        industry_map = {"보험": "INSURANCE", "은행": "BANKING", "증권": "SECURITIES"}
        for kor_name, eng_key in industry_map.items():
            pattern = rf"{kor_name}.*?([0-9.,]+)"
            match = re.search(pattern, answer_text)
            if match:
                result["industry_impact"][eng_key] = safe_float(match.group(1))

        # 3. Extract Uncertainty Note
        uncertainty_markers = ["확인되지 않음", "불확실", "추가 확인 필요", "근거 없음", "시스템 오류"]
        for marker in uncertainty_markers:
            if marker in answer_text:
                result["uncertainty_note"] = marker
                break

        return result

    async def answer_question(self, request: QARequest) -> QAResponse:
        """Main RAG pipeline: Embedding -> Hybrid Search -> Rerank -> LLM -> Parse."""
        start_time = datetime.now()
        
        # 1. Get query embedding
        query_embedding = await self._get_embedding(request.question)
        
        # 2. Hybrid Search
        filters = {}
        if request.date_from:
            filters["date_from"] = request.date_from.isoformat()
        
        search_results = await self.vector_store.hybrid_search(
            query=request.question,
            query_embedding=query_embedding,
            top_k=settings.TOP_K_RETRIEVAL,
            filters=filters
        )
        
        print(f"DEBUG: Retrieval returned {len(search_results)} chunks.")

        # 3. Optional Reranking
        if settings.ENABLE_RERANKING:
            reranked_results = await self.vector_store.rerank(
                query=request.question,
                results=search_results,
                top_k=settings.TOP_K_RERANK
            )
        else:
            print("DEBUG: Reranking disabled. Using top retrieval hits.")
            reranked_results = search_results[:settings.TOP_K_RERANK]
        
        reranked_chunks = [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "document_title": r.document_title,
                "published_at": r.published_at,
                "url": r.url,
                "chunk_text": r.chunk_text,
                "similarity": r.similarity
            }
            for r in reranked_results
        ]
        
        if not reranked_chunks:
            return QAResponse(
                answer="죄송합니다. 관련 문서를 찾을 수 없습니다.",
                summary="검색 결과 없음",
                industry_impact={"INSURANCE": 0.0, "BANKING": 0.0, "SECURITIES": 0.0},
                checklist=[],
                citations=[],
                confidence=0.0,
                uncertainty_note="검색된 정보가 없습니다."
            )
        
        # 4. Generate Answer
        answer_data = await self._generate_answer(request.question, reranked_chunks)
        
        # 5. Build Citations
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
        
        # 6. Parse and Return
        structured_data = self._parse_structured_answer(answer_data["answer"], reranked_chunks)
        
        # Determine if answerable
        # If the answer contains common "I don't know" phrases, mark as not answerable
        unanswerable_phrases = ["확인되지 않음", "정보가 없습니다", "답변을 찾을 수 없습니다", "명시되어 있지 않습니다"]
        answerable = not any(phrase in structured_data["answer"] for phrase in unanswerable_phrases)
        if structured_data.get("uncertainty_note"):
            answerable = False

        # 7. Async Logging to qa_logs
        try:
            from fastapi.encoders import jsonable_encoder
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.db.table("qa_logs").insert(jsonable_encoder({
                "user_query": request.question,
                "retrieved_chunk_ids": [chunk["chunk_id"] for chunk in reranked_chunks],
                "answer": structured_data["answer"],
                "citations": citations,
                "latency_ms": latency_ms
            })).execute()
        except Exception as log_err:
            print(f"Logging to qa_logs failed: {log_err}")

        return QAResponse(
            answer=structured_data["answer"],
            summary=structured_data["summary"],
            industry_impact=structured_data["industry_impact"],
            checklist=structured_data.get("checklist", []),
            citations=citations,
            confidence=0.85 if len(citations) > 0 else 0.0,
            uncertainty_note=structured_data.get("uncertainty_note"),
            answerable=answerable
        )

    async def stream_answer(self, request: QARequest):
        """Stream RAG answer with citations and structured metadata."""
        
        # 1-3. Retrieval and Reranking (Same as non-streaming)
        query_embedding = await self._get_embedding(request.question)
        
        filters = {}
        if request.date_from:
            filters["date_from"] = request.date_from.isoformat()
        if request.date_to:
            filters["date_to"] = request.date_to.isoformat()

        search_results = await self.vector_store.hybrid_search(
            query=request.question,
            query_embedding=query_embedding,
            top_k=settings.TOP_K_RETRIEVAL,
            filters=filters
        )
        
        if settings.ENABLE_RERANKING:
            reranked_results = await self.vector_store.rerank(
                query=request.question,
                results=search_results,
                top_k=settings.TOP_K_RERANK
            )
        else:
            reranked_results = search_results[:settings.TOP_K_RERANK]

        reranked_chunks = [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "document_title": r.document_title,
                "published_at": r.published_at,
                "url": r.url,
                "chunk_text": r.chunk_text,
                "similarity": r.similarity
            }
            for r in reranked_results
        ]
        
        # 4. Citations (Send immediately)
        citations = [
            {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "document_title": chunk["document_title"],
                "published_at": chunk["published_at"],
                "snippet": chunk["chunk_text"][:200],
                "url": chunk["url"]
            }
            for chunk in reranked_chunks
        ]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        
        # 5. Answerability Guardrail
        can_answer, reason = await self._check_answerability(request.question, reranked_chunks)
        if not can_answer:
            yield f"data: {json.dumps({'type': 'error', 'content': reason})}\n\n"
            return

        # 6. Stream Generation
        context_parts = []
        for i, chunk in enumerate(reranked_chunks):
            context_parts.append(
                f"[출처 {i+1}] {chunk['document_title']} ({chunk['published_at'][:10]})\n"
                f"{chunk['chunk_text']}\n"
            )
        context = "\n".join(context_parts)
        
        system_prompt = """당신은 금융정책 전문가입니다. 제공된 문서만을 기반으로 답변하세요.
답변 형식:
1. 요약 (3줄 이내)
2. 업권 영향 (보험/은행/증권별 영향도 0-1)
3. 체크리스트 (의무/기한/대상)
4. 근거 인용 (문서명/발행일)
5. 불확실성 표시 (근거 불충분 시)"""

        user_prompt = f"질문: {request.question}\n\n참고 문서:\n{context}\n\n위 문서만을 기반으로 구조화된 답변을 제공하세요."

        full_answer = ""
        try:
            stream = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            
            # 7. Final structured data
            final_data = self._parse_structured_answer(full_answer, reranked_chunks)
            unanswerable_phrases = ["확인되지 않음", "정보가 없습니다", "답변을 찾을 수 없습니다", "명시되어 있지 않습니다"]
            final_data["answerable"] = not any(phrase in final_data["answer"] for phrase in unanswerable_phrases)
            if final_data.get("uncertainty_note"):
                final_data["answerable"] = False
                
            yield f"data: {json.dumps({'type': 'final', 'data': final_data})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
