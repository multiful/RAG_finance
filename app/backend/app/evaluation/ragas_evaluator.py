"""Ragas-based RAG Evaluation System.

Provides quantitative metrics for:
- Groundedness (근거일치율)
- Answer Relevance
- Context Precision
- Context Recall
- Faithfulness
"""
import json
import logging
import math
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.core.database import get_db


def _load_ragas_eval_deps():
    """ragas/datasets는 평가 API 호출 시에만 로드 (슬림 프로덕션)."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    try:
        from ragas.metrics import answer_correctness as _ac
        return (
            evaluate,
            Dataset,
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            _ac,
            True,
        )
    except ImportError:
        return (
            evaluate,
            Dataset,
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            None,
            False,
        )


@dataclass
class EvaluationResult:
    """Single evaluation result."""
    question_id: str
    question: str
    answer: str
    ground_truth: str
    contexts: List[str]
    
    # Metrics
    groundedness: float  # 근거일치율
    faithfulness: float  # 충실도
    answer_relevancy: float  # 답변 관련성
    context_precision: float  # 컨텍스트 정확도
    context_recall: float  # 컨텍스트 재현율
    
    # Composite score
    overall_score: float


@dataclass
class EvaluationSummary:
    """Summary of evaluation run."""
    run_id: str
    total_questions: int
    avg_groundedness: float
    avg_faithfulness: float
    avg_answer_relevancy: float
    avg_context_precision: float
    avg_context_recall: float
    avg_overall_score: float
    
    # Detailed results
    results: List[EvaluationResult]
    
    # Improvement suggestions
    suggestions: List[str]


class RagasEvaluator:
    """RAG evaluation using Ragas metrics."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,
            api_key=settings.OPENAI_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.db = get_db()
    
    async def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: str
    ) -> Dict[str, float]:
        """Evaluate a single QA pair.
        
        Args:
            question: User question
            answer: Generated answer
            contexts: Retrieved context passages
            ground_truth: Expected correct answer
            
        Returns:
            Dictionary of metric scores
        """
        (
            evaluate,
            Dataset,
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
            has_answer_correctness,
        ) = _load_ragas_eval_deps()
        # Create dataset
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
            "ground_truth": [ground_truth]
        }
        dataset = Dataset.from_dict(data)
        
        # Run evaluation
        metrics_list = [faithfulness, answer_relevancy, context_precision, context_recall]
        if has_answer_correctness and answer_correctness is not None:
            metrics_list.append(answer_correctness)
        try:
            # Ragas evaluate()는 CPU·LLM 동기 호출 → 메인 이벤트 루프 블로킹 방지
            def _run_single_ragas():
                return evaluate(
                    dataset,
                    metrics=metrics_list,
                    llm=self.llm,
                    embeddings=self.embeddings,
                )

            result = await asyncio.to_thread(_run_single_ragas)
            # ragas 0.1.x: dict-like or Result with to_pandas()
            if hasattr(result, "to_pandas"):
                df = result.to_pandas()
                row = df.iloc[0] if len(df) else {}
                scores = {
                    "groundedness": float(row.get("faithfulness", 0)),
                    "faithfulness": float(row.get("faithfulness", 0)),
                    "answer_relevancy": float(row.get("answer_relevancy", 0)),
                    "context_precision": float(row.get("context_precision", 0)),
                    "context_recall": float(row.get("context_recall", 0)),
                    "answer_correctness": float(row.get("answer_correctness", 0)),
                }
            else:
                scores = {
                    "groundedness": (result.get("faithfulness") or [0])[0],
                    "faithfulness": (result.get("faithfulness") or [0])[0],
                    "answer_relevancy": (result.get("answer_relevancy") or [0])[0],
                    "context_precision": (result.get("context_precision") or [0])[0],
                    "context_recall": (result.get("context_recall") or [0])[0],
                    "answer_correctness": (result.get("answer_correctness") or [0])[0],
                }
            
            # Calculate overall score (weighted average)
            scores["overall_score"] = (
                scores["groundedness"] * 0.35 +
                scores["answer_relevancy"] * 0.25 +
                scores["context_precision"] * 0.20 +
                scores["context_recall"] * 0.20
            )
            
            return scores
            
        except Exception as e:
            print(f"Ragas evaluation error: {e}")
            return {
                "groundedness": 0.0,
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
                "answer_correctness": 0.0,
                "overall_score": 0.0
            }
    
    async def evaluate_batch(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> EvaluationSummary:
        """Evaluate a batch of test cases.
        
        Args:
            test_cases: List of {
                "question_id": str,
                "question": str,
                "answer": str,
                "contexts": List[str],
                "ground_truth": str
            }
            
        Returns:
            EvaluationSummary with aggregated metrics
        """
        try:
            (
                evaluate,
                Dataset,
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
                answer_correctness,
                has_answer_correctness,
            ) = _load_ragas_eval_deps()
        except ImportError as e:
            hint = (
                "Ragas/instructor가 현재 openai 패키지와 맞지 않습니다. "
                "골든 평가 CLI: `pip install -r requirements-ragas-compat.txt` 후 재시도. "
                f"원인: {e}"
            )
            logging.error(hint)
            return EvaluationSummary(
                run_id="ragas_import_error",
                total_questions=0,
                avg_groundedness=0.0,
                avg_faithfulness=0.0,
                avg_answer_relevancy=0.0,
                avg_context_precision=0.0,
                avg_context_recall=0.0,
                avg_overall_score=0.0,
                results=[],
                suggestions=[hint],
            )
        results = []
        
        # Create dataset
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        for case in test_cases:
            data["question"].append(case["question"])
            data["answer"].append(case["answer"])
            data["contexts"].append(case.get("contexts", []))
            data["ground_truth"].append(case.get("ground_truth", ""))
        
        dataset = Dataset.from_dict(data)
        
        metrics_batch = [faithfulness, answer_relevancy, context_precision, context_recall]
        if has_answer_correctness and answer_correctness is not None:
            metrics_batch.append(answer_correctness)
        def _run_batch_ragas():
            return evaluate(
                dataset,
                metrics=metrics_batch,
                llm=self.llm,
                embeddings=self.embeddings,
            )

        try:
            ragas_result = await asyncio.to_thread(_run_batch_ragas)
            n = len(test_cases)

            def _to_float(x) -> float:
                """Ragas Score 객체(.value/.score), dict, 또는 스칼라를 float으로 변환."""
                if x is None:
                    return 0.0
                if hasattr(x, "value"):
                    return _to_float(x.value)
                if hasattr(x, "score"):
                    return _to_float(x.score)
                if isinstance(x, dict):
                    v = x.get("score") or x.get("value")
                    return _to_float(v) if v is not None else 0.0
                try:
                    f = float(x)
                    return 0.0 if math.isnan(f) else f
                except (TypeError, ValueError):
                    return 0.0

            def _safe_float_list(val, length: int):
                if val is None:
                    return [0.0] * length
                if isinstance(val, list):
                    out = [_to_float(x) for x in val[:length]]
                    return out + [0.0] * (length - len(out))
                return [0.0] * length

            def _col_from_df(df, possible_names):
                for name in possible_names:
                    if name in df.columns:
                        raw = df[name].tolist()
                        return _safe_float_list(raw, n)
                return [0.0] * n

            def _col_from_scores(scores_list, possible_names):
                out = []
                for row in scores_list:
                    val = None
                    for key in possible_names:
                        if key in row:
                            val = row[key]
                            break
                    if val is None:
                        for k in row:
                            if any(p in str(k).lower() for p in possible_names):
                                val = row[k]
                                break
                    try:
                        f = float(val) if val is not None else 0.0
                        out.append(0.0 if math.isnan(f) else f)
                    except (TypeError, ValueError):
                        out.append(0.0)
                return out[:n] if len(out) >= n else out + [0.0] * (n - len(out))

            # 신규 Ragas: EvaluationResult with .scores (list of dicts) or ._scores_dict (dict of lists)
            if hasattr(ragas_result, "_scores_dict") and getattr(ragas_result, "_scores_dict", None):
                sd = ragas_result._scores_dict
                def _from_sd(keys):
                    for k in keys:
                        if k in sd:
                            return _safe_float_list(sd[k], n)
                    for col in sd:
                        if any(p in col.lower() for p in keys):
                            return _safe_float_list(sd[col], n)
                    return [0.0] * n
                faith_col = _from_sd(["faithfulness"])
                rel_col = _from_sd(["answer_relevancy", "answer_relevance"])
                prec_col = _from_sd(["context_precision", "context_precision_with_reference", "llm_context_precision_with_reference"])
                rec_col = _from_sd(["context_recall"])
            elif hasattr(ragas_result, "scores") and ragas_result.scores:
                scores_list = ragas_result.scores
                faith_col = _col_from_scores(scores_list, ["faithfulness"])
                rel_col = _col_from_scores(scores_list, ["answer_relevancy", "answer_relevance"])
                prec_col = _col_from_scores(scores_list, ["context_precision", "context_precision_with_reference", "llm_context_precision_with_reference"])
                rec_col = _col_from_scores(scores_list, ["context_recall"])
            elif hasattr(ragas_result, "to_pandas"):
                df = ragas_result.to_pandas()
                # DataFrame에서 데이터 컬럼이 아닌 점수 컬럼만 사용 (컬럼명 다양성 대응)
                data_cols = {"question", "answer", "contexts", "ground_truth", "user_input", "response", "retrieved_contexts", "reference"}
                score_cols = [c for c in df.columns if c not in data_cols]
                def _col_by_substring(possible_substrings):
                    for sub in possible_substrings:
                        for c in score_cols:
                            if sub.lower() in c.lower():
                                return _safe_float_list(df[c].tolist(), n)
                    return _col_from_df(df, possible_substrings)
                faith_col = _col_by_substring(["faithfulness"])
                rel_col = _col_by_substring(["answer_relevancy", "answer_relevance"])
                prec_col = _col_by_substring(["context_precision"])
                rec_col = _col_by_substring(["context_recall"])
            else:
                faith_col = _safe_float_list(ragas_result.get("faithfulness"), n)
                rel_col = _safe_float_list(ragas_result.get("answer_relevancy") or ragas_result.get("answer_relevance"), n)
                prec_col = _safe_float_list(ragas_result.get("context_precision"), n)
                rec_col = _safe_float_list(ragas_result.get("context_recall"), n)

            # 지표가 전부 0이면 to_pandas()에서 재추출 (일부 Ragas 버전은 DF에만 실제 값 존재)
            if (sum(faith_col) + sum(rel_col) + sum(prec_col) + sum(rec_col)) == 0 and hasattr(ragas_result, "to_pandas"):
                try:
                    _df = ragas_result.to_pandas()
                    if "faithfulness" in _df.columns:
                        faith_col = _safe_float_list(_df["faithfulness"].tolist(), n)
                    if "answer_relevancy" in _df.columns:
                        rel_col = _safe_float_list(_df["answer_relevancy"].tolist(), n)
                    elif "answer_relevance" in _df.columns:
                        rel_col = _safe_float_list(_df["answer_relevance"].tolist(), n)
                    if "context_precision" in _df.columns:
                        prec_col = _safe_float_list(_df["context_precision"].tolist(), n)
                    if "context_recall" in _df.columns:
                        rec_col = _safe_float_list(_df["context_recall"].tolist(), n)
                except Exception as _e:
                    print("[DEBUG] to_pandas() fallback failed:", _e)

            # Convert to EvaluationResult objects
            for i, case in enumerate(test_cases):
                g = faith_col[i] if i < len(faith_col) else 0
                f = faith_col[i] if i < len(faith_col) else 0
                ar = rel_col[i] if i < len(rel_col) else 0
                cp = prec_col[i] if i < len(prec_col) else 0
                cr = rec_col[i] if i < len(rec_col) else 0
                result = EvaluationResult(
                    question_id=case.get("question_id", f"q{i}"),
                    question=case["question"],
                    answer=case["answer"],
                    ground_truth=case.get("ground_truth", ""),
                    contexts=case.get("contexts", []),
                    groundedness=g,
                    faithfulness=f,
                    answer_relevancy=ar,
                    context_precision=cp,
                    context_recall=cr,
                    overall_score=0.0
                )
                
                # Calculate overall score
                result.overall_score = (
                    result.groundedness * 0.35 +
                    result.answer_relevancy * 0.25 +
                    result.context_precision * 0.20 +
                    result.context_recall * 0.20
                )
                
                results.append(result)
            
        except Exception as e:
            print(f"Batch evaluation error: {e}")
        
        # Calculate summary statistics
        if results:
            summary = EvaluationSummary(
                run_id=f"run_{time.time():.3f}",
                total_questions=len(results),
                avg_groundedness=sum(r.groundedness for r in results) / len(results),
                avg_faithfulness=sum(r.faithfulness for r in results) / len(results),
                avg_answer_relevancy=sum(r.answer_relevancy for r in results) / len(results),
                avg_context_precision=sum(r.context_precision for r in results) / len(results),
                avg_context_recall=sum(r.context_recall for r in results) / len(results),
                avg_overall_score=sum(r.overall_score for r in results) / len(results),
                results=results,
                suggestions=self._generate_suggestions(results)
            )
        else:
            summary = EvaluationSummary(
                run_id="error",
                total_questions=0,
                avg_groundedness=0.0,
                avg_faithfulness=0.0,
                avg_answer_relevancy=0.0,
                avg_context_precision=0.0,
                avg_context_recall=0.0,
                avg_overall_score=0.0,
                results=[],
                suggestions=["Evaluation failed"]
            )
        
        # Save to database
        await self._save_evaluation_summary(summary)
        
        return summary
    
    def _generate_suggestions(self, results: List[EvaluationResult]) -> List[str]:
        """Generate improvement suggestions based on evaluation results."""
        suggestions = []
        
        # Check groundedness
        avg_groundedness = sum(r.groundedness for r in results) / len(results)
        if avg_groundedness < 0.7:
            suggestions.append(
                f"근거일치율(Groundedness)이 낮습니다 ({avg_groundedness:.2f}). "
                "검색 결과와 답변 간의 일치도를 높이기 위해 리랭커를 개선하세요."
            )
        
        # Check context precision
        avg_precision = sum(r.context_precision for r in results) / len(results)
        if avg_precision < 0.6:
            suggestions.append(
                f"컨텍스트 정확도(Context Precision)가 낮습니다 ({avg_precision:.2f}). "
                "검색 알고리즘의 정확성을 개선하세요."
            )
        
        # Check context recall
        avg_recall = sum(r.context_recall for r in results) / len(results)
        if avg_recall < 0.6:
            suggestions.append(
                f"컨텍스트 재현율(Context Recall)이 낮습니다 ({avg_recall:.2f}). "
                "검색 결과에 필요한 정보가 모두 포함되도록 top_k 값을 늘리세요."
            )
        
        # Check answer relevancy
        avg_relevancy = sum(r.answer_relevancy for r in results) / len(results)
        if avg_relevancy < 0.7:
            suggestions.append(
                f"답변 관련성(Answer Relevancy)이 낮습니다 ({avg_relevancy:.2f}). "
                "프롬프트 엔지니어링을 통해 질문과 관련 없는 내용을 줄이세요."
            )
        
        if not suggestions:
            suggestions.append("전반적인 성능이 양호합니다. 지속적인 모니터링을 권장합니다.")
        
        return suggestions
    
    async def _save_evaluation_summary(self, summary: EvaluationSummary):
        """Save evaluation summary to database."""
        try:
            # Insert run
            run_data = {
                "run_name": summary.run_id,
                "system_variant": "ragas_eval",
                "model": settings.OPENAI_MODEL
            }
            run_result = self.db.table("eval_runs").insert(run_data).execute()
            
            if run_result.data:
                run_id = run_result.data[0]["run_id"]
                
                # Insert results
                # eval_results 스키마(dashboard/governance 기준): run_id, metric_groundedness, metric_citation_precision, metric_hallucination_rate
                for result in summary.results:
                    result_data = {
                        "run_id": run_id,
                        "metric_groundedness": result.groundedness,
                        "metric_citation_precision": result.context_precision,
                        "metric_hallucination_rate": 1.0 - result.faithfulness,
                    }
                    try:
                        self.db.table("eval_results").insert(result_data).execute()
                    except Exception as ins_err:
                        print(f"Insert warning (schema may differ): {ins_err}")
        
        except Exception as e:
            print(f"Error saving evaluation: {e}")
    
    async def compare_systems(
        self,
        test_cases: List[Dict[str, Any]],
        system_variants: List[str]
    ) -> Dict[str, EvaluationSummary]:
        """Compare multiple system variants.
        
        Args:
            test_cases: Test cases with answers from different systems
            system_variants: List of system variant names
            
        Returns:
            Dictionary mapping variant name to EvaluationSummary
        """
        results = {}
        
        for variant in system_variants:
            # Extract answers for this variant
            variant_cases = []
            for case in test_cases:
                if variant in case.get("answers", {}):
                    variant_cases.append({
                        "question_id": case["question_id"],
                        "question": case["question"],
                        "answer": case["answers"][variant],
                        "contexts": case.get("contexts", {}).get(variant, []),
                        "ground_truth": case.get("ground_truth", "")
                    })
            
            if variant_cases:
                summary = await self.evaluate_batch(variant_cases)
                results[variant] = summary
        
        return results


# ============ Custom Metrics ============

async def calculate_groundedness(
    answer: str,
    contexts: List[str]
) -> float:
    """Calculate groundedness score.
    
    Measures what percentage of statements in the answer
    are supported by the retrieved contexts.
    """
    if not contexts:
        return 0.0
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    prompt = f"""다음 답변의 각 문장이 제공된 컨텍스트에서 지지되는지 판단하세요.

컨텍스트:
{chr(10).join([f"{i+1}. {ctx[:500]}" for i, ctx in enumerate(contexts)])}

답변:
{answer}

응답 형식 (JSON):
{{
    "statements": [
        {{"text": "문장1", "supported": true/false}},
        ...
    ],
    "groundedness_score": 0.0-1.0  # 지지되는 문장 비율
}}
"""
    
    try:
        response = await llm.ainvoke(prompt)
        result = json.loads(response.content)
        return result.get("groundedness_score", 0.0)
    except:
        return 0.0


async def calculate_hallucination_rate(
    answer: str,
    contexts: List[str]
) -> float:
    """Calculate hallucination rate.
    
    Measures what percentage of statements in the answer
    are NOT supported by the retrieved contexts.
    """
    groundedness = await calculate_groundedness(answer, contexts)
    return 1 - groundedness


# ============ Public API ============

_evaluator: Optional[RagasEvaluator] = None

def get_evaluator() -> RagasEvaluator:
    """Get singleton evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = RagasEvaluator()
    return _evaluator
