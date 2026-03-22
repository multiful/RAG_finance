"""RAG·LLM 스모크: OPENAI_API_KEY·DB·벡터 검색 가능 여부 확인.
   cd app/backend && python -m scripts.smoke_rag
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    from app.core.config import settings
    from app.services.rag_service import RAGService
    from app.models.schemas import QARequest

    print("[1] OPENAI_API_KEY:", "설정됨" if settings.OPENAI_API_KEY else "없음 — RAG 불가")
    try:
        from app.core.database import get_db
        db = get_db()
        r = db.table("documents").select("document_id", count="exact").limit(1).execute()
        n = getattr(r, "count", None) or 0
        print(f"[2] Supabase documents 행(추정): {n}")
    except Exception as e:
        print(f"[2] DB 오류: {e}")

    if not settings.OPENAI_API_KEY:
        print("[3] 스킵: 임베딩/답변 필요")
        return

    rag = RAGService()
    req = QARequest(question="가상자산 규제", top_k=3)
    try:
        resp = await rag.answer_question(req)
        print(f"[3] RAG answer_len={len(resp.answer or '')} citations={len(resp.citations or [])} "
              f"confidence={resp.confidence:.3f}")
    except Exception as e:
        print(f"[3] RAG 실패: {e}")


if __name__ == "__main__":
    asyncio.run(main())
