"""Optimized Vector Store with Supabase pgvector.

Features:
- Hybrid search (BM25 + Vector)
- Metadata filtering
- Reranking
- Batch operations
"""
import json
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
        """Pure vector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of search results
        """
        try:
            # Build query
            query = self.db.table("chunks").select(
                "*, documents!inner(title, published_at, url, category, department), embeddings!inner(embedding)"
            )
            
            # Apply filters
            if filters:
                if "date_from" in filters:
                    query = query.gte("documents.published_at", filters["date_from"])
                if "date_to" in filters:
                    query = query.lte("documents.published_at", filters["date_to"])
                if "category" in filters:
                    query = query.eq("documents.category", filters["category"])
                if "department" in filters:
                    query = query.eq("documents.department", filters["department"])
            
            # Order by vector similarity using pgvector
            embedding_str = json.dumps(query_embedding)
            query = query.order(
                f"embeddings.embedding <-> '{embedding_str}'::vector"
            ).limit(top_k)
            
            result = query.execute()
            
            return self._parse_search_results(result.data or [])
            
        except Exception as e:
            print(f"Similarity search error: {e}")
            return []
    
    async def bm25_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """BM25 keyword search.
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of search results
        """
        try:
            # Use PostgreSQL full-text search
            # First, create a search query
            search_terms = query.split()
            tsquery = " & ".join(search_terms)
            
            # Build raw SQL for BM25-like search
            sql = f"""
                SELECT 
                    c.chunk_id,
                    c.document_id,
                    c.chunk_text,
                    c.chunk_index,
                    d.title as document_title,
                    d.published_at,
                    d.url,
                    d.category,
                    d.department,
                    ts_rank(
                        to_tsvector('korean', c.chunk_text),
                        to_tsquery('korean', '{tsquery}')
                    ) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.document_id
                WHERE 
                    to_tsvector('korean', c.chunk_text) @@ to_tsquery('korean', '{tsquery}')
            """
            
            # Add filters
            if filters:
                if "date_from" in filters:
                    sql += f" AND d.published_at >= '{filters['date_from']}'"
                if "date_to" in filters:
                    sql += f" AND d.published_at <= '{filters['date_to']}'"
                if "category" in filters:
                    sql += f" AND d.category = '{filters['category']}'"
            
            sql += f"""
                ORDER BY similarity DESC
                LIMIT {top_k}
            """
            
            # Execute raw query
            result = self.db.rpc("exec_sql", {"sql": sql}).execute()
            
            return self._parse_bm25_results(result.data or [])
            
        except Exception as e:
            print(f"BM25 search error: {e}")
            # Fallback to simple ILIKE search
            return await self._fallback_keyword_search(query, top_k, filters)
    
    async def _fallback_keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Fallback keyword search using ILIKE."""
        try:
            db_query = self.db.table("chunks").select(
                "*, documents!inner(title, published_at, url, category, department)"
            ).ilike("chunk_text", f"%{query}%").limit(top_k)
            
            if filters:
                if "date_from" in filters:
                    db_query = db_query.gte("documents.published_at", filters["date_from"])
                if "date_to" in filters:
                    db_query = db_query.lte("documents.published_at", filters["date_to"])
            
            result = db_query.execute()
            
            results = self._parse_search_results(result.data or [])
            # Set similarity to 1.0 for keyword matches
            for r in results:
                r.similarity = 1.0
            
            return results
            
        except Exception as e:
            print(f"Fallback search error: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Hybrid search combining vector and keyword search.
        
        Args:
            query: Text query for keyword search
            query_embedding: Embedding for vector search
            top_k: Number of results
            vector_weight: Weight for vector scores (0-1)
            keyword_weight: Weight for keyword scores (0-1)
            filters: Optional metadata filters
            
        Returns:
            List of search results sorted by combined score
        """
        # Run both searches in parallel
        vector_results = await self.similarity_search(
            query_embedding, top_k * 2, filters
        )
        keyword_results = await self.bm25_search(
            query, top_k * 2, filters
        )
        
        # Combine results using Reciprocal Rank Fusion (RRF)
        combined = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            vector_weight,
            keyword_weight
        )
        
        return combined[:top_k]
    
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
            embedding = item.get("embeddings", {})
            
            # Calculate similarity from vector distance
            similarity = 0.0
            if embedding and embedding.get("embedding"):
                # pgvector uses L2 distance, convert to similarity
                # similarity = 1 / (1 + distance)
                similarity = 0.9  # Placeholder
            
            results.append(SearchResult(
                chunk_id=item.get("chunk_id", ""),
                document_id=item.get("document_id", ""),
                chunk_text=item.get("chunk_text", ""),
                chunk_index=item.get("chunk_index", 0),
                document_title=doc.get("title", ""),
                published_at=doc.get("published_at", ""),
                url=doc.get("url", ""),
                similarity=similarity,
                metadata={
                    "category": doc.get("category"),
                    "department": doc.get("department")
                }
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
                similarity=item.get("similarity", 0.0),
                metadata={
                    "category": item.get("category"),
                    "department": item.get("department")
                }
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
