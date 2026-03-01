"""
샌드박스 시나리오 시뮬레이션 (방안 B).
Gap Map 사각지대 + 체크리스트 약점을 입력으로, RAG(국제·국내 문서) 참조해
샌드박스 적용 시나리오의 검토 포인트·완화 가능성·권고를 LLM이 생성.
"""
import json
import logging
from typing import List, Dict, Any, Optional

from app.constants.risk_axes import RISK_AXIS_NAMES, RISK_AXIS_DESCRIPTIONS
from app.services.gap_map_service import get_top_blind_spots, get_gap_map
from app.services.vector_store import get_vector_store
from app.services.rag_service import RAGService
from app.core.config import settings


async def run_sandbox_simulation(
    blind_spot_axes: Optional[List[str]] = None,
    checklist_weaknesses: Optional[List[Dict[str, str]]] = None,
    top_k_context: int = 8,
) -> Dict[str, Any]:
    """
    Gap Map 사각지대 + 체크리스트 약점 기반 샌드박스 시나리오 시뮬레이션.

    Args:
        blind_spot_axes: 축 ID 목록 (미제공 시 Gap 상위 5개 사용)
        checklist_weaknesses: [{"question_id", "question_ko", "response"}]
        top_k_context: RAG 검색 chunk 수

    Returns:
        { scenario_summary, review_points, mitigation_options, citations }
    """
    # 1) 사각지대 확보
    if blind_spot_axes:
        full = get_gap_map()
        axis_set = set(blind_spot_axes)
        blind_spots = [s for s in full if s.axis_id in axis_set]
        blind_spots = sorted(blind_spots, key=lambda x: x.gap, reverse=True)[:5]
        blind_spot_items = [
            {"axis_id": s.axis_id, "name_ko": s.name_ko, "gap": s.gap, "description": getattr(s, "description", "") or RISK_AXIS_DESCRIPTIONS.get(s.axis_id, "")}
            for s in blind_spots
        ]
    else:
        top = get_top_blind_spots(limit=5)
        blind_spot_items = [
            {"axis_id": item.axis_id, "name_ko": item.name_ko, "gap": item.gap, "description": item.description}
            for item in top
        ]

    # 2) RAG 검색용 쿼리: 축 이름 + 샌드박스·규제 키워드
    query_parts = [item["name_ko"] for item in blind_spot_items]
    query_parts.extend(["금융규제 샌드박스", "테스트베드", "규제 완화", "FSB", "BIS", "regulatory sandbox"])
    search_query = " ".join(query_parts)

    # 3) RAG 검색
    try:
        rag = RAGService()
        embedding = await rag._get_embedding(search_query[:4000])
        store = get_vector_store()
        results = await store.hybrid_search(
            query=search_query,
            query_embedding=embedding,
            top_k=top_k_context,
        )
        context_parts = []
        citations = []
        for r in results[:top_k_context]:
            context_parts.append(f"[{r.document_title}]\n{r.chunk_text[:600]}")
            citations.append({"title": r.document_title, "url": getattr(r, "url", ""), "snippet": (r.chunk_text or "")[:200]})
        context_text = "\n\n---\n\n".join(context_parts) if context_parts else "관련 규제 문서를 찾지 못했습니다."
    except Exception as e:
        logging.warning(f"Sandbox simulation RAG search failed: {e}")
        context_text = "문서 검색에 실패하여 일반적인 샌드박스 관점으로만 답변합니다."
        citations = []

    # 4) 체크리스트 약점 요약
    weakness_summary = ""
    if checklist_weaknesses:
        lines = [f"- {w.get('question_ko', w.get('question_id', ''))}: {w.get('response', '')}" for w in checklist_weaknesses[:10]]
        weakness_summary = "자가진단 약점(아니오/부분):\n" + "\n".join(lines)

    # 5) LLM 시뮬레이션
    blind_summary = "\n".join([
        f"- {b['axis_id']} {b['name_ko']} (Gap {b['gap']:.2f}): {(b['description'][:80] + '...') if len(b.get('description', '')) > 80 else b.get('description', '')}"
        for b in blind_spot_items
    ])

    prompt = f"""당신은 금융규제 샌드박스(테스트베드) 정책 분석가입니다.
아래 "규제 사각지대(Gap Map)"와 선택적으로 "자가진단 약점"이 주어졌을 때,
**샌드박스 적용 시나리오**를 전제로 다음을 한국어로 작성하세요. 반드시 아래 참고 문서(context)에 기반하여 답변하세요.

## 규제 사각지대 (Gap 상위)
{blind_summary}

{weakness_summary}

## 참고 문서 (국내·국제)
{context_text[:12000]}

## 출력 형식 (반드시 아래 JSON만 출력, 다른 설명 금지)
{{
  "scenario_summary": "샌드박스 적용 시나리오 관점에서 2~3문장 요약 (검토 포인트·완화 가능성 중심)",
  "review_points": ["검토 포인트 1", "검토 포인트 2", "..."],
  "mitigation_options": ["보완·대응 방안 1", "보완·대응 방안 2", "..."]
}}
"""

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "당신은 금융규제 샌드박스 정책 분석가입니다. 요청된 JSON 형식만 출력하세요."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content or "{}"
        # JSON 블록만 추출
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return {
            "scenario_summary": data.get("scenario_summary", ""),
            "review_points": data.get("review_points", []),
            "mitigation_options": data.get("mitigation_options", []),
            "citations": citations[:10],
            "blind_spots_used": blind_spot_items,
        }
    except Exception as e:
        logging.exception("Sandbox simulation LLM failed: %s", e)
        return {
            "scenario_summary": f"시뮬레이션 생성 중 오류가 발생했습니다: {str(e)}",
            "review_points": [],
            "mitigation_options": ["RAG 또는 LLM 오류로 기본 제안만 제공됩니다. Gap Map 상위 축에 대한 보완 계획을 수동으로 수립하세요."],
            "citations": citations,
            "blind_spots_used": blind_spot_items,
        }
