import { useEffect, useState, useCallback } from 'react';
import { 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Clock,
  TrendingUp,
  AlertTriangle,
  Database,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { getDashboardStats, triggerCollection, triggerFullPipeline, getRecentDocuments, getJobStatus } from '@/lib/api';
import type { DashboardStats, Document } from '@/types';

export default function MonitorDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collecting, setCollecting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'warning' | 'error', text: string } | null>(null);
  const [jobProgress, setJobProgress] = useState<{ stage: string; progress: number; message: string } | null>(null);

  const fetchData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const [statsData, recentData] = await Promise.all([
        getDashboardStats(),
        getRecentDocuments(24),
      ]);
      setStats(statsData);
      setRecentDocs(recentData.documents || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      if (!isSilent) setError('데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(true), 10000); // 10s polling
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRunJob = async (type: 'collect' | 'pipeline') => {
    setCollecting(true);
    setStatusMessage(null);
    setJobProgress({ stage: 'starting', progress: 0, message: '요청 중...' });
    
    try {
      const response = type === 'collect' ? await triggerCollection() : await triggerFullPipeline();
      const jobId = response.job_id;
      
      const pollJobStatus = setInterval(async () => {
        try {
          const job = await getJobStatus(jobId);
          setJobProgress({
            stage: job.stage || 'running',
            progress: job.progress || 0,
            message: job.message || ''
          });
          
          if (['success', 'success_collect', 'no_change', 'error'].includes(job.status)) {
            clearInterval(pollJobStatus);
            setCollecting(false);
            setJobProgress(null);
            
            if (job.status === 'error') {
              setStatusMessage({ type: 'error', text: `작업 실패: ${job.message}` });
            } else {
              const count = job.new_documents_count || 0;
              const text = job.status === 'no_change' ? '변경 사항 없음' : `작업 완료: 신규 ${count}건`;
              setStatusMessage({ type: 'success', text });
              fetchData(true);
              setTimeout(() => setStatusMessage(null), 5000);
            }
          }
        } catch (err) {
          console.error('Job status poll error:', err);
        }
      }, 1000);

    } catch (error) {
      const axiosError = error as any;
      const detail = axiosError.response?.data?.detail || axiosError.message || 'Unknown error';
      console.error(`Error triggering ${type}:`, detail);
      setCollecting(false);
      setJobProgress(null);
      setStatusMessage({ type: 'error', text: `수집 요청 실패: ${detail}` });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'indexed':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-amber-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'indexed':
        return <Badge variant="default" className="bg-emerald-100 text-emerald-700">완료</Badge>;
      case 'failed':
        return <Badge variant="destructive">실패</Badge>;
      default:
        return <Badge variant="secondary">처리중</Badge>;
    }
  };

  if (error && !stats) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {error}
            <Button variant="outline" size="sm" onClick={() => fetchData()} className="ml-4">
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {statusMessage && (
        <Alert variant={statusMessage.type === 'success' ? 'default' : 'destructive'} 
               className={statusMessage.type === 'success' ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : ''}>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{statusMessage.type === 'success' ? '성공' : '알림'}</AlertTitle>
          <AlertDescription className="flex justify-between items-center">
            {statusMessage.text}
            {statusMessage.type === 'warning' && (
              <Button size="sm" variant="outline" onClick={() => handleRunJob('collect')} className="ml-4">
                다시 시도
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {jobProgress && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="pt-6">
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-primary" />
                <span className="font-semibold capitalize text-primary">{jobProgress.stage}</span>
              </div>
              <span className="text-sm font-medium">{jobProgress.progress}%</span>
            </div>
            <Progress value={jobProgress.progress} className="h-2 mb-2" />
            <p className="text-sm text-muted-foreground">{jobProgress.message}</p>
          </CardContent>
        </Card>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">실시간 수집 모니터</h2>
          <p className="text-muted-foreground mt-1">
            금융위원회 RSS 기반 최신 문서 수집 현황
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline"
            onClick={() => handleRunJob('collect')} 
            disabled={collecting || loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${collecting && jobProgress?.stage === 'collecting' ? 'animate-spin' : ''}`} />
            RSS 동기화
          </Button>
          <Button 
            onClick={() => handleRunJob('pipeline')} 
            disabled={collecting || loading}
            className="gradient-primary text-white"
          >
            <TrendingUp className={`w-4 h-4 mr-2 ${collecting && jobProgress?.stage !== 'collecting' ? 'animate-spin' : ''}`} />
            전체 파이프라인 실행
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: '총 문서 수', value: stats?.total_documents, icon: Database, color: 'text-primary', bg: 'bg-primary/10' },
          { label: '24시간 신규', value: stats?.documents_24h, icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-100' },
          { label: '활성 경보', value: stats?.active_alerts, icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-100' },
          { label: '고위험 경보', value: stats?.high_severity_alerts, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100' },
        ].map((item, i) => (
          <Card key={i} className="card-elevated">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{item.label}</p>
                  {loading && !stats ? (
                    <Skeleton className="h-9 w-20 mt-1" />
                  ) : (
                    <p className={`text-3xl font-bold mt-1 ${item.color}`}>
                      {item.value?.toLocaleString() || 0}
                    </p>
                  )}
                </div>
                <div className={`w-12 h-12 rounded-xl ${item.bg} flex items-center justify-center`}>
                  <item.icon className={`w-6 h-6 ${item.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Collection Status */}
      <Card className="card-elevated">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-primary" />
            수집 소스 상태
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {loading && !stats ? (
              [1, 2, 3, 4].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)
            ) : (
              stats?.collection_status?.map((source) => (
                <div key={source.source_id} className="flex items-center gap-4 p-4 bg-muted/50 rounded-xl">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{source.source_name}</span>
                      <Badge variant="outline" className="text-xs">
                        {source.source_id}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span>총 {source.total_documents.toLocaleString()}건</span>
                      <span>24h +{source.new_documents_24h}건</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">성공률</div>
                    <div className="text-lg font-semibold text-emerald-600">
                      {source.success_rate_7d.toFixed(1)}%
                    </div>
                  </div>
                  <div className="w-32">
                    <Progress value={source.success_rate_7d} className="h-2" />
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Recent Documents */}
      <Card className="card-elevated">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            최근 24시간 수집 문서
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {loading && recentDocs.length === 0 ? (
              [1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-xl" />)
            ) : recentDocs.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                최근 수집된 문서가 없습니다
              </p>
            ) : (
              recentDocs.slice(0, 10).map((doc) => (
                <div 
                  key={doc.document_id} 
                  className="flex items-center gap-4 p-4 hover:bg-muted/50 rounded-xl transition-colors"
                >
                  {getStatusIcon(doc.status)}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{doc.title}</p>
                    <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                      <span>{new Date(doc.published_at).toLocaleDateString('ko-KR')}</span>
                      <span>{doc.category}</span>
                      {doc.department && (
                        <span>{doc.department}</span>
                      )}
                    </div>
                  </div>
                  {getStatusBadge(doc.status)}
                  <a 
                    href={doc.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm"
                  >
                    원문보기
                  </a>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
