# ======================================================================
# FSC Policy RAG System | 모듈: app.api.references_routes
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""연구 참고문헌 API (KCI·인용용)."""
from fastapi import APIRouter, Query

from app.constants.references_kci import get_references_meta, get_all_references, get_references_for_kci_style

router = APIRouter(prefix="/references", tags=["References (KCI)"])


@router.get("")
async def api_get_references(
    format: str = Query("meta", description="meta | list | kci"),
):
    """
    연구 참고문헌 조회 (KCI·논문 인용용).
    competition 문서 기반 국제기구·국내 법령·학술 논문 목록.
    """
    if format == "list":
        return {"items": get_all_references()}
    if format == "kci":
        return {"items": get_references_for_kci_style()}
    return get_references_meta()


@router.get("/kci-style")
async def api_get_references_kci_style():
    """KCI 인용 형식 문자열 목록 (저자(연도). 제목.)."""
    return {"citations": get_references_for_kci_style()}
