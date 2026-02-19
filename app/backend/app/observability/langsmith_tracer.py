"""LangSmith Observability Integration.

Traces and monitors:
- Query classification
- Retrieval steps
- LLM calls
- Verification loops
- Performance metrics
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from langsmith import Client
from langsmith.run_trees import RunTree
from langchain.callbacks.tracers.langchain import LangChainTracer
from langchain_core.callbacks import Callbacks

from app.core.config import settings


class LangSmithTracer:
    """LangSmith tracer for RAG system observability."""
    
    def __init__(self):
        self.client = None
        self.tracer = None
        
        if settings.LANGSMITH_API_KEY:
            # Set environment variables for LangSmith
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            
            # Initialize client
            self.client = Client(
                api_key=settings.LANGSMITH_API_KEY,
                api_url=settings.LANGSMITH_ENDPOINT
            )
            
            # Initialize tracer
            self.tracer = LangChainTracer(
                project_name=settings.LANGSMITH_PROJECT
            )
    
    def is_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled."""
        return self.client is not None and getattr(settings, 'ENABLE_TRACING', False)
    
    def create_run(
        self,
        name: str,
        run_type: str = "chain",
        inputs: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None
    ) -> Optional[RunTree]:
        """Create a new run for tracing.
        
        Args:
            name: Run name
            run_type: Type of run (chain, llm, retriever, etc.)
            inputs: Input data
            parent_run_id: Parent run ID for nested runs
            
        Returns:
            RunTree object or None if tracing disabled
        """
        if not self.is_enabled():
            return None
        
        try:
            run = RunTree(
                name=name,
                run_type=run_type,
                inputs=inputs or {},
                extra={
                    "metadata": {
                        "project": settings.LANGSMITH_PROJECT,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            
            if parent_run_id:
                run.parent_run_id = parent_run_id
            
            run.post()
            return run
            
        except Exception as e:
            print(f"Error creating LangSmith run: {e}")
            return None
    
    def end_run(
        self,
        run: Optional[RunTree],
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """End a run with outputs or error.
        
        Args:
            run: RunTree object
            outputs: Output data
            error: Error message if failed
        """
        if not run:
            return
        
        try:
            if error:
                run.end(error=error)
            else:
                run.end(outputs=outputs or {})
            run.patch()
        except Exception as e:
            print(f"Error ending LangSmith run: {e}")
    
    def trace_rag_pipeline(
        self,
        query: str,
        query_type: str,
        retrieved_chunks: List[Dict[str, Any]],
        answer: str,
        confidence: float,
        latency_ms: int
    ) -> Optional[str]:
        """Trace a complete RAG pipeline execution.
        
        Args:
            query: User query
            query_type: Classified query type
            retrieved_chunks: Retrieved document chunks
            answer: Generated answer
            confidence: Confidence score
            latency_ms: Total latency in milliseconds
            
        Returns:
            Run ID if tracing enabled
        """
        if not self.is_enabled():
            return None
        
        try:
            # Create main run
            main_run = self.create_run(
                name="rag_pipeline",
                run_type="chain",
                inputs={"query": query}
            )
            
            if not main_run:
                return None
            
            # Trace query classification
            self._trace_classification(main_run.id, query, query_type)
            
            # Trace retrieval
            self._trace_retrieval(main_run.id, query, retrieved_chunks)
            
            # Trace generation
            self._trace_generation(main_run.id, query, retrieved_chunks, answer)
            
            # End main run
            self.end_run(
                main_run,
                outputs={
                    "answer": answer,
                    "confidence": confidence,
                    "query_type": query_type
                }
            )
            
            # Add feedback
            self.client.create_feedback(
                main_run.id,
                key="latency_ms",
                score=latency_ms,
                comment=f"Total pipeline latency: {latency_ms}ms"
            )
            
            return main_run.id
            
        except Exception as e:
            print(f"Error tracing RAG pipeline: {e}")
            return None
    
    def _trace_classification(
        self,
        parent_run_id: str,
        query: str,
        query_type: str
    ):
        """Trace query classification step."""
        run = self.create_run(
            name="query_classification",
            run_type="chain",
            inputs={"query": query},
            parent_run_id=parent_run_id
        )
        
        if run:
            self.end_run(
                run,
                outputs={"query_type": query_type}
            )
    
    def _trace_retrieval(
        self,
        parent_run_id: str,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ):
        """Trace retrieval step."""
        run = self.create_run(
            name="document_retrieval",
            run_type="retriever",
            inputs={"query": query},
            parent_run_id=parent_run_id
        )
        
        if run:
            self.end_run(
                run,
                outputs={
                    "chunks": [
                        {
                            "chunk_id": c.get("chunk_id"),
                            "document_title": c.get("document_title"),
                            "similarity": c.get("similarity", 0)
                        }
                        for c in retrieved_chunks
                    ],
                    "chunk_count": len(retrieved_chunks)
                }
            )
    
    def _trace_generation(
        self,
        parent_run_id: str,
        query: str,
        contexts: List[Dict[str, Any]],
        answer: str
    ):
        """Trace LLM generation step."""
        run = self.create_run(
            name="answer_generation",
            run_type="llm",
            inputs={
                "query": query,
                "contexts": [c.get("chunk_text", "")[:500] for c in contexts]
            },
            parent_run_id=parent_run_id
        )
        
        if run:
            self.end_run(
                run,
                outputs={"answer": answer}
            )
    
    def trace_agent_workflow(
        self,
        query: str,
        iterations: List[Dict[str, Any]],
        final_result: Dict[str, Any]
    ) -> Optional[str]:
        """Trace LangGraph agent workflow.
        
        Args:
            query: User query
            iterations: List of iteration data
            final_result: Final workflow result
            
        Returns:
            Run ID
        """
        if not self.is_enabled():
            return None
        
        try:
            main_run = self.create_run(
                name="agent_workflow",
                run_type="chain",
                inputs={"query": query}
            )
            
            if not main_run:
                return None
            
            # Trace each iteration
            for i, iteration in enumerate(iterations):
                iter_run = self.create_run(
                    name=f"iteration_{i+1}",
                    run_type="chain",
                    inputs={"step": iteration.get("step")},
                    parent_run_id=main_run.id
                )
                
                if iter_run:
                    self.end_run(
                        iter_run,
                        outputs={
                            "result": iteration.get("result"),
                            "confidence": iteration.get("confidence")
                        }
                    )
            
            # End main run
            self.end_run(
                main_run,
                outputs=final_result
            )
            
            return main_run.id
            
        except Exception as e:
            print(f"Error tracing agent workflow: {e}")
            return None
    
    def add_feedback(
        self,
        run_id: str,
        key: str,
        score: float,
        comment: Optional[str] = None
    ):
        """Add feedback to a run.
        
        Args:
            run_id: Run ID
            key: Feedback key (e.g., "user_rating", "groundedness")
            score: Score value
            comment: Optional comment
        """
        if not self.is_enabled():
            return
        
        try:
            self.client.create_feedback(
                run_id,
                key=key,
                score=score,
                comment=comment
            )
        except Exception as e:
            print(f"Error adding feedback: {e}")
    
    def get_run_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get run statistics.
        
        Args:
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            Statistics dictionary
        """
        if not self.is_enabled():
            return {"error": "LangSmith not enabled"}
        
        try:
            # Query runs
            runs = list(self.client.list_runs(
                project_name=settings.LANGSMITH_PROJECT,
                start_time=start_time,
                end_time=end_time,
                execution_order=1  # Only root runs
            ))
            
            # Calculate stats
            total_runs = len(runs)
            avg_latency = sum(
                (r.end_time - r.start_time).total_seconds() * 1000
                for r in runs if r.end_time and r.start_time
            ) / total_runs if total_runs > 0 else 0
            
            error_count = sum(1 for r in runs if r.error)
            
            return {
                "total_runs": total_runs,
                "avg_latency_ms": avg_latency,
                "error_count": error_count,
                "error_rate": error_count / total_runs if total_runs > 0 else 0,
                "runs": [
                    {
                        "id": r.id,
                        "name": r.name,
                        "status": "error" if r.error else "success",
                        "latency_ms": (r.end_time - r.start_time).total_seconds() * 1000
                        if r.end_time and r.start_time else None
                    }
                    for r in runs[:10]  # Last 10 runs
                ]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def export_traces(
        self,
        output_path: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ):
        """Export traces to JSON file.
        
        Args:
            output_path: Output file path
            start_time: Start time filter
            end_time: End time filter
        """
        if not self.is_enabled():
            print("LangSmith not enabled")
            return
        
        try:
            runs = list(self.client.list_runs(
                project_name=settings.LANGSMITH_PROJECT,
                start_time=start_time,
                end_time=end_time
            ))
            
            traces = []
            for run in runs:
                traces.append({
                    "id": str(run.id),
                    "name": run.name,
                    "run_type": run.run_type,
                    "start_time": run.start_time.isoformat() if run.start_time else None,
                    "end_time": run.end_time.isoformat() if run.end_time else None,
                    "inputs": run.inputs,
                    "outputs": run.outputs,
                    "error": run.error,
                    "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(traces, f, ensure_ascii=False, indent=2)
            
            print(f"Exported {len(traces)} traces to {output_path}")
            
        except Exception as e:
            print(f"Error exporting traces: {e}")


# ============ Decorator for Easy Tracing ============

def trace_function(name: Optional[str] = None):
    """Decorator to trace function execution.
    
    Usage:
        @trace_function("my_function")
        async def my_function():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            run_name = name or func.__name__
            
            run = tracer.create_run(
                name=run_name,
                run_type="chain",
                inputs={"args": str(args), "kwargs": str(kwargs)}
            )
            
            try:
                result = await func(*args, **kwargs)
                tracer.end_run(run, outputs={"result": str(result)})
                return result
            except Exception as e:
                tracer.end_run(run, error=str(e))
                raise
        
        return wrapper
    return decorator


# ============ Public API ============

_tracer: Optional[LangSmithTracer] = None

def get_tracer() -> LangSmithTracer:
    """Get singleton tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = LangSmithTracer()
    return _tracer

def get_callbacks() -> Optional[Callbacks]:
    """Get LangChain callbacks for tracing."""
    tracer = get_tracer()
    if tracer.is_enabled() and tracer.tracer:
        return [tracer.tracer]
    return None
