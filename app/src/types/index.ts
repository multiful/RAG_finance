export interface Document {
  document_id: string;
  title: string;
  published_at: string;
  url: string;
  category?: string;
  department?: string;
  status: 'ingested' | 'parsed' | 'indexed' | 'failed';
  ingested_at: string;
  fail_reason?: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface IndustryClassification {
  document_id?: string;
  label_insurance: number;
  label_banking: number;
  label_securities: number;
  predicted_labels: string[];
  explanation: string;
  evidence_chunk_ids: string[];
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  published_at: string;
  snippet: string;
  url: string;
}

export interface QAResponse {
  answer: string;
  summary: string;
  industry_impact: Record<string, number>;
  checklist?: ChecklistItem[];
  citations: Citation[];
  confidence: number;
  groundedness_score: number;
  citation_coverage: number;
  uncertainty_note?: string;
  answerable?: boolean;
}

export interface Topic {
  topic_id: string;
  topic_name?: string;
  topic_summary?: string;
  time_window_start: string;
  time_window_end: string;
  document_count: number;
  surge_score: number;
  representative_documents: Document[];
}

export interface Alert {
  alert_id: string;
  topic_id: string;
  topic_name?: string;
  surge_score: number;
  severity: 'low' | 'med' | 'high';
  industries: string[];
  generated_at: string;
  status: string;
}

export interface ChecklistItem {
  action: string;
  target?: string;
  due_date_text?: string;
  effective_date?: string;
  scope?: string;
  penalty?: string;
  evidence_chunk_id?: string;
  confidence: number;
}

export interface ChecklistResponse {
  checklist_id: string;
  document_id: string;
  document_title: string;
  items: ChecklistItem[];
  generated_at: string;
}

export interface CollectionStatus {
  source_id: string;
  source_name: string;
  last_fetch?: string;
  new_documents_24h: number;
  total_documents: number;
  success_rate_7d: number;
  parsing_failures_24h: number;
}

export interface DashboardStats {
  total_documents: number;
  documents_24h: number;
  active_alerts: number;
  high_severity_alerts: number;
  collection_status: CollectionStatus[];
  recent_topics: Topic[];
  quality_metrics?: QualityMetrics;
}

export interface QualityMetrics {
  date: string;
  groundedness: number;
  hallucination_rate: number;
  avg_response_time_ms: number;
  citation_accuracy: number;
  unanswered_rate: number;
}

// Smart Alert Types
export type AlertPriority = 'critical' | 'high' | 'medium' | 'low';
export type AlertChannel = 'webhook' | 'email' | 'slack' | 'in_app';

export interface SmartAlert {
  alert_id: string;
  document_id: string;
  document_title: string;
  published_at: string;
  priority: AlertPriority;
  urgency_score: number;
  industries: string[];
  impact_summary: string;
  key_deadlines: Array<{ date: string; description: string; type: string }>;
  action_items: string[];
  affected_regulations: string[];
  generated_at: string;
  notification_sent: boolean;
}

export interface AlertStats {
  total_alerts_24h: number;
  critical_alerts: number;
  high_alerts: number;
  by_industry: Record<string, number>;
  avg_urgency_score: number;
  pending_notifications: number;
}

export interface AlertSubscription {
  subscription_id?: string;
  user_email: string;
  industries: string[];
  channels: AlertChannel[];
  min_priority: AlertPriority;
  webhook_url?: string;
  is_active: boolean;
}

// Timeline Types
export type TimelineEventType = 'effective_date' | 'deadline' | 'grace_period_end' | 'submission_due' | 'review_date';

export interface TimelineEvent {
  event_id: string;
  document_id: string;
  document_title: string;
  event_type: TimelineEventType;
  event_date: string;
  description: string;
  target_entities: string[];
  industries: string[];
  days_remaining: number;
  is_critical: boolean;
}

export interface TimelineResponse {
  events: TimelineEvent[];
  total_events: number;
  upcoming_critical: number;
}

export interface TimelineSummary {
  next_30_days: {
    total: number;
    critical: number;
    by_type: Record<string, number>;
  };
  next_90_days: {
    total: number;
    critical: number;
    by_type: Record<string, number>;
  };
  urgent_within_7_days: Array<{
    event_id: string;
    description: string;
    event_date: string;
    days_remaining: number;
    is_critical: boolean;
  }>;
}
