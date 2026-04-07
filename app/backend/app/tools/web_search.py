# ======================================================================
# FSC Policy RAG System | 모듈: app.tools.web_search
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""Agentic RAG: 정보 부족 시 외부 검색 도구.

- Serper (Google Search API): SERPER_API_KEY
- Tavily (AI 검색): TAVILY_API_KEY

.env에 하나라도 설정하면 "검색 결과 부족 → 추가로 웹 검색" 플로우에서 사용됩니다.
"""
import logging
import httpx
from typing import List, Dict, Any
from app.core.config import settings

_log = logging.getLogger(__name__)


async def web_search_serper(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Serper API로 검색. SERPER_API_KEY 필요."""
    if not settings.SERPER_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": num},
            )
            r.raise_for_status()
            data = r.json()
            out = []
            for item in data.get("organic", [])[:num]:
                out.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "source": "serper",
                })
            return out
    except Exception as e:
        _log.debug("Serper search error: %s", e)
        return []


async def web_search_tavily(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Tavily API로 검색. TAVILY_API_KEY 필요. config에서 search_depth, topic 등 적용."""
    if not settings.TAVILY_API_KEY:
        return []
    depth = getattr(settings, "TAVILY_SEARCH_DEPTH", "advanced")
    topic = getattr(settings, "TAVILY_SEARCH_TOPIC", "general")
    max_results = getattr(settings, "TAVILY_MAX_RESULTS", 5) or num
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "api_key": settings.TAVILY_API_KEY,
                "query": query,
                "search_depth": depth,
                "max_results": min(max_results, num),
            }
            if topic and topic != "general":
                payload["topic"] = topic
            r = await client.post(
                "https://api.tavily.com/search",
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            out = []
            for item in data.get("results", [])[:num]:
                out.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("content", item.get("snippet", "")),
                    "url": item.get("url", ""),
                    "source": "tavily",
                })
            return out
    except Exception as e:
        _log.debug("Tavily search error: %s", e)
        return []


async def web_search_for_context(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """
    설정된 API 키에 따라 Serper 또는 Tavily로 웹 검색.
    Agentic RAG에서 '정보 부족' 시 추가 컨텍스트 확보용.
    """
    if settings.SERPER_API_KEY:
        return await web_search_serper(query, num)
    if settings.TAVILY_API_KEY:
        return await web_search_tavily(query, num)
    return []


def is_web_search_available() -> bool:
    """웹 검색 사용 가능 여부 (API 키 설정 시 True)."""
    return bool(settings.SERPER_API_KEY or settings.TAVILY_API_KEY)
