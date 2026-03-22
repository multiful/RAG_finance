"""
Golden Dataset 기준 RAG 품질 정량 평가 스크립트.

실행 방법 (backend 디렉토리에서, 가상환경 활성화 후):
  # Windows (fastapi venv 예시)
  C:\\Users\\rlaeh\\envs\\fastapi\\.venv\\Scripts\\activate
  cd app/backend
  # 기본: data/golden_eval_12.jsonl 12문항 (지표 목표 시 .env 권장: OPENAI_MODEL=gpt-4o, RAGAS_EVAL_MODEL=gpt-4o)
  python -m scripts.run_golden_ragas
  python -m scripts.run_golden_ragas --jsonl data/golden_temp.jsonl --limit 8

출력: Ragas 평균 지표, Retrieval Recall@3/@5. 결과를 RESULTS_AND_ACHIEVEMENTS.md에 반영.
"""
import asyncio
import argparse
import sys
from pathlib import Path

# backend/app 기준으로 import 가능하도록
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.evaluation.golden_dataset import (
    get_golden_dataset,
    get_dataset_stats,
    load_golden_from_jsonl,
)
from app.evaluation.ragas_evaluator import get_evaluator
from app.models.schemas import QARequest
from app.services.rag_service import RAGService


def _recall_at_k(chunk_texts: list[str], expected_keywords: list[str], k: int) -> bool:
    """Top-k 청크 중 기대 키워드가 하나라도 포함된 청크가 있으면 1, 없으면 0."""
    top = chunk_texts[:k]
    combined = " ".join(top).lower()
    return any(kw.lower() in combined for kw in expected_keywords)


async def run_golden_evaluation(
    limit: int | None = None,
    sample: bool = False,
    jsonl_path: str | None = None,
):
    """Golden set으로 RAG 답변 생성 후 Ragas 배치 평가 실행."""
    if jsonl_path:
        dataset = load_golden_from_jsonl(jsonl_path)
        print(f"[INFO] Golden JSONL: {jsonl_path} ({len(dataset)}문항)")
    else:
        dataset = get_golden_dataset()
        stats = get_dataset_stats()
        print(f"[INFO] Golden dataset: 총 {stats['total_questions']}문항")
    if limit:
        dataset = dataset[:limit]
        print(f"[INFO] 평가 문항 수(적용 후): {len(dataset)}")
    if sample and len(dataset) > 20:
        # 난이도·업권 균형을 위해 앞 10 + 뒤 10 + 중간 5 등 간단 샘플
        step = max(1, len(dataset) // 20)
        indices = list(range(0, len(dataset), step))[:20]
        dataset = [dataset[i] for i in indices]
        print(f"[INFO] 샘플 모드: {len(dataset)}문항")

    rag = RAGService()
    evaluator = get_evaluator()
    test_cases = []
    retrieval_recall_3 = []
    retrieval_recall_5 = []

    for i, g in enumerate(dataset):
        try:
            req = QARequest(question=g.question, include_retrieval_contexts=True)
            resp = await rag.answer_question(req)
            # Ragas용 contexts: 리트리벌 전체 텍스트(스니펫은 DB 비어 있으면 ""일 수 있음)
            if getattr(resp, "retrieval_contexts", None):
                contexts = [t for t in resp.retrieval_contexts if t] or [""]
            else:
                def _snippet(c):
                    return c.get("snippet", "") if isinstance(c, dict) else getattr(c, "snippet", "")
                contexts = [_snippet(c) for c in resp.citations] if resp.citations else [""]
            test_cases.append({
                "question_id": g.id,
                "question": g.question,
                "answer": resp.answer,
                "contexts": contexts,
                "ground_truth": g.ground_truth_summary,
            })
            # Retrieval Recall@3, @5 (기대 키워드가 top-k 청크에 포함 여부)
            chunk_texts = contexts
            r3 = _recall_at_k(chunk_texts, g.expected_citations_keywords, 3)
            r5 = _recall_at_k(chunk_texts, g.expected_citations_keywords, 5)
            retrieval_recall_3.append(1 if r3 else 0)
            retrieval_recall_5.append(1 if r5 else 0)
        except Exception as e:
            print(f"[WARN] {g.id} 실패: {e}")
            test_cases.append({
                "question_id": g.id,
                "question": g.question,
                "answer": "",
                "contexts": [],
                "ground_truth": g.ground_truth_summary,
            })
            retrieval_recall_3.append(0)
            retrieval_recall_5.append(0)

        if (i + 1) % 10 == 0:
            print(f"  진행: {i+1}/{len(dataset)}")

    # 디버그: 첫 문항 기준 Recall 0 원인 확인 (기대 키워드 vs 실제 스니펫)
    if test_cases and dataset:
        g0 = dataset[0]
        tc0 = test_cases[0]
        ctx0 = tc0.get("contexts") or []
        r3_0 = retrieval_recall_3[0] if retrieval_recall_3 else 0
        r5_0 = retrieval_recall_5[0] if retrieval_recall_5 else 0
        print("\n[DEBUG] 1문항 Recall 원인 점검")
        print(f"  question_id: {g0.id}")
        print(f"  expected_citations_keywords: {g0.expected_citations_keywords}")
        print(f"  citations 개수: {len(ctx0)}, 스니펫 길이들: {[len(s) for s in ctx0[:5]]}")
        for ji, snip in enumerate(ctx0[:3]):
            preview = (snip or "")[:150].replace("\n", " ")
            print(f"  snippet[{ji}]: {preview!r}")
        print(f"  Recall@3={r3_0}, Recall@5={r5_0}")

    if not test_cases:
        print("[ERROR] 평가할 케이스가 없습니다.")
        return

    # Ragas 배치 평가 (openai 1.12 + 최신 ragas/instructor 조합 시 ImportError 가능 → requirements-ragas-compat.txt)
    summary = await evaluator.evaluate_batch(test_cases)
    if summary.run_id == "ragas_import_error" or summary.total_questions == 0:
        print("\n[WARN] RAGAS 배치가 실패했거나 스킵되었습니다.")
        if summary.suggestions:
            for s in summary.suggestions:
                print(f"  → {s}")
        if retrieval_recall_3:
            recall3_pct = sum(retrieval_recall_3) / len(retrieval_recall_3) * 100
            recall5_pct = sum(retrieval_recall_5) / len(retrieval_recall_5) * 100
            print(f"\n[부분 결과] Retrieval Recall@3: {recall3_pct:.1f}%  Recall@5: {recall5_pct:.1f}% (RAG 검색만 완료)")
        print("  pip install -r requirements-ragas-compat.txt 후 재실행하면 Ragas 지표가 붙습니다.")
        return

    # 출력
    print("\n" + "=" * 60)
    print("Golden Set 기준 RAG 정량 평가 결과")
    print("=" * 60)
    print(f"총 문항 수: {summary.total_questions}")
    print(f"  - avg_groundedness (근거일치율): {summary.avg_groundedness:.4f}")
    print(f"  - avg_faithfulness (충실도):     {summary.avg_faithfulness:.4f}")
    print(f"  - avg_answer_relevancy:           {summary.avg_answer_relevancy:.4f}")
    print(f"  - avg_context_precision:         {summary.avg_context_precision:.4f}")
    print(f"  - avg_context_recall:            {summary.avg_context_recall:.4f}")
    print(f"  - avg_overall_score:             {summary.avg_overall_score:.4f}")
    if retrieval_recall_3:
        recall3_pct = sum(retrieval_recall_3) / len(retrieval_recall_3) * 100
        recall5_pct = sum(retrieval_recall_5) / len(retrieval_recall_5) * 100
        print(f"  - Retrieval Recall@3 (키워드 포함): {recall3_pct:.1f}%")
        print(f"  - Retrieval Recall@5 (키워드 포함): {recall5_pct:.1f}%")
    print("=" * 60)
    if summary.suggestions:
        print("개선 제안:")
        for s in summary.suggestions:
            print(f"  - {s}")
    print("\n위 수치를 RESULTS_AND_ACHIEVEMENTS.md '프로젝트 성과 (정량 지표)'에 반영하세요.")


def main():
    parser = argparse.ArgumentParser(description="Golden set 기준 Ragas 평가")
    parser.add_argument("--limit", type=int, default=12, help="평가 문항 수 제한 (기본: 12)")
    parser.add_argument("--sample", action="store_true", help="20문항 샘플만 평가")
    parser.add_argument(
        "--jsonl",
        type=str,
        default="data/golden_eval_12.jsonl",
        help="JSONL 골든셋 경로 (기본: data/golden_eval_12.jsonl)",
    )
    args = parser.parse_args()
    asyncio.run(
        run_golden_evaluation(
            limit=args.limit,
            sample=args.sample,
            jsonl_path=args.jsonl,
        )
    )


if __name__ == "__main__":
    main()
