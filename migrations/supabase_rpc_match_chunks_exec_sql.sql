-- Supabase RPC: 벡터 유사도 검색 (애플리케이션에서 match_chunks_v3 호출)
-- database_schema.sql 적용 후, embeddings/chunks/documents 테이블이 있어야 함.

CREATE OR REPLACE FUNCTION match_chunks_v3(
    query_embedding vector(1536),
    match_count int DEFAULT 10
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    chunk_text text,
    chunk_index int,
    document_title text,
    published_at timestamptz,
    url text,
    similarity float,
    chunking_version text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.chunk_id,
        c.document_id,
        c.chunk_text,
        c.chunk_index,
        d.title AS document_title,
        d.published_at,
        d.url,
        1 - (e.embedding <=> query_embedding) AS similarity,
        c.chunking_version
    FROM embeddings e
    JOIN chunks c ON c.chunk_id = e.chunk_id
    JOIN documents d ON d.document_id = c.document_id
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_chunks_v3 IS 'pgvector cosine similarity search for RAG retrieval';

-- 참고: 키워드 검색(Trigram/FTS)은 현재 코드에서 exec_sql(sql) RPC를 호출합니다.
-- Supabase에서 exec_sql를 제공하지 않으면 vector_store._fallback_keyword_search(ILIKE)만 사용됩니다.
-- exec_sql를 만들 경우: 읽기 전용 SELECT만 허용하고, 애플리케이션에서 이미 이스케이프한 SQL만 전달합니다.
