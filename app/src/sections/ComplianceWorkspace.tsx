/**
 * Compliance Workspace - Task management for regulatory compliance.
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  CheckSquare, 
  Clock, 
  AlertTriangle, 
  User,
  Plus,
  Filter,
  BarChart3,
  TrendingUp,
  CheckCircle2,
  Circle,
  XCircle,
  Loader2
} from 'lucide-react';
import api from '@/lib/api';

interface ComplianceTask {
  task_id: string;
  title: string;
  description?: string;
  document_id?: string;
  document_title?: string;
  alert_id?: string;
  industries: string[];
  due_date?: string;
  assigned_to?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'overdue' | 'cancelled';
  priority: 'critical' | 'high' | 'medium' | 'low';
  created_at?: string;
  completed_at?: string;
  days_until_due?: number;
  is_overdue: boolean;
}

interface DashboardStats {
  total_tasks: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_industry: Record<string, number>;
  upcoming_due: ComplianceTask[];
  overdue_tasks: ComplianceTask[];
  completion_rate: number;
}

const STATUS_LABELS: Record<string, string> = {
  pending: '대기',
  in_progress: '진행중',
  completed: '완료',
  overdue: '기한초과',
  cancelled: '취소',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-500',
  in_progress: 'bg-blue-500',
  completed: 'bg-green-500',
  overdue: 'bg-red-500',
  cancelled: 'bg-gray-400',
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-600',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-gray-400',
};

const INDUSTRY_LABELS: Record<string, string> = {
  INSURANCE: '보험',
  BANKING: '은행',
  SECURITIES: '증권',
};

function TaskCard({ 
  task, 
  onStatusChange 
}: { 
  task: ComplianceTask; 
  onStatusChange: (taskId: string, status: string) => void;
}) {
  const [updating, setUpdating] = useState(false);
  
  const handleStatusChange = async (newStatus: string) => {
    setUpdating(true);
    await onStatusChange(task.task_id, newStatus);
    setUpdating(false);
  };
  
  return (
    <Card className={`mb-3 ${task.is_overdue ? 'border-red-300 bg-red-50/30' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge 
                variant="outline" 
                className={`${STATUS_COLORS[task.status]} text-white border-0`}
              >
                {STATUS_LABELS[task.status]}
              </Badge>
              <Badge 
                variant="outline" 
                className={`${PRIORITY_COLORS[task.priority]} text-white border-0 text-xs`}
              >
                {task.priority}
              </Badge>
              {task.industries.map((ind) => (
                <Badge key={ind} variant="secondary" className="text-xs">
                  {INDUSTRY_LABELS[ind] || ind}
                </Badge>
              ))}
            </div>
            
            <h4 className="font-medium text-sm mb-1">{task.title}</h4>
            
            {task.document_title && (
              <p className="text-xs text-muted-foreground mb-1">
                문서: {task.document_title}
              </p>
            )}
            
            {task.assigned_to && (
              <p className="text-xs text-muted-foreground">
                <User className="w-3 h-3 inline mr-1" />
                {task.assigned_to}
              </p>
            )}
          </div>
          
          <div className="text-right">
            {task.due_date && (
              <>
                <div className="text-sm font-medium">
                  {new Date(task.due_date).toLocaleDateString('ko-KR', { 
                    month: 'short', 
                    day: 'numeric' 
                  })}
                </div>
                <div className={`text-xs font-medium ${
                  task.is_overdue ? 'text-red-600' : 
                  task.days_until_due !== null && task.days_until_due <= 3 ? 'text-orange-600' : 
                  'text-muted-foreground'
                }`}>
                  {task.is_overdue ? `D+${Math.abs(task.days_until_due || 0)}` : 
                   task.days_until_due === 0 ? 'D-Day' :
                   task.days_until_due !== null ? `D-${task.days_until_due}` : ''}
                </div>
              </>
            )}
            
            <div className="mt-2">
              <Select 
                value={task.status} 
                onValueChange={handleStatusChange}
                disabled={updating}
              >
                <SelectTrigger className="h-8 w-28 text-xs">
                  {updating ? <Loader2 className="w-3 h-3 animate-spin" /> : <SelectValue />}
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">대기</SelectItem>
                  <SelectItem value="in_progress">진행중</SelectItem>
                  <SelectItem value="completed">완료</SelectItem>
                  <SelectItem value="cancelled">취소</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  color = 'text-primary',
  subtitle 
}: { 
  title: string; 
  value: number | string; 
  icon: React.ElementType;
  color?: string;
  subtitle?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${color}`}>{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function ComplianceWorkspace() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tasks, setTasks] = useState<ComplianceTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [industryFilter, setIndustryFilter] = useState<string>('all');
  
  useEffect(() => {
    loadData();
  }, [statusFilter, industryFilter]);
  
  const loadData = async () => {
    setLoading(true);
    try {
      const industries = industryFilter !== 'all' ? [industryFilter] : undefined;
      
      const [statsData, tasksData] = await Promise.all([
        api.get('/compliance/dashboard', { params: { industries } }).then(r => r.data),
        api.get('/compliance/tasks', { 
          params: { 
            status: statusFilter !== 'all' ? statusFilter : undefined,
            industries 
          } 
        }).then(r => r.data)
      ]);
      
      setStats(statsData);
      setTasks(tasksData);
    } catch (error) {
      console.error('Failed to load compliance data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleStatusChange = async (taskId: string, newStatus: string) => {
    try {
      await api.put(`/compliance/tasks/${taskId}/status`, { status: newStatus });
      await loadData();
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };
  
  if (loading && !stats) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Skeleton className="h-32" />
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
            <CheckSquare className="h-6 w-6" />
            컴플라이언스 워크스페이스
          </h1>
          <p className="text-muted-foreground">
            규제 준수 업무 관리 및 현황 모니터링
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
        </div>
      </div>
      
      {/* Overdue Alert */}
      {stats && stats.overdue_tasks.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>기한 초과 업무</AlertTitle>
          <AlertDescription>
            {stats.overdue_tasks.length}건의 업무가 기한을 초과했습니다. 즉시 확인이 필요합니다.
          </AlertDescription>
        </Alert>
      )}
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <StatCard 
          title="전체 업무" 
          value={stats?.total_tasks || 0} 
          icon={CheckSquare}
        />
        <StatCard 
          title="진행중" 
          value={stats?.by_status.in_progress || 0} 
          icon={Loader2}
          color="text-blue-600"
        />
        <StatCard 
          title="완료" 
          value={stats?.by_status.completed || 0} 
          icon={CheckCircle2}
          color="text-green-600"
        />
        <StatCard 
          title="기한초과" 
          value={stats?.by_status.overdue || 0} 
          icon={AlertTriangle}
          color="text-red-600"
        />
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              완료율
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats?.completion_rate || 0}%
            </div>
            <Progress value={stats?.completion_rate || 0} className="h-2 mt-2" />
          </CardContent>
        </Card>
      </div>
      
      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Task List */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>업무 목록</CardTitle>
                  <CardDescription>
                    {tasks.length}개의 업무
                  </CardDescription>
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-32">
                    <Filter className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="상태" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">전체</SelectItem>
                    <SelectItem value="pending">대기</SelectItem>
                    <SelectItem value="in_progress">진행중</SelectItem>
                    <SelectItem value="completed">완료</SelectItem>
                    <SelectItem value="overdue">기한초과</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {tasks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>등록된 업무가 없습니다</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {tasks.map((task) => (
                    <TaskCard 
                      key={task.task_id} 
                      task={task} 
                      onStatusChange={handleStatusChange}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        
        {/* Sidebar */}
        <div className="space-y-6">
          {/* Upcoming Due */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4" />
                임박한 업무
              </CardTitle>
              <CardDescription>7일 내 마감</CardDescription>
            </CardHeader>
            <CardContent>
              {stats?.upcoming_due.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  임박한 업무가 없습니다
                </p>
              ) : (
                <div className="space-y-3">
                  {stats?.upcoming_due.slice(0, 5).map((task) => (
                    <div key={task.task_id} className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{task.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {task.due_date && new Date(task.due_date).toLocaleDateString('ko-KR')}
                        </p>
                      </div>
                      <Badge 
                        variant="outline" 
                        className={`ml-2 ${
                          task.days_until_due !== null && task.days_until_due <= 3 
                            ? 'bg-orange-100 text-orange-700' 
                            : ''
                        }`}
                      >
                        D-{task.days_until_due}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* By Priority */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4" />
                우선순위별 현황
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {['critical', 'high', 'medium', 'low'].map((priority) => (
                  <div key={priority} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${PRIORITY_COLORS[priority]}`} />
                      <span className="text-sm capitalize">{priority}</span>
                    </div>
                    <span className="font-medium">
                      {stats?.by_priority[priority] || 0}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          
          {/* By Industry */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                업권별 현황
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(INDUSTRY_LABELS).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm">{label}</span>
                    <span className="font-medium">
                      {stats?.by_industry[key] || 0}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
