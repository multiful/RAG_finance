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
    ) -> tuple[bool, str, float]:
        """Check if query can be answered from retrieved chunks.
        Returns (can_answer, reason, consistency_score)."""
        if not chunks:
            return False, "검색된 문서가 없습니다.", 0.0
        
        # Filter chunks by minimum similarity if available (similarity is from hybrid search RRF)
        # For RRF, scores are usually small, but let's assume if we have hits, we proceed
        # and let the LLM judge consistency.
        
        combined_text = "\n\n".join([f"[{i+1}] {c['chunk_text']}" for i, c in enumerate(chunks[:5])])
        
        check_prompt = f"""당신은 금융 정책 질의응답 검증관입니다.
질문: {query}

참고 문서 내용:
{combined_text[:2000]}

규칙:
1. 제공된 문서 내용만으로 질문에 대해 구체적인 답변이 가능하면 'YES'라고 하세요.
2. 문서에 관련 내용이 없거나 부족하면 'NO'라고 하고 이유를 짧게 쓰세요.
3. 답변의 근거가 되는 문서 번호를 나열하세요. (예: YES [1, 2])

출력 형식: [YES/NO] [이유] [근거번호]"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini", # Use mini for cheaper checks
                messages=[{"role": "user", "content": check_prompt}],
                temperature=0,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.upper()
            if "YES" in content:
                # Estimate consistency score based on how many chunks were useful
                cited_count = len(re.findall(r'\[\d+\]', content))
                consistency = min(1.0, cited_count / 2.0) # Assume 2 chunks is a solid answer
                return True, "", consistency
            else:
                return False, "검색된 문서에서 구체적인 답을 찾을 수 없습니다. (근거 부족)", 0.0
        
        except Exception:
            return True, "", 0.5  # Fallback to allowing
    
    async def _calculate_scores(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
        consistency_score: float
    ) -> tuple[float, float, float]:
        """Enhanced grounding and confidence score calculation.
        
        Features:
        - Sentence-level grounding analysis
        - Hallucination detection
        - Uncertainty quantification
        
        Returns (grounding_score, confidence_score, citation_coverage).
        """
        # 1. Calculate Citation Coverage
        citations_found = set(re.findall(r'\[(?:출처\s*)?(\d+)\]', answer))
        unique_citations = len(citations_found)
        citation_coverage = min(1.0, unique_citations / max(1, len(chunks)))
        
        # 2. Calculate Evidence Strength
        cited_similarities = []
        for idx_str in citations_found:
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(chunks):
                    cited_similarities.append(chunks[idx].get("similarity", 0.5))
            except ValueError:
                continue
        
        evidence_strength = sum(cited_similarities) / len(cited_similarities) if cited_similarities else 0.0
        
        # 3. Sentence-level Grounding Analysis
        sentence_grounding = await self._analyze_sentence_grounding(answer, chunks)
        
        # 4. Hallucination Detection
        hallucination_score = await self._detect_hallucination(answer, chunks)
        
        # 5. Calculate Enhanced Grounding Score (0-100)
        grounding = (
            0.30 * consistency_score +           # LLM consistency check
            0.20 * evidence_strength +           # Retrieved document quality
            0.20 * citation_coverage +           # Citation usage ratio
            0.15 * sentence_grounding +          # Sentence-level verification
            0.15 * (1 - hallucination_score)     # Hallucination penalty
        ) * 100
        
        # 6. Uncertainty Quantification
        uncertainty_markers = [
            ("불확실", 15), ("추측", 20), ("가능성이 있음", 10),
            ("확인되지 않음", 15), ("추정", 10), ("아마도", 10),
            ("~인 것으로 보인다", 5), ("정확하지 않", 15)
        ]
        
        total_penalty = 0
        for marker, penalty in uncertainty_markers:
            if marker in answer:
                total_penalty += penalty
        
        # 7. Calculate Confidence Score
        confidence = max(0.0, grounding - min(total_penalty, 40))
        
        # Bonus for high-quality responses
        if citation_coverage >= 0.6 and hallucination_score < 0.1:
            confidence = min(100.0, confidence + 5)
        
        return round(grounding, 1), round(confidence, 1), round(citation_coverage, 2)
    
    async def _analyze_sentence_grounding(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> float:
        """Analyze how well each sentence is grounded in source documents.
        
        Returns a score from 0 to 1.
        """
        sentences = re.split(r'[.!?]\s+', answer)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences or not chunks:
            return 0.5
        
        chunk_texts = " ".join([c.get("chunk_text", "") for c in chunks[:5]])
        
        grounded_count = 0
        for sentence in sentences[:10]:  # Analyze first 10 sentences
            # Check for explicit citation
            if re.search(r'\[(?:출처\s*)?\d+\]', sentence):
                grounded_count += 1
                continue
            
            # Check keyword overlap
            sentence_words = set(re.findall(r'[가-힣a-zA-Z]{2,}', sentence.lower()))
            chunk_words = set(re.findall(r'[가-힣a-zA-Z]{2,}', chunk_texts.lower()))
            
            if sentence_words:
                overlap = len(sentence_words & chunk_words) / len(sentence_words)
                if overlap > 0.3:
                    grounded_count += 0.8
                elif overlap > 0.15:
                    grounded_count += 0.5
        
        return min(1.0, grounded_count / max(1, len(sentences[:10])))
    
    async def _detect_hallucination(
        self,
        answer: str,
        chunks: List[Dict[str, Any]]
    ) -> float:
        """Detect potential hallucinations in the answer.
        
        Returns a score from 0 (no hallucination) to 1 (high hallucination).
        """
        if not chunks:
            return 0.5
        
        chunk_texts = " ".join([c.get("chunk_text", "") for c in chunks])
        
        # Check for specific numeric claims
        numbers_in_answer = re.findall(r'\d+(?:\.\d+)?(?:%|원|억|만|년|월|일|조|개월)?', answer)
        numbers_in_chunks = re.findall(r'\d+(?:\.\d+)?(?:%|원|억|만|년|월|일|조|개월)?', chunk_texts)
        
        ungrounded_numbers = 0
        for num in numbers_in_answer:
            if num not in numbers_in_chunks:
                if any(c.isdigit() for c in num):
                    ungrounded_numbers += 1
        
        # Check for specific entity mentions (organization names, law names)
        entity_patterns = [
            r'(?:법|규정|규칙|지침|고시|조례)(?:안)?',
            r'제\d+조(?:제\d+항)?',
            r'(?:금융위원회|금감원|한국은행|예금보험공사)',
        ]
        
        ungrounded_entities = 0
        for pattern in entity_patterns:
            entities_in_answer = re.findall(pattern, answer)
            entities_in_chunks = re.findall(pattern, chunk_texts)
            
            for entity in entities_in_answer:
                if entity not in entities_in_chunks:
                    ungrounded_entities += 1
        
        # Calculate hallucination score
        total_claims = len(numbers_in_answer) + sum(len(re.findall(p, answer)) for p in entity_patterns)
        ungrounded_claims = ungrounded_numbers + ungrounded_entities
        
        if total_claims == 0:
            return 0.1  # Low hallucination risk for general statements
        
        hallucination_ratio = ungrounded_claims / total_claims
        
        return min(1.0, hallucination_ratio)

    async def _expand_query(self, query: str) -> str:
        """Expand query with financial synonyms and related terms."""
        expansion_map = {
            "금소법": "금융소비자보호법",
            "가출법": "가계대출 규제",
            "바젤3": "자본적정성 규제 바젤III",
            "ESG": "ESG 공시 의무화 환경 사회 지배구조",
            "가상자산": "가상자산 이용자 보호법 암호화폐 코인",
            "금리": "기준금리 예금금리 대출금리",
            "부채": "가계부채 기업부채 부채비율",
            "보험": "보험업법 지급여력비율 K-ICS",
            "은행": "은행법 유동성 커버리지 비율 LCR",
            "증권": "자본시장법 금융투자업"
        }
        
        expanded = query
        for short, full in expansion_map.items():
            if short in query and full not in query:
                expanded += f" ({full})"
        
        return expanded

    async def answer_question(self, request: QARequest) -> QAResponse:
        """Main RAG pipeline: Embedding -> Hybrid Search -> Rerank -> LLM -> Parse."""
        start_time = datetime.now()
        
        # 0. Query Expansion
        expanded_query = await self._expand_query(request.question)
        print(f"DEBUG: Expanded query: '{request.question}' -> '{expanded_query}'")
        
        # 1. Get query embedding
        query_embedding = await self._get_embedding(expanded_query)
        
        # 2. Hybrid Search (RRF)
        filters = {}
        if request.date_from:
            filters["date_from"] = request.date_from.isoformat()
        
        search_results = await self.vector_store.hybrid_search(
            query=expanded_query,
            query_embedding=query_embedding,
            top_k=settings.TOP_K_RETRIEVAL,
            filters=filters
        )
        
        # 3. Optional Reranking
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
        
        # 4. Answerability Guardrail
        can_answer, reason, consistency = await self._check_answerability(request.question, reranked_chunks)
        
        if not can_answer:
            return QAResponse(
                answer=f"죄송합니다. {reason}\n\n질문을 더 구체적으로 입력하시거나 다른 키워드로 시도해 주세요.",
                summary="답변 불가",
                industry_impact={"INSURANCE": 0.0, "BANKING": 0.0, "SECURITIES": 0.0},
                checklist=[],
                citations=[],
                confidence=0.0,
                groundedness_score=0.0,
                uncertainty_note=reason,
                answerable=False
            )
        
        # 5. Generate Answer
        answer_data = await self._generate_answer(request.question, reranked_chunks)
        
        # 6. Calculate Real Scores
        grounding_score, confidence_score, coverage = await self._calculate_scores(
            answer_data["answer"], 
            reranked_chunks,
            consistency
        )
        
        # 7. Build Citations
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
        
        # 8. Parse structured data
        structured_data = self._parse_structured_answer(answer_data["answer"], reranked_chunks)
        
        # 9. Async Logging to qa_logs
        try:
            from fastapi.encoders import jsonable_encoder
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.db.table("qa_logs").insert(jsonable_encoder({
                "user_query": request.question,
                "retrieved_chunk_ids": [chunk["chunk_id"] for chunk in reranked_chunks],
                "answer": structured_data["answer"],
                "citations": citations,
                "grounding_score": grounding_score,
                "confidence_score": confidence_score,
                "citation_coverage": coverage,
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
            confidence=confidence_score / 100.0,
            groundedness_score=grounding_score / 100.0,
            citation_coverage=coverage,
            uncertainty_note=structured_data.get("uncertainty_note"),
            answerable=True
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
        can_answer, reason, consistency = await self._check_answerability(request.question, reranked_chunks)
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
            
            # Calculate real metrics for streaming too
            grounding_score, confidence_score, coverage = await self._calculate_scores(
                full_answer, 
                reranked_chunks,
                consistency
            )
            
            final_data["groundedness_score"] = grounding_score / 100.0
            final_data["confidence"] = confidence_score / 100.0
            final_data["citation_coverage"] = coverage
            
            unanswerable_phrases = ["확인되지 않음", "정보가 없습니다", "답변을 찾을 수 없습니다", "명시되어 있지 않습니다"]
            final_data["answerable"] = not any(phrase in final_data["answer"] for phrase in unanswerable_phrases)
            if final_data.get("uncertainty_note"):
                final_data["answerable"] = False
                
            yield f"data: {json.dumps({'type': 'final', 'data': final_data})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
