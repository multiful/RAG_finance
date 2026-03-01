/**
 * Analytics Dashboard - Data Analysis & Visualization for Financial Regulations
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Area,
  AreaChart,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import {
  TrendingUp,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Building2,
  Landmark,
  FileText,
  AlertTriangle,
  RefreshCw,
  Calendar,
  Zap,
  Target,
  ChevronUp,
  ChevronDown,
  Minus,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getTopicTrends,
  getIndustryImpact,
  getDocumentStats,
  getKeywordCloud,
  getRegulationSummary,
  type TopicTrendData,
  type IndustryImpactData,
  type DocumentStatsData,
  type KeywordCloudData,
  type RegulationSummary,
} from '@/lib/api';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

function StatCard({ 
  title, 
  value, 
  change, 
  icon: Icon, 
  color 
}: { 
  title: string; 
  value: string | number; 
  change?: number; 
  icon: React.ElementType; 
  color: string;
}) {
  return (
    <Card className="card-interactive border-none bg-white">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className={`w-12 h-12 rounded-2xl ${color} flex items-center justify-center`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <div className="text-right">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{title}</p>
            <p className="text-2xl font-black text-slate-900 mt-1">{value}</p>
            {change !== undefined && (
              <div className={`flex items-center justify-end gap-1 text-xs font-bold mt-1 ${
                change > 0 ? 'text-emerald-600' : change < 0 ? 'text-red-600' : 'text-slate-400'
              }`}>
                {change > 0 ? <ChevronUp className="w-3 h-3" /> : change < 0 ? <ChevronDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                {Math.abs(change)}% vs 전주
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function KeywordCloud({ data }: { data: KeywordCloudData }) {
  const maxValue = Math.max(...data.keywords.map(k => k.value));
  
  return (
    <div className="flex flex-wrap gap-2 p-4">
      {data.keywords.map((keyword) => {
        const size = Math.max(12, Math.min(32, (keyword.value / maxValue) * 32));
        const opacity = 0.4 + (keyword.value / maxValue) * 0.6;
        
        return (
          <span
            key={keyword.text}
            className="px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 font-bold transition-all duration-200 hover:bg-indigo-200 hover:scale-105 cursor-default"
            style={{ 
              fontSize: `${size}px`,
              opacity,
            }}
            title={`${keyword.text}: ${keyword.value}회`}
          >
            {keyword.text}
          </span>
        );
      })}
    </div>
  );
}

export default function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [topicTrends, setTopicTrends] = useState<TopicTrendData | null>(null);
  const [industryImpact, setIndustryImpact] = useState<IndustryImpactData | null>(null);
  const [documentStats, setDocumentStats] = useState<DocumentStatsData | null>(null);
  const [keywordCloud, setKeywordCloud] = useState<KeywordCloudData | null>(null);
  const [summary, setSummary] = useState<RegulationSummary | null>(null);
  const [periodDays, setPeriodDays] = useState<string>('90');
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null);

  useEffect(() => {
    loadData(false);
  }, [periodDays]);

  const loadData = async (userRefresh = false) => {
    if (userRefresh) setIsRefreshing(true);
    else setLoading(true);
    try {
      const days = parseInt(periodDays);
      const months = Math.ceil(days / 30);
      
      const [trendsData, impactData, statsData, cloudData, summaryData] = await Promise.all([
        getTopicTrends(months),
        getIndustryImpact(days),
        getDocumentStats(days),
        getKeywordCloud(days, 40),
        getRegulationSummary(),
      ]);
      
      setTopicTrends(trendsData);
      setIndustryImpact(impactData);
      setDocumentStats(statsData);
      setKeywordCloud(cloudData);
      setSummary(summaryData);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      if (userRefresh) toast.error('분석 데이터를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
      setLastFetchedAt(new Date());
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6 animate-page-enter">
        <Skeleton className="h-10 w-64 rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-96 rounded-2xl" />
          <Skeleton className="h-96 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto animate-page-enter">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
            <BarChart3 className="h-7 w-7 text-indigo-600" />
            규제 분석
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            스테이블코인·가상자산·토큰증권 등 규제 트렌드 · 영향도 시각화 · 키워드 분석
            {lastFetchedAt && (
              <span className="ml-2 text-slate-400">
                · 기준 {lastFetchedAt.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Select value={periodDays} onValueChange={setPeriodDays}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="30">30일</SelectItem>
              <SelectItem value="90">90일</SelectItem>
              <SelectItem value="180">180일</SelectItem>
              <SelectItem value="365">1년</SelectItem>
            </SelectContent>
          </Select>
          
          <Button 
            variant="outline" 
            onClick={() => loadData(true)} 
            disabled={isRefreshing}
            className="transition-colors duration-200"
          >
            {isRefreshing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            새로고침
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="총 규제 문서"
            value={summary.overview.total_regulations.toLocaleString()}
            icon={FileText}
            color="bg-indigo-500"
          />
          <StatCard
            title="이번 주 신규"
            value={summary.overview.regulations_this_week}
            change={summary.overview.week_over_week_change}
            icon={TrendingUp}
            color="bg-emerald-500"
          />
          <StatCard
            title="활성 알림"
            value={summary.overview.active_alerts}
            icon={AlertTriangle}
            color="bg-amber-500"
          />
          <StatCard
            title="고위험 알림"
            value={summary.overview.high_severity_alerts}
            icon={Zap}
            color="bg-red-500"
          />
        </div>
      )}

      {/* Main Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Topic Trend Chart */}
        <Card className="border-none shadow-sm transition-shadow duration-200 hover:shadow-lg rounded-2xl overflow-hidden">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              월별 규제 발표 트렌드
            </CardTitle>
            <CardDescription>
              시간에 따른 규제 발표 빈도 변화
            </CardDescription>
          </CardHeader>
          <CardContent>
            {topicTrends && topicTrends.monthly_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={topicTrends.monthly_trends}>
                  <defs>
                    <linearGradient id="colorDocs" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis 
                    dataKey="month" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      const [, month] = value.split('-');
                      return `${month}월`;
                    }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: 'none', 
                      borderRadius: '12px',
                      color: '#fff'
                    }}
                    formatter={(value: number) => [`${value}건`, '문서 수']}
                    labelFormatter={(label) => `${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="total_documents"
                    stroke="#6366f1"
                    strokeWidth={3}
                    fill="url(#colorDocs)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-400">
                데이터가 없습니다
              </div>
            )}
          </CardContent>
        </Card>

        {/* Industry Impact Chart */}
        <Card className="border-none shadow-sm transition-shadow duration-200 hover:shadow-lg rounded-2xl overflow-hidden">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              업권별 규제 영향도
            </CardTitle>
            <CardDescription>
              각 업권이 받는 규제 영향 점수
            </CardDescription>
          </CardHeader>
          <CardContent>
            {industryImpact && industryImpact.industry_impact.length > 0 ? (
              <div className="space-y-6">
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={industryImpact.industry_impact}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis 
                      dataKey="industry_label" 
                      tick={{ fontSize: 12, fontWeight: 600 }}
                    />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Radar
                      name="영향도"
                      dataKey="impact_score"
                      stroke="#6366f1"
                      fill="#6366f1"
                      fillOpacity={0.5}
                    />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
                
                <div className="space-y-3">
                  {industryImpact.industry_impact.map((item) => (
                    <div key={item.industry} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {item.industry === 'INSURANCE' && <Building2 className="w-4 h-4 text-blue-500" />}
                          {item.industry === 'BANKING' && <Landmark className="w-4 h-4 text-emerald-500" />}
                          {item.industry === 'SECURITIES' && <TrendingUp className="w-4 h-4 text-purple-500" />}
                          <span className="font-bold text-sm">{item.industry_label}</span>
                          <Badge 
                            className={`text-[10px] ${
                              item.risk_level === 'HIGH' ? 'bg-red-100 text-red-700' :
                              item.risk_level === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                              'bg-green-100 text-green-700'
                            }`}
                          >
                            {item.risk_level}
                          </Badge>
                        </div>
                        <span className="font-black text-slate-900">{item.impact_score}점</span>
                      </div>
                      <Progress 
                        value={item.impact_score} 
                        className="h-2"
                      />
                      <div className="flex gap-4 text-xs text-slate-500">
                        <span>문서 {item.document_count}건</span>
                        <span>알림 {item.alert_count}건</span>
                        <span className="text-red-500">고위험 {item.high_severity_count}건</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-400">
                데이터가 없습니다
              </div>
            )}
          </CardContent>
        </Card>

        {/* Industry Impact Radar Chart */}
        <Card className="border-none shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              업권별 영향도 레이더
            </CardTitle>
            <CardDescription>
              업권별 규제 영향 다차원 분석
            </CardDescription>
          </CardHeader>
          <CardContent>
            {industryImpact && industryImpact.industry_impact && industryImpact.industry_impact.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={[
                  { metric: '문서 수', ...industryImpact.industry_impact.reduce((acc, i) => ({...acc, [i.industry_label]: Math.min(i.document_count, 100)}), {}) },
                  { metric: '알림 수', ...industryImpact.industry_impact.reduce((acc, i) => ({...acc, [i.industry_label]: Math.min(i.alert_count * 10, 100)}), {}) },
                  { metric: '영향 점수', ...industryImpact.industry_impact.reduce((acc, i) => ({...acc, [i.industry_label]: i.impact_score}), {}) },
                  { metric: '고위험', ...industryImpact.industry_impact.reduce((acc, i) => ({...acc, [i.industry_label]: Math.min(i.high_severity_count * 20, 100)}), {}) },
                ]}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                  {industryImpact.industry_impact.map((industry, idx) => (
                    <Radar
                      key={industry.industry}
                      name={industry.industry_label}
                      dataKey={industry.industry_label}
                      stroke={COLORS[idx]}
                      fill={COLORS[idx]}
                      fillOpacity={0.3}
                    />
                  ))}
                  <Legend />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-400">
                데이터가 없습니다
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Keywords */}
        <Card className="border-none shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-primary" />
              주요 규제 키워드
            </CardTitle>
            <CardDescription>
              가장 자주 등장하는 규제 관련 키워드
            </CardDescription>
          </CardHeader>
          <CardContent>
            {topicTrends && topicTrends.top_keywords_overall.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart 
                  data={topicTrends.top_keywords_overall.slice(0, 10)}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis 
                    dataKey="keyword" 
                    type="category" 
                    tick={{ fontSize: 12 }}
                    width={80}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: 'none', 
                      borderRadius: '12px',
                      color: '#fff'
                    }}
                  />
                  <Bar 
                    dataKey="count" 
                    fill="#6366f1" 
                    radius={[0, 8, 8, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-400">
                데이터가 없습니다
              </div>
            )}
          </CardContent>
        </Card>

        {/* Keyword Cloud */}
        <Card className="border-none shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChartIcon className="h-5 w-5 text-primary" />
              규제 키워드 클라우드
            </CardTitle>
            <CardDescription>
              키워드 빈도에 따른 시각화
            </CardDescription>
          </CardHeader>
          <CardContent>
            {keywordCloud && keywordCloud.keywords.length > 0 ? (
              <KeywordCloud data={keywordCloud} />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-400">
                데이터가 없습니다
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Document Stats */}
      {documentStats && (
        <Card className="border-none shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              문서 통계 상세
            </CardTitle>
            <CardDescription>
              기간별 문서 수집 현황 및 카테고리 분포. 카테고리는 수집 유형(보도자료, 보도설명, 공지사항 등) 기준입니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Weekly Trend */}
              <div>
                <h4 className="text-sm font-bold text-slate-700 mb-4">주간 수집 트렌드</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={documentStats.weekly_trend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis 
                      dataKey="week_start" 
                      tick={{ fontSize: 10 }}
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return `${date.getMonth() + 1}/${date.getDate()}`;
                      }}
                    />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1e293b', 
                        border: 'none', 
                        borderRadius: '12px',
                        color: '#fff'
                      }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      stroke="#10b981" 
                      strokeWidth={2}
                      dot={{ fill: '#10b981', strokeWidth: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Category Distribution */}
              <div>
                <h4 className="text-sm font-bold text-slate-700 mb-4">카테고리별 분포</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={documentStats.by_category}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="count"
                      nameKey="category"
                      label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {documentStats.by_category.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Stats Summary */}
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-50/80 border border-slate-100 rounded-xl p-4 text-center shadow-sm">
                <p className="text-2xl font-black text-slate-900">{documentStats.total_documents}</p>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">총 문서</p>
              </div>
              <div className="bg-slate-50/80 border border-slate-100 rounded-xl p-4 text-center shadow-sm">
                <p className="text-2xl font-black text-slate-900">{documentStats.avg_documents_per_day}</p>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">일평균</p>
              </div>
              <div className="bg-slate-50/80 border border-slate-100 rounded-xl p-4 text-center shadow-sm">
                <p className="text-2xl font-black text-slate-900">{documentStats.by_category.length}</p>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">카테고리</p>
              </div>
              <div className="bg-slate-50/80 border border-slate-100 rounded-xl p-4 text-center shadow-sm">
                <p className="text-2xl font-black text-slate-900">{documentStats.period_days}일</p>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">분석 기간</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Insights */}
      {summary && summary.insights.length > 0 && (
        <Card className="border-none shadow-lg bg-gradient-to-br from-slate-900 to-slate-800 text-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Zap className="h-5 w-5 text-yellow-400" />
              AI 분석 인사이트
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {summary.insights.map((insight, idx) => (
                <div 
                  key={idx}
                  className={`p-4 rounded-xl ${
                    insight.type === 'alert' ? 'bg-red-500/20' :
                    insight.type === 'success' ? 'bg-emerald-500/20' :
                    'bg-blue-500/20'
                  }`}
                >
                  <p className="font-medium">{insight.message}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
