import { useEffect, useState } from 'react';
import { 
  Zap, 
  TrendingUp, 
  FileText, 
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
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
      const [topicsData, alertsData] = await Promise.all([
        getTopics({ days: 7 }),
        getAlerts(),
      ]);
      setTopics(topicsData);
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
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">이슈맵 + 급부상 경보</h2>
          <p className="text-muted-foreground mt-1">
            임베딩 기반 클러스터링과 Surge Score 기반 이슈 탐지
          </p>
        </div>
        <Button 
          onClick={handleDetect} 
          disabled={detecting || loading}
          className="gradient-primary text-white"
        >
          <Zap className={`w-4 h-4 mr-2 ${detecting ? 'animate-pulse' : ''}`} />
          {detecting ? '탐지중...' : '토픽 탐지'}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="bg-red-50 border-red-200">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>오류 발생</AlertTitle>
          <AlertDescription>
            {error}
            <Button variant="outline" size="sm" onClick={() => fetchData()} className="ml-4 h-7 text-xs">
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Surging Topics Alert */}
      {alerts.length > 0 && (
        <Card className="card-elevated border-red-200 bg-red-50/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-5 h-5" />
              급부상 토픽 경보 ({alerts.length}건)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert) => (
                <div 
                  key={alert.alert_id}
                  className="flex items-center gap-4 p-4 bg-white rounded-xl shadow-sm"
                >
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${getSeverityColor(alert.severity)}`}>
                    {alert.severity === 'high' ? '고위험' : alert.severity === 'med' ? '중위험' : '저위험'}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{alert.topic_name || 'Unknown Topic'}</p>
                    <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                      <span>Surge Score: {alert.surge_score.toFixed(1)}</span>
                      {alert.industries.length > 0 && (
                        <span>영향 업권: {alert.industries.join(', ')}</span>
                      )}
                    </div>
                  </div>
                  <div className="w-24">
                    <Progress 
                      value={alert.surge_score} 
                      className="h-2"
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Topic Clusters */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Topic List */}
        <Card className="card-elevated">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              토픽 클러스터 (Top 10)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {topics.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  탐지된 토픽이 없습니다. 토픽 탐지를 실행하세요.
                </p>
              ) : (
                topics.slice(0, 10).map((topic, index) => (
                  <div 
                    key={topic.topic_id}
                    className="p-4 bg-muted/50 rounded-xl hover:bg-muted transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center text-white font-bold text-sm">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{topic.topic_name || 'Unnamed Topic'}</p>
                          <Badge variant="outline" className="text-xs">
                            {topic.document_count}개 문서
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {topic.topic_summary}
                        </p>
                        <div className="flex items-center gap-4 mt-3">
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Surge Score:</span>
                            <span className={`font-semibold ${getSurgeColor(topic.surge_score)}`}>
                              {topic.surge_score.toFixed(1)}
                            </span>
                          </div>
                          <Progress 
                            value={topic.surge_score} 
                            className="w-24 h-2"
                          />
                        </div>
                        {/* Representative Documents */}
                        {topic.representative_documents.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-border">
                            <p className="text-xs text-muted-foreground mb-2">대표 문서:</p>
                            <div className="space-y-1">
                              {topic.representative_documents.slice(0, 3).map((doc) => (
                                <a
                                  key={doc.document_id}
                                  href={doc.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-2 text-sm text-primary hover:underline"
                                >
                                  <FileText className="w-3 h-3" />
                                  <span className="truncate">{doc.title}</span>
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Topic Visualization */}
        <Card className="card-elevated">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              토픽 분포 시각화
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[500px] flex items-center justify-center bg-gradient-to-br from-lavender-50 to-lavender-100 rounded-xl">
              {topics.length === 0 ? (
                <div className="text-center">
                  <TrendingUp className="w-16 h-16 text-lavender-300 mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    토픽 탐지를 실행하면<br />클   스터링 시각화가 표시됩니다
                  </p>
                </div>
              ) : (
                <div className="w-full h-full p-6">
                  {/* Simple bubble chart representation */}
                  <div className="relative w-full h-full">
                    {topics.slice(0, 8).map((topic, index) => {
                      const size = Math.max(60, topic.document_count * 15);
                      const left = (index % 3) * 33 + 10 + Math.random() * 10;
                      const top = Math.floor(index / 3) * 30 + 10 + Math.random() * 10;
                      
                      return (
                        <div
                          key={topic.topic_id}
                          className="absolute rounded-full flex items-center justify-center text-center p-4 transition-all hover:scale-110 cursor-pointer"
                          style={{
                            width: size,
                            height: size,
                            left: `${left}%`,
                            top: `${top}%`,
                            backgroundColor: `hsla(${260 + index * 20}, 70%, ${85 - index * 5}%, 0.8)`,
                            border: `2px solid hsla(${260 + index * 20}, 70%, 55%, 0.5)`,
                          }}
                        >
                          <div>
                            <p className="text-xs font-medium line-clamp-2">
                              {topic.topic_name}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              {topic.document_count}개
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
