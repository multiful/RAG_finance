/**
 * Executive Summary View - One-page dashboard for management reporting.
 * 
 * Provides:
 * - Weekly policy highlights (TOP 5)
 * - Industry impact heatmap
 * - D-Day countdown for compliance items
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  FileText, 
  TrendingUp, 
  AlertTriangle, 
  Calendar,
  Building2,
  Landmark,
  BarChart3,
  Download,
  RefreshCw,
  Clock,
  ChevronRight,
  Zap
} from 'lucide-react';
import api from '@/lib/api';
import type { SmartAlert, TimelineEvent, TimelineSummary } from '@/types';

interface WeeklyHighlight {
  document_id: string;
  document_title: string;
  published_at: string;
  priority: string;
  urgency_score: number;
  industries: string[];
  impact_summary: string;
  key_points: string[];
}

interface IndustryHeatmapData {
  insurance: { alerts: number; tasks: number; score: number };
  banking: { alerts: number; tasks: number; score: number };
  securities: { alerts: number; tasks: number; score: number };
}

const INDUSTRY_CONFIG = {
  INSURANCE: { label: '보험', icon: Building2, color: 'bg-blue-500' },
  BANKING: { label: '은행', icon: Landmark, color: 'bg-green-500' },
  SECURITIES: { label: '증권', icon: TrendingUp, color: 'bg-purple-500' },
};

function getHeatmapColor(score: number): string {
  if (score >= 80) return 'bg-red-500';
  if (score >= 60) return 'bg-orange-400';
  if (score >= 40) return 'bg-yellow-400';
  if (score >= 20) return 'bg-green-300';
  return 'bg-green-100';
}

function HeatmapCell({ value, label }: { value: number; label: string }) {
  return (
    <div className={`p-4 rounded-xl ${getHeatmapColor(value)} transition-colors`}>
      <div className="text-2xl font-black text-white">{value}</div>
      <div className="text-[10px] font-bold text-white/80 uppercase">{label}</div>
    </div>
  );
}

export default function ExecutiveSummary() {
  const [loading, setLoading] = useState(true);
  const [weeklyAlerts, setWeeklyAlerts] = useState<SmartAlert[]>([]);
  const [timelineSummary, setTimelineSummary] = useState<TimelineSummary | null>(null);
  const [heatmapData, setHeatmapData] = useState<IndustryHeatmapData | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setLoading(true);
    try {
      const [alertsRes, timelineRes, complianceRes, alertStatsRes] = await Promise.all([
        api.get('/alerts', { params: { limit: 10 } }),
        api.get('/timeline/summary'),
        api.get('/compliance/dashboard'),
        api.get('/alerts/stats')
      ]);
      
      const alerts = alertsRes.data as SmartAlert[];
      setWeeklyAlerts(alerts.slice(0, 5));
      setTimelineSummary(timelineRes.data);
      
      // Build heatmap data
      const byIndustry = alertStatsRes.data?.by_industry || {};
      const complianceByIndustry = complianceRes.data?.by_industry || {};
      
      setHeatmapData({
        insurance: {
          alerts: byIndustry.INSURANCE || 0,
          tasks: complianceByIndustry.INSURANCE || 0,
          score: Math.min(100, (byIndustry.INSURANCE || 0) * 10 + (complianceByIndustry.INSURANCE || 0) * 5)
        },
        banking: {
          alerts: byIndustry.BANKING || 0,
          tasks: complianceByIndustry.BANKING || 0,
          score: Math.min(100, (byIndustry.BANKING || 0) * 10 + (complianceByIndustry.BANKING || 0) * 5)
        },
        securities: {
          alerts: byIndustry.SECURITIES || 0,
          tasks: complianceByIndustry.SECURITIES || 0,
          score: Math.min(100, (byIndustry.SECURITIES || 0) * 10 + (complianceByIndustry.SECURITIES || 0) * 5)
        }
      });
      
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to load executive summary:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const exportPDF = () => {
    window.print();
  };
  
  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-96" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-64" />
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }
  
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto print:p-0">
      {/* Header */}
      <div className="flex items-center justify-between print:hidden">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center gap-3">
            <Zap className="h-8 w-8 text-primary" />
            경영진 요약 보고
          </h1>
          <p className="text-slate-500 mt-1">
            {new Date().toLocaleDateString('ko-KR', { 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric',
              weekday: 'long'
            })} 기준
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            새로고침
          </Button>
          <Button onClick={exportPDF}>
            <Download className="h-4 w-4 mr-2" />
            PDF 내보내기
          </Button>
        </div>
      </div>
      
      {/* Print Header */}
      <div className="hidden print:block mb-8">
        <h1 className="text-2xl font-black text-center">금융 정책 주간 요약 보고</h1>
        <p className="text-center text-slate-500">
          {new Date().toLocaleDateString('ko-KR', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric'
          })} 기준
        </p>
      </div>
      
      {/* Urgent Alerts */}
      {timelineSummary && timelineSummary.urgent_within_7_days.length > 0 && (
        <Alert variant="destructive" className="print:border-2 print:border-red-500">
          <AlertTriangle className="h-5 w-5" />
          <AlertTitle className="text-lg font-bold">긴급 주의 필요</AlertTitle>
          <AlertDescription>
            7일 내 마감 기한이 있는 항목이 {timelineSummary.urgent_within_7_days.length}건 있습니다.
          </AlertDescription>
        </Alert>
      )}
      
      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly TOP 5 */}
        <Card className="lg:col-span-2 print:break-inside-avoid">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              주간 핵심 정책 변화 TOP 5
            </CardTitle>
            <CardDescription>
              긴급도 및 영향도 기준 상위 5개 항목
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {weeklyAlerts.length === 0 ? (
              <p className="text-center py-8 text-slate-400">
                이번 주 주요 알림이 없습니다
              </p>
            ) : (
              weeklyAlerts.map((alert, idx) => (
                <div 
                  key={alert.alert_id}
                  className="flex items-start gap-4 p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors print:bg-white print:border print:border-slate-200"
                >
                  <div className={`
                    w-8 h-8 rounded-lg flex items-center justify-center font-black text-white
                    ${idx === 0 ? 'bg-red-500' : idx < 3 ? 'bg-orange-400' : 'bg-slate-400'}
                  `}>
                    {idx + 1}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge 
                        variant={alert.priority === 'critical' ? 'destructive' : 'secondary'}
                        className="text-[10px] font-bold"
                      >
                        {alert.priority.toUpperCase()}
                      </Badge>
                      {alert.industries.map((ind) => (
                        <Badge key={ind} variant="outline" className="text-[10px]">
                          {INDUSTRY_CONFIG[ind as keyof typeof INDUSTRY_CONFIG]?.label || ind}
                        </Badge>
                      ))}
                    </div>
                    
                    <h4 className="font-bold text-sm text-slate-900 mb-1 line-clamp-1">
                      {alert.document_title}
                    </h4>
                    
                    <p className="text-xs text-slate-500 line-clamp-2">
                      {alert.impact_summary}
                    </p>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-2xl font-black text-slate-900">
                      {Math.round(alert.urgency_score)}
                    </div>
                    <div className="text-[10px] text-slate-400 font-bold uppercase">
                      Urgency
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
        
        {/* Industry Heatmap */}
        <Card className="print:break-inside-avoid">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              업권별 영향도
            </CardTitle>
            <CardDescription>
              알림 및 이행과제 기준
            </CardDescription>
          </CardHeader>
          <CardContent>
            {heatmapData && (
              <div className="space-y-4">
                {Object.entries(INDUSTRY_CONFIG).map(([key, config]) => {
                  const data = heatmapData[key.toLowerCase() as keyof IndustryHeatmapData];
                  const Icon = config.icon;
                  
                  return (
                    <div key={key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className={`h-4 w-4 text-slate-400`} />
                          <span className="font-bold text-sm">{config.label}</span>
                        </div>
                        <span className="text-xs text-slate-500">
                          알림 {data.alerts} · 과제 {data.tasks}
                        </span>
                      </div>
                      <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${getHeatmapColor(data.score)} transition-all duration-500`}
                          style={{ width: `${data.score}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
                
                <div className="pt-4 border-t border-slate-100">
                  <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase">
                    <span>영향도 범례</span>
                  </div>
                  <div className="flex items-center gap-1 mt-2">
                    <div className="flex-1 h-2 bg-green-100 rounded" />
                    <div className="flex-1 h-2 bg-green-300 rounded" />
                    <div className="flex-1 h-2 bg-yellow-400 rounded" />
                    <div className="flex-1 h-2 bg-orange-400 rounded" />
                    <div className="flex-1 h-2 bg-red-500 rounded" />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                    <span>낮음</span>
                    <span>높음</span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      
      {/* D-Day Countdown */}
      <Card className="print:break-inside-avoid">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            이행 기한 D-Day
          </CardTitle>
          <CardDescription>
            30일 내 마감 예정 항목
          </CardDescription>
        </CardHeader>
        <CardContent>
          {timelineSummary ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Stats Summary */}
              <div className="bg-slate-900 text-white rounded-xl p-6">
                <div className="text-4xl font-black">
                  {timelineSummary.next_30_days.total}
                </div>
                <div className="text-sm text-slate-300 mt-1">
                  30일 내 일정
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <Badge className="bg-red-500 text-white border-0">
                    중요 {timelineSummary.next_30_days.critical}
                  </Badge>
                </div>
              </div>
              
              {/* Urgent Items */}
              {timelineSummary.urgent_within_7_days.slice(0, 3).map((item, idx) => (
                <div 
                  key={item.event_id}
                  className={`p-4 rounded-xl border-2 ${
                    item.days_remaining <= 3 
                      ? 'border-red-300 bg-red-50' 
                      : 'border-orange-200 bg-orange-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Badge 
                      className={item.days_remaining <= 3 ? 'bg-red-500' : 'bg-orange-500'}
                    >
                      D-{item.days_remaining}
                    </Badge>
                    {item.is_critical && (
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                  <p className="text-sm font-medium text-slate-900 line-clamp-2">
                    {item.description}
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    <Clock className="h-3 w-3 inline mr-1" />
                    {new Date(item.event_date).toLocaleDateString('ko-KR')}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-slate-400">
              예정된 일정이 없습니다
            </p>
          )}
        </CardContent>
      </Card>
      
      {/* Footer */}
      <div className="text-center text-xs text-slate-400 pt-4 print:pt-8">
        <p>FSC Policy RAG System | 자동 생성 보고서</p>
        {lastUpdated && (
          <p>마지막 업데이트: {lastUpdated.toLocaleString('ko-KR')}</p>
        )}
      </div>
    </div>
  );
}
