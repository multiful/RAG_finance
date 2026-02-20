import axios from 'axios';
import type {
  DocumentListResponse,
  Document,
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
  TimelineSummary
} from '@/types';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

export const getRecentDocuments = async (hours: number = 24) => {
  const response = await api.get('/collection/recent', { params: { hours } });
  return response.data;
};

// RAG QA
export const askQuestion = async (data: {
  question: string;
  industry_filter?: string[];
  date_from?: string;
  date_to?: string;
  top_k?: number;
}): Promise<QAResponse> => {
  const response = await api.post('/qa', data);
  return response.data;
};

export const askQuestionStream = async (
  data: {
    question: string;
    industry_filter?: string[];
    date_from?: string;
    date_to?: string;
    top_k?: number;
  },
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

// Dashboard
export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await api.get('/dashboard/stats');
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

export default api;
