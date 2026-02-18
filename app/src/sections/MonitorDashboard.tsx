import { useEffect, useState } from 'react';
import { 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Clock,
  TrendingUp,
  AlertTriangle,
  Database
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { getDashboardStats, triggerCollection, getRecentDocuments } from '@/lib/api';
import type { DashboardStats, Document } from '@/types';

export default function MonitorDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);

  const fetchData = async () => {
    try {
      const [statsData, recentData] = await Promise.all([
        getDashboardStats(),
        getRecentDocuments(24),
      ]);
      setStats(statsData);
      setRecentDocs(recentData.documents || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const handleTriggerCollection = async () => {
    setCollecting(true);
    try {
      await triggerCollection();
      setTimeout(fetchData, 2000);
    } catch (error) {
      console.error('Error triggering collection:', error);
    } finally {
      setCollecting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

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

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">실시간 수집 모니터</h2>
          <p className="text-muted-foreground mt-1">
            금융위원회 RSS 기반 최신 문서 수집 현황
          </p>
        </div>
        <Button 
          onClick={handleTriggerCollection} 
          disabled={collecting}
          className="gradient-primary text-white"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${collecting ? 'animate-spin' : ''}`} />
          {collecting ? '수집중...' : '수집 시작'}
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">총 문서 수</p>
                <p className="text-3xl font-bold mt-1">
                  {stats?.total_documents?.toLocaleString() || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Database className="w-6 h-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">24시간 신규</p>
                <p className="text-3xl font-bold mt-1 text-emerald-600">
                  +{stats?.documents_24h || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">활성 경보</p>
                <p className="text-3xl font-bold mt-1 text-amber-600">
                  {stats?.active_alerts || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-amber-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="card-elevated">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">고위험 경보</p>
                <p className="text-3xl font-bold mt-1 text-red-600">
                  {stats?.high_severity_alerts || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
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
            {stats?.collection_status?.map((source) => (
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
            ))}
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
            {recentDocs.length === 0 ? (
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
