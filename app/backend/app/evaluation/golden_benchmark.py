# ======================================================================
# FSC Policy RAG System | 모듈: app.evaluation.golden_benchmark
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""골든셋 기반 검색·근거 품질 벤치마크 (RAGAS와 별도, 빠른 리트리벌 점검용)."""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.config import settings
from app.evaluation.golden_dataset import GOLDEN_DATASET, GoldenQuestion
from app.services.rag_service import (
    RAGService,
    hybrid_weights_for_query,
    expand_regulatory_query_for_retrieval,
)


def _keywords_hit(blob: str, keywords: List[str]) -> bool:
    """상위 검색 본문에 기대 키워드가 모두 포함되는지(대소문자 무시)."""
    if not keywords:
        return True
    low = blob.lower()
    return all((kw or "").lower() in low for kw in keywords)


def _recall_at_k(chunk_texts: List[str], keywords: List[str], k: int) -> bool:
    top = chunk_texts[:k]
    return _keywords_hit(" ".join(top), keywords)


async def run_golden_retrieval_benchmark(sample_size: int = 12) -> Dict[str, Any]:
    """
    골든 질문에 대해 HyDE(설정 시)·하이브리드 검색만 수행하고,
    기대 키워드가 상위 청크에 포함되는지로 근거 검색 품질을 추정합니다.
    (전체 QA·RAGAS보다 가볍고, 인덱스·검색 튜닝에 유리)
    """
    cap = min(max(1, sample_size), len(GOLDEN_DATASET), 50)
    subset: List[GoldenQuestion] = GOLDEN_DATASET[:cap]

    rag = RAGService()
    rows: List[Dict[str, Any]] = []
    r5_hits = 0
    r10_hits = 0

    for g in subset:
        lex = expand_regulatory_query_for_retrieval(g.question)
        if getattr(settings, "ENABLE_QUERY_HYDE", False):
            expanded = await rag._expand_query_hyde(lex)
        else:
            expanded = lex
        q_emb = await rag._get_embedding(expanded)
        vw, kw = hybrid_weights_for_query(lex)
        results = await rag.vector_store.hybrid_search(
            query=lex,
            query_embedding=q_emb,
            top_k=settings.TOP_K_RETRIEVAL,
            vector_weight=vw,
            keyword_weight=kw,
            similarity_threshold=getattr(settings, "HYBRID_SIMILARITY_THRESHOLD", 0.22),
            filters={},
        )
        texts = [r.chunk_text for r in results]
        top_sim = float(results[0].similarity) if results else 0.0
        ok5 = _recall_at_k(texts, g.expected_citations_keywords, 5)
        ok10 = _recall_at_k(texts, g.expected_citations_keywords, 10)
        if ok5:
            r5_hits += 1
        if ok10:
            r10_hits += 1
        rows.append(
            {
                "id": g.id,
                "question": g.question[:120],
                "recall_at_5": ok5,
                "recall_at_10": ok10,
                "top_similarity": round(top_sim, 4),
                "industry": g.industry.value,
                "difficulty": g.difficulty.value,
            }
        )

    return {
        "mode": "golden_retrieval_keyword_recall",
        "sample_size": cap,
        "recall_at_5_rate": round(r5_hits / cap, 4),
        "recall_at_10_rate": round(r10_hits / cap, 4),
        "rows": rows,
        "note": "상위 k개 청크 본문에 expected_citations_keywords가 모두 포함되면 성공. 인덱스·질문 표현에 민감합니다.",
    }
