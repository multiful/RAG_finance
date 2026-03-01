/**
 * Unified Dashboard - 통합 대시보드
 * 핵심 지표 + 실시간 피드 + 주간 요약을 한 눈에
 */
import { useEffect, useState, useCallback } from 'react';
import { 
  FileText, 
  TrendingUp, 
  AlertTriangle, 
  Clock,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Building2,
  Landmark,
  BarChart3,
  ExternalLink,
  Loader2,
  Calendar,
  Map,
  ClipboardList,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { 
  getDashboardStats, 
  getRecentDocuments, 
  getHourlyStats, 
  getWeeklyReport,
  getIndustryImpact,
  getMetricsSummary,
  type HourlyStats,
  type WeeklyReport,
  type IndustryImpactData
} from '@/lib/api';
import { toast } from 'sonner';
import { useCollection } from '@/contexts/CollectionContext';
import type { DashboardStats, Document } from '@/types';
import { NavLink } from 'react-router-dom';

const INDUSTRY_ICONS = {
  INSURANCE: Building2,
  BANKING: Landmark,
  SECURITIES: BarChart3,
};

export default function UnifiedDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [hourlyStats, setHourlyStats] = useState<HourlyStats | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [industryImpact, setIndustryImpact] = useState<IndustryImpactData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);
  const [metricsSummary, setMetricsSummary] = useState<{ hallucination_rate_recent_pct?: number | null; hallucination_goal_pct?: number; evaluation_count?: number } | null>(null);
  const [demoGuideOpen, setDemoGuideOpen] = useState(false);

  const { isCollecting, jobProgress, startCollection, lastResult } = useCollection();

  const fetchData = useCallback(async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setIsRefreshing(true);
    else setLoading(true);
    try {
      const [statsData, recentData, hourlyData, reportData, impactData, metricsData] = await Promise.all([
        getDashboardStats(),
        getRecentDocuments(72),
        getHourlyStats(48),
        getWeeklyReport(),
        getIndustryImpact(90),
        getMetricsSummary().catch(() => null),
      ]);
      setStats(statsData);
      setRecentDocs(recentData?.documents || []);
      setHourlyStats(hourlyData);
      setWeeklyReport(reportData);
      setIndustryImpact(impactData);
      setMetricsSummary(metricsData ? {
        hallucination_rate_recent_pct: metricsData.rag_metrics?.hallucination_rate_recent_pct,
        hallucination_goal_pct: metricsData.rag_metrics?.hallucination_goal_pct ?? 5,
        evaluation_count: metricsData.rag_metrics?.evaluation_count,
      } : null);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      if (!showRefreshSpinner) toast.error('대시보드 데이터를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
      setLastFetchedAt(new Date());
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // 수집 완료 시 데이터 재조회 (주간 요약/총 문서 수 갱신). 약간 지연 후 호출해 서버 반영 후 가져옴
  useEffect(() => {
    if (lastResult?.status === 'completed') {
      const t = setTimeout(() => fetchData(true), 400);
      return () => clearTimeout(t);
    }
  }, [lastResult?.status, lastResult?.result?.total_new, fetchData]);

  if (loading && !stats) {
    return (
      <div className="space-y-6 animate-page-enter">
        <Skeleton className="h-48 w-full rounded-2xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-80 lg:col-span-2 rounded-2xl" />
          <Skeleton className="h-80 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Hero - Clean high-impact card (reference style) */}
      <section className="rounded-3xl bg-white border border-[#e9e9e9] overflow-hidden shadow-sm">
        <div className="h-1 w-full bg-gradient-to-r from-slate-800 via-indigo-600 to-slate-800" />
        <div className="p-8">
          <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-8">
            <div className="space-y-4 max-w-2xl">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-[0.12em] flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-500" />
                스테이블코인·STO 규제·Gap 분석
              </p>
              <h1 className="text-2xl lg:text-[1.75rem] font-bold text-slate-900 leading-snug tracking-tight">
                {lastResult?.status === 'completed' && (lastResult?.result?.total_new ?? 0) > 0
                  ? `신규 ${lastResult.result!.total_new}건 수집 완료. 스테이블코인·STO 관련 국내·국제 규제 문서가 갱신되었습니다.`
                  : (weeklyReport?.summary || '스테이블코인·STO 관련 규제·국제 권고 동향을 분석 중입니다.')}
              </h1>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500">
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  {new Date().toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })} 기준
                </span>
                {lastFetchedAt && (
                  <span>데이터 기준 {lastFetchedAt.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
                )}
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                variant="outline"
                onClick={() => fetchData(true)}
                disabled={isRefreshing}
                className="rounded-2xl border-[#e9e9e9] text-slate-700 hover:bg-slate-50"
              >
                {isRefreshing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                새로고침
              </Button>
              <Button
                onClick={startCollection}
                disabled={isCollecting}
                className="rounded-2xl bg-slate-900 text-white hover:bg-slate-800 font-semibold"
              >
                {isCollecting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />수집 중...</> : <><TrendingUp className="w-4 h-4 mr-2" />데이터 수집</>}
              </Button>
            </div>
          </div>
          {isCollecting && jobProgress && (
            <div className="mt-6 p-4 rounded-2xl bg-slate-50 border border-[#e9e9e9]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700">{jobProgress.stage}</span>
                <span className="text-sm font-semibold text-slate-600">{jobProgress.progress}%</span>
              </div>
              <Progress value={jobProgress.progress} className="h-2 rounded-full" />
            </div>
          )}
          {/* 실현 가능성·데모 시나리오 안내 (평가위원·데모용) */}
          <Collapsible open={demoGuideOpen} onOpenChange={setDemoGuideOpen} className="mt-6 pt-6 border-t border-slate-100">
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-900 gap-2 -ml-2">
                {demoGuideOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                실현 가능성 · 데모 시나리오 안내
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-4">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">타깃 사용자</p>
                  <p className="text-sm text-slate-700">금융당국(FSC/FSS) · 샌드박스 신청 기업 · 전문 서비스 제공자</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">로드맵 (3단계)</p>
                  <ol className="text-sm text-slate-700 list-decimal list-inside space-y-0.5">
                    <li>솔루션 고도화</li>
                    <li>샌드박스 시범 적용</li>
                    <li>제도화 지원</li>
                  </ol>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">권장 데모 흐름 (4단계)</p>
                  <ol className="text-sm text-slate-700 space-y-1.5">
                    <li className="flex items-center gap-2">
                      <span className="font-medium text-slate-500">1.</span>
                      <NavLink to="/gap-map" className="text-indigo-600 hover:underline inline-flex items-center gap-1"><Map className="w-4 h-4 shrink-0" /> Gap Map</NavLink>
                      <span>에서 상위 사각지대·LC 근거 보기 확인</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="font-medium text-slate-500">2.</span>
                      <NavLink to="/sandbox/checklist" className="text-indigo-600 hover:underline inline-flex items-center gap-1"><ClipboardList className="w-4 h-4 shrink-0" /> Sandbox 체크리스트</NavLink>
                      <span>에서 「데모 시나리오 적용」 → 자가진단 제출</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="font-medium text-slate-500">3.</span>
                      <span>같은 페이지 또는 Gap Map에서 「샌드박스 시뮬레이션」 실행</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="font-medium text-slate-500">4.</span>
                      <span>검토 포인트·보완 방안 확인</span>
                    </li>
                  </ol>
                </div>
                <p className="text-xs text-slate-500 pt-1 border-t border-slate-200">
                  성공 지표: Hallucination Rate 5% 미만 (아래 RAG KPI 참고)
                </p>
              </div>
            </CollapsibleContent>
          </Collapsible>
          {/* RAG KPI: 환각률 (최근 N건) */}
          {metricsSummary != null && (
            <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">RAG 품질 KPI</p>
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900">
                    {metricsSummary.hallucination_rate_recent_pct != null
                      ? `${metricsSummary.hallucination_rate_recent_pct}%`
                      : '—'}
                  </span>
                  <span className="text-sm text-slate-500">환각률 (최근 평가)</span>
                </div>
                <span className="text-slate-400">|</span>
                <div>
                  <span className="text-sm font-medium text-slate-600">목표 </span>
                  <span className="text-sm font-bold text-emerald-600">{metricsSummary.hallucination_goal_pct ?? 5}% 미만</span>
                </div>
                {metricsSummary.evaluation_count != null && metricsSummary.evaluation_count > 0 && (
                  <>
                    <span className="text-slate-400">|</span>
                    <span className="text-xs text-slate-500">평가 {metricsSummary.evaluation_count}회 반영</span>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Key Metrics - 수집 직후에는 방금 수집한 건수(lastResult)를 우선 표시 */}
      {(() => {
        // 이번 주 신규: 백엔드 documents_this_week(국내+국제) 우선, 없으면 수집 직후 total_new, 없으면 주간보고서 합계
        const newThisWeek = (stats?.documents_this_week != null && stats.documents_this_week > 0)
          ? stats.documents_this_week
          : (lastResult?.status === 'completed' && lastResult?.result?.total_new != null)
            ? lastResult.result.total_new
            : (weeklyReport?.statistics?.total_documents ?? 0);
        const domesticWeek = stats?.domestic_this_week ?? 0;
        const internationalWeek = stats?.international_this_week ?? 0;
        const subLabel = (domesticWeek > 0 || internationalWeek > 0)
          ? `국내 ${domesticWeek} · 국제 ${internationalWeek}`
          : null;
        return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: '총 수집 문서', value: stats?.total_documents || 0, icon: FileText, color: 'bg-slate-900', change: null, subLabel: null },
          { label: '이번 주 신규', value: newThisWeek, icon: TrendingUp, color: 'bg-emerald-600', change: newThisWeek > 0 ? `+${newThisWeek}` : null, subLabel },
          { label: '활성 알림', value: stats?.active_alerts || 0, icon: AlertTriangle, color: 'bg-amber-500', change: null, subLabel: null },
          { label: '긴급 알림', value: weeklyReport?.statistics?.urgent_alerts || 0, icon: Clock, color: 'bg-rose-500', change: null, subLabel: null },
        ].map((item, i) => (
          <Card key={i} className="rounded-2xl border border-[#e9e9e9] bg-white shadow-sm hover:shadow transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">{item.label}</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1.5 tracking-tight">{item.value.toLocaleString()}</p>
                  {item.subLabel && <p className="text-[11px] text-slate-500 mt-0.5">{item.subLabel}</p>}
                  {item.change && <p className="text-xs font-medium text-emerald-600 mt-1">{item.change}</p>}
                </div>
                <div className={`w-12 h-12 rounded-2xl ${item.color} flex items-center justify-center`}>
                  <item.icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
        );
      })()}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Collection Trend Chart */}
        <Card className="lg:col-span-2 rounded-2xl border border-[#e9e9e9] bg-white shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-500" />
              수집 트렌드 (48시간)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {hourlyStats?.hourly && hourlyStats.hourly.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={hourlyStats.hourly.slice(-24)}>
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
                    tickFormatter={(value) => value.split(' ')[1]?.replace(':00', 'h') || ''}
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: 'none', 
                      borderRadius: '8px',
                      color: 'white',
                      fontSize: '12px'
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="count" 
                    stroke="#6366f1" 
                    strokeWidth={2}
                    fill="url(#colorCount)" 
                    name="수집 문서"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-slate-400">
                데이터 로딩 중...
              </div>
            )}
          </CardContent>
        </Card>

        {/* Industry Impact */}
        <Card className="rounded-2xl border border-[#e9e9e9] bg-white shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
              <BarChart3 className="w-5 h-5 text-emerald-500" />
              업권별 영향도
            </CardTitle>
          </CardHeader>
          <CardContent>
            {industryImpact?.industry_impact && industryImpact.industry_impact.length > 0 ? (
              <div className="space-y-4">
                {industryImpact.industry_impact.map((item) => {
                  const Icon = INDUSTRY_ICONS[item.industry as keyof typeof INDUSTRY_ICONS] || Building2;
                  return (
                    <div key={item.industry} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-slate-500" />
                          <span className="text-sm font-semibold text-slate-700">{item.industry_label}</span>
                        </div>
                        <Badge className={`text-xs ${
                          item.risk_level === 'HIGH' ? 'bg-red-100 text-red-700' :
                          item.risk_level === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {item.impact_score}점
                        </Badge>
                      </div>
                      <Progress value={item.impact_score} className="h-2" />
                      <div className="flex gap-3 text-xs text-slate-500">
                        <span>문서 {item.document_count}건</span>
                        <span>알림 {item.alert_count}건</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-slate-400">
                분석 데이터 없음
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Documents + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Feed */}
        <Card className="lg:col-span-2 rounded-2xl border border-[#e9e9e9] bg-white shadow-sm">
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" />
              최근 수집 문서
            </CardTitle>
            <span className="text-xs text-slate-400">최근 72시간</span>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {recentDocs.length > 0 ? (
                recentDocs.slice(0, 6).map((doc) => (
                  <div key={doc.document_id} className="px-6 py-4 hover:bg-slate-50 active:bg-slate-100 transition-colors duration-150 cursor-default">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-900 line-clamp-1">{doc.title}</p>
                        <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                          <Badge variant="secondary" className="text-xs">{doc.category}</Badge>
                          <span>{new Date(doc.published_at).toLocaleDateString('ko-KR')}</span>
                        </div>
                      </div>
                      <a 
                        href={doc.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="p-2 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors duration-150"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-slate-400">
                  <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p>최근 수집된 문서가 없습니다</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="rounded-2xl border border-[#e9e9e9] bg-white shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold text-slate-900">빠른 작업</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <NavLink
              to="/analytics"
              className="group flex items-center justify-between p-4 rounded-2xl bg-slate-900 text-white hover:bg-slate-800 transition-colors font-medium"
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="w-5 h-5" />
                <span className="font-semibold">규제 트렌드 분석</span>
              </div>
              <ChevronRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-0.5" />
            </NavLink>
            
            <NavLink
              to="/qa"
              className="group flex items-center justify-between p-4 rounded-2xl bg-emerald-600 text-white hover:bg-emerald-700 transition-colors font-medium"
            >
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5" />
                <span className="font-semibold">AI에게 질문하기</span>
              </div>
              <ChevronRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-0.5" />
            </NavLink>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
