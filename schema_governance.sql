-- Governance Engine Schema

CREATE TABLE IF NOT EXISTS public.qa_logs (
    qa_id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_query text NOT NULL,
    retrieved_chunk_ids uuid[],
    answer text,
    citations jsonb,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT qa_logs_pkey PRIMARY KEY (qa_id)
);

CREATE TABLE IF NOT EXISTS public.eval_runs (
    run_id uuid NOT NULL DEFAULT gen_random_uuid(),
    run_name text,
    system_variant text,
    model text,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT eval_runs_pkey PRIMARY KEY (run_id)
);

CREATE TABLE IF NOT EXISTS public.eval_results (
    result_id uuid NOT NULL DEFAULT gen_random_uuid(),
    qa_id uuid REFERENCES public.qa_logs(qa_id) ON DELETE CASCADE,
    run_id uuid REFERENCES public.eval_runs(run_id) ON DELETE CASCADE,
    metric_groundedness double precision CHECK (metric_groundedness >= 0 AND metric_groundedness <= 1),
    metric_citation_precision double precision CHECK (metric_citation_precision >= 0 AND metric_citation_precision <= 1),
    metric_hallucination_rate double precision CHECK (metric_hallucination_rate >= 0 AND metric_hallucination_rate <= 1),
    notes jsonb,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT eval_results_pkey PRIMARY KEY (result_id),
    CONSTRAINT eval_results_qa_unique UNIQUE (qa_id)
);

CREATE INDEX IF NOT EXISTS idx_eval_results_created_at ON public.eval_results(created_at);
