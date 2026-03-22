"""RAG (Retrieval Augmented Generation) service."""
import logging
import openai
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
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

_log = logging.getLogger(__name__)


def _qa_llm_model() -> str:
    """RAG 질의(HyDE·답변가능성·최종 답변) 전용 모델. OPENAI_MODEL_QA 미설정 시 OPENAI_MODEL."""
    q = (getattr(settings, "OPENAI_MODEL_QA", None) or "").strip()
    return q if q else settings.OPENAI_MODEL


# 규제·금융 키워드가 있으면 BM25/키워드 채널 비중을 소폭 올려 조문·고시명 등 정확 매칭 강화
_REGULATORY_QUERY_HINTS = (
    "금융위", "금융위원회", "금감원", "금융감독", "한국은행", "예금보험",
    "시행령", "시행규칙", "고시", "지침", "규정", "조문",
    "FSC", "FSS", "BIS", "FSB", "ESG", "스테이블코인", "가상자산", "STO",
    "DSR", "LCR", "K-ICS", "IFRS", "내부통제", "자본시장법", "금융소비자",
)

# 질문에만 등장하고 상위 검색 청크에 없으면 '부실기업 퇴출' vs '가상자산' 같은 오검색으로
# 어휘 겹침(금융위·규제 등)만으로 빠른 통과하는 것을 막기 위한 주제 키워드
_TOPIC_SPECIFIC_QUERY_TERMS = (
    "가상자산", "가상 자산", "VASP", "특금법", "스테이블코인", "스테이블 코인",
    "토큰증권", "STO", "보안토큰", "디지털자산", "디지털 자산",
)


def hybrid_weights_for_query(question: str) -> Tuple[float, float]:
    """규제·금융 키워드가 있으면 BM25 비중을 높여 조문·고시명 등 키워드 매칭을 강화."""
    vw = float(getattr(settings, "HYBRID_VECTOR_WEIGHT", 0.7))
    kw = float(getattr(settings, "HYBRID_KEYWORD_WEIGHT", 0.3))
    q = question or ""
    looks_regulatory = any(h in q for h in _REGULATORY_QUERY_HINTS) or bool(
        re.search(r"제\s*\d+\s*조", q)
    )
    if looks_regulatory:
        # 조문·고시명 등 키워드 매칭 강화(근거 검색 정확도)
        return (min(vw, 0.58), max(kw, 0.42))
    return (vw, kw)


class RAGService:
    """RAG service with hybrid search, reranking, and guardrails."""
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
        self.vector_store = get_vector_store()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @staticmethod
    def _hybrid_weights_for_query(question: str) -> Tuple[float, float]:
        return hybrid_weights_for_query(question)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text with Redis caching."""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"emb:{text_hash}"
        try:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        
        response = await self.openai_client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text[:8000]
        )
        embedding = response.data[0].embedding
        
        try:
            self.redis.setex(cache_key, 86400, json.dumps(embedding))
        except Exception:
            pass
        return embedding

    async def _get_embeddings_batch(self, texts: List[str], batch_size: int = 48) -> List[List[float]]:
        """OpenAI 임베딩 배치 호출 — 청크 대량 인덱싱 시 N회 순차 대비 지연 대폭 감소."""
        if not texts:
            return []
        import hashlib
        out: List[List[float]] = []
        for j in range(0, len(texts), batch_size):
            batch = texts[j : j + batch_size]
            resp = await self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=[t[:8000] for t in batch],
            )
            ordered = sorted(
                resp.data,
                key=lambda d: getattr(d, "index", 0),
            )
            for k, emb_obj in enumerate(ordered):
                vec = emb_obj.embedding
                out.append(vec)
                raw = batch[k]
                h = hashlib.md5(raw.encode()).hexdigest()
                try:
                    self.redis.setex(f"emb:{h}", 86400, json.dumps(vec))
                except Exception:
                    pass
        return out

    async def _expand_query_hyde(self, query: str) -> str:
        """HyDE (Hypothetical Document Embeddings): Generate a hypothetical answer to improve retrieval."""
        hyde_prompt = f"""당신은 금융 정책·규제 문서 작성에 익숙한 전문가입니다. 다음 질문에 대해 금융위·금감원 보도자료, 고시, 시행령 설명문과 비슷한 톤으로 1~2문장의 '가상 답변'을 작성하세요.
실제 정답 여부는 중요하지 않습니다. 검색 인덱스에서 잡히도록 조문·제도명·업권 용어를 자연스럽게 넣는 것이 목적입니다.

질문: {query}
가상 답변:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=_qa_llm_model(),
                messages=[{"role": "user", "content": hyde_prompt}],
                temperature=0.35,
                max_tokens=160
            )
            hyde_answer = response.choices[0].message.content
            return f"{query}\n{hyde_answer}"
        except Exception:
            return query

    @staticmethod
    def _lexical_overlap_score(query: str, chunks: List[Dict[str, Any]]) -> float:
        """질문 토큰과 상위 청크 본문의 겹침 비율 (0~1). LLM 없이 답변가능성 힌트."""
        if not chunks or not (query or "").strip():
            return 0.0
        q_words = set(re.findall(r"[가-힣a-zA-Z0-9]{2,}", query.lower()))
        text = " ".join((c.get("chunk_text") or "") for c in chunks[:8]).lower()
        hit = len(q_words & set(re.findall(r"[가-힣a-zA-Z0-9]{2,}", text)))
        if not q_words:
            return 0.0
        return hit / max(1, len(q_words))

    async def _check_answerability(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> tuple[bool, str, float]:
        """Check if query can be answered from retrieved chunks with high strictness."""
        if not chunks:
            return False, "검색된 문서가 없습니다.", 0.0

        top_sim = float(chunks[0].get("similarity") or 0.0)
        sim_thresh = float(getattr(settings, "ANSWERABILITY_FAST_PATH_MIN_SIM", 0.46))
        if (
            getattr(settings, "ENABLE_FAST_ANSWERABILITY", True)
            and sim_thresh >= 0
            and top_sim >= sim_thresh
        ):
            consistency = min(0.94, 0.55 + top_sim * 0.4)
            return True, "", consistency

        overlap = self._lexical_overlap_score(query, chunks)
        min_ov = float(getattr(settings, "FAST_ANSWERABILITY_MIN_OVERLAP", 0.18))
        if getattr(settings, "ENABLE_FAST_ANSWERABILITY", True) and overlap >= min_ov:
            consistency = min(0.93, 0.52 + overlap * 0.45)
            return True, "", consistency

        combined_text = "\n\n".join([f"[{i+1}] {c['chunk_text']}" for i, c in enumerate(chunks[:6])])
        
        check_prompt = f"""당신은 금융 정책 규제 준수 검증관입니다.
질문: {query}

참고 문서 내용:
{combined_text[:4800]}

규칙:
1. 제공된 문서 내용에 질문 주제와 직접 연결되는 설명(제도명, 목적, 원칙, 의무, 적용대상, 조문·고시명 등)이 있으면 답변 가능으로 본다.
2. 추측하거나 외부 지식을 사용하지 마세요.
3. 수치·기한이 없어도 문서가 질문의 핵심을 다루면 YES. 완전히 무관한 주제만 NO.
4. 문서가 질문과 관련은 있으나 핵심 근거 문장이 없으면 NO(근거 부족 명시).
5. 답변이 가능하면 'YES [근거번호]', 불가능하면 'NO [이유]'를 출력하세요.

출력 예시:
YES [1, 2, 4]
NO [해당 문서에는 가계대출 금리에 대한 직접적인 언급이 없음]"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=_qa_llm_model(),
                messages=[{"role": "user", "content": check_prompt}],
                temperature=0,
                max_tokens=140
            )
            
            content = response.choices[0].message.content.strip().upper()
            if content.startswith("YES"):
                cited_indices = re.findall(r'\[(.*?)\]', content)
                consistency = 0.9 if cited_indices else 0.6
                return True, "", consistency
            else:
                reason = content.replace("NO", "").strip() or "검색된 문서에 질문과 관련된 구체적인 정책 내용이 포함되어 있지 않습니다."
                return False, reason, 0.0
        
        except Exception as ex:
            # 검증 실패 시 '통과'하면 오검색·환각 답변이 그대로 나가므로 보수적으로 거부
            _log.warning("Answerability LLM check failed: %s", ex)
            return (
                False,
                "근거 적합성 자동 검증을 완료하지 못했습니다. 질문을 더 구체화하거나 잠시 후 다시 시도해 주세요.",
                0.0,
            )

    def _safe_published_at(self, raw: Any) -> datetime:
        """published_at 문자열/None을 datetime으로 안전 변환."""
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            return datetime.now(timezone.utc)
        if hasattr(raw, "isoformat"):
            return raw if getattr(raw, "tzinfo", None) else raw.replace(tzinfo=timezone.utc)
        s = str(raw).replace("Z", "+00:00").strip()
        if not s:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)

    async def _generate_answer(self, query: str, chunks: List[Dict[str, Any]], compliance_mode: bool = False) -> Dict[str, Any]:
        """Generate a structured, cited answer using LLM."""
        def _date_str(c: Dict[str, Any]) -> str:
            pa = c.get("published_at")
            if pa is None or (isinstance(pa, str) and not pa):
                return ""
            return str(pa)[:10] if len(str(pa)) >= 10 else str(pa)
        context = "\n\n".join([f"[{i+1}] {c['document_title']} ({_date_str(c)})\n{c.get('chunk_text', '')}" for i, c in enumerate(chunks)])
        
        mode_instruction = ""
        if compliance_mode:
            mode_instruction = "당신은 현재 '컴플라이언스 모드'입니다. 모든 문장의 끝에 반드시 근거 문서 번호 [번호]를 명시하십시오. 근거가 없는 문장은 작성하지 마십시오. 한 문장에 복수 근거가 있으면 [1][2]처럼 표기하십시오."
        else:
            mode_instruction = "답변의 모든 문장에는 근거가 되는 문서의 번호를 [1], [2]와 같이 표시하십시오. 인용 번호는 [참고 문서]에 부여된 번호와 일치해야 합니다."

        system_prompt = f"""당신은 금융위원회(FSC) 정책·규제 문서를 근거로 답변하는 'FSC AI 어시스턴트'입니다.
다음 규칙을 엄격히 준수하여 답변하십시오:

1. 오직 제공된 [참고 문서]의 내용만을 기반으로 답변하십시오.
2. 첫 문장에서 질문의 핵심에 직접 답한 뒤, 필요하면 세부 설명을 이어가십시오 (질문과 무관한 서론 금지).
3. {mode_instruction}
4. 문서에 없는 내용은 절대 추측하여 답변하지 마십시오. 모르는 경우 '제공된 문서에서 관련 내용을 찾을 수 없습니다'라고 하십시오.
5. 금융·규제 용어를 정확히 쓰고, 보도자료·고시·지침·시행령 등 문서 유형에 맞는 어조를 유지하십시오.
6. 참고 문서 제목·본문에 나온 제도명·고시명·조문 표기가 있으면 답변에서도 동일하게 사용하십시오. 시행일·게시일·적용 시점이 문서에 있으면 함께 언급하십시오.
7. 비율·한도·기한·의무·적용 대상 등 수치·조건은 해당 문서에 근거가 있을 때만 서술하고, 반드시 [번호] 인용과 연결하십시오.
8. "answer" 문자열 안에는 반드시 참고 문서 번호 [1]~[{len(chunks)}] 형식의 인용을 문장마다 포함하십시오. 인용 없이 문장을 쓰지 마십시오.
9. 반드시 아래 JSON 형식으로만 출력하십시오.

출력 JSON 형식:
{{
    "answer": "상세 답변 내용 (문장별 [1][2] 인용 필수)",
    "summary": "3줄 이내 요약",
    "industry_impact": {{
        "BANKING": 0.0~1.0,
        "INSURANCE": 0.0~1.0,
        "SECURITIES": 0.0~1.0
    }},
    "checklist": [
        {{"action": "행동지침", "target": "대상", "due_date_text": "기한", "penalty": "제재사항"}}
    ],
    "uncertainty_note": "답변의 한계나 추가 확인이 필요한 사항 (없으면 null)"
}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=_qa_llm_model(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"질문: {query}\n\n[참고 문서]\n{context}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2800,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            ans = data.get("answer")
            if ans is not None and not isinstance(ans, str):
                data["answer"] = json.dumps(ans, ensure_ascii=False) if isinstance(ans, (dict, list)) else str(ans)
            return data
        except Exception as e:
            _log.warning("Answer generation error: %s", e)
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "summary": "오류 발생",
                "industry_impact": {"BANKING": 0, "INSURANCE": 0, "SECURITIES": 0},
                "checklist": []
            }

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
        # 1. Calculate Citation Coverage (supports both [1] and [출처 1] formats)
        citations_found = set(re.findall(r'\[(?:출처\s*)?(\d+)\]', answer))
        unique_citations = len(citations_found)
        if unique_citations > 0:
            citation_coverage = min(1.0, unique_citations / max(1, len(chunks)))
        elif chunks:
            # LLM이 JSON 답변에서 [1] 마커를 누락해도 검색·근거 청크가 있으면 0%만 표시되지 않게 유사도 기반 하한
            sims = [float(c.get("similarity") or 0.0) for c in chunks[: min(5, len(chunks))]]
            avg_sim = sum(sims) / len(sims) if sims else 0.0
            citation_coverage = max(0.15, min(0.55, avg_sim * 0.85))
        else:
            citation_coverage = 0.0
        
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
        sentence_grounding = self._analyze_sentence_grounding(answer, chunks)
        
        # 4. Hallucination Detection
        hallucination_score = self._detect_hallucination(answer, chunks)
        
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
    
    def _analyze_sentence_grounding(
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
    
    def _detect_hallucination(
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

    async def answer_question(self, request: QARequest) -> QAResponse:
        """Main RAG pipeline: HyDE -> Hybrid Search -> Rerank -> LLM -> Parse."""
        start_time = datetime.now(timezone.utc)
        
        # 1. HyDE Query Expansion (비활성 시 질문만 임베딩 — 지연·비용 절감)
        if getattr(settings, "ENABLE_QUERY_HYDE", True):
            expanded_query = await self._expand_query_hyde(request.question)
        else:
            expanded_query = request.question
        
        # 2. Get query embedding
        query_embedding = await self._get_embedding(expanded_query)
        
        # 3. Hybrid Search (RRF)
        filters = {}
        if request.date_from:
            filters["date_from"] = request.date_from.isoformat()
        
        vw, kw = self._hybrid_weights_for_query(request.question)
        search_results = await self.vector_store.hybrid_search(
            query=request.question,
            query_embedding=query_embedding,
            top_k=settings.TOP_K_RETRIEVAL,
            vector_weight=vw,
            keyword_weight=kw,
            similarity_threshold=getattr(settings, "HYBRID_SIMILARITY_THRESHOLD", 0.3),
            filters=filters,
        )
        
        # 4. Optional Reranking
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
                "similarity": r.similarity,
                "parsing_source": getattr(r, "parsing_source", None),
            }
            for r in reranked_results
        ]
        # 본문이 비어 있는 청크는 답변·Ragas 입력 품질을 망가뜨리므로 제외
        reranked_chunks = [c for c in reranked_chunks if (c.get("chunk_text") or "").strip()]
        if not reranked_chunks:
            return QAResponse(
                answer="죄송합니다. 검색 결과에 유효한 문서 본문이 없습니다. 다른 질문으로 시도해 주세요.",
                summary="답변 불가",
                industry_impact={"BANKING": 0.0, "INSURANCE": 0.0, "SECURITIES": 0.0},
                checklist=[],
                citations=[],
                confidence=0.0,
                groundedness_score=0.0,
                citation_coverage=0.0,
                uncertainty_note="유효 청크 없음",
                answerable=False,
                retrieval_contexts=None,
            )

        # 5. Answerability Guardrail
        can_answer, reason, consistency = await self._check_answerability(request.question, reranked_chunks)

        if not can_answer:
            return QAResponse(
                answer=f"죄송합니다. {reason}\n\n다른 질문으로 시도하시거나, 더 구체적인 키워드를 입력해 주세요.",
                summary="답변 불가",
                industry_impact={"BANKING": 0.0, "INSURANCE": 0.0, "SECURITIES": 0.0},
                checklist=[],
                citations=[],
                confidence=0.0,
                groundedness_score=0.0,
                citation_coverage=0.0,
                uncertainty_note=reason,
                answerable=False,
                retrieval_contexts=(
                    [c.get("chunk_text") or "" for c in reranked_chunks]
                    if request.include_retrieval_contexts
                    else None
                ),
            )
        
        # 6. Generate Answer
        structured_data = await self._generate_answer(request.question, reranked_chunks, request.compliance_mode)
        
        # 7. Metrics
        grounding_score, confidence_score, coverage = await self._calculate_scores(
            structured_data["answer"], 
            reranked_chunks,
            consistency
        )
        
        # 8. Build Citations (parsing_source: LlamaParse 등 파싱 출처 노출)
        citations = [
            Citation(
                chunk_id=chunk.get("chunk_id", ""),
                document_id=chunk.get("document_id", ""),
                document_title=chunk.get("document_title", ""),
                published_at=self._safe_published_at(chunk.get("published_at")),
                snippet=(chunk.get("chunk_text") or "")[:200],
                url=chunk.get("url") or "",
                parsing_source=chunk.get("parsing_source"),
            )
            for chunk in reranked_chunks
        ]
        
        # 9. Logging with quality metrics
        try:
            from fastapi.encoders import jsonable_encoder
            latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            # confidence 컬럼은 스키마에 없을 수 있음(PGRST204) — 핵심 필드만 삽입
            self.db.table("qa_logs").insert(jsonable_encoder({
                "user_query": request.question,
                "retrieved_chunk_ids": [chunk["chunk_id"] for chunk in reranked_chunks],
                "answer": structured_data["answer"],
                "citations": citations,
                "latency_ms": latency_ms,
                "response_time_ms": latency_ms,
                "groundedness_score": grounding_score / 100.0,
                "citation_coverage": coverage,
                "status": "success",
                "created_at": datetime.now(timezone.utc).isoformat()
            })).execute()
        except Exception as log_err:
            _log.debug("qa_logs insert skipped or failed: %s", log_err)

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
            answerable=True,
            retrieval_contexts=(
                [c.get("chunk_text") or "" for c in reranked_chunks]
                if request.include_retrieval_contexts
                else None
            ),
        )

    async def stream_answer(self, request: QARequest):
        """Stream RAG answer (minimal implementation using non-streaming logic for stability)."""
        response = await self.answer_question(request)
        # Convert Pydantic to Dict
        data = json.loads(response.model_dump_json())
        
        # Yield citations first
        yield f"data: {json.dumps({'type': 'citations', 'citations': data['citations']})}\n\n"
        
        # Stream the answer token by token (simulated for UI compatibility)
        answer = data["answer"]
        chunk_size = 5
        for i in range(0, len(answer), chunk_size):
            token = answer[i:i+chunk_size]
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            
        yield f"data: {json.dumps({'type': 'final', 'data': data})}\n\n"
