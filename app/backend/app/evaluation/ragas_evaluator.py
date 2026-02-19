"""Ragas-based RAG Evaluation System.

Provides quantitative metrics for:
- Groundedness (근거일치율)
- Answer Relevance
- Context Precision
- Context Recall
- Faithfulness
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_similarity,
    answer_correctness
)
from datasets import Dataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.core.database import get_db


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
        # Create dataset
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
            "ground_truth": [ground_truth]
        }
        dataset = Dataset.from_dict(data)
        
        # Run evaluation
        try:
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    answer_correctness
                ],
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            # Extract scores
            scores = {
                "groundedness": result.get("faithfulness", [0])[0],
                "faithfulness": result.get("faithfulness", [0])[0],
                "answer_relevancy": result.get("answer_relevancy", [0])[0],
                "context_precision": result.get("context_precision", [0])[0],
                "context_recall": result.get("context_recall", [0])[0],
                "answer_correctness": result.get("answer_correctness", [0])[0]
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
        
        # Run evaluation
        try:
            ragas_result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    answer_correctness
                ],
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            # Convert to EvaluationResult objects
            for i, case in enumerate(test_cases):
                result = EvaluationResult(
                    question_id=case.get("question_id", f"q{i}"),
                    question=case["question"],
                    answer=case["answer"],
                    ground_truth=case.get("ground_truth", ""),
                    contexts=case.get("contexts", []),
                    groundedness=ragas_result.get("faithfulness", [0] * len(test_cases))[i],
                    faithfulness=ragas_result.get("faithfulness", [0] * len(test_cases))[i],
                    answer_relevancy=ragas_result.get("answer_relevancy", [0] * len(test_cases))[i],
                    context_precision=ragas_result.get("context_precision", [0] * len(test_cases))[i],
                    context_recall=ragas_result.get("context_recall", [0] * len(test_cases))[i],
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
                run_id=f"run_{asyncio.get_event_loop().time()}",
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
                for result in summary.results:
                    result_data = {
                        "run_id": run_id,
                        "question_id": result.question_id,
                        "metric_groundedness": result.groundedness,
                        "metric_hallucination": 1 - result.faithfulness,  # Hallucination is inverse of faithfulness
                        "metric_industry_f1": result.overall_score,
                        "metric_checklist_missing": 0.0,  # Not applicable for QA
                        "notes": json.dumps({
                            "answer_relevancy": result.answer_relevancy,
                            "context_precision": result.context_precision,
                            "context_recall": result.context_recall
                        })
                    }
                    self.db.table("eval_results").insert(result_data).execute()
        
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
