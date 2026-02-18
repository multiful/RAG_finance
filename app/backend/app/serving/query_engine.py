"""Phase B: 서빙 서비스 (FastAPI + Redis)

Pipeline: Request → Cache → Reasoning → Retrieval → Reranker → Generation & Guardrail
"""
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.redis import get_redis
from app.services.vector_store import get_vector_store, SearchResult


@dataclass
class QueryResult:
    """Query processing result."""
    query: str
    query_type: Literal["qa", "checklist_extract", "industry_analysis", "topic_search"]
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    groundedness_score: float
    hallucination_flag: bool
    processing_time_ms: int
    cache_hit: bool = False


class CacheLayer:
    """Upstash Redis 캐시 레이어."""
    
    def __init__(self):
        self.redis = get_redis()
        self.ttl_seconds = 3600  # 1시간
    
    def _generate_cache_key(self, query: str, filters: Optional[Dict] = None) -> str:
        """캐시 키 생성."""
        content = f"{query}:{json.dumps(filters, sort_keys=True) if filters else ''}"
        return f"query:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    async def get(self, query: str, filters: Optional[Dict] = None) -> Optional[Dict]:
        """캐시에서 결과 조회."""
        try:
            key = self._generate_cache_key(query, filters)
            cached = self.redis.get(key)
            
            if cached:
                return json.loads(cached)
            return None
            
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, query: str, result: Dict, filters: Optional[Dict] = None):
        """결과를 캐시에 저장."""
        try:
            key = self._generate_cache_key(query, filters)
            self.redis.setex(
                key,
                self.ttl_seconds,
                json.dumps(result, ensure_ascii=False)
            )
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def invalidate_document(self, document_id: str):
        """문서 관련 캐시 무효화."""
        try:
            # 패턴 매칭으로 관련 캐시 삭제
            keys = self.redis.keys("query:*")
            for key in keys:
                cached = self.redis.get(key)
                if cached and document_id in cached:
                    self.redis.delete(key)
        except Exception as e:
            print(f"Cache invalidation error: {e}")


class ReasoningEngine:
    """LangGraph Agent: 질문 유형 판단 + Query Expansion."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def classify_query(self, query: str) -> Dict[str, Any]:
        """질문 유형 분류."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 금융정책 질문 분석 전문가입니다.

질문을 다음 4가지 유형 중 하나로 분류하고, 최적의 검색 쿼리를 생성하세요:

1. **qa** - 일반적인 질문응답 (시행 시점, 적용 대상 등)
2. **checklist_extract** - 준수 항목 추출 (해야 할 일, 기한, 제재 등)
3. **industry_analysis** - 업권 영향 분석 (보험/은행/증권 영향)
4. **topic_search** - 토픽/이슈 검색 (최근 급부상 이슈, 주요 토픽)

응답 형식 (JSON):
{
    "query_type": "qa|checklist_extract|industry_analysis|topic_search",
    "confidence": 0.0-1.0,
    "search_query": "검색에 최적화된 쿼리",
    "expanded_keywords": ["관련 키워드1", "관련 키워드2"],
    "filters": {
        "industry": "INSURANCE|BANKING|SECURITIES|null",
        "date_range": "recent|all"
    }
}"""),
            ("human", f"질문: {query}")
        ])
        
        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            result = json.loads(response.content)
            return result
        except:
            # Fallback
            return {
                "query_type": "qa",
                "confidence": 0.5,
                "search_query": query,
                "expanded_keywords": [],
                "filters": {}
            }
    
    async def expand_query(self, query: str, query_type: str) -> List[str]:
        """쿼리 확장 (동의어, 관련 용어 추가)."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "금융정책 검색 쿼리 확장 전문가. 원본 쿼리와 관련된 동의어, 유사 용어를 생성하세요."),
            ("human", f"쿼리: {query}\n유형: {query_type}\n\n응답 형식: ["확장1", "확장2", ...]")
        ])
        
        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            expanded = json.loads(response.content)
            return expanded if isinstance(expanded, list) else [query]
        except:
            return [query]


class HybridRetriever:
    """Hybrid Search: 키워드(BM25) + 의미(Vector) 검색."""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def retrieve(
        self,
        query: str,
        expanded_queries: List[str],
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """하이브리드 검색 수행."""
        # 쿼리 임베딩
        query_embedding = await self.embeddings.aembed_query(query)
        
        # Hybrid search
        results = await self.vector_store.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            vector_weight=0.7,
            keyword_weight=0.3,
            filters=filters
        )
        
        return results


class Reranker:
    """Cross-Encoder 기반 리랭커."""
    
    def __init__(self):
        self.model = None
    
    def _load_model(self):
        """Lazy loading of cross-encoder model."""
        if self.model is None:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """검색 결과 재정렬."""
        if not results:
            return []
        
        try:
            self._load_model()
            
            # 쿼리-문서 쌍 생성
            pairs = [
                (query, result.chunk_text[:512])
                for result in results
            ]
            
            # 점수 계산
            scores = self.model.predict(pairs)
            
            # 점수 업데이트 및 정렬
            for result, score in zip(results, scores):
                result.similarity = float(score)
            
            results.sort(key=lambda x: x.similarity, reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            print(f"Reranking error: {e}")
            return results[:top_k]


class GuardrailChecker:
    """Generation & Guardrail: 근거 문단 태그 + 환각 체크."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def check_groundedness(
        self,
        answer: str,
        contexts: List[str]
    ) -> float:
        """근거일치율(Groundedness) 계산."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """답변의 각 문장이 제공된 컨텍스트에서 지지되는지 판단하세요.

응답 형식 (JSON):
{
    "groundedness_score": 0.0-1.0,
    "unsupported_statements": ["지지되지 않는 문장1", ...],
    "analysis": "분석 내용"
}"""),
            ("human", f"""컨텍스트:
{chr(10).join([f'{i+1}. {ctx[:300]}' for i, ctx in enumerate(contexts[:3])])}

답변:
{answer}

분석 결과를 JSON으로 제공하세요.""")
        ])
        
        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            result = json.loads(response.content)
            return result.get("groundedness_score", 0.0)
        except:
            return 0.0
    
    async def check_hallucination(
        self,
        answer: str,
        contexts: List[str]
    ) -> Dict[str, Any]:
        """환각 여부 체크."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """답변에 컨텍스트에 없는 정보가 포함되어 있는지 체크하세요.

응답 형식 (JSON):
{
    "has_hallucination": true/false,
    "hallucinated_content": ["환각 내용1", ...],
    "confidence": 0.0-1.0
}"""),
            ("human", f"""컨텍스트:
{chr(10).join([f'{i+1}. {ctx[:300]}' for i, ctx in enumerate(contexts[:3])])}

답변:
{answer}

JSON으로 응답하세요.""")
        ])
        
        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            result = json.loads(response.content)
            return result
        except:
            return {"has_hallucination": False, "hallucinated_content": [], "confidence": 0.5}
    
    async def generate_with_citations(
        self,
        query: str,
        query_type: str,
        contexts: List[SearchResult]
    ) -> Dict[str, Any]:
        """근거 문단 태그를 달아 답변 생성."""
        # 컨텍스트 포맷팅 (태그 포함)
        formatted_contexts = []
        for i, ctx in enumerate(contexts):
            formatted_contexts.append(
                f"[출처 {i+1}] {ctx.document_title} ({ctx.published_at[:10] if ctx.published_at else 'N/A'})\n"
                f"{ctx.chunk_text}\n"
            )
        
        context_text = "\n\n".join(formatted_contexts)
        
        # 쿼리 유형별 프롬프트
        if query_type == "checklist_extract":
            system_prompt = """당신은 금융 규제 준수 전문가입니다.
제공된 문서를 기반으로 체크리스트를 추출하세요.

응답 형식:
1. 요약 (2-3줄)
2. 체크리스트 항목 (각 항목은 [출처 N] 형태로 근거 표시)
   - 해야 할 일
   - 대상
   - 기한
   - 제재 (있는 경우)
3. 불확실성 표시 (근거가 약한 부분)

중요: 모든 항목은 반드시 [출처 N] 태그로 근거를 표시하세요."""
        
        elif query_type == "industry_analysis":
            system_prompt = """당신은 금융정책 영향 분석 전문가입니다.

응답 형식:
1. 요약
2. 업권별 영향도 (0-100%)
   - 보험: X% ([출처 N])
   - 은행: X% ([출처 N])
   - 증권: X% ([출처 N])
3. 핵심 영향 내용 (각 항목에 [출처 N] 태그)"""
        
        else:  # qa, topic_search
            system_prompt = """당신은 금융정책 전문가입니다.
제공된 문서만을 기반으로 답변하세요.

응답 형식:
1. 요약 (3줄 이내)
2. 상세 답변 (각 주요 주장에 [출처 N] 태그)
3. 불확실성 표시 (근거가 약한 경우 "확인 필요" 표시)

중요: 문서에 없는 정보는 추측하지 말고 "확인되지 않음"으로 표시하세요."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"""질문: {query}

참고 문서:
{context_text}

위 문서만을 기반으로 답변을 제공하세요.""")
        ])
        
        try:
            response = await self.llm.ainvoke(prompt.format_messages())
            
            return {
                "answer": response.content,
                "citations": [
                    {
                        "index": i + 1,
                        "chunk_id": ctx.chunk_id,
                        "document_id": ctx.document_id,
                        "document_title": ctx.document_title,
                        "published_at": ctx.published_at,
                        "url": ctx.url
                    }
                    for i, ctx in enumerate(contexts)
                ]
            }
        except Exception as e:
            return {
                "answer": f"답변 생성 중 오류: {str(e)}",
                "citations": []
            }


class QueryEngine:
    """전체 쿼리 엔진 오케스트레이터."""
    
    def __init__(self):
        self.cache = CacheLayer()
        self.reasoning = ReasoningEngine()
        self.retriever = HybridRetriever()
        self.reranker = Reranker()
        self.guardrail = GuardrailChecker()
    
    async def process_query(
        self,
        query: str,
        use_cache: bool = True,
        top_k: int = 5
    ) -> QueryResult:
        """전체 쿼리 처리 파이프라인."""
        start_time = datetime.now()
        
        # 1. Cache Check
        if use_cache:
            cached = await self.cache.get(query)
            if cached:
                return QueryResult(
                    query=query,
                    query_type=cached.get("query_type", "qa"),
                    answer=cached.get("answer", ""),
                    citations=cached.get("citations", []),
                    confidence=cached.get("confidence", 0),
                    groundedness_score=cached.get("groundedness_score", 0),
                    hallucination_flag=cached.get("hallucination_flag", False),
                    processing_time_ms=0,
                    cache_hit=True
                )
        
        # 2. Reasoning (Query Classification + Expansion)
        reasoning_result = await self.reasoning.classify_query(query)
        query_type = reasoning_result.get("query_type", "qa")
        search_query = reasoning_result.get("search_query", query)
        expanded_keywords = reasoning_result.get("expanded_keywords", [])
        filters = reasoning_result.get("filters", {})
        
        # 3. Retrieval (Hybrid Search)
        retrieved_results = await self.retriever.retrieve(
            query=search_query,
            expanded_queries=expanded_keywords,
            top_k=top_k * 2,  # Reranking을 위해 더 많이 검색
            filters=filters
        )
        
        # 4. Reranking
        reranked_results = await self.reranker.rerank(
            query=search_query,
            results=retrieved_results,
            top_k=top_k
        )
        
        # 5. Generation with Citations
        generation_result = await self.guardrail.generate_with_citations(
            query=query,
            query_type=query_type,
            contexts=reranked_results
        )
        
        answer = generation_result.get("answer", "")
        citations = generation_result.get("citations", [])
        
        # 6. Guardrail Checks
        context_texts = [r.chunk_text for r in reranked_results]
        groundedness = await self.guardrail.check_groundedness(answer, context_texts)
        hallucination_check = await self.guardrail.check_hallucination(answer, context_texts)
        
        # 7. Confidence Calculation
        confidence = (
            groundedness * 0.4 +
            reasoning_result.get("confidence", 0.5) * 0.3 +
            (1.0 if not hallucination_check.get("has_hallucination", False) else 0.0) * 0.3
        )
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        result = QueryResult(
            query=query,
            query_type=query_type,
            answer=answer,
            citations=citations,
            confidence=confidence,
            groundedness_score=groundedness,
            hallucination_flag=hallucination_check.get("has_hallucination", False),
            processing_time_ms=processing_time,
            cache_hit=False
        )
        
        # 8. Cache Store
        if use_cache:
            await self.cache.set(query, {
                "query_type": query_type,
                "answer": answer,
                "citations": citations,
                "confidence": confidence,
                "groundedness_score": groundedness,
                "hallucination_flag": result.hallucination_flag
            })
        
        return result


# 싱글톤 인스턴스
_query_engine: Optional[QueryEngine] = None

def get_query_engine() -> QueryEngine:
    global _query_engine
    if _query_engine is None:
        _query_engine = QueryEngine()
    return _query_engine
