import { useEffect, useState } from 'react';
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
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

import { getDocuments, getDocumentChecklist, exportChecklist } from '@/lib/api';
import type { Document, ChecklistResponse, ChecklistItem } from '@/types';

interface DocumentWithChecklist extends Document {
  checklist?: ChecklistResponse;
  loading?: boolean;
}

export default function ChecklistGenerator() {
  const [documents, setDocuments] = useState<DocumentWithChecklist[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentWithChecklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDocuments({ page_size: 30, days: 30 });
      setDocuments(data.documents);
    } catch (err: any) {
      console.error('Error fetching documents:', err);
      setError('문서 목록을 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleGenerateChecklist = async (doc: DocumentWithChecklist) => {
    setError(null);
    setDocuments(prev => 
      prev.map(d => 
        d.document_id === doc.document_id 
          ? { ...d, loading: true } 
          : d
      )
    );

    try {
      const checklist = await getDocumentChecklist(doc.document_id);
      const updatedDoc = { ...doc, checklist, loading: false };
      
      setDocuments(prev => 
        prev.map(d => 
          d.document_id === doc.document_id ? updatedDoc : d
        )
      );
      setSelectedDoc(updatedDoc);
    } catch (err: any) {
      console.error('Error generating checklist:', err);
      setError(err.response?.data?.detail || '체크리스트 생성 중 오류가 발생했습니다.');
      setDocuments(prev => 
        prev.map(d => 
          d.document_id === doc.document_id 
            ? { ...d, loading: false } 
            : d
        )
      );
    }
  };

  const handleExport = async (format: string) => {
    if (!selectedDoc?.checklist) return;
    
    try {
      const content = await exportChecklist(selectedDoc.document_id, format);
      
      // Download file
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/plain' 
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `checklist_${selectedDoc.document_id}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting checklist:', error);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-emerald-100 text-emerald-700';
    if (confidence >= 0.5) return 'bg-amber-100 text-amber-700';
    return 'bg-red-100 text-red-700';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">컴플라이언스 체크리스트</h2>
          <p className="text-slate-500 mt-2 text-lg">
            금융정책 문서에서 자동 추출한 필수 준수 항목 및 이행 조치
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline"
            onClick={() => fetchDocuments()} 
            disabled={loading}
            className="border-slate-200 text-slate-600 font-semibold h-11 px-5 rounded-xl hover:bg-slate-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            문서 새로고침
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="animate-in slide-in-from-top-4 duration-500 border-none shadow-md bg-red-50 text-red-700">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle className="font-bold">오류 발생</AlertTitle>
          <AlertDescription className="font-medium">
            {error}
            <Button variant="outline" size="sm" onClick={() => fetchDocuments()} className="ml-4 h-8 bg-white border-red-200 text-red-700 hover:bg-red-50 font-bold rounded-lg">
              다시 시도
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Document List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              대상 문서 선택
            </h3>
            <Badge variant="secondary" className="bg-slate-100 text-slate-500 font-bold border-none uppercase tracking-tighter">
              Last 30 Days
            </Badge>
          </div>

          <Card className="border-none shadow-sm bg-white rounded-3xl overflow-hidden">
            <CardContent className="p-0">
              <div className="divide-y divide-slate-50 max-h-[700px] overflow-y-auto">
                {documents.map((doc) => (
                  <div
                    key={doc.document_id}
                    onClick={() => setSelectedDoc(doc)}
                    className={`p-5 cursor-pointer transition-all border-l-4 ${
                      selectedDoc?.document_id === doc.document_id
                        ? 'bg-primary/5 border-primary'
                        : 'bg-white border-transparent hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className={`font-bold text-sm truncate ${selectedDoc?.document_id === doc.document_id ? 'text-primary' : 'text-slate-900'}`}>
                          {doc.title}
                        </p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-[10px] font-black text-slate-400 uppercase tracking-tighter bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">{doc.category}</span>
                          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(doc.published_at).toLocaleDateString('ko-KR')}
                          </span>
                        </div>
                      </div>
                      
                      {!doc.checklist ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleGenerateChecklist(doc);
                          }}
                          disabled={doc.loading}
                          className="h-8 w-8 p-0 rounded-lg text-slate-400 hover:text-primary hover:bg-primary/10"
                        >
                          {doc.loading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-primary" />
                          ) : (
                            <CheckSquare className="w-4 h-4" />
                          )}
                        </Button>
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-emerald-50 flex items-center justify-center border border-emerald-100">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Checklist Display */}
        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-primary" />
              체크리스트 상세
            </h3>
            {selectedDoc?.checklist && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExport('markdown')}
                  className="h-8 border-slate-200 text-slate-600 font-bold text-xs rounded-lg px-3"
                >
                  <Download className="w-3.5 h-3.5 mr-1.5" />
                  Markdown
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExport('csv')}
                  className="h-8 border-slate-200 text-slate-600 font-bold text-xs rounded-lg px-3"
                >
                  <Download className="w-3.5 h-3.5 mr-1.5" />
                  CSV
                </Button>
              </div>
            )}
          </div>

          <Card className="border-none shadow-sm bg-white rounded-3xl overflow-hidden min-h-[600px]">
            <CardContent className="p-8">
              {!selectedDoc ? (
                <div className="flex flex-col items-center justify-center h-[500px] text-center">
                  <div className="w-20 h-20 rounded-[2rem] bg-slate-50 flex items-center justify-center mb-6">
                    <FileText className="w-10 h-10 text-slate-200" />
                  </div>
                  <h4 className="text-lg font-bold text-slate-900 mb-2">선택된 문서가 없습니다</h4>
                  <p className="text-slate-500 max-w-xs mx-auto font-medium">
                    왼쪽 목록에서 분석할 문서를 선택하여 체크리스트를 확인하세요.
                  </p>
                </div>
              ) : !selectedDoc.checklist ? (
                <div className="flex flex-col items-center justify-center h-[500px] text-center">
                  <div className="w-24 h-24 rounded-[2.5rem] bg-indigo-50 flex items-center justify-center mb-6">
                    <CheckSquare className="w-12 h-12 text-indigo-200" />
                  </div>
                  <h4 className="text-xl font-bold text-slate-900 mb-2">분석이 필요한 문서입니다</h4>
                  <p className="text-slate-500 mb-8 max-w-sm mx-auto font-medium">
                    LLM을 활용하여 해당 정책 문서에서 필수적으로 준수해야 할 항목들을 자동으로 추출합니다.
                  </p>
                  <Button
                    onClick={() => handleGenerateChecklist(selectedDoc)}
                    disabled={selectedDoc.loading}
                    className="gradient-primary text-white font-black h-12 px-10 rounded-2xl shadow-xl shadow-primary/20"
                  >
                    {selectedDoc.loading ? (
                      <Loader2 className="w-5 h-5 mr-3 animate-spin" />
                    ) : (
                      <Zap className="w-5 h-5 mr-3" />
                    )}
                    {selectedDoc.loading ? '분석 중...' : '체크리스트 생성하기'}
                  </Button>
                </div>
              ) : selectedDoc.checklist.items.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[500px] text-center">
                  <div className="w-20 h-20 rounded-[2rem] bg-rose-50 flex items-center justify-center mb-6">
                    <AlertCircle className="w-10 h-10 text-rose-200" />
                  </div>
                  <h4 className="text-lg font-bold text-slate-900 mb-2">추출된 항목이 없습니다</h4>
                  <p className="text-slate-500 max-w-xs mx-auto font-medium">
                    해당 문서에는 명시적인 준수 사항이 포함되어 있지 않을 수 있습니다.
                  </p>
                </div>
              ) : (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <div className="flex items-start gap-4 p-5 bg-slate-50 rounded-2xl border border-slate-100 mb-8">
                    <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-sm flex-shrink-0">
                      <FileText className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Selected Document</p>
                      <h4 className="text-sm font-bold text-slate-900 line-clamp-1">{selectedDoc.title}</h4>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    {selectedDoc.checklist.items.map((item, index) => (
                      <ChecklistItemCard 
                        key={index} 
                        item={item} 
                        index={index}
                        getConfidenceColor={getConfidenceColor}
                      />
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface ChecklistItemCardProps {
  item: ChecklistItem;
  index: number;
  getConfidenceColor: (confidence: number) => string;
}

function ChecklistItemCard({ item, index, getConfidenceColor }: ChecklistItemCardProps) {
  return (
    <Card className="border-none shadow-sm bg-slate-50/50 hover:bg-white hover:shadow-md transition-all duration-300 rounded-2xl overflow-hidden group">
      <CardContent className="p-6">
        <div className="flex items-start gap-5">
          <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center text-sm font-black flex-shrink-0 group-hover:scale-110 transition-transform">
            {index + 1}
          </div>
          <div className="flex-1">
            {/* Action */}
            <div className="mb-4">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Action Item</p>
              <p className="text-base font-bold text-slate-900 leading-snug">{item.action}</p>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {item.target && (
                <div className="flex items-start gap-3 p-3 bg-white rounded-xl border border-slate-100">
                  <div className="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <Users className="w-3.5 h-3.5 text-indigo-500" />
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">Target</p>
                    <p className="text-xs font-bold text-slate-700">{item.target}</p>
                  </div>
                </div>
              )}
              
              {item.due_date_text && (
                <div className="flex items-start gap-3 p-3 bg-white rounded-xl border border-slate-100">
                  <div className="w-7 h-7 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
                    <Calendar className="w-3.5 h-3.5 text-amber-500" />
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">Deadline</p>
                    <p className="text-xs font-bold text-slate-700">{item.due_date_text}</p>
                  </div>
                </div>
              )}
              
              {item.scope && (
                <div className="flex items-start gap-3 p-3 bg-white rounded-xl border border-slate-100">
                  <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center flex-shrink-0">
                    <Shield className="w-3.5 h-3.5 text-emerald-500" />
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-tighter">Scope</p>
                    <p className="text-xs font-bold text-slate-700">{item.scope}</p>
                  </div>
                </div>
              )}
              
              {item.penalty && (
                <div className="flex items-start gap-3 p-3 bg-rose-50 rounded-xl border border-rose-100">
                  <div className="w-7 h-7 rounded-lg bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
                    <FileWarning className="w-3.5 h-3.5 text-rose-500" />
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-rose-400 uppercase tracking-tighter">Penalty</p>
                    <p className="text-xs font-bold text-rose-600">{item.penalty}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Confidence */}
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-100">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Confidence</span>
                <Badge className={`px-2 py-0 text-[10px] font-black border-none ${getConfidenceColor(item.confidence)}`}>
                  {(item.confidence * 100).toFixed(0)}%
                </Badge>
              </div>
              <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${item.confidence >= 0.8 ? 'bg-emerald-500' : 'bg-amber-500'}`} 
                  style={{ width: `${item.confidence * 100}%` }} 
                />
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

