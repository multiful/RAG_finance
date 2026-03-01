-- FSC Policy RAG System - Execution Ready Schema for Supabase
-- This schema includes necessary extensions and corrected types.

-- 1. Enable Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
-- 하이브리드 검색 키워드(Trigram + FTS)용
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 2. Clean up existing tables (Optional - use with caution in production)
-- DROP TABLE IF EXISTS public.alerts CASCADE;
-- DROP TABLE IF EXISTS public.checklist_items CASCADE;
-- DROP TABLE IF EXISTS public.checklists CASCADE;
-- DROP TABLE IF EXISTS public.embeddings CASCADE;
-- DROP TABLE IF EXISTS public.chunks CASCADE;
-- DROP TABLE IF EXISTS public.document_files CASCADE;
-- DROP TABLE IF EXISTS public.industry_labels CASCADE;
-- DROP TABLE IF EXISTS public.documents CASCADE;
-- DROP TABLE IF EXISTS public.sources CASCADE;
-- DROP TABLE IF EXISTS public.topics CASCADE;
-- DROP TABLE IF EXISTS public.topic_memberships CASCADE;
-- DROP TABLE IF EXISTS public.qa_logs CASCADE;
-- DROP TABLE IF EXISTS public.eval_results CASCADE;
-- DROP TABLE IF EXISTS public.eval_runs CASCADE;

-- 3. Core Tables
CREATE TABLE public.sources (
    source_id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL,
    type text NOT NULL CHECK (type = ANY (ARRAY['rss', 'html_list', 'api'])),
    base_url text NOT NULL,
    fid text,
    active boolean DEFAULT true,
    fetch_interval_min integer DEFAULT 360,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT sources_pkey PRIMARY KEY (source_id)
);

CREATE TABLE public.documents (
    document_id uuid NOT NULL DEFAULT gen_random_uuid(),
    source_id uuid REFERENCES public.sources(source_id),
    title text NOT NULL,
    published_at timestamp with time zone NOT NULL,
    url text NOT NULL UNIQUE,
    category text,
    department text,
    raw_text text,
    raw_html text,
    language text DEFAULT 'ko',
    hash text NOT NULL,
    ingested_at timestamp with time zone DEFAULT now(),
    status text NOT NULL DEFAULT 'ingested' CHECK (status = ANY (ARRAY['ingested', 'parsed', 'indexed', 'failed'])),
    fail_reason text,
    CONSTRAINT documents_pkey PRIMARY KEY (document_id)
);

CREATE TABLE public.chunks (
    chunk_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES public.documents(document_id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    chunk_text text NOT NULL,
    chunk_tokens integer,
    chunking_version text DEFAULT 'v1'::text,
    section_title text,
    page_no integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chunks_pkey PRIMARY KEY (chunk_id)
);

CREATE TABLE public.embeddings (
    chunk_id uuid NOT NULL REFERENCES public.chunks(chunk_id) ON DELETE CASCADE,
    embedding_model text DEFAULT 'text-embedding-3-small'::text,
    embedding vector(1536), -- Fixed from USER-DEFINED
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT embeddings_pkey PRIMARY KEY (chunk_id)
);

-- Use HNSW index (Better performance and stability than ivfflat for most cases)
CREATE INDEX idx_embeddings_hnsw ON public.embeddings 
USING hnsw (embedding vector_cosine_ops);

CREATE TABLE public.industry_labels (
    label_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES public.documents(document_id) ON DELETE CASCADE,
    label_insurance double precision DEFAULT 0 CHECK (label_insurance >= 0 AND label_insurance <= 1),
    label_banking double precision DEFAULT 0 CHECK (label_banking >= 0 AND label_banking <= 1),
    label_securities double precision DEFAULT 0 CHECK (label_securities >= 0 AND label_securities <= 1),
    predicted_labels text[], -- Fixed from ARRAY
    model_version text,
    explanation_chunk_ids uuid[], -- Fixed from ARRAY
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT industry_labels_pkey PRIMARY KEY (label_id)
);

CREATE TABLE public.topics (
    topic_id uuid NOT NULL DEFAULT gen_random_uuid(),
    topic_name text,
    topic_summary text,
    time_window_start timestamp with time zone NOT NULL,
    time_window_end timestamp with time zone NOT NULL,
    topic_embedding vector(1536), -- Fixed from USER-DEFINED
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT topics_pkey PRIMARY KEY (topic_id)
);

CREATE INDEX idx_topics_embedding_hnsw ON public.topics 
USING hnsw (topic_embedding vector_cosine_ops);

CREATE TABLE public.alerts (
    alert_id uuid NOT NULL DEFAULT gen_random_uuid(),
    topic_id uuid REFERENCES public.topics(topic_id) ON DELETE CASCADE,
    surge_score double precision NOT NULL CHECK (surge_score >= 0 AND surge_score <= 100),
    severity text CHECK (severity = ANY (ARRAY['low'::text, 'med'::text, 'high'::text])),
    industries text[], -- Fixed from ARRAY
    generated_at timestamp with time zone DEFAULT now(),
    status text DEFAULT 'open'::text CHECK (status = ANY (ARRAY['open'::text, 'ack'::text, 'closed'::text])),
    CONSTRAINT alerts_pkey PRIMARY KEY (alert_id)
);

CREATE TABLE public.checklists (
    checklist_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES public.documents(document_id) ON DELETE CASCADE,
    generated_by_model text,
    model_version text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT checklists_pkey PRIMARY KEY (checklist_id)
);

CREATE TABLE public.checklist_items (
    item_id uuid NOT NULL DEFAULT gen_random_uuid(),
    checklist_id uuid REFERENCES public.checklists(checklist_id) ON DELETE CASCADE,
    action text NOT NULL,
    target text,
    due_date_text text,
    effective_date date,
    scope text,
    penalty text,
    evidence_chunk_id uuid REFERENCES public.chunks(chunk_id),
    confidence double precision DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT checklist_items_pkey PRIMARY KEY (item_id)
);

-- 4. Monitoring & Logs
CREATE TABLE public.qa_logs (
    qa_id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_query text NOT NULL,
    retrieved_chunk_ids uuid[],
    reranked_chunk_ids uuid[],
    answer text,
    citations jsonb,
    latency_ms integer,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT qa_logs_pkey PRIMARY KEY (qa_id)
);

-- Seed Initial Data
INSERT INTO public.sources (name, type, base_url, fid, active, fetch_interval_min) VALUES
('금융위 보도자료', 'rss', 'http://www.fsc.go.kr/about/fsc_bbs_rss/', '0111', true, 360),
('금융위 보도설명', 'rss', 'http://www.fsc.go.kr/about/fsc_bbs_rss/', '0112', true, 360),
('금융위 공지사항', 'rss', 'http://www.fsc.go.kr/about/fsc_bbs_rss/', '0114', true, 360),
('금융위 카드뉴스', 'rss', 'http://www.fsc.go.kr/about/fsc_bbs_rss/', '0411', true, 720)
ON CONFLICT DO NOTHING;
