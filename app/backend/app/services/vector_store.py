"""Optimized Vector Store with Supabase pgvector.

Features:
- Hybrid search (BM25 + Vector)
- Metadata filtering
- Reranking
- Batch operations
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from app.core.config import settings
from app.core.database import get_db


@dataclass
class SearchResult:
    """Search result item."""
    chunk_id: str
    document_id: str
    chunk_text: str
    chunk_index: int
    document_title: str
    published_at: str
    url: str
    similarity: float
    metadata: Dict[str, Any]
    parsing_source: Optional[str] = None  # e.g. "llamaparse_v1", "pdfplumber"


class VectorStore:
    """Optimized vector store with hybrid search."""
    
    def __init__(self):
        self.db = get_db()
        self.dimension = settings.VECTOR_DIMENSION
    
    async def add_embeddings(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        embedding_model: str = "text-embedding-3-small"
    ) -> bool:
        """Add embeddings in batch.
        
        Args:
            chunk_ids: List of chunk IDs
            embeddings: List of embedding vectors
            embedding_model: Model name
            
        Returns:
            True if successful
        """
        try:
            data = [
                {
                    "chunk_id": chunk_id,
                    "embedding_model": embedding_model,
                    "embedding": json.dumps(embedding)
                }
                for chunk_id, embedding in zip(chunk_ids, embeddings)
            ]
            
            self.db.table("embeddings").upsert(data).execute()
            return True
            
        except Exception as e:
            print(f"Error adding embeddings: {e}")
            return False
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Pure vector similarity search using match_chunks_v3 RPC."""
        try:
            print(f"DEBUG: Starting similarity search (dims={len(query_embedding)})")
            
            # Use the RPC to avoid selecting the embedding column directly
            # and to handle computed similarity server-side
            rpc_params = {
                "query_embedding": query_embedding,
                "match_count": top_k
            }
            
            # PostgREST RPC call
            result = self.db.rpc("match_chunks_v3", rpc_params).execute()
            
            if not result.data:
                print("DEBUG: match_chunks_v3 returned 0 rows.")
                return []
            
            print(f"DEBUG: Vector search found {len(result.data)} raw hits.")
            
            results = []
            for item in result.data:
                results.append(SearchResult(
                    chunk_id=item.get("chunk_id"),
                    document_id=item.get("document_id"),
                    chunk_text=item.get("chunk_text"),
                    chunk_index=item.get("chunk_index"),
                    document_title=item.get("document_title", "Unknown"),
                    published_at=item.get("published_at"),
                    url=item.get("url"),
                    similarity=item.get("similarity", 0.0),
                    metadata=item.get("metadata") or {},
                    parsing_source=item.get("chunking_version"),
                ))
            return results
            
        except Exception as e:
            print(f"ERROR: Similarity search failed: {e}")
            return []

    @staticmethod
    def _escape_sql_literal(value: str, max_len: int = 500) -> str:
        """SQL 인젝션 방지: 작은따옴표 이중 이스케이프, 길이 제한."""
        if not value:
            return ""
        s = str(value)[:max_len].replace("\\", "\\\\").replace("'", "''")
        return s

    async def bm25_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Trigram-based and FTS keyword search with better acronym handling."""
        try:
            print(f"DEBUG: Starting keyword search for: '{query}'")
            top_k = max(1, min(100, int(top_k)))
            safe_query = self._escape_sql_literal(query)
            if not safe_query.strip():
                return await self._fallback_keyword_search(query, top_k, filters)
            clean_query = re.sub(r"[^\w\s]", "", query)
            fts_parts = [w for w in clean_query.split() if len(w) > 0]
            fts_query = " | ".join(fts_parts) if fts_parts else safe_query
            fts_safe = self._escape_sql_literal(fts_query)

            sql = f"""
                WITH matches AS (
                    SELECT 
                        c.chunk_id,
                        c.document_id,
                        c.chunk_text,
                        c.chunk_index,
                        c.chunking_version,
                        d.title as document_title,
                        d.published_at,
                        d.url,
                        (
                            similarity(c.chunk_text, '{safe_query}') * 0.4 +
                            ts_rank_cd(to_tsvector('simple', c.chunk_text), to_tsquery('simple', '{fts_safe}')) * 0.6
                        ) as combined_score
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.document_id
                    WHERE 
                        c.chunk_text % '{safe_query}'
                        OR c.chunk_text ILIKE '%' || '{safe_query}' || '%'
                        OR to_tsvector('simple', c.chunk_text) @@ to_tsquery('simple', '{fts_safe}')
                )
                SELECT * FROM matches ORDER BY combined_score DESC LIMIT {top_k}
            """
            result = self.db.rpc("exec_sql", {"sql": sql}).execute()
            
            if not result.data:
                return await self._fallback_keyword_search(query, top_k, filters)
                
            return self._parse_bm25_results(result.data)
            
        except Exception as e:
            print(f"BM25/Trigram error: {e}")
            return await self._fallback_keyword_search(query, top_k, filters)

    async def _fallback_keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Fallback keyword search using liberal ILIKE word matching."""
        try:
            print(f"DEBUG: Falling back to word-based ILIKE for: '{query}'")
            
            # Split query into words and build a liberal search
            words = [w for w in query.split() if len(w) > 1]
            if not words: words = [query]
            
            db_query = self.db.table("chunks").select(
                "chunk_id, document_id, chunk_text, chunk_index, documents!inner(title, published_at, url)"
            )
            
            # Use the first two words for an OR condition to increase recall
            if len(words) >= 2:
                filter_str = f"chunk_text.ilike.%{words[0]}%,chunk_text.ilike.%{words[1]}%"
                result = db_query.or_(filter_str).limit(top_k).execute()
            else:
                result = db_query.ilike("chunk_text", f"%{words[0]}%").limit(top_k).execute()
            
            results = []
            for item in (result.data or []):
                doc = item.get("documents", {})
                results.append(SearchResult(
                    chunk_id=item["chunk_id"],
                    document_id=item["document_id"],
                    chunk_text=item["chunk_text"],
                    chunk_index=item["chunk_index"],
                    document_title=doc.get("title", "Unknown"),
                    published_at=doc.get("published_at"),
                    url=doc.get("url"),
                    similarity=0.1,
                    metadata={}
                ))
            
            print(f"DEBUG: Fallback word search found {len(results)} results.")
            return results
            
        except Exception as e:
            print(f"Fallback search fatal error: {e}")
            return []
    
    def _normalize_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """Normalize scores to [0, 1] using Min-Max scaling."""
        if not results:
            return []
        
        scores = [r.similarity for r in results]
        min_s = min(scores)
        max_s = max(scores)
        
        if max_s == min_s:
            for r in results:
                r.similarity = 1.0 if max_s > 0 else 0.0
            return results
            
        for r in results:
            r.similarity = (r.similarity - min_s) / (max_s - min_s)
            
        return results

    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        similarity_threshold: float = 0.3, # Minimum normalized similarity
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Hybrid search combining vector and keyword search.
        
        Args:
            query: Text query for keyword search
            query_embedding: Embedding for vector search
            top_k: Number of results
            vector_weight: Weight for vector scores (0-1)
            keyword_weight: Weight for keyword scores (0-1)
            similarity_threshold: Drop results below this
            filters: Optional metadata filters
            
        Returns:
            List of search results sorted by combined score
        """
        # 1. Run searches in parallel
        vector_results = await self.similarity_search(
            query_embedding, top_k * 3, filters
        )
        keyword_results = await self.bm25_search(
            query, top_k * 3, filters
        )
        
        # 2. Normalize scores for each set
        vector_results = self._normalize_scores(vector_results)
        keyword_results = self._normalize_scores(keyword_results)
        
        print(f"DEBUG: Hybrid combining {len(vector_results)} vector vs {len(keyword_results)} keyword results.")
        
        # 3. Combine results using Reciprocal Rank Fusion (RRF)
        combined = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            vector_weight,
            keyword_weight
        )
        
        # 4. Filter by threshold
        # RRF scores are usually low, so we normalize the final scores again for the threshold
        final_results = self._normalize_scores(combined)
        filtered = [r for r in final_results if r.similarity >= similarity_threshold]
        
        print(f"DEBUG: Hybrid filtered {len(final_results)} -> {len(filtered)} results (threshold={similarity_threshold})")
        return filtered[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float,
        keyword_weight: float,
        k: int = 60
    ) -> List[SearchResult]:
        """Combine results using Reciprocal Rank Fusion.
        
        RRF score = Σ (weight / (k + rank))
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            vector_weight: Weight for vector results
            keyword_weight: Weight for keyword results
            k: RRF constant
            
        Returns:
            Combined and re-ranked results
        """
        # Create score dictionary
        scores: Dict[str, float] = {}
        result_map: Dict[str, SearchResult] = {}
        
        # Add vector scores
        for rank, result in enumerate(vector_results):
            chunk_id = result.chunk_id
            rrf_score = vector_weight / (k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
            result_map[chunk_id] = result
        
        # Add keyword scores
        for rank, result in enumerate(keyword_results):
            chunk_id = result.chunk_id
            rrf_score = keyword_weight / (k + rank + 1)
            scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
            if chunk_id not in result_map:
                result_map[chunk_id] = result
        
        # Sort by RRF score
        sorted_chunks = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create final results
        results = []
        for chunk_id, score in sorted_chunks:
            result = result_map[chunk_id]
            result.similarity = score
            results.append(result)
        
        return results
    
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """Rerank results using cross-encoder.
        
        Args:
            query: Original query
            results: Initial search results
            top_k: Number of results after reranking
            
        Returns:
            Reranked results
        """
        if not results:
            return []
        
        print(f"DEBUG: Reranking {len(results)} results using cross-encoder...")
        try:
            from sentence_transformers import CrossEncoder
            
            # Load cross-encoder (cached)
            model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            # Create query-document pairs
            pairs = [
                (query, result.chunk_text[:512])
                for result in results
            ]
            
            # Get scores
            scores = model.predict(pairs)
            
            # Update results with new scores
            for result, score in zip(results, scores):
                result.similarity = float(score)
            
            # Sort by new scores
            results.sort(key=lambda x: x.similarity, reverse=True)
            
            print(f"DEBUG: Reranking complete. Top score: {results[0].similarity if results else 'N/A'}")
            return results[:top_k]
            
        except Exception as e:
            print(f"Reranking error: {e}")
            # Return original results if reranking fails
            return results[:top_k]
    
    def _parse_search_results(self, data: List[Dict]) -> List[SearchResult]:
        """Parse database results to SearchResult objects."""
        results = []
        
        for item in data:
            doc = item.get("documents", {})
            
            results.append(SearchResult(
                chunk_id=item.get("chunk_id", ""),
                document_id=item.get("document_id", ""),
                chunk_text=item.get("chunk_text", ""),
                chunk_index=item.get("chunk_index", 0),
                document_title=doc.get("title", "Unknown"),
                published_at=doc.get("published_at", ""),
                url=doc.get("url", ""),
                similarity=0.5,
                metadata={
                    "category": doc.get("category"),
                    "department": doc.get("department"),
                },
                parsing_source=item.get("chunking_version"),
            ))
        
        return results
    
    def _parse_bm25_results(self, data: List[Dict]) -> List[SearchResult]:
        """Parse BM25 search results."""
        results = []
        for item in data:
            results.append(SearchResult(
                chunk_id=item.get("chunk_id", ""),
                document_id=item.get("document_id", ""),
                chunk_text=item.get("chunk_text", ""),
                chunk_index=item.get("chunk_index", 0),
                document_title=item.get("document_title", ""),
                published_at=item.get("published_at", ""),
                url=item.get("url", ""),
                similarity=item.get("combined_score", item.get("similarity", 0.0)),
                metadata={
                    "category": item.get("category"),
                    "department": item.get("department"),
                },
                parsing_source=item.get("chunking_version"),
            ))
        return results
    
    async def delete_document_embeddings(self, document_id: str) -> bool:
        """Delete all embeddings for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful
        """
        try:
            # Get chunk IDs
            chunks = self.db.table("chunks").select("chunk_id").eq(
                "document_id", document_id
            ).execute()
            
            if chunks.data:
                chunk_ids = [c["chunk_id"] for c in chunks.data]
                
                # Delete embeddings
                self.db.table("embeddings").delete().in_(
                    "chunk_id", chunk_ids
                ).execute()
            
            return True
            
        except Exception as e:
            print(f"Error deleting embeddings: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        try:
            # Total chunks
            chunks_count = self.db.table("chunks").select(
                "count", count="exact"
            ).execute()
            
            # Total embeddings
            embeddings_count = self.db.table("embeddings").select(
                "count", count="exact"
            ).execute()
            
            # Documents with embeddings
            docs_with_embeddings = self.db.rpc(
                "count_documents_with_embeddings"
            ).execute()
            
            return {
                "total_chunks": chunks_count.count if hasattr(chunks_count, 'count') else 0,
                "total_embeddings": embeddings_count.count if hasattr(embeddings_count, 'count') else 0,
                "documents_with_embeddings": docs_with_embeddings.data or 0
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                "total_chunks": 0,
                "total_embeddings": 0,
                "documents_with_embeddings": 0
            }


# ============ Public API ============

_vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    """Get singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
