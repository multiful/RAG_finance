import axios from 'axios';
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

export const getQualityMetrics = async (days: number = 7): Promise<QualityMetrics> => {
  const response = await api.get('/dashboard/quality', { params: { days } });
  return response.data;
};

export default api;
