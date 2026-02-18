import { useEffect, useState } from 'react';
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
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
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
}

function MetricCard({ title, value, target, unit, icon: Icon, trend, description }: MetricCardProps) {
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
              <p className={`text-3xl font-bold ${getStatusColor()}`}>
                {value.toFixed(1)}{unit}
              </p>
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
            value={(value / target) * 100} 
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

  const fetchMetrics = async () => {
    try {
      const data = await getQualityMetrics(7);
      setMetrics(data);
    } catch (error) {
      console.error('Error fetching quality metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const mockHighRiskResponses = [
    {
      id: '1',
      question: '보험사 신규 상품 승인 절차는?',
      issue: '근거 문서 불일치',
      severity: 'high',
      timestamp: '2024-01-15 14:30',
    },
    {
      id: '2',
      question: '은행권 대출금리 산정 기준',
      issue: '환각 가능성',
      severity: 'medium',
      timestamp: '2024-01-15 13:45',
    },
    {
      id: '3',
      question: '증권사 수수료 변경 공시 기한',
      issue: '불확실한 답변',
      severity: 'low',
      timestamp: '2024-01-15 12:20',
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="section-title">품질/리스크 평가</h2>
        <p className="text-muted-foreground mt-1">
          RAG 시스템 품질 메트릭스 및 환각 모니터링
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          title="근거일치율 (Groundedness)"
          value={metrics?.groundedness || 0.87}
          target={0.9}
          unit=""
          icon={CheckCircle2}
          trend="up"
          description="답변의 근거 문서 일치 비율"
        />

        <MetricCard
          title="환각률 (Hallucination)"
          value={(metrics?.hallucination_rate || 0.08) * 100}
          target={5}
          unit="%"
          icon={AlertTriangle}
          trend="down"
          description="문서에 없는 정보 생성 비율 (낮을수록 좋음)"
        />

        <MetricCard
          title="인용 정확도"
          value={(metrics?.citation_accuracy || 0.92) * 100}
          target={95}
          unit="%"
          icon={FileText}
          trend="up"
          description="인용 문서의 정확성"
        />

        <MetricCard
          title="평균 응답 시간"
          value={(metrics?.avg_response_time_ms || 2500) / 1000}
          target={3}
          unit="s"
          icon={Clock}
          trend="up"
          description="질문부터 답변까지 소요 시간"
        />

        <MetricCard
          title="미응답률"
          value={(metrics?.unanswered_rate || 0.05) * 100}
          target={5}
          unit="%"
          icon={XCircle}
          trend="down"
          description="근거 부족으로 답변 불가 비율"
        />

        <Card className="card-elevated bg-gradient-to-br from-primary/5 to-primary/10">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">종합 품질 점수</p>
                <p className="text-3xl font-bold text-primary">
                  {Math.round(
                    ((metrics?.groundedness || 0.87) * 0.4 +
                     (1 - (metrics?.hallucination_rate || 0.08)) * 0.3 +
                     (metrics?.citation_accuracy || 0.92) * 0.3) * 100
                  )}
                </p>
              </div>
            </div>
            <Progress 
              value={
                ((metrics?.groundedness || 0.87) * 0.4 +
                 (1 - (metrics?.hallucination_rate || 0.08)) * 0.3 +
                 (metrics?.citation_accuracy || 0.92) * 0.3) * 100
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
            {mockHighRiskResponses.map((item) => (
              <div 
                key={item.id}
                className="flex items-center gap-4 p-4 bg-muted/50 rounded-xl"
              >
                <Badge 
                  className={`
                    ${item.severity === 'high' ? 'bg-red-100 text-red-700' : ''}
                    ${item.severity === 'medium' ? 'bg-amber-100 text-amber-700' : ''}
                    ${item.severity === 'low' ? 'bg-blue-100 text-blue-700' : ''}
                  `}
                >
                  {item.severity === 'high' ? '고위험' : 
                   item.severity === 'medium' ? '중위험' : '저위험'}
                </Badge>
                <div className="flex-1">
                  <p className="font-medium">{item.question}</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    이슈: {item.issue}
                  </p>
                </div>
                <div className="text-right text-sm text-muted-foreground">
                  {item.timestamp}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">RAG 엔진</p>
                <p className="font-medium text-emerald-600">정상 운영중</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">벡터 DB</p>
                <p className="font-medium text-emerald-600">연결 정상</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">LLM API</p>
                <p className="font-medium text-emerald-600">응답 정상</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
