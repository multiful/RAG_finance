import axios from 'axios';
import { toast } from 'sonner';
import type {
  DocumentListResponse,
  Document,
  QARequest,
  QAResponse,
  IndustryClassification,
  Topic,
  Alert,
  ChecklistResponse,
  DashboardStats,
  QualityMetrics,
  SmartAlert,
  AlertStats,
  AlertSubscription,
  TimelineEvent,
  TimelineResponse,
  TimelineSummary,
  ComplianceDocument,
  ComplianceChecklist,
  ComplianceActionItem,
  ActionItemAudit
} from '@/types';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 5xx·네트워크 에러 시 토스트 (고도화)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const isServerError = status >= 500;
    const isNetworkError = !err.response && err.message?.includes('Network');
    if (isServerError || isNetworkError) {
      const detail = err.response?.data?.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail) && detail[0] && typeof detail[0] === 'object' && 'msg' in detail[0]
            ? String((detail[0] as { msg: string }).msg)
            : err.response?.data?.message ?? err.message ?? '요청을 처리할 수 없습니다.';
      toast.error(message, { duration: 5000 });
    }
    return Promise.reject(err);
  }
);

// Documents
export const getDocuments = async (params?: {
  page?: number;
  page_size?: number;
  category?: string;
  days?: number;
}): Promise<DocumentListResponse> => {
  const response = await api.get('/documents', { params });
  return response.data;
};

export const getDocument = async (id: string): Promise<Document> => {
  const response = await api.get(`/documents/${id}`);
  return response.data;
};

// Collection
export const triggerCollection = async (): Promise<{ message: string; job_id: string; status: string }> => {
  const response = await api.post('/collection/trigger');
  return response.data;
};

export const triggerFullPipeline = async (): Promise<{ message: string; job_id: string; status: string }> => {
  const response = await api.post('/pipeline/collect');
  return response.data;
};

export const getJobStatus = async (jobId: string) => {
  const response = await api.get(`/collection/jobs/${jobId}`);
  return response.data;
};

export const getCollectionStatus = async () => {
  const response = await api.get('/collection/status');
  return response.data;
};

export type SourceStat = { source_id: string; name: string; fid: string; document_count: number };
export type CollectionSourceStats = {
  by_source: SourceStat[];
  by_category: { category: string; count: number }[];
  sources_active: string[];
};

export const getCollectionSourceStats = async (): Promise<CollectionSourceStats> => {
  const response = await api.get('/collection/source-stats');
  return response.data;
};

export const getRecentDocuments = async (hours: number = 24) => {
  const response = await api.get('/collection/recent', { params: { hours } });
  return response.data;
};

// RAG QA
export const askQuestion = async (data: QARequest): Promise<QAResponse> => {
  const response = await api.post('/qa', data);
  return response.data;
};

export const askQuestionStream = async (
  data: QARequest,
  onChunk: (event: { type: string; [key: string]: unknown }) => void
) => {
  const response = await fetch(`${API_BASE_URL}/qa/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Failed to fetch streaming response');
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    // Keep the last partial line in the buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.trim().startsWith('data: ')) {
        try {
          const jsonStr = line.replace('data: ', '').trim();
          if (jsonStr) {
            const data = JSON.parse(jsonStr);
            onChunk(data);
          }
        } catch (e) {
          console.error('Error parsing streaming chunk:', e, 'Line:', line);
        }
      }
    }
  }
};

// Industry Classification
export const classifyIndustry = async (data: {
  document_id?: string;
  text?: string;
}): Promise<IndustryClassification> => {
  const response = await api.post('/classify', data);
  return response.data;
};

export const getDocumentIndustry = async (documentId: string): Promise<IndustryClassification> => {
  const response = await api.get(`/documents/${documentId}/industry`);
  return response.data;
};

// Topics & Alerts
export const getTopics = async (params?: {
  days?: number;
  detect?: boolean;
}): Promise<{ topics: Topic[]; topics_detected: number }> => {
  const response = await api.get('/topics', { params });
  return response.data;
};

export const detectTopics = async (days: number = 7): Promise<{ topics: Topic[]; topics_detected: number }> => {
  const response = await api.post('/topics/detect', null, { params: { days } });
  return response.data;
};

export const getAlerts = async (params?: {
  severity?: string;
  status?: string;
}): Promise<Alert[]> => {
  const response = await api.get('/alerts', { params });
  return response.data;
};

// Checklists
export const generateChecklist = async (documentId: string): Promise<ChecklistResponse> => {
  const response = await api.post('/checklists', { document_id: documentId });
  return response.data;
};

export const getDocumentChecklist = async (documentId: string): Promise<ChecklistResponse> => {
  const response = await api.get(`/documents/${documentId}/checklist`);
  return response.data;
};

export const exportChecklist = async (documentId: string, format: string = 'json') => {
  const response = await api.get(`/documents/${documentId}/checklist/export`, {
    params: { format },
    responseType: 'text',
  });
  return response.data;
};

// Compliance Hub
export const getComplianceDocument = async (id: string): Promise<ComplianceDocument> => {
  const response = await api.get(`/compliance/documents/${id}`);
  return response.data;
};

export const getComplianceChecklist = async (id: string): Promise<ComplianceChecklist> => {
  const response = await api.get(`/compliance/checklists/${id}`);
  return response.data;
};

export const listComplianceChecklists = async (params?: {
  skip?: number;
  limit?: number;
  status?: string;
  risk_level?: string;
}): Promise<ComplianceChecklist[]> => {
  const response = await api.get('/compliance/checklists', { params });
  return response.data;
};

export const generateComplianceChecklist = async (originalDocumentId: string, userId?: string): Promise<ComplianceChecklist> => {
  const response = await api.post('/compliance/checklists/generate', null, {
    params: { original_document_id: originalDocumentId, user_id: userId }
  });
  return response.data;
};

export const updateActionItem = async (
  id: string, 
  update: Partial<ComplianceActionItem>,
  userId?: string
): Promise<ComplianceActionItem> => {
  const response = await api.put(`/compliance/action-items/${id}`, update, {
    params: { user_id: userId }
  });
  return response.data;
};

export const getActionItemAudit = async (id: string): Promise<ActionItemAudit[]> => {
  const response = await api.get(`/compliance/action-items/${id}/audit`);
  return response.data;
};

export const recalculateRisk = async (id: string): Promise<{ message: string }> => {
  const response = await api.post(`/compliance/action-items/${id}/recalculate-risk`);
  return response.data;
};

// Dashboard
export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await api.get('/dashboard/stats');
  return response.data;
};

export interface HourlyStats {
  hourly: Array<{ hour: string; count: number; success: number; failed: number }>;
  by_source: Array<{ name: string; count: number }>;
  total: number;
  period_hours: number;
}

export const getHourlyStats = async (hours: number = 24): Promise<HourlyStats> => {
  const response = await api.get('/dashboard/hourly-stats', { params: { hours } });
  return response.data;
};

export const getQualityMetrics = async (days: number = 7): Promise<QualityMetrics> => {
  const response = await api.get('/dashboard/quality', { params: { days } });
  return response.data;
};

// Smart Alerts
export const getSmartAlerts = async (params?: {
  industries?: string[];
  min_priority?: string;
  limit?: number;
}): Promise<SmartAlert[]> => {
  const response = await api.get('/alerts', { params });
  return response.data;
};

export const processNewAlerts = async (): Promise<SmartAlert[]> => {
  const response = await api.post('/alerts/process');
  return response.data;
};

export const analyzeDocument = async (documentId: string): Promise<SmartAlert> => {
  const response = await api.post(`/alerts/analyze/${documentId}`);
  return response.data;
};

export const getAlertStats = async (): Promise<AlertStats> => {
  const response = await api.get('/alerts/stats');
  return response.data;
};

export const createAlertSubscription = async (data: Omit<AlertSubscription, 'subscription_id' | 'is_active'>): Promise<AlertSubscription> => {
  const response = await api.post('/alerts/subscriptions', data);
  return response.data;
};

export const getAlertSubscriptions = async (email?: string): Promise<AlertSubscription[]> => {
  const response = await api.get('/alerts/subscriptions', { params: { user_email: email } });
  return response.data;
};

// Timeline
export const getTimelineEvents = async (params?: {
  days_ahead?: number;
  industries?: string[];
  include_past?: boolean;
}): Promise<TimelineResponse> => {
  const response = await api.get('/timeline', { params });
  return response.data;
};

export const getTimelineByRange = async (
  start_date: string,
  end_date: string,
  industries?: string[]
): Promise<TimelineEvent[]> => {
  const response = await api.get('/timeline/range', {
    params: { start_date, end_date, industries }
  });
  return response.data;
};

export const extractTimeline = async (documentId: string, forceRefresh?: boolean): Promise<TimelineEvent[]> => {
  const response = await api.post(`/timeline/extract/${documentId}`, null, {
    params: { force_refresh: forceRefresh }
  });
  return response.data;
};

export const getCriticalEvents = async (params?: {
  days_ahead?: number;
  industries?: string[];
}): Promise<TimelineEvent[]> => {
  const response = await api.get('/timeline/critical', { params });
  return response.data;
};

export const getTimelineSummary = async (industries?: string[]): Promise<TimelineSummary> => {
  const response = await api.get('/timeline/summary', { params: { industries } });
  return response.data;
};

export const exportTimelineIcal = async (params?: {
  days_ahead?: number;
  industries?: string[];
}): Promise<Blob> => {
  const response = await api.get('/timeline/export/ical', {
    params,
    responseType: 'blob'
  });
  return response.data;
};

// Analytics API
export interface TopicTrendData {
  period: string;
  monthly_trends: Array<{
    month: string;
    keywords: Array<{ keyword: string; count: number }>;
    total_documents: number;
  }>;
  top_keywords_overall: Array<{ keyword: string; count: number }>;
  total_documents_analyzed: number;
}

export interface IndustryImpactItem {
  industry: string;
  industry_label: string;
  document_count: number;
  alert_count: number;
  high_severity_count: number;
  impact_score: number;
  risk_level: string;
  top_keywords: Array<{ keyword: string; count: number }>;
}

export interface IndustryImpactData {
  period_days: number;
  analysis_date: string;
  industry_impact: IndustryImpactItem[];
  summary: {
    most_affected: string | null;
    total_regulations: number;
    total_alerts: number;
  };
}

export interface DocumentStatsData {
  period_days: number;
  total_documents: number;
  daily_trend: Array<{ date: string; count: number }>;
  weekly_trend: Array<{ week_start: string; count: number }>;
  monthly_trend: Array<{ month: string; count: number }>;
  by_category: Array<{ category: string; count: number }>;
  by_status: Array<{ status: string; count: number }>;
  avg_documents_per_day: number;
}

export interface KeywordCloudData {
  period_days: number;
  keywords: Array<{ text: string; value: number; normalized: number }>;
}

export interface RegulationSummary {
  generated_at: string;
  overview: {
    total_regulations: number;
    regulations_this_week: number;
    week_over_week_change: number;
    active_alerts: number;
    high_severity_alerts: number;
  };
  insights: Array<{ type: string; message: string }>;
}

export const getTopicTrends = async (months?: number, industry?: string): Promise<TopicTrendData> => {
  const response = await api.get('/analytics/topic-trends', { params: { months, industry } });
  return response.data;
};

export const getIndustryImpact = async (days?: number): Promise<IndustryImpactData> => {
  const response = await api.get('/analytics/industry-impact', { params: { days } });
  return response.data;
};

export const getDocumentStats = async (days?: number): Promise<DocumentStatsData> => {
  const response = await api.get('/analytics/document-stats', { params: { days } });
  return response.data;
};

export const getKeywordCloud = async (days?: number, limit?: number): Promise<KeywordCloudData> => {
  const response = await api.get('/analytics/keyword-cloud', { params: { days, limit } });
  return response.data;
};

export const getRegulationSummary = async (): Promise<RegulationSummary> => {
  const response = await api.get('/analytics/regulation-summary');
  return response.data;
};

export interface WeeklyReport {
  generated_at: string;
  period: { start: string; end: string };
  summary: string;
  statistics: {
    total_documents: number;
    by_industry: Record<string, number>;
    urgent_alerts: number;
    total_alerts: number;
  };
  highlights: Array<{ title: string; date: string; category: string }>;
  recommendations: Array<{ priority: string; text: string } | null>;
}

export const getWeeklyReport = async (): Promise<WeeklyReport> => {
  const response = await api.get('/analytics/weekly-report');
  return response.data;
};

// System Health API
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'warning';
  timestamp: string;
  services: {
    api: boolean;
    redis: boolean;
    supabase: boolean;
    openai: boolean;
  };
  components: {
    rag_engine: { status: string; label: string };
    vector_db: { status: string; label: string };
    llm_api: { status: string; label: string };
    cache: { status: string; label: string };
  };
}

export const getSystemHealth = async (): Promise<SystemHealth> => {
  const response = await axios.get('/health');
  return response.data;
};

// RAGAS Evaluation API
export interface EvaluationMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
  overall_score: number;
  sample_size: number;
  evaluated_at: string;
}

export interface EvaluationResult {
  status: string;
  evaluation: EvaluationMetrics;
  details: Array<{
    question: string;
    answer: string;
    rag_confidence: number;
    rag_groundedness: number;
    context_count: number;
  }>;
}

export interface MetricsSummary {
  system_name: string;
  version: string;
  generated_at: string;
  data_metrics: {
    total_documents: number;
    documents_24h: number;
    collection_success_rate: number;
    data_sources: number;
  };
  rag_metrics: {
    avg_faithfulness: number;
    avg_answer_relevancy: number;
    avg_context_precision: number;
    avg_context_recall: number;
    avg_overall_score: number;
    evaluation_count: number;
    note?: string;
  };
  technology_stack: Record<string, string>;
  features: string[];
}

export const runEvaluation = async (sampleSize: number = 16): Promise<EvaluationResult> => {
  const response = await api.post('/evaluation/run', { sample_size: sampleSize });
  return response.data;
};

export const getLatestEvaluation = async (): Promise<{
  has_evaluation: boolean;
  evaluation?: EvaluationMetrics;
  message?: string;
}> => {
  const response = await api.get('/evaluation/latest');
  return response.data;
};

export const getEvaluationHistory = async (limit: number = 10) => {
  const response = await api.get('/evaluation/history', { params: { limit } });
  return response.data;
};

export const getMetricsSummary = async (): Promise<MetricsSummary> => {
  const response = await api.get('/evaluation/metrics/summary');
  return response.data;
};

// LangGraph Agent API
export interface AgentResponse {
  answer: string;
  citations: Array<{
    chunk_id: string;
    document_id: string;
    document_title: string;
    snippet: string;
    published_at: string;
    url: string;
  }>;
  confidence: number;
  groundedness_score: number;
  citation_coverage: number;
  metadata: {
    question_type: string;
    agent_iterations: number;
    processed_at: string;
    engine: string;
  };
}

export const askAgentQuestion = async (question: string): Promise<AgentResponse> => {
  const response = await api.post('/evaluation/agent/ask', { question, use_agent: true });
  return response.data;
};

export default api;
