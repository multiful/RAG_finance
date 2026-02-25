/**
 * Settings Page - 시스템 설정 및 데이터 수집 관리
 */
import { useState, useEffect } from 'react';
import { 
  Settings, 
  Database, 
  RefreshCw, 
  Clock,
  Loader2,
  ExternalLink,
  FileText,
  Beaker,
  TrendingUp,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { useCollection } from '@/contexts/CollectionContext';
import { getLatestEvaluation, runEvaluation, getMetricsSummary, getCollectionSourceStats, type EvaluationMetrics, type MetricsSummary, type CollectionSourceStats } from '@/lib/api';

interface DataSource {
  id: string;
  name: string;
  description: string;
  url: string;
  status: 'active' | 'inactive' | 'error' | 'preparing';
  lastSync?: string;
  documentCount?: number;
}

const DATA_SOURCES_BASE: Omit<DataSource, 'status' | 'documentCount'>[] = [
  { id: 'fsc', name: '금융위원회 (FSC)', description: '금융 정책 및 규제 발표', url: 'https://www.fsc.go.kr' },
  { id: 'fss', name: '금융감독원 (FSS)', description: '금융 감독 및 검사 정보', url: 'https://www.fss.or.kr' },
  { id: 'klia', name: '생명보험협회', description: '생명보험 업계 규제 동향', url: 'https://www.klia.or.kr' },
  { id: 'knia', name: '손해보험협회', description: '손해보험 업계 규제 동향', url: 'https://www.knia.or.kr' },
];

function mapSourceStatsToSources(stats: CollectionSourceStats | null): DataSource[] {
  if (!stats?.by_source?.length) {
    return DATA_SOURCES_BASE.map((s) => ({ ...s, status: 'inactive' as const, documentCount: 0 }));
  }
  const fscCount = stats.by_source.filter((x) => x.name === '금융위원회' || (x.fid && ['0111', '0112', '0114', '0411'].includes(x.fid))).reduce((a, x) => a + x.document_count, 0);
  const fssCount = stats.by_source.filter((x) => x.name === '금융감독원' || x.fid === 'FSS').reduce((a, x) => a + x.document_count, 0);
  const byId: Record<string, number> = { fsc: fscCount, fss: fssCount, klia: 0, knia: 0 };
  return DATA_SOURCES_BASE.map((s) => {
    const count = byId[s.id] ?? 0;
    const status: DataSource['status'] = s.id === 'klia' || s.id === 'knia' ? 'preparing' : count > 0 ? 'active' : 'inactive';
    return { ...s, status, documentCount: count };
  });
}

export default function SettingsPage() {
  const { isCollecting, jobProgress, startCollection, lastResult } = useCollection();
  const [autoSync, setAutoSync] = useState(true);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationMetrics | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [sourceStats, setSourceStats] = useState<CollectionSourceStats | null>(null);

  const dataSources = mapSourceStatsToSources(sourceStats);

  useEffect(() => {
    loadEvaluation();
    loadMetrics();
    loadSourceStats();
  }, []);

  useEffect(() => {
    if (lastResult?.status === 'success_collect' || lastResult?.status === 'no_change') {
      loadSourceStats();
    }
  }, [lastResult?.status, lastResult?.result?.total_new]);

  const loadSourceStats = async () => {
    try {
      const stats = await getCollectionSourceStats();
      setSourceStats(stats);
    } catch (e) {
      console.error('Failed to load source stats:', e);
    }
  };

  const loadEvaluation = async () => {
    try {
      const result = await getLatestEvaluation();
      if (result.has_evaluation && result.evaluation) {
        setEvaluation(result.evaluation);
      }
    } catch (error) {
      console.error('Failed to load evaluation:', error);
    }
  };

  const loadMetrics = async () => {
    try {
      const result = await getMetricsSummary();
      setMetrics(result);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  };

  const handleRunEvaluation = async () => {
    setIsEvaluating(true);
    try {
      const result = await runEvaluation(8);
      setEvaluation(result.evaluation);
      await loadMetrics();
      const score = (result.evaluation.overall_score * 100).toFixed(1);
      toast.success(`RAGAS 평가 완료 · 종합 ${score}%`);
    } catch (error) {
      console.error('Evaluation failed:', error);
      toast.error('평가 실행에 실패했습니다.');
    } finally {
      setIsEvaluating(false);
    }
  };

  const getScoreStatus = (score: number) => {
    if (score >= 0.8) return { color: 'text-emerald-600 bg-emerald-100', label: '우수' };
    if (score >= 0.6) return { color: 'text-blue-600 bg-blue-100', label: '양호' };
    return { color: 'text-amber-600 bg-amber-100', label: '개선필요' };
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-page-enter">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
          <Settings className="h-7 w-7 text-slate-600" />
          설정
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          시스템 설정 및 데이터 수집 관리
        </p>
      </div>

      {/* Data Collection Section */}
      <Card className="border-none shadow-sm transition-shadow duration-200 hover:shadow-md rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Database className="w-5 h-5 text-indigo-500" />
            데이터 수집
          </CardTitle>
          <CardDescription>
            규제 데이터 소스 관리 및 수집 현황
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Collection Status */}
          <div className="p-4 rounded-xl bg-slate-50 transition-colors duration-200">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="font-semibold text-slate-900">수집 상태</p>
                <p className="text-sm text-slate-500">
                  {isCollecting 
                    ? `${jobProgress?.stage || '처리 중'}...` 
                    : lastResult?.status === 'completed'
                      ? `최근 수집: 신규 ${lastResult.result?.total_new || 0}건`
                      : '대기 중'
                  }
                </p>
              </div>
              <Button 
                onClick={startCollection}
                disabled={isCollecting}
                className="bg-indigo-600 hover:bg-indigo-700 active:scale-[0.98] transition-all duration-200"
              >
                {isCollecting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    수집 중
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    지금 수집
                  </>
                )}
              </Button>
            </div>
            
            {isCollecting && jobProgress && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">{jobProgress.message || jobProgress.stage}</span>
                  <span className="font-medium">{jobProgress.progress}%</span>
                </div>
                <Progress value={jobProgress.progress} className="h-2" />
              </div>
            )}
          </div>

          {/* Auto Sync Toggle */}
          <div className="flex items-center justify-between p-4 rounded-xl border border-slate-200 transition-colors duration-200 hover:border-slate-300 hover:bg-slate-50/50">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                <Clock className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">자동 수집</p>
                <p className="text-sm text-slate-500">매시간 자동으로 새 문서를 수집합니다</p>
              </div>
            </div>
            <Switch 
              checked={autoSync} 
              onCheckedChange={setAutoSync}
            />
          </div>

          {/* Data Sources - 실제 수집 현황 반영 */}
          <div className="space-y-3">
            <h3 className="font-semibold text-slate-900">데이터 소스</h3>
            <p className="text-sm text-slate-500">현재 수집: 금융위원회 RSS 4개 채널 + 금융감독원 스크래핑. 생명/손해보험협회는 준비 중입니다.</p>
            {dataSources.map((source) => (
              <div 
                key={source.id}
                className="flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm transition-all duration-200"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                    source.status === 'active' ? 'bg-emerald-500' :
                    source.status === 'preparing' ? 'bg-amber-400' :
                    source.status === 'error' ? 'bg-red-500' : 'bg-slate-300'
                  }`} />
                  <div>
                    <p className="font-semibold text-slate-900">{source.name}</p>
                    <p className="text-sm text-slate-500">{source.description}</p>
                    {source.documentCount !== undefined && source.documentCount > 0 && (
                      <p className="text-xs text-slate-400 mt-0.5">문서 {source.documentCount}건</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className={`text-xs ${
                    source.status === 'active' ? 'bg-emerald-100 text-emerald-700' :
                    source.status === 'preparing' ? 'bg-amber-100 text-amber-700' :
                    source.status === 'error' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {source.status === 'active' ? '활성' : source.status === 'preparing' ? '준비 중' : source.status === 'error' ? '오류' : '비활성'}
                  </Badge>
                  <a 
                    href={source.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors duration-150"
                    aria-label={`${source.name} 열기`}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* RAGAS Evaluation Section */}
      <Card className="border-none shadow-sm transition-shadow duration-200 hover:shadow-md rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Beaker className="w-5 h-5 text-purple-500" />
            RAG 품질 평가 (RAGAS)
          </CardTitle>
          <CardDescription>
            RAG 답변의 충실도·관련성·검색 정밀도·재현율을 자동 측정해, 개선 포인트를 파악합니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Run Evaluation */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-purple-50 to-indigo-50 transition-shadow duration-200">
            <div>
              <p className="font-semibold text-slate-900">평가 실행</p>
              <p className="text-sm text-slate-500">
                {evaluation 
                  ? `마지막 평가: ${new Date(evaluation.evaluated_at).toLocaleString('ko-KR')}`
                  : '아직 평가가 실행되지 않았습니다'
                }
              </p>
            </div>
            <Button 
              onClick={handleRunEvaluation}
              disabled={isEvaluating}
              className="bg-purple-600 hover:bg-purple-700 active:scale-[0.98] transition-all duration-200"
            >
              {isEvaluating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  평가 중...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 mr-2" />
                  평가 시작
                </>
              )}
            </Button>
          </div>

          {/* Evaluation Results */}
          {evaluation && (
            <div className="space-y-4">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                평가 결과
              </h3>
              
              {/* Overall Score */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white transition-transform duration-200 hover:scale-[1.01]">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-white/80">종합 점수</p>
                    <p className="text-3xl font-bold">{(evaluation.overall_score * 100).toFixed(1)}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-white/80">샘플 수</p>
                    <p className="text-xl font-semibold">{evaluation.sample_size}개</p>
                  </div>
                </div>
              </div>

              {/* Individual Metrics */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { key: 'faithfulness', label: '충실도', desc: '답변이 문서에 충실한가' },
                  { key: 'answer_relevancy', label: '관련성', desc: '질문과 답변의 연관성' },
                  { key: 'context_precision', label: '정밀도', desc: '검색 컨텍스트의 정확성' },
                  { key: 'context_recall', label: '재현율', desc: '필요 정보 포함 여부' }
                ].map(({ key, label, desc }) => {
                  const score = evaluation[key as keyof EvaluationMetrics] as number;
                  const status = getScoreStatus(score);
                  
                  return (
                    <div key={key} className="p-4 rounded-xl border border-slate-200 bg-white transition-shadow duration-200 hover:shadow-md">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-700">{label}</span>
                        <Badge className={`text-xs ${status.color}`}>
                          {status.label}
                        </Badge>
                      </div>
                      <span className="text-2xl font-bold text-slate-900">
                        {(score * 100).toFixed(1)}%
                      </span>
                      <p className="text-xs text-slate-500 mt-1">{desc}</p>
                      <Progress value={score * 100} className="h-1.5 mt-2" />
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* About */}
      <Card className="border-none shadow-sm bg-gradient-to-br from-slate-900 to-indigo-900 text-white transition-shadow duration-200 hover:shadow-lg">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-bold">RegTech Platform</h3>
              <p className="text-slate-300 text-sm mt-1">
                RAG 기반 금융 규제 인텔리전스 시스템
              </p>
              <div className="flex items-center gap-2 mt-3">
                <Badge className="bg-white/20 text-white text-xs">LangGraph Agent</Badge>
                <Badge className="bg-white/20 text-white text-xs">RAGAS Evaluation</Badge>
                <Badge className="bg-white/20 text-white text-xs">Real-time</Badge>
              </div>
            </div>
            <FileText className="w-12 h-12 text-white/20" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
