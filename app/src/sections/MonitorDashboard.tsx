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
  AlertCircle,
  Shield,
  Sparkles,
  Eye,
  Scale,
  Building2,
  Activity,
  PieChart as PieChartIcon
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { getDashboardStats, triggerCollection, triggerFullPipeline, getRecentDocuments, getJobStatus, getHourlyStats, type HourlyStats } from '@/lib/api';
import type { DashboardStats, Document } from '@/types';

const CHART_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function MonitorDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [hourlyStats, setHourlyStats] = useState<HourlyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collecting, setCollecting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'warning' | 'error', text: string } | null>(null);
  const [jobProgress, setJobProgress] = useState<{ stage: string; progress: number; message: string } | null>(null);

  const fetchData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const [statsData, recentData, hourlyData] = await Promise.all([
        getDashboardStats(),
        getRecentDocuments(24),
        getHourlyStats(24),
      ]);
      setStats(statsData);
      setRecentDocs(recentData?.documents || []);
      setHourlyStats(hourlyData);
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      if (!isSilent) setError('데이터를 불러오는 중 오류가 발생했습니다. 서버 연결 상태를 확인해주세요.');
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
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header with quick actions */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">수집 현황 모니터</h2>
          <p className="text-slate-500 mt-2 text-lg">
            금융위원회 RSS 기반 실시간 데이터 인제스천 상태
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline"
            onClick={() => fetchData()} 
            disabled={loading}
            className="border-slate-200 text-slate-600 font-semibold h-11 px-5 rounded-xl hover:bg-slate-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading && !collecting ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
          <Button 
            onClick={() => handleRunJob('pipeline')} 
            disabled={collecting || loading}
            className="gradient-primary text-white font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/20"
          >
            <TrendingUp className={`w-4 h-4 mr-2 ${collecting && jobProgress?.stage !== 'collecting' ? 'animate-spin' : ''}`} />
            전체 파이프라인 실행
          </Button>
        </div>
      </div>

      {statusMessage && (
        <Alert variant={statusMessage.type === 'success' ? 'default' : 'destructive'} 
               className={`animate-in slide-in-from-top-4 duration-500 border-none shadow-md ${statusMessage.type === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle className="font-bold">{statusMessage.type === 'success' ? '성공' : '알림'}</AlertTitle>
          <AlertDescription className="font-medium">
            {statusMessage.text}
          </AlertDescription>
        </Alert>
      )}

      {jobProgress && (
        <Card className="border-none shadow-xl shadow-primary/10 bg-white overflow-hidden">
          <div className="h-1.5 w-full bg-slate-100">
            <div 
              className="h-full bg-primary transition-all duration-500 ease-out" 
              style={{ width: `${jobProgress.progress}%` }}
            />
          </div>
          <CardContent className="pt-6 pb-6 px-8">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <RefreshCw className="w-5 h-5 animate-spin text-primary" />
                </div>
                <div>
                  <span className="text-sm font-bold uppercase tracking-wider text-primary">{jobProgress.stage}</span>
                  <p className="text-slate-500 font-medium text-sm">{jobProgress.message}</p>
                </div>
              </div>
              <span className="text-2xl font-black text-slate-900">{jobProgress.progress}%</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Why This System - Differentiation Banner */}
      <Card className="border-none shadow-lg bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-3xl overflow-hidden">
        <CardContent className="p-8">
          <div className="flex flex-col lg:flex-row lg:items-center gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-5 h-5 text-emerald-400" />
                <span className="text-xs font-black uppercase tracking-widest text-emerald-400">
                  Enterprise Compliance RAG
                </span>
              </div>
              <h3 className="text-2xl font-black mb-2">
                금융 규제 전문 RAG 시스템
              </h3>
              <p className="text-slate-400 text-sm font-medium">
                금융위원회·금융감독원 <span className="text-white font-bold">공식 문서</span>를 기반으로 
                <span className="text-emerald-400 font-bold"> 출처가 명확한 답변</span>을 제공합니다.
              </p>
            </div>
            
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { icon: Shield, label: '공식 출처', value: '금융위/금감원', color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
                { icon: Sparkles, label: '출처 추적', value: '100% 제공', color: 'text-blue-400', bg: 'bg-blue-500/20' },
                { icon: Eye, label: '실시간 모니터링', value: '24/7 수집', color: 'text-purple-400', bg: 'bg-purple-500/20' },
                { icon: Scale, label: '감사 추적', value: '이력 저장', color: 'text-amber-400', bg: 'bg-amber-500/20' },
              ].map((item, i) => (
                <div key={i} className={`${item.bg} rounded-2xl p-4 text-center`}>
                  <item.icon className={`w-6 h-6 ${item.color} mx-auto mb-2`} />
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1">{item.label}</p>
                  <p className={`text-sm font-black ${item.color}`}>{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: '총 수집 문서', value: stats?.total_documents, icon: Database, color: 'text-indigo-600', bg: 'bg-indigo-50' },
          { label: '24시간 신규', value: stats?.documents_24h, icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-50' },
          { label: '활성 경보', value: stats?.active_alerts, icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50' },
          { label: '고위험 경보', value: stats?.high_severity_alerts, icon: AlertCircle, color: 'text-rose-600', bg: 'bg-rose-50' },
        ].map((item, i) => (
          <Card key={i} className="border-none shadow-sm bg-white hover:shadow-md transition-shadow duration-300 rounded-2xl">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-2xl ${item.bg} flex items-center justify-center`}>
                  <item.icon className={`w-6 h-6 ${item.color}`} />
                </div>
                <div className="flex flex-col items-end">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{item.label}</p>
                  {loading && !stats ? (
                    <Skeleton className="h-8 w-16 mt-1 rounded-lg" />
                  ) : (
                    <p className={`text-2xl font-black mt-1 text-slate-900`}>
                      {item.value?.toLocaleString() || 0}
                    </p>
                  )}
                </div>
              </div>
              <div className="h-1 w-full bg-slate-50 rounded-full overflow-hidden">
                <div className={`h-full ${item.bg.replace('bg-', 'text-').replace('50', '500').replace('text-', 'bg-')} opacity-60`} style={{ width: '60%' }} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Collection Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hourly Collection Chart */}
        <Card className="lg:col-span-2 border-none shadow-sm bg-white rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-500" />
              시간별 수집 현황
            </CardTitle>
          </CardHeader>
          <CardContent>
            {hourlyStats?.hourly && hourlyStats.hourly.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={hourlyStats.hourly.slice(-12)}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="hour" 
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    tickFormatter={(value) => value.split(' ')[1]?.replace(':00', 'h') || value}
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: 'none', 
                      borderRadius: '12px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                    labelFormatter={(value) => `시간: ${value}`}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="count" 
                    stroke="#6366f1" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorCount)" 
                    name="수집 문서"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-400">
                데이터 로딩 중...
              </div>
            )}
          </CardContent>
        </Card>

        {/* Source Distribution Pie Chart */}
        <Card className="border-none shadow-sm bg-white rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <PieChartIcon className="w-5 h-5 text-emerald-500" />
              소스별 분포
            </CardTitle>
          </CardHeader>
          <CardContent>
            {hourlyStats?.by_source && hourlyStats.by_source.length > 0 ? (
              <div className="flex flex-col items-center">
                <ResponsiveContainer width="100%" height={150}>
                  <PieChart>
                    <Pie
                      data={hourlyStats.by_source}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={2}
                      dataKey="count"
                      nameKey="name"
                    >
                      {hourlyStats.by_source.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1e293b', 
                        border: 'none', 
                        borderRadius: '8px',
                        color: 'white',
                        fontSize: '12px'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-wrap justify-center gap-2 mt-2">
                  {hourlyStats.by_source.slice(0, 4).map((item, idx) => (
                    <div key={item.name} className="flex items-center gap-1 text-xs">
                      <div 
                        className="w-2 h-2 rounded-full" 
                        style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
                      />
                      <span className="text-slate-500 truncate max-w-[80px]">{item.name}</span>
                      <span className="font-bold text-slate-700">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-400">
                데이터 없음
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Collection Status */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-primary" />
              수집 채널 상태
            </h3>
            <Badge variant="outline" className="bg-white border-slate-200 text-slate-500 font-bold">
              {stats?.collection_status?.length || 0} Active Channels
            </Badge>
          </div>
          
          <div className="grid grid-cols-1 gap-4">
            {loading && !stats ? (
              [1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 w-full rounded-2xl" />)
            ) : (
              stats?.collection_status?.map((source) => (
                <Card key={source.source_id} className="border-none shadow-sm bg-white hover:shadow-md transition-all duration-300 rounded-2xl group">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-6">
                      <div className="w-14 h-14 rounded-2xl bg-slate-50 flex flex-col items-center justify-center border border-slate-100 group-hover:bg-primary/5 group-hover:border-primary/10 transition-colors">
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">FID</span>
                        <span className="text-sm font-black text-slate-900">{source.source_id}</span>
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-bold text-slate-900">{source.source_name}</h4>
                          {source.new_documents_24h > 0 && (
                            <Badge className="bg-emerald-500 hover:bg-emerald-600 text-[10px] font-black py-0 h-4 uppercase">New</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-xs font-bold text-slate-400">
                          <span className="flex items-center gap-1"><Database className="w-3 h-3" /> {source.total_documents.toLocaleString()} Total</span>
                          <span className="flex items-center gap-1 text-emerald-500"><TrendingUp className="w-3 h-3" /> +{source.new_documents_24h} Today</span>
                        </div>
                      </div>

                      <div className="hidden md:flex flex-col items-end gap-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-black text-slate-400 uppercase">Health Score</span>
                          <span className={`text-sm font-black ${source.success_rate_7d > 90 ? 'text-emerald-500' : 'text-amber-500'}`}>
                            {source.success_rate_7d.toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-32 h-1.5 bg-slate-50 rounded-full overflow-hidden border border-slate-100">
                          <div 
                            className={`h-full transition-all duration-1000 ${source.success_rate_7d > 90 ? 'bg-emerald-500' : 'bg-amber-500'}`} 
                            style={{ width: `${source.success_rate_7d}%` }} 
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Recent Documents */}
        <div className="space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              실시간 피드
            </h3>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Last 24h</span>
          </div>
          
          <Card className="border-none shadow-sm bg-white rounded-3xl overflow-hidden">
            <CardContent className="p-0">
              <div className="divide-y divide-slate-50">
                {loading && recentDocs.length === 0 ? (
                  [1, 2, 3, 4, 5].map(i => (
                    <div key={i} className="p-5 flex gap-4">
                      <Skeleton className="h-10 w-10 rounded-xl flex-shrink-0" />
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-3 w-2/3" />
                      </div>
                    </div>
                  ))
                ) : recentDocs.length === 0 ? (
                  <div className="py-20 flex flex-col items-center justify-center text-center px-6">
                    <div className="w-16 h-16 rounded-3xl bg-slate-50 flex items-center justify-center mb-4">
                      <FileText className="w-8 h-8 text-slate-300" />
                    </div>
                    <p className="text-slate-400 font-bold text-sm uppercase tracking-wider">No updates found</p>
                  </div>
                ) : (
                  recentDocs.slice(0, 8).map((doc) => (
                    <div 
                      key={doc.document_id} 
                      className="p-5 flex items-start gap-4 hover:bg-slate-50/50 transition-colors group cursor-pointer"
                    >
                      <div className={`w-10 h-10 rounded-xl flex-shrink-0 flex items-center justify-center border transition-colors ${
                        doc.status === 'indexed' ? 'bg-emerald-50 border-emerald-100 text-emerald-500' : 'bg-slate-50 border-slate-100 text-slate-400'
                      }`}>
                        {doc.status === 'indexed' ? <CheckCircle2 className="w-5 h-5" /> : <Clock className="w-5 h-5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm text-slate-900 line-clamp-1 group-hover:text-primary transition-colors">{doc.title}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">{doc.category}</span>
                          <span className="text-[10px] font-bold text-slate-400">{new Date(doc.published_at).toLocaleDateString('ko-KR')}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div className="p-4 bg-slate-50/50 border-t border-slate-50 text-center">
                <Button variant="ghost" className="text-xs font-black uppercase tracking-widest text-slate-400 hover:text-primary">
                  View Full History
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

}
