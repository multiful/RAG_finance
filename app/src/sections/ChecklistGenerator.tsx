import { useEffect, useState, useCallback } from 'react';
import { 
  CheckSquare, 
  FileText, 
  Download, 
  Calendar, 
  Users,
  AlertCircle,
  Shield,
  Loader2,
  CheckCircle2,
  FileWarning,
  Zap,
  RefreshCw,
  Search,
  ChevronRight,
  Clock,
  User,
  MoreVertical,
  History,
  AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter,
  DialogTrigger
} from '@/components/ui/dialog';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from "sonner";

import { 
  getDocuments, 
  generateComplianceChecklist, 
  listComplianceChecklists,
  updateActionItem,
  getActionItemAudit,
  recalculateRisk
} from '@/lib/api';
import type { 
  Document, 
  ComplianceChecklist, 
  ComplianceActionItem,
  ActionItemAudit
} from '@/types';

export default function ChecklistGenerator() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [checklists, setChecklists] = useState<ComplianceChecklist[]>([]);
  const [selectedChecklist, setSelectedChecklist] = useState<ComplianceChecklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [docsData, checklistsData] = await Promise.all([
        getDocuments({ page_size: 50 }),
        listComplianceChecklists({ limit: 50 })
      ]);
      setDocuments(docsData.documents);
      setChecklists(checklistsData);
    } catch (err: any) {
      console.error('Error fetching data:', err);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGenerate = async (docId: string) => {
    setGenerating(docId);
    try {
      const newChecklist = await generateComplianceChecklist(docId);
      setChecklists(prev => [newChecklist, ...prev]);
      setSelectedChecklist(newChecklist);
      toast.success("체크리스트가 생성되었습니다.");
    } catch (err: any) {
      console.error('Generation error:', err);
      toast.error("체크리스트 생성에 실패했습니다.");
    } finally {
      setGenerating(null);
    }
  };

  const handleUpdateItem = async (itemId: string, update: Partial<ComplianceActionItem>) => {
    try {
      const updatedItem = await updateActionItem(itemId, update);
      if (selectedChecklist) {
        setSelectedChecklist({
          ...selectedChecklist,
          action_items: selectedChecklist.action_items.map(item => 
            item.action_item_id === itemId ? updatedItem : item
          )
        });
      }
      toast.success("항목이 업데이트되었습니다.");
    } catch (err) {
      toast.error("업데이트 실패");
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical': return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'high': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'medium': return 'bg-amber-100 text-amber-700 border-amber-200';
      default: return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return <Badge className="bg-emerald-500 hover:bg-emerald-600 border-none">완료</Badge>;
      case 'in_progress': return <Badge className="bg-blue-500 hover:bg-blue-600 border-none">진행중</Badge>;
      case 'overdue': return <Badge className="bg-rose-500 hover:bg-rose-600 border-none">지연</Badge>;
      default: return <Badge variant="outline" className="text-slate-500">대기</Badge>;
    }
  };

  if (loading && checklists.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const filteredDocs = documents.filter(doc => 
    doc.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">Compliance Hub</h2>
          <p className="text-slate-500 mt-2 text-lg">
            정책 준수 현황 관리 및 위험 평가 대시보드
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline"
            onClick={fetchData} 
            className="border-slate-200 text-slate-600 font-semibold h-11 px-5 rounded-xl hover:bg-slate-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            데이터 새로고침
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Document & Checklist List */}
        <div className="lg:col-span-4 space-y-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input 
              placeholder="문서 검색..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 h-11 bg-white border-slate-200 rounded-xl shadow-sm focus:ring-primary/20"
            />
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest px-2">Active Checklists</h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {checklists.map(cl => (
                <Card 
                  key={cl.checklist_id}
                  onClick={() => setSelectedChecklist(cl)}
                  className={`cursor-pointer transition-all border-none shadow-sm hover:shadow-md ${
                    selectedChecklist?.checklist_id === cl.checklist_id 
                      ? 'ring-2 ring-primary bg-primary/5' 
                      : 'bg-white'
                  }`}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <Badge className={`text-[10px] font-black uppercase ${getRiskLevelColor(cl.risk_level)}`}>
                        {cl.risk_level} Risk
                      </Badge>
                      <span className="text-[10px] font-bold text-slate-400">
                        {new Date(cl.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </div>
                    <h4 className="font-bold text-sm text-slate-900 line-clamp-2 mb-3">
                      {cl.title || "Compliance Review"}
                    </h4>
                    <div className="flex items-center justify-between text-[10px] font-bold text-slate-500">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                        <span>{cl.action_items.filter(i => i.status === 'completed').length}/{cl.action_items.length} Done</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Zap className="w-3 h-3 text-amber-500" />
                        <span>Score: {cl.risk_score.toFixed(1)}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}

              <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest px-2 pt-4">Recent Documents</h3>
              {filteredDocs
                .filter(doc => !checklists.some(cl => cl.compliance_doc_id === doc.document_id))
                .map(doc => (
                <div 
                  key={doc.document_id}
                  className="flex items-center justify-between p-4 bg-white rounded-xl shadow-sm border border-slate-50 hover:border-primary/30 transition-colors"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="text-xs font-bold text-slate-900 truncate">{doc.title}</p>
                    <p className="text-[10px] text-slate-400 mt-1">{new Date(doc.published_at).toLocaleDateString()}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleGenerate(doc.document_id)}
                    disabled={generating === doc.document_id}
                    className="h-8 w-8 p-0 rounded-lg text-slate-400 hover:text-primary hover:bg-primary/10"
                  >
                    {generating === doc.document_id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    ) : (
                      <Zap className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Detailed View */}
        <div className="lg:col-span-8">
          {!selectedChecklist ? (
            <Card className="h-full min-h-[600px] border-none shadow-sm bg-white rounded-3xl flex flex-col items-center justify-center text-center p-8">
              <div className="w-20 h-20 rounded-[2.5rem] bg-slate-50 flex items-center justify-center mb-6">
                <Shield className="w-10 h-10 text-slate-200" />
              </div>
              <h4 className="text-xl font-bold text-slate-900 mb-2">체크리스트를 선택하세요</h4>
              <p className="text-slate-500 max-w-sm mx-auto font-medium">
                왼쪽 목록에서 규제 준수 현황을 확인할 체크리스트를 선택하거나 새 문서를 분석하세요.
              </p>
            </Card>
          ) : (
            <div className="space-y-6 animate-in fade-in duration-500">
              {/* Checklist Header */}
              <Card className="border-none shadow-sm bg-white rounded-3xl overflow-hidden">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <Badge className={`px-2 py-0.5 text-[10px] font-black uppercase tracking-widest ${getRiskLevelColor(selectedChecklist.risk_level)}`}>
                          {selectedChecklist.risk_level} RISK
                        </Badge>
                        <span className="text-xs font-bold text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Updated {new Date(selectedChecklist.updated_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <CardTitle className="text-2xl font-black text-slate-900 mt-2">
                        {selectedChecklist.title || "Compliance Review"}
                      </CardTitle>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Risk Score</div>
                      <div className="text-4xl font-black text-slate-900 leading-none">
                        {selectedChecklist.risk_score.toFixed(1)}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                   <div className="grid grid-cols-3 gap-4 mt-4">
                      <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total Items</div>
                        <div className="text-xl font-bold text-slate-900">{selectedChecklist.action_items.length}</div>
                      </div>
                      <div className="p-4 bg-emerald-50 rounded-2xl border border-emerald-100">
                        <div className="text-[10px] font-black text-emerald-600/60 uppercase tracking-widest mb-1">Completed</div>
                        <div className="text-xl font-bold text-emerald-700">
                          {selectedChecklist.action_items.filter(i => i.status === 'completed').length}
                        </div>
                      </div>
                      <div className="p-4 bg-amber-50 rounded-2xl border border-amber-100">
                        <div className="text-[10px] font-black text-amber-600/60 uppercase tracking-widest mb-1">Pending</div>
                        <div className="text-xl font-bold text-amber-700">
                          {selectedChecklist.action_items.filter(i => i.status === 'pending').length}
                        </div>
                      </div>
                   </div>
                </CardContent>
              </Card>

              {/* Action Items List */}
              <div className="space-y-4">
                <div className="flex items-center justify-between px-2">
                  <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                    <CheckSquare className="w-5 h-5 text-primary" />
                    이행 조치 사항
                  </h3>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {selectedChecklist.action_items.map((item) => (
                    <ActionItemCard 
                      key={item.action_item_id} 
                      item={item} 
                      onUpdate={(update) => handleUpdateItem(item.action_item_id, update)}
                      getRiskLevelColor={getRiskLevelColor}
                      getStatusBadge={getStatusBadge}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface ActionItemCardProps {
  item: ComplianceActionItem;
  onUpdate: (update: Partial<ComplianceActionItem>) => void;
  getRiskLevelColor: (level: string) => string;
  getStatusBadge: (status: string) => React.ReactNode;
}

function ActionItemCard({ item, onUpdate, getRiskLevelColor, getStatusBadge }: ActionItemCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [auditLog, setAuditLog] = useState<ActionItemAudit[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const fetchAudit = async () => {
    setLoadingAudit(true);
    try {
      const logs = await getActionItemAudit(item.action_item_id);
      setAuditLog(logs);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAudit(false);
    }
  };

  return (
    <Card className="border-none shadow-sm bg-white hover:shadow-md transition-all duration-300 rounded-3xl overflow-hidden group">
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                {getStatusBadge(item.status)}
                <Badge className={`text-[10px] font-black uppercase ${getRiskLevelColor(item.risk_level)}`}>
                  {item.risk_level} Risk
                </Badge>
              </div>
              
              <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={fetchAudit} className="h-8 w-8 text-slate-400">
                    <MoreVertical className="w-4 h-4" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl rounded-3xl">
                  <DialogHeader>
                    <DialogTitle className="text-xl font-black">이행 조치 관리</DialogTitle>
                  </DialogHeader>
                  
                  <div className="space-y-6 py-4">
                    <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                       <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Action</p>
                       <p className="text-sm font-bold text-slate-900">{item.action}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">상태 변경</label>
                        <Select 
                          defaultValue={item.status} 
                          onValueChange={(val) => onUpdate({ status: val as any })}
                        >
                          <SelectTrigger className="rounded-xl h-11">
                            <SelectValue placeholder="상태 선택" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="pending">대기 (Pending)</SelectItem>
                            <SelectItem value="in_progress">진행중 (In Progress)</SelectItem>
                            <SelectItem value="completed">완료 (Completed)</SelectItem>
                            <SelectItem value="skipped">제외 (Skipped)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">담당자 배정</label>
                        <Input 
                          placeholder="담당자 이름/ID" 
                          defaultValue={item.assigned_user_id}
                          onBlur={(e) => onUpdate({ assigned_user_id: e.target.value })}
                          className="rounded-xl h-11"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                       <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">노트 / 특이사항</label>
                       <Textarea 
                          placeholder="이행 관련 상세 내용을 입력하세요..."
                          defaultValue={item.notes || ''}
                          onBlur={(e) => onUpdate({ notes: e.target.value })}
                          className="rounded-xl min-h-[100px]"
                       />
                    </div>

                    <div className="space-y-3">
                       <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 flex items-center gap-2">
                         <History className="w-3 h-3" />
                         변경 이력 (Audit Log)
                       </h5>
                       <div className="space-y-2 max-h-40 overflow-y-auto pr-2">
                         {loadingAudit ? (
                           <div className="flex justify-center py-4"><Loader2 className="w-4 h-4 animate-spin" /></div>
                         ) : auditLog.length === 0 ? (
                           <p className="text-[10px] text-center text-slate-400 py-4">이력이 없습니다.</p>
                         ) : auditLog.map(log => (
                           <div key={log.audit_id} className="text-[10px] p-3 bg-slate-50 rounded-lg border border-slate-100">
                             <div className="flex justify-between font-bold mb-1">
                               <span className="text-slate-900">{log.changed_fields.join(', ')} 변경</span>
                               <span className="text-slate-400">{new Date(log.created_at).toLocaleString()}</span>
                             </div>
                             <div className="text-slate-500">
                               {log.changed_fields.map(field => (
                                 <div key={field}>{field}: {String(log.old_values[field] || 'None')} → {String(log.new_values[field])}</div>
                               ))}
                             </div>
                           </div>
                         ))}
                       </div>
                    </div>
                  </div>
                  
                  <DialogFooter>
                    <Button onClick={() => setIsModalOpen(false)} className="rounded-xl h-11 px-8 gradient-primary text-white font-bold">
                      닫기
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            <h4 className="text-base font-bold text-slate-900 mb-4 group-hover:text-primary transition-colors">
              {item.action}
            </h4>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-1">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Target</p>
                <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                  <Users className="w-3.5 h-3.5 text-indigo-400" />
                  {item.target || 'N/A'}
                </div>
              </div>
              
              <div className="space-y-1">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Due Date</p>
                <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                  <Calendar className="w-3.5 h-3.5 text-amber-400" />
                  {item.due_date ? new Date(item.due_date).toLocaleDateString() : 'No Limit'}
                </div>
              </div>

              <div className="space-y-1">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Assignee</p>
                <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  {item.assigned_user_id || 'Unassigned'}
                </div>
              </div>

              <div className="space-y-1">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Risk Score</p>
                <div className="flex items-center gap-2 text-xs font-black text-slate-900">
                  <AlertTriangle className={`w-3.5 h-3.5 ${item.risk_score > 60 ? 'text-rose-500' : 'text-slate-300'}`} />
                  {item.risk_score.toFixed(1)}
                </div>
              </div>
            </div>

            {item.notes && (
               <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-500 font-medium italic">
                 "{item.notes}"
               </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
