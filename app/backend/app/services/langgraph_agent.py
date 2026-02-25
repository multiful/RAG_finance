"""
LangGraph Multi-Agent System - 복잡한 규제 질문 처리
공모전용 최신 기술 적용
"""
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from datetime import datetime, timezone
import operator
import json
import logging

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor

from app.core.config import settings
from app.core.database import get_db


class AgentState(TypedDict):
    """에이전트 상태 정의"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    question: str
    question_type: str
    search_queries: List[str]
    retrieved_contexts: List[Dict[str, Any]]
    draft_answer: str
    final_answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    needs_clarification: bool
    iteration: int


class RegulationAgent:
    """
    금융 규제 전문 멀티 에이전트 시스템
    
    에이전트 구성:
    1. Planner: 질문 분석 및 검색 전략 수립
    2. Retriever: 관련 문서 검색
    3. Analyzer: 검색 결과 분석 및 답변 초안 작성
    4. Verifier: 답변 검증 및 출처 확인
    5. Synthesizer: 최종 답변 생성
    """
    
    def __init__(self):
        self.db = get_db()
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("retriever", self._retriever_node)
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("verifier", self._verifier_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "retriever")
        workflow.add_edge("retriever", "analyzer")
        workflow.add_conditional_edges(
            "analyzer",
            self._should_verify,
            {
                "verify": "verifier",
                "retry": "retriever",
                "end": "synthesizer"
            }
        )
        workflow.add_edge("verifier", "synthesizer")
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    async def _planner_node(self, state: AgentState) -> Dict[str, Any]:
        """질문 분석 및 검색 전략 수립"""
        question = state["question"]
        
        planner_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 금융 규제 전문가입니다. 사용자 질문을 분석하여 최적의 검색 전략을 수립하세요.

질문 유형:
- factual: 사실 확인 (예: "DSR 규제란?")
- comparison: 비교 분석 (예: "K-ICS와 RBC의 차이점")
- procedural: 절차/방법 (예: "보험 청약철회 방법")
- trend: 동향/변화 (예: "최근 가상자산 규제 변화")
- impact: 영향 분석 (예: "ESG 의무화가 보험사에 미치는 영향")

응답 형식 (JSON):
{{
    "question_type": "factual|comparison|procedural|trend|impact",
    "search_queries": ["검색어1", "검색어2", "검색어3"],
    "key_entities": ["주요 엔티티"],
    "industries": ["INSURANCE", "BANKING", "SECURITIES"]
}}"""),
            ("human", "{question}")
        ])
        
        try:
            response = await self.llm.ainvoke(
                planner_prompt.format_messages(question=question)
            )
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            plan = json.loads(content)
            
            return {
                "question_type": plan.get("question_type", "factual"),
                "search_queries": plan.get("search_queries", [question]),
                "messages": [AIMessage(content=f"질문 분석 완료: {plan.get('question_type')} 유형")]
            }
        except Exception as e:
            logging.error(f"Planner error: {e}")
            return {
                "question_type": "factual",
                "search_queries": [question],
                "messages": [AIMessage(content="질문 분석 (기본)")]
            }
    
    async def _retriever_node(self, state: AgentState) -> Dict[str, Any]:
        """관련 문서 검색"""
        search_queries = state.get("search_queries", [state["question"]])
        
        all_contexts = []
        seen_ids = set()
        
        for query in search_queries[:3]:
            try:
                query_embedding = await self.embeddings.aembed_query(query)
                
                result = self.db.rpc(
                    "match_chunks",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": 0.5,
                        "match_count": 5
                    }
                ).execute()
                
                for chunk in (result.data or []):
                    chunk_id = chunk.get("chunk_id")
                    if chunk_id and chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        all_contexts.append({
                            "chunk_id": chunk_id,
                            "document_id": chunk.get("document_id"),
                            "document_title": chunk.get("document_title", ""),
                            "chunk_text": chunk.get("chunk_text", ""),
                            "similarity": chunk.get("similarity", 0),
                            "published_at": chunk.get("published_at", ""),
                            "url": chunk.get("url", "")
                        })
            except Exception as e:
                logging.error(f"Retriever error for query '{query}': {e}")
        
        all_contexts.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        top_contexts = all_contexts[:8]
        
        return {
            "retrieved_contexts": top_contexts,
            "messages": [AIMessage(content=f"검색 완료: {len(top_contexts)}개 문서 청크 발견")]
        }
    
    async def _analyzer_node(self, state: AgentState) -> Dict[str, Any]:
        """검색 결과 분석 및 답변 초안 작성"""
        question = state["question"]
        question_type = state.get("question_type", "factual")
        contexts = state.get("retrieved_contexts", [])
        
        if not contexts:
            return {
                "draft_answer": "관련 문서를 찾을 수 없습니다. 질문을 다시 확인해주세요.",
                "confidence": 0.2,
                "needs_clarification": True,
                "messages": [AIMessage(content="검색 결과 없음")]
            }
        
        context_text = "\n\n".join([
            f"[문서 {i+1}] {ctx.get('document_title', 'N/A')}\n{ctx.get('chunk_text', '')[:500]}"
            for i, ctx in enumerate(contexts[:5])
        ])
        
        analyzer_prompts = {
            "factual": "정확한 사실을 기반으로 명확하게 답변하세요.",
            "comparison": "두 개념을 체계적으로 비교 분석하세요.",
            "procedural": "단계별로 절차를 설명하세요.",
            "trend": "시간순으로 변화를 정리하세요.",
            "impact": "영향을 다각도로 분석하세요."
        }
        
        analyzer_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""당신은 금융 규제 전문 분석가입니다.
제공된 문서를 기반으로 질문에 답변하세요.

분석 지침: {analyzer_prompts.get(question_type, analyzer_prompts['factual'])}

중요:
- 문서에 없는 내용은 추측하지 마세요
- 출처를 명확히 하세요
- 불확실한 부분은 명시하세요"""),
            ("human", f"""질문: {question}

참조 문서:
{context_text}

위 문서를 기반으로 답변해주세요.""")
        ])
        
        try:
            response = await self.llm.ainvoke(
                analyzer_prompt.format_messages()
            )
            
            draft = response.content
            confidence = min(0.9, 0.5 + len(contexts) * 0.05)
            
            return {
                "draft_answer": draft,
                "confidence": confidence,
                "needs_clarification": len(contexts) < 2,
                "iteration": state.get("iteration", 0) + 1,
                "messages": [AIMessage(content="분석 완료")]
            }
        except Exception as e:
            logging.error(f"Analyzer error: {e}")
            return {
                "draft_answer": "분석 중 오류가 발생했습니다.",
                "confidence": 0.1,
                "needs_clarification": True,
                "messages": [AIMessage(content=f"분석 오류: {str(e)}")]
            }
    
    def _should_verify(self, state: AgentState) -> str:
        """검증 필요 여부 판단"""
        confidence = state.get("confidence", 0)
        iteration = state.get("iteration", 0)
        
        if iteration >= settings.MAX_AGENT_ITERATIONS:
            return "end"
        
        if confidence < 0.4 and iteration < 2:
            return "retry"
        
        if confidence >= 0.6:
            return "verify"
        
        return "end"
    
    async def _verifier_node(self, state: AgentState) -> Dict[str, Any]:
        """답변 검증 및 출처 확인"""
        draft = state.get("draft_answer", "")
        contexts = state.get("retrieved_contexts", [])
        
        verifier_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 금융 규제 문서 검증 전문가입니다.
답변이 제공된 문서에 기반하고 있는지 검증하세요.

검증 기준:
1. 답변의 모든 주장이 문서에 근거하는가?
2. 문서에 없는 정보가 추가되지 않았는가?
3. 인용이 정확한가?

응답 형식 (JSON):
{{
    "is_grounded": true/false,
    "grounded_statements": ["근거 있는 문장들"],
    "ungrounded_statements": ["근거 없는 문장들"],
    "confidence_adjustment": 0.0 (증가) ~ -0.3 (감소)
}}"""),
            ("human", f"""답변:
{draft}

참조 문서:
{chr(10).join([f"- {ctx.get('chunk_text', '')[:300]}" for ctx in contexts[:5]])}""")
        ])
        
        try:
            response = await self.llm.ainvoke(verifier_prompt.format_messages())
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            verification = json.loads(content)
            
            confidence = state.get("confidence", 0.5)
            confidence += verification.get("confidence_adjustment", 0)
            confidence = max(0.1, min(1.0, confidence))
            
            return {
                "confidence": confidence,
                "messages": [AIMessage(content=f"검증 완료: grounded={verification.get('is_grounded')}")]
            }
        except Exception as e:
            logging.error(f"Verifier error: {e}")
            return {
                "messages": [AIMessage(content="검증 건너뜀")]
            }
    
    async def _synthesizer_node(self, state: AgentState) -> Dict[str, Any]:
        """최종 답변 생성"""
        draft = state.get("draft_answer", "")
        contexts = state.get("retrieved_contexts", [])
        confidence = state.get("confidence", 0.5)
        
        citations = []
        for ctx in contexts[:5]:
            citations.append({
                "chunk_id": ctx.get("chunk_id", ""),
                "document_id": ctx.get("document_id", ""),
                "document_title": ctx.get("document_title", ""),
                "snippet": ctx.get("chunk_text", "")[:200],
                "published_at": ctx.get("published_at", ""),
                "url": ctx.get("url", "")
            })
        
        uncertainty_note = None
        if confidence < 0.5:
            uncertainty_note = "이 답변은 제한된 정보를 기반으로 생성되었습니다. 정확한 내용은 원문을 확인해주세요."
        
        return {
            "final_answer": draft,
            "citations": citations,
            "confidence": confidence,
            "messages": [AIMessage(content="최종 답변 생성 완료")]
        }
    
    async def process_question(self, question: str) -> Dict[str, Any]:
        """
        질문 처리 메인 함수
        
        Args:
            question: 사용자 질문
            
        Returns:
            Dict containing answer, citations, confidence, etc.
        """
        initial_state: AgentState = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "question_type": "",
            "search_queries": [],
            "retrieved_contexts": [],
            "draft_answer": "",
            "final_answer": "",
            "citations": [],
            "confidence": 0.0,
            "needs_clarification": False,
            "iteration": 0
        }
        
        try:
            final_state = await self.graph.ainvoke(
                initial_state,
                config={"recursion_limit": 50}
            )
            
            return {
                "answer": final_state.get("final_answer", ""),
                "citations": final_state.get("citations", []),
                "confidence": final_state.get("confidence", 0),
                "groundedness_score": final_state.get("confidence", 0),
                "citation_coverage": len(final_state.get("citations", [])) / 5,
                "question_type": final_state.get("question_type", "factual"),
                "agent_iterations": final_state.get("iteration", 1),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logging.error(f"Agent processing error: {e}")
            return {
                "answer": f"처리 중 오류가 발생했습니다: {str(e)}",
                "citations": [],
                "confidence": 0,
                "groundedness_score": 0,
                "citation_coverage": 0,
                "error": str(e)
            }


regulation_agent = RegulationAgent()
