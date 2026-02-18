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
  QualityMetrics
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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
export const triggerCollection = async (): Promise<{ message: string }> => {
  const response = await api.post('/collection/trigger');
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
}): Promise<Topic[]> => {
  const response = await api.get('/topics', { params });
  return response.data;
};

export const detectTopics = async (days: number = 7) => {
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

export default api;
