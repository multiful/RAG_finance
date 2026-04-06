# ======================================================================
# FSC Policy RAG System | 모듈: app.chunking.__init__
# 최종 수정일: 2026-04-07
# 연관 문서: SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# ======================================================================

from app.chunking.recursive_split import get_recursive_splitter, split_text_recursive

__all__ = ["get_recursive_splitter", "split_text_recursive"]
