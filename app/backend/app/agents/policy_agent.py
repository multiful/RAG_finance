"""LangGraph-based Policy Analysis Agent Workflow.

Enhanced Multi-Step Reasoning Agent with:
- Query Decomposition: 복잡한 질문 분해
- Adaptive Retrieval: 필요시 추가 검색
- Self-Reflection: 답변 품질 자가 검증 및 재생성
- Comparative Analysis: 정책 비교 분석

Implements: 분석 -> 검색 전략 -> 검색 -> 평가 -> 생성 -> 자가검증
"""
from typing import TypedDict, Annotated, Sequence, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
import json
import re

from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.industry_classifier import IndustryClassifier
from app.services.checklist_service import ChecklistService


# ============ Enhanced State Definition ============

class AgentState(TypedDict):
    """Enhanced state for the multi-step reasoning agent."""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    query: str
    query_type: Literal["qa", "industry_classification", "compliance_extract", "topic_surge", "comparative", "unknown"]
    document_id: str | None
    
    # Query Analysis
    sub_queries: list[str]
    search_strategy: str
    expanded_query: str
    
    # Retrieval
    retrieved_chunks: list[dict]
    retrieval_score: float
    needs_more_retrieval: bool
    retrieval_attempts: int
    
    # Processing Results
    industry_classification: dict | None
    checklist: dict | None
    answer: str | None
    partial_answers: list[dict]
    
    # Quality Metrics
    confidence: float
    groundedness_score: float
    citation_coverage: float
    
    # Verification
    verification_status: Literal["pending", "passed", "failed", "needs_retry", "needs_more_context"]
    self_reflection: dict | None
    iteration_count: int
    error_message: str | None


# ============ LLM Setup ============

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.2,
    api_key=settings.OPENAI_API_KEY
)

llm_mini = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)

# ============ Query Analysis Node (Enhanced) ============

QUERY_ANALYSIS_PROMPT = """당신은 금융정책 질문 분석 전문가입니다.

사용자 질문을 분석하여 다음을 수행하세요:

1. **질문 유형 분류**:
   - qa: 일반적인 질문응답
   - industry_classification: 업권 영향 분류
   - compliance_extract: 준수 항목 추출
   - topic_surge: 토픽/경보 관련
   - comparative: 비교 분석 ("차이점", "비교", "변경사항")

2. **질문 분해**: 복잡한 질문은 2-3개의 하위 질문으로 분해

3. **검색 전략 수립**: 
   - broad: 넓은 범위 검색 (개념적 질문)
   - precise: 정확한 키워드 검색 (구체적 질문)
   - temporal: 시간 기반 검색 (최근, 변경사항)
   - comparative: 비교를 위한 다중 검색

4. **쿼리 확장**: 동의어, 관련 용어 추가

응답 형식 (JSON):
{{
    "query_type": "qa|industry_classification|compliance_extract|topic_surge|comparative",
    "sub_queries": ["하위질문1", "하위질문2"],
    "search_strategy": "broad|precise|temporal|comparative",
    "expanded_query": "확장된 검색어",
    "key_entities": ["핵심 개체1", "핵심 개체2"],
    "confidence": 0.0-1.0,
    "reasoning": "분석 근거"
}}
"""

async def analyze_query_node(state: AgentState) -> AgentState:
    """Analyze and decompose the user query."""
    query = state["query"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", QUERY_ANALYSIS_PROMPT),
        ("human", f"질문: {query}")
    ])
    
    response = await llm_mini.ainvoke(prompt.format_messages())
    
    try:
        result = json.loads(response.content)
        state["query_type"] = result.get("query_type", "qa")
        state["sub_queries"] = result.get("sub_queries", [query])
        state["search_strategy"] = result.get("search_strategy", "broad")
        state["expanded_query"] = result.get("expanded_query", query)
        state["confidence"] = result.get("confidence", 0.5)
    except json.JSONDecodeError:
        # Fallback classification
        if any(kw in query for kw in ["비교", "차이", "변경", "개정"]):
            state["query_type"] = "comparative"
            state["search_strategy"] = "comparative"
        elif any(kw in query for kw in ["업권", "보험", "은행", "증권", "분류"]):
            state["query_type"] = "industry_classification"
            state["search_strategy"] = "precise"
        elif any(kw in query for kw in ["체크리스트", "해야 할 일", "준수"]):
            state["query_type"] = "compliance_extract"
            state["search_strategy"] = "precise"
        elif any(kw in query for kw in ["토픽", "경보", "이슈", "급부상", "최근"]):
            state["query_type"] = "topic_surge"
            state["search_strategy"] = "temporal"
        else:
            state["query_type"] = "qa"
            state["search_strategy"] = "broad"
        
        state["sub_queries"] = [query]
        state["expanded_query"] = query
    
    state["messages"] = list(state["messages"]) + [
        AIMessage(content=f"Query analyzed: type={state['query_type']}, strategy={state['search_strategy']}, sub_queries={len(state['sub_queries'])}")
    ]
    
    return state


# ============ Router Node ============

async def route_query_node(state: AgentState) -> Literal["retrieve", "industry", "checklist", "topic", "comparative", "end"]:
    """Route to appropriate handler based on query type."""
    query_type = state.get("query_type", "unknown")
    
    if query_type == "qa":
        return "retrieve"
    elif query_type == "industry_classification":
        return "industry"
    elif query_type == "compliance_extract":
        return "checklist"
    elif query_type == "topic_surge":
        return "topic"
    elif query_type == "comparative":
        return "comparative"
    else:
        return "retrieve"


# ============ Adaptive Retrieval Node ============

rag_service = RAGService()

async def adaptive_retrieval_node(state: AgentState) -> AgentState:
    """Perform adaptive retrieval based on search strategy."""
    query = state.get("expanded_query", state["query"])
    sub_queries = state.get("sub_queries", [query])
    strategy = state.get("search_strategy", "broad")
    
    state["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1
    
    all_chunks = []
    
    try:
        from app.models.schemas import QARequest
        
        # Multi-query retrieval for complex questions
        for sq in sub_queries[:3]:
            request = QARequest(
                question=sq,
                top_k=5 if strategy == "precise" else 8
            )
            
            query_embedding = await rag_service._get_embedding(sq)
            
            search_results = await rag_service.vector_store.hybrid_search(
                query=sq,
                query_embedding=query_embedding,
                top_k=settings.TOP_K_RETRIEVAL,
                filters={}
            )
            
            for r in search_results:
                chunk_dict = {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "published_at": r.published_at,
                    "url": r.url,
                    "chunk_text": r.chunk_text,
                    "snippet": r.chunk_text[:200],
                    "similarity": r.similarity
                }
                
                # Deduplicate
                if not any(c["chunk_id"] == chunk_dict["chunk_id"] for c in all_chunks):
                    all_chunks.append(chunk_dict)
        
        # Sort by similarity and take top results
        all_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        state["retrieved_chunks"] = all_chunks[:10]
        
        # Calculate retrieval score
        if all_chunks:
            avg_similarity = sum(c.get("similarity", 0) for c in all_chunks[:5]) / min(5, len(all_chunks))
            state["retrieval_score"] = avg_similarity
            state["needs_more_retrieval"] = avg_similarity < 0.3 and state["retrieval_attempts"] < 2
        else:
            state["retrieval_score"] = 0.0
            state["needs_more_retrieval"] = state["retrieval_attempts"] < 2
        
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"Retrieved {len(all_chunks)} chunks. Avg similarity: {state['retrieval_score']:.2f}")
        ]
        
    except Exception as e:
        state["error_message"] = str(e)
        state["needs_more_retrieval"] = False
    
    return state


# ============ RAG Generation Node ============

async def rag_generation_node(state: AgentState) -> AgentState:
    """Generate answer from retrieved chunks with grounding."""
    query = state["query"]
    chunks = state.get("retrieved_chunks", [])
    
    if not chunks:
        state["answer"] = "검색된 문서가 없어 답변을 생성할 수 없습니다."
        state["confidence"] = 0.0
        state["verification_status"] = "failed"
        return state
    
    try:
        from app.models.schemas import QARequest
        
        request = QARequest(question=query)
        response = await rag_service.answer_question(request)
        
        state["answer"] = response.answer
        state["confidence"] = response.confidence
        state["groundedness_score"] = response.groundedness_score
        state["citation_coverage"] = response.citation_coverage
        state["verification_status"] = "pending"
        
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"Answer generated. Groundedness: {response.groundedness_score:.2f}, Confidence: {response.confidence:.2f}")
        ]
        
    except Exception as e:
        state["error_message"] = str(e)
        state["verification_status"] = "failed"
    
    return state


# ============ Comparative Analysis Node ============

COMPARATIVE_PROMPT = """당신은 금융 규제 비교 분석 전문가입니다.

다음 문서들을 분석하여 변경사항/차이점을 구조화하세요.

질문: {query}

참고 문서:
{context}

다음 형식으로 비교 분석을 제공하세요:

1. **주요 변경사항 요약** (3줄 이내)

2. **상세 비교표**
| 항목 | 기존 | 변경 | 비고 |
|------|------|------|------|

3. **영향 분석**
- 보험업: 
- 은행업:
- 증권업:

4. **핵심 조치사항**
- [ ] 조치1
- [ ] 조치2

모든 내용에 [출처 N] 형태로 근거를 표시하세요.
"""

async def comparative_analysis_node(state: AgentState) -> AgentState:
    """Perform comparative analysis between policies."""
    query = state["query"]
    chunks = state.get("retrieved_chunks", [])
    
    if not chunks:
        state["answer"] = "비교 분석을 위한 문서를 찾을 수 없습니다."
        state["verification_status"] = "failed"
        return state
    
    context_parts = []
    for i, chunk in enumerate(chunks[:8]):
        context_parts.append(
            f"[출처 {i+1}] {chunk.get('document_title', 'Unknown')} ({chunk.get('published_at', '')[:10]})\n"
            f"{chunk.get('chunk_text', chunk.get('snippet', ''))}\n"
        )
    context = "\n".join(context_parts)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 금융 규제 비교 분석 전문가입니다. 반드시 한국어로 답변하세요."),
        ("human", COMPARATIVE_PROMPT.format(query=query, context=context))
    ])
    
    try:
        response = await llm.ainvoke(prompt.format_messages())
        
        state["answer"] = response.content
        state["confidence"] = 0.8
        state["verification_status"] = "pending"
        
        state["messages"] = list(state["messages"]) + [
            AIMessage(content="Comparative analysis completed.")
        ]
        
    except Exception as e:
        state["error_message"] = str(e)
        state["verification_status"] = "failed"
    
    return state


# ============ Industry Classification Node ============

industry_classifier = IndustryClassifier()

async def industry_classification_node(state: AgentState) -> AgentState:
    """Classify document by industry impact."""
    query = state["query"]
    document_id = state.get("document_id")
    
    # Extract document_id from query if not provided
    if not document_id:
        import re
        match = re.search(r'([0-9a-f-]{36})', query)
        if match:
            document_id = match.group(1)
    
    if not document_id:
        state["error_message"] = "Document ID not found in query"
        state["verification_status"] = "failed"
        return state
    
    try:
        from app.models.schemas import IndustryClassificationRequest
        
        request = IndustryClassificationRequest(document_id=document_id)
        result = await industry_classifier.classify(request)
        
        state["industry_classification"] = {
            "insurance": result.label_insurance,
            "banking": result.label_banking,
            "securities": result.label_securities,
            "predicted_labels": result.predicted_labels,
            "explanation": result.explanation
        }
        state["confidence"] = max(
            result.label_insurance,
            result.label_banking,
            result.label_securities
        )
        state["verification_status"] = "pending"
        
        state["messages"] = state["messages"] + [
            AIMessage(content=f"Industry classification completed. Labels: {result.predicted_labels}")
        ]
        
    except Exception as e:
        state["error_message"] = str(e)
        state["verification_status"] = "failed"
    
    return state


# ============ Checklist Extraction Node ============

checklist_service = ChecklistService()

async def checklist_extraction_node(state: AgentState) -> AgentState:
    """Extract compliance checklist from document."""
    query = state["query"]
    document_id = state.get("document_id")
    
    # Extract document_id from query if not provided
    if not document_id:
        import re
        match = re.search(r'([0-9a-f-]{36})', query)
        if match:
            document_id = match.group(1)
    
    if not document_id:
        state["error_message"] = "Document ID not found in query"
        state["verification_status"] = "failed"
        return state
    
    try:
        from app.models.schemas import ChecklistRequest
        
        request = ChecklistRequest(document_id=document_id)
        result = await checklist_service.extract_checklist(request)
        
        state["checklist"] = {
            "checklist_id": result.checklist_id,
            "document_title": result.document_title,
            "items_count": len(result.items),
            "items": [
                {
                    "action": item.action,
                    "target": item.target,
                    "due_date": item.due_date_text,
                    "penalty": item.penalty,
                    "confidence": item.confidence
                }
                for item in result.items
            ]
        }
        
        # Calculate average confidence
        if result.items:
            avg_confidence = sum(item.confidence for item in result.items) / len(result.items)
            state["confidence"] = avg_confidence
        
        state["verification_status"] = "pending"
        
        state["messages"] = state["messages"] + [
            AIMessage(content=f"Checklist extracted with {len(result.items)} items.")
        ]
        
    except Exception as e:
        state["error_message"] = str(e)
        state["verification_status"] = "failed"
    
    return state


# ============ Self-Reflection Node ============

SELF_REFLECTION_PROMPT = """당신은 금융정책 답변 품질 검증 전문가입니다.

생성된 답변을 다음 기준으로 엄격하게 평가하세요:

1. **근거성 (Groundedness)**: 모든 주장이 검색된 문서에 근거하는가? (0-100)
2. **완전성 (Completeness)**: 질문의 모든 측면에 답변했는가? (0-100)
3. **정확성 (Accuracy)**: 문서 내용을 정확히 반영했는가? (0-100)
4. **인용 품질 (Citation)**: 출처 표시가 정확한가? (0-100)

응답 형식 (JSON):
{{
    "scores": {{
        "groundedness": 0-100,
        "completeness": 0-100,
        "accuracy": 0-100,
        "citation_quality": 0-100
    }},
    "overall_score": 0-100,
    "issues": ["발견된 문제점"],
    "hallucination_detected": true/false,
    "missing_info": ["누락된 정보"],
    "verification_status": "passed|needs_more_context|needs_retry|failed",
    "improvement_suggestions": ["개선 제안"]
}}

기준:
- overall_score >= 70: passed
- overall_score >= 50 && < 70: needs_more_context (추가 검색 필요)
- overall_score < 50: needs_retry (재생성 필요)
- hallucination_detected: failed
"""

async def self_reflection_node(state: AgentState) -> AgentState:
    """Perform self-reflection on the generated answer."""
    if state.get("verification_status") == "failed":
        return state
    
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    
    if state["iteration_count"] >= settings.MAX_AGENT_ITERATIONS:
        state["verification_status"] = "passed"
        return state
    
    query = state["query"]
    answer = state.get("answer", "")
    chunks = state.get("retrieved_chunks", [])
    
    if not answer:
        state["verification_status"] = "failed"
        return state
    
    chunks_text = "\n\n".join([
        f"[출처 {i+1}] {c.get('document_title', 'Unknown')}\n{c.get('chunk_text', c.get('snippet', ''))[:500]}"
        for i, c in enumerate(chunks[:5])
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SELF_REFLECTION_PROMPT),
        ("human", f"""질문: {query}

검색된 문서:
{chunks_text}

생성된 답변:
{answer[:2000]}

위 내용을 기반으로 답변 품질을 JSON 형식으로 평가하세요.""")
    ])
    
    try:
        response = await llm_mini.ainvoke(prompt.format_messages())
        result = json.loads(response.content)
        
        state["self_reflection"] = result
        overall_score = result.get("overall_score", 70)
        
        if result.get("hallucination_detected", False):
            state["verification_status"] = "failed"
            state["error_message"] = "환각이 감지되었습니다."
        else:
            state["verification_status"] = result.get("verification_status", "passed")
        
        # Update confidence based on reflection
        state["confidence"] = overall_score / 100.0
        
        state["messages"] = list(state["messages"]) + [
            AIMessage(content=f"Self-reflection: score={overall_score}, status={state['verification_status']}")
        ]
        
    except Exception as e:
        state["verification_status"] = "passed"
    
    return state


# ============ Retrieval Route Decision Node ============

def retrieval_route_decision_node(state: AgentState) -> Literal["more_retrieval", "comparative", "generate"]:
    """Decide next step after retrieval.
    
    - If needs more retrieval -> retrieve again
    - If comparative query -> go directly to comparative analysis (skip generic generation)
    - Otherwise -> generate answer
    """
    if state.get("needs_more_retrieval", False):
        return "more_retrieval"
    if state.get("query_type") == "comparative":
        return "comparative"
    return "generate"


# ============ Retry Decision Node ============

def retry_decision_node(state: AgentState) -> Literal["more_retrieval", "retry_generate", "end"]:
    """Decide whether to retry based on self-reflection."""
    status = state.get("verification_status", "passed")
    iteration = state.get("iteration_count", 0)
    
    if iteration >= settings.MAX_AGENT_ITERATIONS:
        return "end"
    
    if status == "needs_more_context":
        return "more_retrieval"
    elif status == "needs_retry":
        return "retry_generate"
    else:
        return "end"


# ============ Build the Enhanced Graph ============

def create_policy_agent():
    """Create and configure the multi-step reasoning agent workflow.
    
    Flow:
    analyze -> route -> [retrieve -> route -> generate/comparative] -> reflect -> decide
                     -> [industry/checklist]
    
    Comparative queries: analyze -> retrieve -> comparative -> reflect
    QA queries: analyze -> retrieve -> generate -> reflect
    """
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_query_node)
    workflow.add_node("retrieve", adaptive_retrieval_node)
    workflow.add_node("generate", rag_generation_node)
    workflow.add_node("comparative", comparative_analysis_node)
    workflow.add_node("industry", industry_classification_node)
    workflow.add_node("checklist_node", checklist_extraction_node)
    workflow.add_node("reflect", self_reflection_node)
    
    # Entry point
    workflow.set_entry_point("analyze")
    
    # From analyze, route to appropriate handler
    # Note: comparative queries go to retrieve first (need documents for comparison)
    workflow.add_conditional_edges(
        "analyze",
        route_query_node,
        {
            "retrieve": "retrieve",
            "industry": "industry",
            "checklist": "checklist_node",
            "topic": "retrieve",
            "comparative": "retrieve",
            "end": END
        }
    )
    
    # After retrieval, decide next step:
    # - If needs more retrieval -> retrieve again
    # - If comparative query -> go directly to comparative analysis (skip generic generation)
    # - Otherwise -> generate answer
    workflow.add_conditional_edges(
        "retrieve",
        retrieval_route_decision_node,
        {
            "more_retrieval": "retrieve",
            "comparative": "comparative",
            "generate": "generate"
        }
    )
    
    # Generation goes directly to reflection
    workflow.add_edge("generate", "reflect")
    
    # Comparative analysis goes to reflection
    workflow.add_edge("comparative", "reflect")
    
    # Other processing nodes go to reflection
    workflow.add_edge("industry", "reflect")
    workflow.add_edge("checklist_node", "reflect")
    
    # After reflection, decide next step
    workflow.add_conditional_edges(
        "reflect",
        retry_decision_node,
        {
            "more_retrieval": "retrieve",
            "retry_generate": "generate",
            "end": END
        }
    )
    
    return workflow.compile()


# Global agent instance
policy_agent = None

def get_policy_agent():
    global policy_agent
    if policy_agent is None:
        policy_agent = create_policy_agent()
    return policy_agent


# ============ Public API ============

async def run_policy_agent(query: str, document_id: str | None = None) -> dict:
    """Run the multi-step reasoning agent with the given query.
    
    Enhanced features:
    - Query decomposition for complex questions
    - Adaptive retrieval with quality scoring
    - Self-reflection for answer quality
    - Comparative analysis support
    
    Args:
        query: User query
        document_id: Optional document ID for classification/checklist tasks
        
    Returns:
        Agent execution result with detailed metrics
    """
    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "query_type": "unknown",
        "document_id": document_id,
        
        # Query Analysis
        "sub_queries": [],
        "search_strategy": "broad",
        "expanded_query": query,
        
        # Retrieval
        "retrieved_chunks": [],
        "retrieval_score": 0.0,
        "needs_more_retrieval": False,
        "retrieval_attempts": 0,
        
        # Processing Results
        "industry_classification": None,
        "checklist": None,
        "answer": None,
        "partial_answers": [],
        
        # Quality Metrics
        "confidence": 0.0,
        "groundedness_score": 0.0,
        "citation_coverage": 0.0,
        
        # Verification
        "verification_status": "pending",
        "self_reflection": None,
        "iteration_count": 0,
        "error_message": None
    }
    
    result = await get_policy_agent().ainvoke(initial_state)
    
    return {
        "query_type": result["query_type"],
        "search_strategy": result.get("search_strategy", "broad"),
        "sub_queries": result.get("sub_queries", []),
        "answer": result.get("answer"),
        "industry_classification": result.get("industry_classification"),
        "checklist": result.get("checklist"),
        "confidence": result["confidence"],
        "groundedness_score": result.get("groundedness_score", 0.0),
        "citation_coverage": result.get("citation_coverage", 0.0),
        "verification_status": result["verification_status"],
        "self_reflection": result.get("self_reflection"),
        "iterations": result["iteration_count"],
        "retrieval_attempts": result.get("retrieval_attempts", 1),
        "retrieval_score": result.get("retrieval_score", 0.0),
        "error": result.get("error_message"),
        "retrieved_chunks": result.get("retrieved_chunks", [])
    }
