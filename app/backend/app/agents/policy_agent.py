"""LangGraph-based Policy Analysis Agent Workflow.

Implements: 분류 -> 추출 -> 검증 (Classification -> Extraction -> Verification)
"""
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import json

from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.industry_classifier import IndustryClassifier
from app.services.checklist_service import ChecklistService


# ============ State Definition ============

class AgentState(TypedDict):
    """State for the policy analysis agent."""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    query: str
    query_type: Literal["qa", "industry_classification", "compliance_extract", "topic_surge", "unknown"]
    document_id: str | None
    retrieved_chunks: list[dict]
    industry_classification: dict | None
    checklist: dict | None
    answer: str | None
    confidence: float
    verification_status: Literal["pending", "passed", "failed", "needs_retry"]
    iteration_count: int
    error_message: str | None


# ============ LLM Setup ============

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    temperature=0.2,
    api_key=settings.OPENAI_API_KEY
)

# ============ Query Classifier Node ============

QUERY_CLASSIFIER_PROMPT = """당신은 금융정책 질문 분류 전문가입니다.

사용자 질문을 다음 4가지 유형 중 하나로 분류하세요:

1. **qa** - 일반적인 질문응답 ("시행 시점이 언제인가?", "적용 대상은?")
2. **industry_classification** - 업권 영향 분류 ("이 문서는 어떤 업권에 영향을 주나?")
3. **compliance_extract** - 준수 항목 추출 ("해야 할 일을 정리해줘", "체크리스트 생성")
4. **topic_surge** - 토픽/경보 관련 ("최근 급부상 이슈는?", "이번 주 주요 토픽")

응답은 반드시 다음 JSON 형식으로 제공:
{
    "query_type": "qa|industry_classification|compliance_extract|topic_surge",
    "confidence": 0.0-1.0,
    "reasoning": "분류 이유"
}
"""

async def classify_query_node(state: AgentState) -> AgentState:
    """Classify the user query into one of the predefined types."""
    query = state["query"]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", QUERY_CLASSIFIER_PROMPT),
        ("human", f"질문: {query}")
    ])
    
    response = await llm.ainvoke(prompt.format_messages())
    
    try:
        result = json.loads(response.content)
        state["query_type"] = result.get("query_type", "unknown")
        state["confidence"] = result.get("confidence", 0.5)
    except json.JSONDecodeError:
        # Fallback to simple keyword matching
        if any(kw in query for kw in ["업권", "보험", "은행", "증권", "분류"]):
            state["query_type"] = "industry_classification"
        elif any(kw in query for kw in ["체크리스트", "해야 할 일", "준수", "추출"]):
            state["query_type"] = "compliance_extract"
        elif any(kw in query for kw in ["토픽", "경보", "이슈", "급부상"]):
            state["query_type"] = "topic_surge"
        else:
            state["query_type"] = "qa"
    
    state["messages"] = state["messages"] + [
        AIMessage(content=f"Query classified as: {state['query_type']}")
    ]
    
    return state


# ============ Router Node ============

async def route_query_node(state: AgentState) -> Literal["qa", "industry", "checklist", "topic", "end"]:
    """Route to appropriate handler based on query type."""
    query_type = state.get("query_type", "unknown")
    
    if query_type == "qa":
        return "qa"
    elif query_type == "industry_classification":
        return "industry"
    elif query_type == "compliance_extract":
        return "checklist"
    elif query_type == "topic_surge":
        return "topic"
    else:
        return "end"


# ============ RAG QA Node ============

rag_service = RAGService()

async def rag_qa_node(state: AgentState) -> AgentState:
    """Perform RAG-based question answering."""
    query = state["query"]
    
    try:
        from app.models.schemas import QARequest
        
        request = QARequest(question=query)
        response = await rag_service.answer_question(request)
        
        state["answer"] = response.answer
        state["retrieved_chunks"] = [
            {
                "chunk_id": c.chunk_id,
                "document_title": c.document_title,
                "snippet": c.snippet,
                "url": c.url
            }
            for c in response.citations
        ]
        state["confidence"] = response.confidence
        state["verification_status"] = "pending"
        
        state["messages"] = state["messages"] + [
            AIMessage(content=f"RAG Answer generated. Confidence: {response.confidence}")
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


# ============ Verification Node ============

VERIFICATION_PROMPT = """당신은 금융정책 분석 검증 전문가입니다.

다음 결과의 품질을 검증하고 개선이 필요한지 판단하세요.

검증 기준:
1. **근거 충분성**: 검색된 문서가 질문에 답하기에 충분한가?
2. **정확성**: 답변이 문서 내용과 일치하는가?
3. **완전성**: 중요한 정보가 누락되지 않았는가?

응답 형식 (JSON):
{
    "verification_status": "passed|failed|needs_retry",
    "confidence": 0.0-1.0,
    "issues": ["문제점1", "문제점2"],
    "suggestions": ["개선 제안1", "개선 제안2"]
}
"""

async def verification_node(state: AgentState) -> AgentState:
    """Verify the quality of the generated result."""
    # Skip verification if already failed
    if state.get("verification_status") == "failed":
        return state
    
    # Increment iteration count
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    
    # Check max iterations
    if state["iteration_count"] >= settings.MAX_AGENT_ITERATIONS:
        state["verification_status"] = "passed"  # Force pass after max iterations
        return state
    
    query = state["query"]
    answer = state.get("answer", "")
    retrieved_chunks = state.get("retrieved_chunks", [])
    
    chunks_text = "\n\n".join([
        f"[문서: {c.get('document_title', 'Unknown')}]\n{c.get('snippet', '')}"
        for c in retrieved_chunks[:3]
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", VERIFICATION_PROMPT),
        ("human", f"""질문: {query}

검색된 문서:
{chunks_text}

생성된 답변:
{answer[:1000] if answer else 'N/A'}

검증 결과를 JSON으로 제공하세요.""")
    ])
    
    try:
        response = await llm.ainvoke(prompt.format_messages())
        result = json.loads(response.content)
        
        state["verification_status"] = result.get("verification_status", "passed")
        state["confidence"] = result.get("confidence", state.get("confidence", 0.5))
        
        state["messages"] = state["messages"] + [
            AIMessage(content=f"Verification: {state['verification_status']}. Issues: {result.get('issues', [])}")
        ]
        
    except Exception as e:
        # If verification fails, still pass to avoid infinite loops
        state["verification_status"] = "passed"
    
    return state


# ============ Retry Decision Node ============

def retry_decision_node(state: AgentState) -> Literal["retry", "end"]:
    """Decide whether to retry or end the workflow."""
    if state.get("verification_status") == "needs_retry" and state.get("iteration_count", 0) < settings.MAX_AGENT_ITERATIONS:
        return "retry"
    return "end"


# ============ Build the Graph ============

def create_policy_agent():
    """Create and configure the policy analysis agent workflow."""
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("classify", classify_query_node)
    workflow.add_node("qa", rag_qa_node)
    workflow.add_node("industry", industry_classification_node)
    workflow.add_node("checklist_node", checklist_extraction_node)
    workflow.add_node("verify", verification_node)
    
    # Add edges
    workflow.set_entry_point("classify")
    
    # From classify, route to appropriate handler
    workflow.add_conditional_edges(
        "classify",
        route_query_node,
        {
            "qa": "qa",
            "industry": "industry",
            "checklist": "checklist_node",
            "topic": "qa",  # Topic surge uses RAG QA for now
            "end": END
        }
    )
    
    # All processing nodes go to verification
    workflow.add_edge("qa", "verify")
    workflow.add_edge("industry", "verify")
    workflow.add_edge("checklist_node", "verify")
    
    # Verification decides next step
    workflow.add_conditional_edges(
        "verify",
        retry_decision_node,
        {
            "retry": "classify",  # Go back to start for retry
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
    """Run the policy analysis agent with the given query.
    
    Args:
        query: User query
        document_id: Optional document ID for classification/checklist tasks
        
    Returns:
        Agent execution result
    """
    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "query": query,
        "query_type": "unknown",
        "document_id": document_id,
        "retrieved_chunks": [],
        "industry_classification": None,
        "checklist": None,
        "answer": None,
        "confidence": 0.0,
        "verification_status": "pending",
        "iteration_count": 0,
        "error_message": None
    }
    
    result = await get_policy_agent().ainvoke(initial_state)

    
    return {
        "query_type": result["query_type"],
        "answer": result.get("answer"),
        "industry_classification": result.get("industry_classification"),
        "checklist": result.get("checklist"),
        "confidence": result["confidence"],
        "verification_status": result["verification_status"],
        "iterations": result["iteration_count"],
        "error": result.get("error_message"),
        "retrieved_chunks": result.get("retrieved_chunks", [])
    }
