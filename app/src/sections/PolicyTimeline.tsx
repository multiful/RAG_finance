/**
 * Policy Timeline - Calendar view for regulatory deadlines and events.
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Calendar, 
  Clock, 
  AlertTriangle, 
  Download,
  ChevronLeft,
  ChevronRight,
  Building2,
  FileText,
  Bell
} from 'lucide-react';
import { getTimelineEvents, getTimelineSummary, getCriticalEvents, exportTimelineIcal } from '@/lib/api';
import type { TimelineEvent, TimelineResponse, TimelineSummary } from '@/types';

const EVENT_TYPE_LABELS: Record<string, string> = {
  effective_date: '시행일',
  deadline: '기한',
  grace_period_end: '유예기간 종료',
  submission_due: '제출 마감',
  review_date: '검토 예정',
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  effective_date: 'bg-blue-500',
  deadline: 'bg-red-500',
  grace_period_end: 'bg-orange-500',
  submission_due: 'bg-purple-500',
  review_date: 'bg-green-500',
};

const INDUSTRY_LABELS: Record<string, string> = {
  INSURANCE: '보험',
  BANKING: '은행',
  SECURITIES: '증권',
};

function EventCard({ event }: { event: TimelineEvent }) {
  const eventDate = new Date(event.event_date);
  const isOverdue = event.days_remaining < 0;
  const isUrgent = event.days_remaining >= 0 && event.days_remaining <= 7;
  
  return (
    <Card className={`mb-3 ${event.is_critical ? 'border-red-300 bg-red-50/50' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge 
                variant="outline" 
                className={`${EVENT_TYPE_COLORS[event.event_type]} text-white border-0`}
              >
                {EVENT_TYPE_LABELS[event.event_type]}
              </Badge>
              {event.is_critical && (
                <Badge variant="destructive" className="text-xs">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  중요
                </Badge>
              )}
              {event.industries.map((ind) => (
                <Badge key={ind} variant="secondary" className="text-xs">
                  {INDUSTRY_LABELS[ind] || ind}
                </Badge>
              ))}
            </div>
            
            <h4 className="font-medium text-sm mb-1">{event.description}</h4>
            <p className="text-xs text-muted-foreground mb-2">
              <FileText className="w-3 h-3 inline mr-1" />
              {event.document_title}
            </p>
            
            {event.target_entities.length > 0 && (
              <p className="text-xs text-muted-foreground">
                <Building2 className="w-3 h-3 inline mr-1" />
                대상: {event.target_entities.join(', ')}
              </p>
            )}
          </div>
          
          <div className="text-right ml-4">
            <div className="text-sm font-medium">
              {eventDate.toLocaleDateString('ko-KR', { 
                month: 'short', 
                day: 'numeric' 
              })}
            </div>
            <div className={`text-xs font-medium mt-1 ${
              isOverdue ? 'text-red-600' : 
              isUrgent ? 'text-orange-600' : 
              'text-muted-foreground'
            }`}>
              {isOverdue ? `D+${Math.abs(event.days_remaining)}` : 
               event.days_remaining === 0 ? 'D-Day' :
               `D-${event.days_remaining}`}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CalendarView({ events }: { events: TimelineEvent[] }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  
  const eventsByDate: Record<string, TimelineEvent[]> = {};
  events.forEach(event => {
    const dateKey = event.event_date.split('T')[0];
    if (!eventsByDate[dateKey]) {
      eventsByDate[dateKey] = [];
    }
    eventsByDate[dateKey].push(event);
  });
  
  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
  
  const days = [];
  for (let i = 0; i < firstDay; i++) {
    days.push(<div key={`empty-${i}`} className="h-24 bg-muted/20" />);
  }
  
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayEvents = eventsByDate[dateStr] || [];
    const isToday = new Date().toISOString().split('T')[0] === dateStr;
    
    days.push(
      <div 
        key={day} 
        className={`h-24 border border-border p-1 overflow-hidden ${
          isToday ? 'bg-blue-50 border-blue-300' : ''
        }`}
      >
        <div className={`text-xs font-medium mb-1 ${isToday ? 'text-blue-600' : ''}`}>
          {day}
        </div>
        <div className="space-y-0.5">
          {dayEvents.slice(0, 3).map((event, idx) => (
            <div 
              key={idx}
              className={`text-[10px] px-1 py-0.5 rounded truncate text-white ${
                EVENT_TYPE_COLORS[event.event_type]
              }`}
              title={event.description}
            >
              {event.description.substring(0, 15)}
            </div>
          ))}
          {dayEvents.length > 3 && (
            <div className="text-[10px] text-muted-foreground">
              +{dayEvents.length - 3} more
            </div>
          )}
        </div>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="outline" size="icon" onClick={prevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h3 className="font-semibold">
          {currentDate.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' })}
        </h3>
        <Button variant="outline" size="icon" onClick={nextMonth}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      
      <div className="grid grid-cols-7 gap-0">
        {['일', '월', '화', '수', '목', '금', '토'].map(d => (
          <div key={d} className="text-center text-xs font-medium py-2 bg-muted">
            {d}
          </div>
        ))}
        {days}
      </div>
    </div>
  );
}

export default function PolicyTimeline() {
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [summary, setSummary] = useState<TimelineSummary | null>(null);
  const [criticalEvents, setCriticalEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [industryFilter, setIndustryFilter] = useState<string>('all');
  const [daysAhead, setDaysAhead] = useState<number>(90);
  
  useEffect(() => {
    loadData();
  }, [industryFilter, daysAhead]);
  
  const loadData = async () => {
    setLoading(true);
    try {
      const industries = industryFilter !== 'all' ? [industryFilter] : undefined;
      
      const [timelineData, summaryData, criticalData] = await Promise.all([
        getTimelineEvents({ days_ahead: daysAhead, industries }),
        getTimelineSummary(industries),
        getCriticalEvents({ days_ahead: 30, industries })
      ]);
      
      setTimeline(timelineData);
      setSummary(summaryData);
      setCriticalEvents(criticalData);
    } catch (error) {
      console.error('Failed to load timeline:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleExportIcal = async () => {
    try {
      const industries = industryFilter !== 'all' ? [industryFilter] : undefined;
      const blob = await exportTimelineIcal({ days_ahead: daysAhead, industries });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'fsc_policy_timeline.ics';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export iCal:', error);
    }
  };
  
  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }
  
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Calendar className="h-6 w-6" />
            정책 타임라인
          </h1>
          <p className="text-muted-foreground">
            금융 규제 시행일 및 주요 기한 추적
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Select value={industryFilter} onValueChange={setIndustryFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="업권 선택" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">전체</SelectItem>
              <SelectItem value="INSURANCE">보험</SelectItem>
              <SelectItem value="BANKING">은행</SelectItem>
              <SelectItem value="SECURITIES">증권</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={String(daysAhead)} onValueChange={(v) => setDaysAhead(Number(v))}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="기간" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="30">30일</SelectItem>
              <SelectItem value="90">90일</SelectItem>
              <SelectItem value="180">180일</SelectItem>
              <SelectItem value="365">1년</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" onClick={handleExportIcal}>
            <Download className="h-4 w-4 mr-2" />
            iCal 내보내기
          </Button>
        </div>
      </div>
      
      {/* Urgent Alerts */}
      {summary && summary.urgent_within_7_days.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>긴급 일정 알림</AlertTitle>
          <AlertDescription>
            7일 내 {summary.urgent_within_7_days.length}건의 중요 일정이 있습니다:
            <ul className="mt-2 space-y-1">
              {summary.urgent_within_7_days.slice(0, 3).map((item) => (
                <li key={item.event_id} className="text-sm">
                  <Clock className="h-3 w-3 inline mr-1" />
                  <strong>D-{item.days_remaining}</strong>: {item.description}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>30일 내 일정</CardDescription>
            <CardTitle className="text-3xl">{summary?.next_30_days.total || 0}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground">
              중요: <span className="text-red-600 font-medium">{summary?.next_30_days.critical || 0}</span>건
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>90일 내 일정</CardDescription>
            <CardTitle className="text-3xl">{summary?.next_90_days.total || 0}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground">
              중요: <span className="text-red-600 font-medium">{summary?.next_90_days.critical || 0}</span>건
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>긴급 (7일 내)</CardDescription>
            <CardTitle className="text-3xl text-orange-600">
              {summary?.urgent_within_7_days.length || 0}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground">
              즉시 확인 필요
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>중요 일정</CardDescription>
            <CardTitle className="text-3xl text-red-600">
              {criticalEvents.length}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground">
              위반 시 제재 있음
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Main Content */}
      <Tabs defaultValue="list" className="space-y-4">
        <TabsList>
          <TabsTrigger value="list">목록 보기</TabsTrigger>
          <TabsTrigger value="calendar">캘린더 보기</TabsTrigger>
          <TabsTrigger value="critical">중요 일정</TabsTrigger>
        </TabsList>
        
        <TabsContent value="list">
          <Card>
            <CardHeader>
              <CardTitle>예정된 일정</CardTitle>
              <CardDescription>
                {timeline?.total_events || 0}개의 일정이 있습니다
              </CardDescription>
            </CardHeader>
            <CardContent>
              {timeline?.events.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>예정된 일정이 없습니다</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {timeline?.events.map((event) => (
                    <EventCard key={event.event_id} event={event} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="calendar">
          <Card>
            <CardHeader>
              <CardTitle>캘린더</CardTitle>
              <CardDescription>
                월별 일정 보기
              </CardDescription>
            </CardHeader>
            <CardContent>
              <CalendarView events={timeline?.events || []} />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="critical">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-red-500" />
                중요 일정
              </CardTitle>
              <CardDescription>
                위반 시 제재가 있는 중요 기한
              </CardDescription>
            </CardHeader>
            <CardContent>
              {criticalEvents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>중요 일정이 없습니다</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {criticalEvents.map((event) => (
                    <EventCard key={event.event_id} event={event} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
