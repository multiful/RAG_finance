"""Governance Evaluation Pipeline."""
import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.database import get_db
import openai

class EvaluationPipeline:
    """Async pipeline for computing governance metrics."""

    def __init__(self):
        self.db = get_db()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def run_batch_evaluation(self, limit: int = 10) -> Dict[str, int]:
        """Process pending QA logs and compute metrics."""
        sql = f"""
            SELECT q.* FROM qa_logs q 
            LEFT JOIN eval_results e ON q.qa_id = e.qa_id 
            WHERE e.result_id IS NULL 
            ORDER BY q.created_at DESC
            LIMIT {limit}
        """
        res = self.db.rpc("exec_sql", {"sql": sql}).execute()
        
        if not res.data:
            return {"processed": 0}

        run_res = self.db.table("eval_runs").insert({
            "run_name": f"auto_{datetime.now().isoformat()}",
            "model": "gpt-3.5-turbo"
        }).execute()
        run_id = run_res.data[0]["run_id"]

        processed = 0
        for log in res.data:
            try:
                m = await self._evaluate_single_log(log)
                self.db.table("eval_results").insert({
                    "qa_id": log["qa_id"], 
                    "run_id": run_id,
                    "metric_groundedness": m["groundedness"],
                    "metric_citation_precision": m["citation_precision"],
                    "metric_hallucination_rate": m["hallucination_rate"],
                    "notes": json.dumps(m["details"])
                }).execute()
                processed += 1
            except Exception as e:
                print(f"Eval Error for QA {log['qa_id']}: {e}")
        
        return {"processed": processed}

    async def _evaluate_single_log(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """Compute metrics for a single QA interaction."""
        answer = log.get("answer", "")
        citations = log.get("citations") or []
        chunk_ids = log.get("retrieved_chunk_ids") or []
        
        # 1. Basic check
        if not chunk_ids:
             return {
                "groundedness": 0.0, "citation_precision": 0.0, 
                "hallucination_rate": 1.0, "details": {"reason": "No chunks"}
            }

        # 2. Citation Precision
        if not citations:
            precision = 0.0 if "출처" in answer else 1.0
        else:
            valid = sum(1 for c in citations if c.get("chunk_id") in chunk_ids)
            precision = valid / len(citations)

        # 3. Groundedness (LLM-as-Judge)
        sentences = [s.strip() for s in re.split(r'[.?!]\s+', answer) if len(s.strip()) > 15]
        if not sentences:
             return {
                "groundedness": 1.0, "citation_precision": precision, 
                "hallucination_rate": 0.0, "details": {"reason": "Too short"}
            }

        chunks_res = self.db.table("chunks").select("chunk_text").in_("chunk_id", chunk_ids).execute()
        context = "\n\n".join([c["chunk_text"] for c in (chunks_res.data or [])])[:3500]

        prompt = f"""Evaluate if each statement is supported by the context.
Context:
{context}

Statements:
{json.dumps(sentences, ensure_ascii=False)}

Return JSON: {{"results": [true, false, ...]}} matching the statements."""

        groundedness = 0.0
        try:
            resp = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            results = data.get("results") or []
            if results:
                groundedness = sum(1 for x in results if x is True) / len(results)
        except Exception as e:
            print(f"LLM Judge Error: {e}")

        return {
            "groundedness": groundedness,
            "citation_precision": precision,
            "hallucination_rate": 1.0 - groundedness,
            "details": {"sentences": len(sentences)}
        }

pipeline = EvaluationPipeline()
