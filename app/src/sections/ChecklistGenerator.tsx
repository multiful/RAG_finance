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
  FileWarning
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

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

  const fetchDocuments = async () => {
    try {
      const data = await getDocuments({ page_size: 30, days: 30 });
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleGenerateChecklist = async (doc: DocumentWithChecklist) => {
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
    } catch (error) {
      console.error('Error generating checklist:', error);
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
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="section-title">컴플라이언스 체크리스트 생성기</h2>
        <p className="text-muted-foreground mt-1">
          문서에서 자동 추출한 준수 항목 및 조치사항
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Document List */}
        <Card className="card-elevated">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              문서 선택
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {documents.map((doc) => (
                <div
                  key={doc.document_id}
                  onClick={() => setSelectedDoc(doc)}
                  className={`p-4 rounded-xl cursor-pointer transition-all ${
                    selectedDoc?.document_id === doc.document_id
                      ? 'bg-primary/10 border-2 border-primary'
                      : 'bg-muted/50 hover:bg-muted border-2 border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{doc.title}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <span>{new Date(doc.published_at).toLocaleDateString('ko-KR')}</span>
                        <span>{doc.category}</span>
                      </div>
                    </div>
                    
                    {!doc.checklist ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleGenerateChecklist(doc);
                        }}
                        disabled={doc.loading}
                      >
                        {doc.loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          '생성'
                        )}
                      </Button>
                    ) : (
                      <Badge className="bg-emerald-100 text-emerald-700">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        완료
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Checklist Display */}
        <Card className="card-elevated">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckSquare className="w-5 h-5 text-primary" />
                체크리스트
              </CardTitle>
              {selectedDoc?.checklist && (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleExport('markdown')}
                  >
                    <Download className="w-4 h-4 mr-1" />
                    Markdown
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleExport('csv')}
                  >
                    <Download className="w-4 h-4 mr-1" />
                    CSV
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedDoc ? (
              <div className="flex flex-col items-center justify-center h-96 text-center text-muted-foreground">
                <CheckSquare className="w-16 h-16 mb-4 opacity-30" />
                <p>왼쪽에서 문서를 선택하세요</p>
              </div>
            ) : !selectedDoc.checklist ? (
              <div className="flex flex-col items-center justify-center h-96 text-center">
                <CheckSquare className="w-16 h-16 mb-4 text-muted-foreground" />
                <p className="text-muted-foreground mb-4">
                  체크리스트를 생성하세요
                </p>
                <Button
                  onClick={() => handleGenerateChecklist(selectedDoc)}
                  disabled={selectedDoc.loading}
                  className="gradient-primary text-white"
                >
                  {selectedDoc.loading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <CheckSquare className="w-4 h-4 mr-2" />
                  )}
                  체크리스트 생성
                </Button>
              </div>
            ) : selectedDoc.checklist.items.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-96 text-center text-muted-foreground">
                <AlertCircle className="w-16 h-16 mb-4 opacity-30" />
                <p>추출된 체크리스트 항목이 없습니다</p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[600px] overflow-y-auto">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <FileText className="w-4 h-4" />
                  <span>{selectedDoc.title}</span>
                </div>

                {selectedDoc.checklist.items.map((item, index) => (
                  <ChecklistItemCard 
                    key={index} 
                    item={item} 
                    index={index}
                    getConfidenceColor={getConfidenceColor}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
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
    <div className="p-4 bg-muted/50 rounded-xl">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
          {index + 1}
        </div>
        <div className="flex-1">
          {/* Action */}
          <div className="mb-3">
            <p className="text-sm text-muted-foreground mb-1">해야 할 일</p>
            <p className="font-medium">{item.action}</p>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-3">
            {item.target && (
              <div className="flex items-start gap-2">
                <Users className="w-4 h-4 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-xs text-muted-foreground">대상</p>
                  <p className="text-sm">{item.target}</p>
                </div>
              </div>
            )}
            
            {item.due_date_text && (
              <div className="flex items-start gap-2">
                <Calendar className="w-4 h-4 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-xs text-muted-foreground">기한</p>
                  <p className="text-sm">{item.due_date_text}</p>
                </div>
              </div>
            )}
            
            {item.scope && (
              <div className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-xs text-muted-foreground">적용범위</p>
                  <p className="text-sm">{item.scope}</p>
                </div>
              </div>
            )}
            
            {item.penalty && (
              <div className="flex items-start gap-2">
                <FileWarning className="w-4 h-4 text-red-500 mt-0.5" />
                <div>
                  <p className="text-xs text-red-500">제재</p>
                  <p className="text-sm text-red-600">{item.penalty}</p>
                </div>
              </div>
            )}
          </div>

          {/* Confidence */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
            <span className="text-xs text-muted-foreground">신뢰도:</span>
            <Progress 
              value={item.confidence * 100} 
              className="w-20 h-1.5"
            />
            <Badge className={`text-xs ${getConfidenceColor(item.confidence)}`}>
              {(item.confidence * 100).toFixed(0)}%
            </Badge>
          </div>
        </div>
      </div>
    </div>
  );
}
