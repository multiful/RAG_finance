-- FSC Policy RAG - QA Logging & Feedback Migration
-- Ensures the qa_logs table exists with all necessary metrics for observability.

CREATE TABLE IF NOT EXISTS public.qa_logs (
    qa_id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_query text NOT NULL,
    retrieved_chunk_ids uuid[],
    answer text,
    citations jsonb,
    grounding_score double precision,
    confidence_score double precision,
    citation_coverage double precision,
    latency_ms integer,
    user_feedback integer DEFAULT 0, -- 0: none, 1: up, -1: down
    feedback_comment text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT qa_logs_pkey PRIMARY KEY (qa_id)
);

-- Index for analytics
CREATE INDEX IF NOT EXISTS idx_qa_logs_created_at ON public.qa_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_qa_logs_grounding_score ON public.qa_logs(grounding_score);

-- Also ensure feedback table for more granular feedback if needed in future
CREATE TABLE IF NOT EXISTS public.user_feedback (
    feedback_id uuid NOT NULL DEFAULT gen_random_uuid(),
    qa_id uuid REFERENCES public.qa_logs(qa_id) ON DELETE CASCADE,
    rating integer NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT user_feedback_pkey PRIMARY KEY (feedback_id)
);
