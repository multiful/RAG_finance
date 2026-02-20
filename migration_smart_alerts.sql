-- FSC Policy RAG System - Smart Alert & Timeline Migration
-- Run this after the base schema is created

-- ==================== Smart Alerts ====================

CREATE TABLE IF NOT EXISTS public.smart_alerts (
    alert_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES public.documents(document_id) ON DELETE CASCADE,
    priority text NOT NULL CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    urgency_score double precision NOT NULL CHECK (urgency_score >= 0 AND urgency_score <= 100),
    industries text[],
    impact_summary text,
    key_deadlines jsonb DEFAULT '[]'::jsonb,
    action_items jsonb DEFAULT '[]'::jsonb,
    affected_regulations jsonb DEFAULT '[]'::jsonb,
    analysis_raw jsonb,
    notification_sent boolean DEFAULT false,
    generated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT smart_alerts_pkey PRIMARY KEY (alert_id)
);

CREATE INDEX IF NOT EXISTS idx_smart_alerts_urgency ON public.smart_alerts (urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_priority ON public.smart_alerts (priority);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_generated ON public.smart_alerts (generated_at DESC);

-- ==================== Alert Subscriptions ====================

CREATE TABLE IF NOT EXISTS public.alert_subscriptions (
    subscription_id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_email text NOT NULL,
    industries text[] DEFAULT '{}',
    channels text[] DEFAULT '{in_app}',
    min_priority text DEFAULT 'medium' CHECK (min_priority IN ('critical', 'high', 'medium', 'low')),
    webhook_url text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT alert_subscriptions_pkey PRIMARY KEY (subscription_id),
    CONSTRAINT alert_subscriptions_email_unique UNIQUE (user_email)
);

CREATE INDEX IF NOT EXISTS idx_alert_subscriptions_active ON public.alert_subscriptions (is_active);

-- ==================== Policy Timeline Events ====================

CREATE TABLE IF NOT EXISTS public.timeline_events (
    event_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES public.documents(document_id) ON DELETE CASCADE,
    event_type text NOT NULL CHECK (event_type IN ('effective_date', 'deadline', 'grace_period_end', 'submission_due', 'review_date')),
    event_date date NOT NULL,
    description text NOT NULL,
    target_entities text[],
    industries text[],
    is_critical boolean DEFAULT false,
    extracted_at timestamp with time zone DEFAULT now(),
    CONSTRAINT timeline_events_pkey PRIMARY KEY (event_id)
);

CREATE INDEX IF NOT EXISTS idx_timeline_events_date ON public.timeline_events (event_date);
CREATE INDEX IF NOT EXISTS idx_timeline_events_type ON public.timeline_events (event_type);
CREATE INDEX IF NOT EXISTS idx_timeline_events_critical ON public.timeline_events (is_critical) WHERE is_critical = true;

-- ==================== Compliance Tasks ====================

CREATE TABLE IF NOT EXISTS public.compliance_tasks (
    task_id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid REFERENCES public.documents(document_id) ON DELETE SET NULL,
    alert_id uuid REFERENCES public.smart_alerts(alert_id) ON DELETE SET NULL,
    title text NOT NULL,
    description text,
    industries text[],
    due_date date,
    assigned_to text,
    status text DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'overdue', 'cancelled')),
    priority text DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    CONSTRAINT compliance_tasks_pkey PRIMARY KEY (task_id)
);

CREATE INDEX IF NOT EXISTS idx_compliance_tasks_status ON public.compliance_tasks (status);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_due ON public.compliance_tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_assigned ON public.compliance_tasks (assigned_to);

-- ==================== Update qa_logs for enhanced metrics ====================

ALTER TABLE public.qa_logs 
ADD COLUMN IF NOT EXISTS grounding_score double precision,
ADD COLUMN IF NOT EXISTS confidence_score double precision,
ADD COLUMN IF NOT EXISTS citation_coverage double precision;

-- ==================== Notification History ====================

CREATE TABLE IF NOT EXISTS public.notification_history (
    notification_id uuid NOT NULL DEFAULT gen_random_uuid(),
    alert_id uuid REFERENCES public.smart_alerts(alert_id) ON DELETE CASCADE,
    subscription_id uuid REFERENCES public.alert_subscriptions(subscription_id) ON DELETE CASCADE,
    channel text NOT NULL,
    status text DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'delivered')),
    sent_at timestamp with time zone,
    error_message text,
    CONSTRAINT notification_history_pkey PRIMARY KEY (notification_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_history_alert ON public.notification_history (alert_id);
CREATE INDEX IF NOT EXISTS idx_notification_history_status ON public.notification_history (status);
