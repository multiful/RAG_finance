-- FSC Policy RAG System - Database Schema
-- Supabase PostgreSQL with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ==================== CORE TABLES ====================

-- Sources (RSS feeds)
CREATE TABLE sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('rss', 'html_list', 'api')),
    base_url TEXT NOT NULL,
    fid TEXT,
    active BOOLEAN DEFAULT true,
    fetch_interval_min INTEGER DEFAULT 360,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES sources(source_id),
    title TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    url TEXT UNIQUE NOT NULL,
    category TEXT,
    department TEXT,
    raw_text TEXT,
    raw_html TEXT,
    language TEXT DEFAULT 'ko',
    hash TEXT NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'ingested' CHECK (status IN ('ingested', 'parsed', 'indexed', 'failed')),
    fail_reason TEXT
);

CREATE INDEX idx_documents_published_at ON documents(published_at DESC);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_source_id ON documents(source_id);
CREATE INDEX idx_documents_hash ON documents(hash);

-- Document Files (attachments)
CREATE TABLE document_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    file_type TEXT CHECK (file_type IN ('pdf', 'hwp', 'xls', 'xlsx', 'zip', 'doc', 'docx')),
    file_name TEXT,
    download_status TEXT DEFAULT 'pending',
    parse_status TEXT DEFAULT 'pending',
    parsed_text TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks
CREATE TABLE chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_tokens INTEGER,
    chunking_version TEXT DEFAULT 'v1',
    section_title TEXT,
    page_no INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);

-- Embeddings (pgvector)
CREATE TABLE embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    embedding_model TEXT DEFAULT 'text-embedding-3-small',
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- ==================== APPLICATION TABLES ====================

-- Industry Labels
CREATE TABLE industry_labels (
    label_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    label_insurance FLOAT DEFAULT 0 CHECK (label_insurance >= 0 AND label_insurance <= 1),
    label_banking FLOAT DEFAULT 0 CHECK (label_banking >= 0 AND label_banking <= 1),
    label_securities FLOAT DEFAULT 0 CHECK (label_securities >= 0 AND label_securities <= 1),
    predicted_labels TEXT[],
    model_version TEXT,
    explanation_chunk_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_industry_labels_document_id ON industry_labels(document_id);

-- Topics
CREATE TABLE topics (
    topic_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_name TEXT,
    topic_summary TEXT,
    time_window_start TIMESTAMPTZ NOT NULL,
    time_window_end TIMESTAMPTZ NOT NULL,
    topic_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_topics_time_window ON topics(time_window_start, time_window_end);

-- Topic Memberships
CREATE TABLE topic_memberships (
    topic_id UUID REFERENCES topics(topic_id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    score FLOAT DEFAULT 0,
    PRIMARY KEY (topic_id, document_id)
);

-- Alerts
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(topic_id) ON DELETE CASCADE,
    surge_score FLOAT NOT NULL CHECK (surge_score >= 0 AND surge_score <= 100),
    severity TEXT CHECK (severity IN ('low', 'med', 'high')),
    industries TEXT[],
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'ack', 'closed'))
);

CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);

-- Checklists
CREATE TABLE checklists (
    checklist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(document_id) ON DELETE CASCADE,
    generated_by_model TEXT,
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Checklist Items
CREATE TABLE checklist_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id UUID REFERENCES checklists(checklist_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    target TEXT,
    due_date_text TEXT,
    effective_date DATE,
    scope TEXT,
    penalty TEXT,
    evidence_chunk_id UUID REFERENCES chunks(chunk_id),
    confidence FLOAT DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_checklist_items_checklist_id ON checklist_items(checklist_id);

-- ==================== MONITORING TABLES ====================

-- QA Logs
CREATE TABLE qa_logs (
    qa_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query TEXT NOT NULL,
    retrieved_chunk_ids UUID[],
    reranked_chunk_ids UUID[],
    answer TEXT,
    citations JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_qa_logs_created_at ON qa_logs(created_at DESC);

-- Evaluation Runs
CREATE TABLE eval_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name TEXT,
    system_variant TEXT,
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluation Results
CREATE TABLE eval_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES eval_runs(run_id) ON DELETE CASCADE,
    question_id TEXT,
    metric_groundedness FLOAT,
    metric_hallucination FLOAT,
    metric_industry_f1 FLOAT,
    metric_checklist_missing FLOAT,
    metric_topic_precision_at_k FLOAT,
    notes TEXT
);

-- ==================== ROW LEVEL SECURITY ====================

-- Enable RLS on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE industry_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE checklists ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for demo)
CREATE POLICY "Allow all" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all" ON chunks FOR ALL USING (true);
CREATE POLICY "Allow all" ON embeddings FOR ALL USING (true);
CREATE POLICY "Allow all" ON industry_labels FOR ALL USING (true);
CREATE POLICY "Allow all" ON topics FOR ALL USING (true);
CREATE POLICY "Allow all" ON alerts FOR ALL USING (true);
CREATE POLICY "Allow all" ON checklists FOR ALL USING (true);

-- ==================== FUNCTIONS ====================

-- Function to search similar chunks
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE(
    chunk_id UUID,
    document_id UUID,
    chunk_text TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.chunk_id,
        c.document_id,
        c.chunk_text,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM chunks c
    JOIN embeddings e ON c.chunk_id = e.chunk_id
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get documents by date range
CREATE OR REPLACE FUNCTION get_documents_by_date(
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ
)
RETURNS TABLE(
    document_id UUID,
    title TEXT,
    published_at TIMESTAMPTZ,
    url TEXT,
    category TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.document_id,
        d.title,
        d.published_at,
        d.url,
        d.category
    FROM documents d
    WHERE d.published_at BETWEEN start_date AND end_date
    ORDER BY d.published_at DESC;
END;
$$ LANGUAGE plpgsql;

-- ==================== SEED DATA ====================

-- Insert default RSS sources
INSERT INTO sources (name, type, base_url, fid, active, fetch_interval_min) VALUES
('금융위 볏  도자료', 'rss', 'https://www.fsc.go.kr/rss/rss.asp', '0111', true, 360),
('금융위 볏  도설명', 'rss', 'https://www.fsc.go.kr/rss/rss.asp', '0112', true, 360),
('금융위 공지사항', 'rss', 'https://www.fsc.go.kr/rss/rss.asp', '0114', true, 360),
('금융위 카드뉴스', 'rss', 'https://www.fsc.go.kr/rss/rss.asp', '0411', true, 720);
