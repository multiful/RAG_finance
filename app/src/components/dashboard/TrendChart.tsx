/**
 * TrendChart: Redis/DB에서 가져온 급부상 토픽 시각화.
 */
import { useState, useMemo } from 'react';
import { 
  TrendingUp, 
  AlertTriangle,
  Zap,
  Filter
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  ReferenceLine
} from 'recharts';

interface TopicTrend {
  date: string;
  topic_name: string;
  surge_score: number;
  document_count: number;
  industries: string[];
}

interface TrendChartProps {
  data: TopicTrend[];
  title?: string;
  chartType?: 'line' | 'bar' | 'bubble';
}

export default function TrendChart({ 
  data, 
  title = "급부상 토픽 트렌드",
  chartType = 'line'
}: TrendChartProps) {
  const [selectedIndustry, setSelectedIndustry] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<number>(7); // days

  // 필터링된 데이터
  const filteredData = useMemo(() => {
    let filtered = data;
    
    // 업권 필터
    if (selectedIndustry !== 'all') {
      filtered = filtered.filter(d => 
        d.industries.includes(selectedIndustry)
      );
    }
    
    // 시간 범위 필터
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - timeRange);
    
    filtered = filtered.filter(d => 
      new Date(d.date) >= cutoffDate
    );
    
    // 날짜순 정렬
    return filtered.sort((a, b) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  }, [data, selectedIndustry, timeRange]);

  // 차트 데이터 변환
  const chartData = useMemo(() => {
    // 날짜별 그룹화
    const grouped = filteredData.reduce((acc, item) => {
      const date = item.date.slice(0, 10);
      if (!acc[date]) {
        acc[date] = { date, topics: [], totalScore: 0 };
      }
      acc[date].topics.push(item);
      acc[date].totalScore += item.surge_score;
      return acc;
    }, {} as Record<string, any>);

    return Object.values(grouped).map((g: any) => ({
      date: g.date,
      score: g.totalScore,
      topicCount: g.topics.length,
      topTopic: g.topics[0]?.topic_name || ''
    }));
  }, [filteredData]);

  // Surge Score 색상
  const getScoreColor = (score: number) => {
    if (score >= 75) return '#ef4444'; // red-500
    if (score >= 50) return '#f59e0b'; // amber-500
    return '#10b981'; // emerald-500
  };

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-lavender-100">
          <p className="text-sm font-medium">{label}</p>
          <p className="text-lg font-bold text-primary">
            Surge Score: {data.score.toFixed(1)}
          </p>
          <p className="text-sm text-muted-foreground">
            토픽 수: {data.topicCount}
          </p>
          {data.topTopic && (
            <p className="text-xs text-muted-foreground mt-1">
              주요: {data.topTopic}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="card-elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              {title}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              최근 {timeRange}일간 급부상한 토픽 트렌드
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-red-500 border-red-200 bg-red-50">
              <AlertTriangle className="w-3 h-3 mr-1" />
              High
            </Badge>
            <Badge variant="outline" className="text-amber-500 border-amber-200 bg-amber-50">
              Med
            </Badge>
            <Badge variant="outline" className="text-emerald-500 border-emerald-200 bg-emerald-50">
              Low
            </Badge>
          </div>
        </div>

        {/* 필터 바 */}
        <div className="flex items-center gap-3 mt-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <select
              value={selectedIndustry}
              onChange={(e) => setSelectedIndustry(e.target.value)}
              className="h-9 px-3 rounded-md border border-input bg-background text-sm"
            >
              <option value="all">전체 업권</option>
              <option value="INSURANCE">보험</option>
              <option value="BANKING">은행</option>
              <option value="SECURITIES">증권</option>
            </select>
          </div>
          
          <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
            {[7, 14, 30].map((days) => (
              <button
                key={days}
                onClick={() => setTimeRange(days)}
                className={`
                  px-3 py-1 rounded text-sm transition-colors
                  ${timeRange === days 
                    ? 'bg-white shadow-sm text-primary' 
                    : 'text-muted-foreground hover:text-foreground'
                  }
                `}
              >
                {days}일
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            <TrendingUp className="w-12 h-12 mb-4 opacity-30" />
            <p>데이터가 없습니다</p>
          </div>
        ) : (
          <>
            {/* 메인 차트 */}
            <div className="h-64 mb-6">
              <ResponsiveContainer width="100%" height="100%">
                {chartType === 'bar' ? (
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => value.slice(5)} // MM-DD
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={getScoreColor(entry.score)} 
                        />
                      ))}
                    </Bar>
                    <ReferenceLine y={75} stroke="#ef4444" strokeDasharray="3 3" />
                    <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="3 3" />
                  </BarChart>
                ) : (
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => value.slice(5)}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line 
                      type="monotone" 
                      dataKey="score" 
                      stroke="#8b5cf6" 
                      strokeWidth={2}
                      dot={{ fill: '#8b5cf6', strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                    <ReferenceLine y={75} stroke="#ef4444" strokeDasharray="3 3" label="High" />
                    <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="3 3" label="Med" />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>

            {/* 토픽 리스트 */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                주요 급부상 토픽
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {filteredData
                  .sort((a, b) => b.surge_score - a.surge_score)
                  .slice(0, 5)
                  .map((topic, index) => (
                    <div 
                      key={`${topic.date}-${topic.topic_name}`}
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span className={`
                          w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                          ${topic.surge_score >= 75 ? 'bg-red-100 text-red-600' :
                            topic.surge_score >= 50 ? 'bg-amber-100 text-amber-600' :
                            'bg-emerald-100 text-emerald-600'}
                        `}>
                          {index + 1}
                        </span>
                        <div>
                          <p className="font-medium text-sm">{topic.topic_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(topic.date).toLocaleDateString('ko-KR')} • 
                            문서 {topic.document_count}개
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`
                          font-bold
                          ${topic.surge_score >= 75 ? 'text-red-600' :
                            topic.surge_score >= 50 ? 'text-amber-600' :
                            'text-emerald-600'}
                        `}>
                          {topic.surge_score.toFixed(1)}
                        </p>
                        <div className="flex gap-1 mt-1">
                          {topic.industries.map((ind) => (
                            <Badge key={ind} variant="outline" className="text-xs px-1">
                              {ind === 'INSURANCE' ? '보' : 
                               ind === 'BANKING' ? '은' : '증'}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// 버블 차트 변형 (토픽 클러스터링 시각화)
interface BubbleChartProps {
  topics: Array<{
    topic_id: string;
    topic_name: string;
    surge_score: number;
    document_count: number;
    x: number;
    y: number;
  }>;
}

export function TopicBubbleChart({ topics }: BubbleChartProps) {
  return (
    <Card className="card-elevated">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className="w-5 h-5 text-primary" />
          토픽 클러스터 맵
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative h-80 bg-gradient-to-br from-lavender-50 to-lavender-100 rounded-xl overflow-hidden">
          {topics.map((topic) => {
            const size = Math.max(40, topic.document_count * 8);
            const color = topic.surge_score >= 75 ? 'bg-red-400' :
                         topic.surge_score >= 50 ? 'bg-amber-400' :
                         'bg-emerald-400';
            
            return (
              <div
                key={topic.topic_id}
                className={`
                  absolute rounded-full flex items-center justify-center
                  text-white text-xs font-medium shadow-lg
                  transition-transform hover:scale-110 cursor-pointer
                  ${color}
                `}
                style={{
                  width: size,
                  height: size,
                  left: `${topic.x}%`,
                  top: `${topic.y}%`,
                  transform: 'translate(-50%, -50%)'
                }}
                title={`${topic.topic_name} (Score: ${topic.surge_score.toFixed(1)})`}
              >
                <span className="text-center px-2 line-clamp-2">
                  {topic.topic_name.slice(0, 8)}
                </span>
              </div>
            );
          })}
        </div>
        
        <div className="flex justify-center gap-4 mt-4 text-sm">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-red-400" />
            High (75+)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-amber-400" />
            Med (50-75)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-emerald-400" />
            Low (&lt;50)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
