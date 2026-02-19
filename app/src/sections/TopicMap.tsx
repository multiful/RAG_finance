import { useEffect, useState } from 'react';
import { 
  Zap, 
  TrendingUp, 
  FileText, 
  AlertTriangle,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { getTopics, getAlerts, detectTopics } from '@/lib/api';
import type { Topic, Alert as AlertType } from '@/types';


export default function TopicMap() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [topicsResponse, alertsData] = await Promise.all([
        getTopics({ days: 7 }),
        getAlerts(),
      ]);
      setTopics(topicsResponse.topics);
      setAlerts(alertsData);
      setError(null);
    } catch (err: any) {
      console.error('Error fetching topics:', err);
      setError(err.response?.data?.detail || err.message || '데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDetect = async () => {
    setDetecting(true);
    setError(null);
    try {
      await detectTopics(7);
      await fetchData();
    } catch (err: any) {
      console.error('Error detecting topics:', err);
      setError(err.response?.data?.detail || err.message || '토픽 탐지 중 오류가 발생했습니다.');
    } finally {
      setDetecting(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'med':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      default:
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    }
  };

  const getSurgeColor = (score: number) => {
    if (score >= 75) return 'text-red-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-emerald-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header with quick actions */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">Issue Radar</h2>
          <p className="text-slate-500 mt-2 text-lg">
            임베딩 기반 클러스터링과 Surge Score 기반 실시간 이슈 탐지
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline"
            onClick={() => fetchData()} 
            disabled={loading || detecting}
            className="border-slate-200 text-slate-600 font-semibold h-11 px-5 rounded-xl hover:bg-slate-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading && !detecting ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
          <Button 
            onClick={handleDetect} 
            disabled={detecting || loading}
            className="gradient-primary text-white font-bold h-11 px-6 rounded-xl shadow-lg shadow-primary/20"
          >
            <Zap className={`w-4 h-4 mr-2 ${detecting ? 'animate-pulse' : ''}`} />
            {detecting ? '이슈 분석 중...' : '신규 토픽 탐지'}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="animate-in slide-in-from-top-4 duration-500 border-none shadow-md bg-red-50 text-red-700">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle className="font-bold">분석 오류</AlertTitle>
          <AlertDescription className="font-medium">
            {error}
            <Button variant="outline" size="sm" onClick={() => fetchData()} className="ml-4 h-8 bg-white border-red-200 text-red-700 hover:bg-red-50 font-bold rounded-lg">
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Surging Topics Alert */}
      {alerts.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2 px-2">
            <AlertTriangle className="w-6 h-6 text-rose-500" />
            실시간 고위험 경보
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {alerts.slice(0, 4).map((alert) => (
              <Card 
                key={alert.alert_id}
                className="border-none shadow-md bg-white hover:shadow-xl transition-all duration-300 rounded-2xl overflow-hidden group"
              >
                <div className={`h-1 w-full ${alert.severity === 'high' ? 'bg-rose-500' : 'bg-amber-500'}`} />
                <CardContent className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <Badge className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border-none ${getSeverityColor(alert.severity)}`}>
                      {alert.severity === 'high' ? 'Critical' : 'Warning'}
                    </Badge>
                    <div className="text-right">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Surge Score</p>
                      <p className={`text-xl font-black ${getSurgeColor(alert.surge_score)}`}>{alert.surge_score.toFixed(0)}</p>
                    </div>
                  </div>
                  <h4 className="text-lg font-bold text-slate-900 mb-2 group-hover:text-primary transition-colors line-clamp-1">{alert.topic_name || '분석 중인 토픽'}</h4>
                  <div className="flex flex-wrap gap-2 mt-4">
                    {alert.industries.map((ind, idx) => (
                      <span key={idx} className="text-[10px] font-bold px-2 py-1 bg-slate-50 text-slate-500 rounded-md border border-slate-100 uppercase tracking-tighter">
                        {ind}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Topic Clusters */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Topic List */}
        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              주요 토픽 클러스터
            </h3>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Top 10 Trending</span>
          </div>

          <div className="space-y-4">
            {loading && !detecting ? (
              [1, 2, 3].map(i => <Skeleton key={i} className="h-32 w-full rounded-2xl" />)
            ) : topics.length === 0 ? (
              <Card className="border-2 border-dashed border-slate-200 bg-slate-50/50 rounded-3xl p-12 text-center">
                <div className="w-20 h-20 rounded-3xl bg-white shadow-sm flex items-center justify-center mx-auto mb-6">
                  <TrendingUp className="w-10 h-10 text-slate-200" />
                </div>
                <h4 className="text-lg font-bold text-slate-900 mb-2">탐지된 토픽이 없습니다</h4>
                <p className="text-slate-500 mb-8 max-w-xs mx-auto font-medium">
                  최근 7일간의 데이터를 분석하여 새로운 정책 이슈를 클러스터링합니다.
                </p>
                <Button onClick={handleDetect} className="gradient-primary text-white font-bold h-11 px-8 rounded-xl shadow-lg shadow-primary/20">
                  지금 분석 실행
                </Button>
              </Card>
            ) : (
              topics.slice(0, 10).map((topic, index) => (
                <Card 
                  key={topic.topic_id}
                  className="border-none shadow-sm bg-white hover:shadow-md transition-all duration-300 rounded-2xl overflow-hidden group"
                >
                  <CardContent className="p-6">
                    <div className="flex items-start gap-6">
                      <div className="w-12 h-12 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-black text-xl flex-shrink-0 shadow-lg shadow-slate-200 group-hover:scale-110 transition-transform">
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h4 className="text-lg font-bold text-slate-900 truncate">{topic.topic_name || 'Unnamed Topic'}</h4>
                          <Badge variant="secondary" className="bg-slate-100 text-slate-600 border-none font-bold">
                            {topic.document_count} Docs
                          </Badge>
                        </div>
                        <p className="text-sm font-medium text-slate-500 line-clamp-2 mb-4">
                          {topic.topic_summary}
                        </p>
                        
                        <div className="flex items-center gap-6">
                          <div className="flex items-center gap-3 flex-1 max-w-xs">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Surge Score</span>
                            <div className="flex-1 h-1.5 bg-slate-50 rounded-full overflow-hidden border border-slate-100">
                              <div 
                                className={`h-full transition-all duration-1000 ${getSurgeColor(topic.surge_score).replace('text-', 'bg-')}`} 
                                style={{ width: `${topic.surge_score}%` }} 
                              />
                            </div>
                            <span className={`text-sm font-black w-8 ${getSurgeColor(topic.surge_score)}`}>
                              {topic.surge_score.toFixed(0)}
                            </span>
                          </div>
                        </div>

                        {topic.representative_documents.length > 0 && (
                          <div className="mt-5 pt-5 border-t border-slate-50 flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
                            {topic.representative_documents.slice(0, 2).map((doc) => (
                              <a
                                key={doc.document_id}
                                href={doc.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 min-w-[200px] p-3 rounded-xl bg-slate-50/50 hover:bg-primary/5 transition-colors border border-slate-100 group/link"
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <FileText className="w-3 h-3 text-slate-400 group-hover/link:text-primary transition-colors" />
                                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Source Link</span>
                                </div>
                                <p className="text-xs font-bold text-slate-700 line-clamp-1 group-hover/link:text-primary transition-colors">{doc.title}</p>
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Topic Visualization */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              이슈 상관관계 맵
            </h3>
          </div>
          
          <Card className="border-none shadow-sm bg-white rounded-[2rem] overflow-hidden sticky top-24">
            <CardContent className="p-0">
              <div className="h-[600px] relative bg-gradient-to-br from-white to-slate-50/50 p-8">
                {topics.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center px-10">
                    <div className="w-24 h-24 rounded-[2rem] bg-slate-50 flex items-center justify-center mb-6">
                      <TrendingUp className="w-12 h-12 text-slate-200" />
                    </div>
                    <p className="text-slate-400 font-bold text-sm uppercase tracking-widest leading-relaxed">
                      분석을 실행하면<br />토픽간 거리를 시각화합니다
                    </p>
                  </div>
                ) : (
                  <div className="w-full h-full relative">
                    {topics.slice(0, 8).map((topic, index) => {
                      const size = Math.max(100, topic.document_count * 20);
                      const left = (index % 2) * 45 + 5 + Math.random() * 10;
                      const top = Math.floor(index / 2) * 20 + 5 + Math.random() * 10;
                      
                      const colors = [
                        'from-indigo-500/10 to-indigo-500/20 text-indigo-700 border-indigo-200',
                        'from-emerald-500/10 to-emerald-500/20 text-emerald-700 border-emerald-200',
                        'from-amber-500/10 to-amber-500/20 text-amber-700 border-amber-200',
                        'from-rose-500/10 to-rose-500/20 text-rose-700 border-rose-200',
                        'from-violet-500/10 to-violet-500/20 text-violet-700 border-violet-200',
                        'from-cyan-500/10 to-cyan-500/20 text-cyan-700 border-cyan-200',
                      ];
                      
                      const colorClass = colors[index % colors.length];
                      
                      return (
                        <div
                          key={topic.topic_id}
                          className={`absolute rounded-[2.5rem] flex items-center justify-center text-center p-6 transition-all hover:scale-110 cursor-pointer bg-gradient-to-br shadow-lg shadow-black/5 border animate-in zoom-in duration-1000 delay-${index * 100} ${colorClass}`}
                          style={{
                            width: size,
                            height: size,
                            left: `${left}%`,
                            top: `${top}%`,
                          }}
                        >
                          <div>
                            <p className="text-xs font-black uppercase tracking-tighter mb-1 opacity-60">Issue {index + 1}</p>
                            <p className="text-sm font-black leading-tight line-clamp-3">
                              {topic.topic_name}
                            </p>
                            <div className="mt-2 flex items-center justify-center gap-1">
                              <div className="w-1 h-1 rounded-full bg-current opacity-40" />
                              <span className="text-[10px] font-black opacity-60 uppercase">{topic.document_count} Cases</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
