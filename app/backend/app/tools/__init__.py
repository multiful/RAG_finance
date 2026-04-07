# ======================================================================
# FSC Policy RAG System | 모듈: app.tools.__init__
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""Agentic RAG / 에이전트용 도구. 웹 검색 등."""
from app.tools.web_search import web_search_for_context

__all__ = ["web_search_for_context"]
