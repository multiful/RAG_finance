/**
 * Global Collection State Context
 * 페이지 이동해도 수집 상태가 유지됩니다.
 */
import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from 'react';
import { toast } from 'sonner';
import api from '@/lib/api';

export interface JobProgress {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  stage: string;
  message: string;
  progress: number;
  started_at?: string;
  completed_at?: string;
  result?: {
    total_new: number;
    total_existing: number;
    errors: string[];
  };
}

interface CollectionContextType {
  isCollecting: boolean;
  jobProgress: JobProgress | null;
  lastResult: JobProgress | null;
  startCollection: () => Promise<void>;
  cancelCollection: () => void;
}

const CollectionContext = createContext<CollectionContextType | null>(null);

// 백엔드 응답을 프론트엔드 형식으로 변환
interface BackendJobData {
  job_id: string;
  status: string;
  stage: string;
  progress: number;
  message: string;
  started_at?: string;
  finished_at?: string;
  new_documents_count?: number;
  processed_documents_count?: number;
  total_documents_count?: number;
}

function normalizeJobStatus(data: BackendJobData): JobProgress {
  // status 변환: 백엔드 → 프론트엔드
  let normalizedStatus: JobProgress['status'] = 'processing';
  if (data.status === 'success' || data.status === 'success_collect' || data.status === 'no_change') {
    normalizedStatus = 'completed';
  } else if (data.status === 'error' || data.status === 'failed') {
    normalizedStatus = 'failed';
  } else if (data.status === 'running') {
    normalizedStatus = 'processing';
  }

  return {
    job_id: data.job_id,
    status: normalizedStatus,
    stage: data.stage || '처리 중',
    message: data.message || '',
    progress: data.progress || 0,
    started_at: data.started_at,
    completed_at: data.finished_at,
    result: {
      total_new: data.new_documents_count || 0,
      total_existing: (data.processed_documents_count || 0) - (data.new_documents_count || 0),
      errors: []
    }
  };
}

export function CollectionProvider({ children }: { children: ReactNode }) {
  const [isCollecting, setIsCollecting] = useState(false);
  const [jobProgress, setJobProgress] = useState<JobProgress | null>(null);
  const [lastResult, setLastResult] = useState<JobProgress | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const jobIdRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      // 올바른 API 엔드포인트 사용
      const response = await api.get(`/collection/jobs/${jobId}`);
      const data = response.data;
      
      // 백엔드 응답을 프론트엔드 형식으로 변환
      const normalizedStatus = normalizeJobStatus(data);
      setJobProgress(normalizedStatus);
      
      if (normalizedStatus.status === 'completed' || normalizedStatus.status === 'failed') {
        stopPolling();
        setIsCollecting(false);
        setLastResult(normalizedStatus);
        jobIdRef.current = null;
        if (normalizedStatus.status === 'completed') {
          const count = normalizedStatus.result?.total_new ?? 0;
          toast.success(count > 0 ? `수집 완료: 신규 ${count}건` : '수집 완료');
        } else if (normalizedStatus.status === 'failed') {
          toast.error('데이터 수집에 실패했습니다.');
        }
      }
    } catch (error) {
      console.error('Failed to poll job status:', error);
    }
  }, [stopPolling]);

  const startCollection = useCallback(async () => {
    if (isCollecting) return;
    
    setIsCollecting(true);
    setJobProgress({
      job_id: '',
      status: 'pending',
      stage: '초기화',
      message: '수집 작업을 시작합니다...',
      progress: 0
    });
    
    try {
      const response = await api.post('/collection/trigger');
      const { job_id } = response.data;
      
      jobIdRef.current = job_id;
      
      setJobProgress({
        job_id,
        status: 'processing',
        stage: '수집 중',
        message: 'RSS 피드 수집 중...',
        progress: 10
      });
      
      // Start polling every 1.5 seconds (faster polling)
      pollingRef.current = setInterval(() => {
        pollJobStatus(job_id);
      }, 1500);
      
    } catch (error) {
      console.error('Failed to start collection:', error);
      setIsCollecting(false);
      setJobProgress(null);
      toast.error('데이터 수집을 시작할 수 없습니다. 서버 상태를 확인해 주세요.');
    }
  }, [isCollecting, pollJobStatus]);

  const cancelCollection = useCallback(() => {
    stopPolling();
    setIsCollecting(false);
    setJobProgress(null);
    jobIdRef.current = null;
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Resume polling if there's an active job on mount
  useEffect(() => {
    if (jobIdRef.current && isCollecting && !pollingRef.current) {
      pollingRef.current = setInterval(() => {
        pollJobStatus(jobIdRef.current!);
      }, 1500);
    }
  }, [isCollecting, pollJobStatus]);

  return (
    <CollectionContext.Provider value={{
      isCollecting,
      jobProgress,
      lastResult,
      startCollection,
      cancelCollection
    }}>
      {children}
    </CollectionContext.Provider>
  );
}

export function useCollection() {
  const context = useContext(CollectionContext);
  if (!context) {
    throw new Error('useCollection must be used within a CollectionProvider');
  }
  return context;
}
