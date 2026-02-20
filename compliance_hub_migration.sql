-- Compliance Hub Migration
-- Adds tables for tracking compliance documents, checklists, action items, and audits.

-- 1. Compliance Documents
-- Links to the original documents table but maintains compliance-specific state
CREATE TABLE IF NOT EXISTS public.compliance_documents (
    compliance_doc_id uuid NOT NULL DEFAULT gen_random_uuid(),
    original_document_id uuid NOT NULL REFERENCES public.documents(document_id) ON DELETE CASCADE,
    title text NOT NULL,
    version text DEFAULT '1.0',
    status text DEFAULT 'active' CHECK (status = ANY (ARRAY['active', 'archived', 'superseded'])),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by_user_id text,
    CONSTRAINT compliance_documents_pkey PRIMARY KEY (compliance_doc_id),
    CONSTRAINT compliance_documents_original_document_id_key UNIQUE (original_document_id)
);

-- 2. Compliance Checklists
CREATE TABLE IF NOT EXISTS public.compliance_checklists (
    checklist_id uuid NOT NULL DEFAULT gen_random_uuid(),
    compliance_doc_id uuid NOT NULL REFERENCES public.compliance_documents(compliance_doc_id) ON DELETE CASCADE,
    title text,
    description text,
    status text DEFAULT 'draft' CHECK (status = ANY (ARRAY['draft', 'active', 'completed', 'cancelled'])),
    risk_score double precision DEFAULT 0,
    risk_level text DEFAULT 'low' CHECK (risk_level = ANY (ARRAY['low', 'medium', 'high', 'critical'])),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by_user_id text,
    CONSTRAINT compliance_checklists_pkey PRIMARY KEY (checklist_id)
);

-- 3. Compliance Action Items
CREATE TABLE IF NOT EXISTS public.compliance_action_items (
    action_item_id uuid NOT NULL DEFAULT gen_random_uuid(),
    checklist_id uuid NOT NULL REFERENCES public.compliance_checklists(checklist_id) ON DELETE CASCADE,
    action text NOT NULL,
    target text,
    due_date timestamp with time zone,
    completed_at timestamp with time zone,
    status text DEFAULT 'pending' CHECK (status = ANY (ARRAY['pending', 'in_progress', 'completed', 'overdue', 'skipped'])),
    priority text DEFAULT 'medium' CHECK (priority = ANY (ARRAY['low', 'medium', 'high', 'urgent'])),
    risk_score double precision DEFAULT 0,
    risk_level text DEFAULT 'low' CHECK (risk_level = ANY (ARRAY['low', 'medium', 'high', 'critical'])),
    assigned_user_id text,
    notes text,
    evidence_chunk_id uuid REFERENCES public.chunks(chunk_id),
    llm_confidence double precision DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT compliance_action_items_pkey PRIMARY KEY (action_item_id)
);

-- 4. Compliance Action Item Audits
CREATE TABLE IF NOT EXISTS public.compliance_action_item_audits (
    audit_id uuid NOT NULL DEFAULT gen_random_uuid(),
    action_item_id uuid NOT NULL REFERENCES public.compliance_action_items(action_item_id) ON DELETE CASCADE,
    changed_by_user_id text,
    old_values jsonb,
    new_values jsonb,
    changed_fields text[],
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT compliance_action_item_audits_pkey PRIMARY KEY (audit_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_compliance_docs_original_id ON public.compliance_documents(original_document_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checklists_doc_id ON public.compliance_checklists(compliance_doc_id);
CREATE INDEX IF NOT EXISTS idx_compliance_action_items_checklist_id ON public.compliance_action_items(checklist_id);
CREATE INDEX IF NOT EXISTS idx_compliance_action_items_status ON public.compliance_action_items(status);
CREATE INDEX IF NOT EXISTS idx_compliance_action_items_risk_level ON public.compliance_action_items(risk_level);
CREATE INDEX IF NOT EXISTS idx_compliance_action_items_due_date ON public.compliance_action_items(due_date);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_compliance_documents_updated_at
    BEFORE UPDATE ON public.compliance_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_checklists_updated_at
    BEFORE UPDATE ON public.compliance_checklists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_action_items_updated_at
    BEFORE UPDATE ON public.compliance_action_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
