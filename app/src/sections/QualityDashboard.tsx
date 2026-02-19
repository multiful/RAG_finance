import { useEffect, useState, useCallback } from 'react';
import { 
  Shield, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle,
  TrendingUp,
  TrendingDown,
  Clock,
  FileText,
  AlertOctagon,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { getQualityMetrics } from '@/lib/api';
import type { QualityMetrics } from '@/types';

interface MetricCardProps {
  title: string;
  value: number;
  target: number;
  unit: string;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
  description: string;
  loading?: boolean;
}

function MetricCard({ title, value, target, unit, icon: Icon, trend, description, loading }: MetricCardProps) {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-emerald-500" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    if (value >= target) return 'text-emerald-600';
    if (value >= target * 0.8) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <Card className="card-elevated hover-lift">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm text-muted-foreground">{title}</p>
              {getTrendIcon()}
            </div>
            <div className="flex items-baseline gap-2 mt-2">
              {loading ? (
                <Skeleton className="h-9 w-24" />
              ) : (
                <p className={`text-3xl font-bold ${getStatusColor()}`}>
                  {value.toFixed(1)}{unit}
                </p>
              )}
              <span className="text-sm text-muted-foreground">
                / {target}{unit}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">{description}</p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Icon className="w-6 h-6 text-primary" />
          </div>
        </div>
        <div className="mt-4">
          <Progress 
            value={loading ? 0 : (value / target) * 100} 
            className="h-2"
          />
        </div>
      </CardContent>
    </Card>
  );
}

export default function QualityDashboard() {
  const [metrics, setMetrics] = useState<QualityMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const data = await getQualityMetrics(7);
      setMetrics(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching quality metrics:', err);
      if (!isSilent) setError('품질 지표를 불러오는 중 오류가 발생했습니다.');
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(() => fetchMetrics(true), 15000); // 15s polling
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  if (error && !metrics) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {error}
            <Button variant="outline" size="sm" onClick={() => fetchMetrics()} className="ml-4">
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">품질/리스크 평가</h2>
          <p className="text-muted-foreground mt-1">
            RAG 시스템 품질 메트릭스 및 환각 모니터링
          </p>
        </div>
        {loading && metrics && <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          title="근거일치율 (Groundedness)"
          value={metrics?.groundedness || 0}
          target={0.9}
          unit=""
          icon={CheckCircle2}
          trend="up"
          description="답변의 근거 문서 일치 비율"
          loading={loading && !metrics}
        />

        <MetricCard
          title="환각률 (Hallucination)"
          value={(metrics?.hallucination_rate || 0) * 100}
          target={5}
          unit="%"
          icon={AlertTriangle}
          trend="down"
          description="문서에 없는 정보 생성 비율"
          loading={loading && !metrics}
        />

        <MetricCard
          title="인용 정확도"
          value={(metrics?.citation_accuracy || 0) * 100}
          target={95}
          unit="%"
          icon={FileText}
          trend="up"
          description="인용 문서의 정확성"
          loading={loading && !metrics}
        />

        <MetricCard
          title="평균 응답 시간"
          value={(metrics?.avg_response_time_ms || 0) / 1000}
          target={3}
          unit="s"
          icon={Clock}
          trend="up"
          description="질문부터 답변까지 소요 시간"
          loading={loading && !metrics}
        />

        <MetricCard
          title="미응답률"
          value={(metrics?.unanswered_rate || 0) * 100}
          target={5}
          unit="%"
          icon={XCircle}
          trend="down"
          description="근거 부족으로 답변 불가 비율"
          loading={loading && !metrics}
        />

        <Card className="card-elevated bg-gradient-to-br from-primary/5 to-primary/10">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">종합 품질 점수</p>
                {loading && !metrics ? (
                  <Skeleton className="h-9 w-16 mt-1" />
                ) : (
                  <p className="text-3xl font-bold text-primary">
                    {Math.round(
                      ((metrics?.groundedness || 0) * 0.4 +
                       (1 - (metrics?.hallucination_rate || 0)) * 0.3 +
                       (metrics?.citation_accuracy || 0) * 0.3) * 100
                    )}
                  </p>
                )}
              </div>
            </div>
            <Progress 
              value={
                ((metrics?.groundedness || 0) * 0.4 +
                 (1 - (metrics?.hallucination_rate || 0)) * 0.3 +
                 (metrics?.citation_accuracy || 0) * 0.3) * 100
              } 
              className="h-3"
            />
            <p className="text-xs text-muted-foreground mt-2">
              Groundedness 40% + (1-Hallucination) 30% + Citation 30%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Risk Review Queue */}
      <Card className="card-elevated">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 text-red-500" />
            고위험 답변 리뷰 큐
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {loading && !metrics ? (
              [1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-xl" />)
            ) : (
              <div className="py-8 text-center text-muted-foreground italic">
                검토가 필요한 고위험 답변이 없습니다.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'RAG 엔진', status: '정상 운영중' },
          { label: '벡터 DB', status: '연결 정상' },
          { label: 'LLM API', status: '응답 정상' }
        ].map((item, i) => (
          <Card key={i} className="card-elevated">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{item.label}</p>
                  <p className="font-medium text-emerald-600">{item.status}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
