/**
 * ComplianceTable: 추출된 의무/기한/대상 항목을 보여주는 데이터 그리드.
 */
import { useState } from 'react';
import { 
  Calendar, 
  Users, 
  AlertTriangle, 
  CheckCircle2, 
  Shield,
  FileWarning,
  ChevronDown,
  ChevronUp,
  Download,
  Filter
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ChecklistItem {
  id: string;
  action: string;
  target?: string;
  due_date?: string;
  effective_date?: string;
  scope?: string;
  penalty?: string;
  confidence: number;
  evidence?: string;
}

interface ComplianceTableProps {
  items: ChecklistItem[];
  documentTitle?: string;
  onExport?: (format: 'csv' | 'json') => void;
}

export default function ComplianceTable({ 
  items, 
  documentTitle,
  onExport 
}: ComplianceTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [filterConfidence, setFilterConfidence] = useState<number>(0);

  // 필터링
  const filteredItems = items.filter(item => {
    const matchesSearch = 
      item.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.target?.toLowerCase() || '').includes(searchTerm.toLowerCase());
    const matchesConfidence = item.confidence >= filterConfidence;
    return matchesSearch && matchesConfidence;
  });

  // 행 확장 토글
  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  // 신뢰도에 따른 색상
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (confidence >= 0.5) return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-red-100 text-red-700 border-red-200';
  };

  // CSV 나이스포트
  const exportToCSV = () => {
    const headers = ['항목', '대상', '기한', '적용범위', '제재', '신뢰도'];
    const rows = filteredItems.map(item => [
      item.action,
      item.target || '',
      item.due_date || '',
      item.scope || '',
      item.penalty || '',
      `${(item.confidence * 100).toFixed(0)}%`
    ]);
    
    const csv = [headers, ...rows]
      .map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
      .join('\n');
    
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `compliance_checklist_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    
    onExport?.('csv');
  };

  return (
    <Card className="card-elevated">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              준수 체크리스트
            </CardTitle>
            {documentTitle && (
              <p className="text-sm text-muted-foreground mt-1">
                출처: {documentTitle}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportToCSV}
            >
              <Download className="w-4 h-4 mr-1" />
              CSV
            </Button>
          </div>
        </div>

        {/* 필터 바 */}
        <div className="flex items-center gap-3 mt-4">
          <div className="relative flex-1">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="항목 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          <select
            value={filterConfidence}
            onChange={(e) => setFilterConfidence(Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-input bg-background text-sm"
          >
            <option value={0}>전체 신뢰도</option>
            <option value={0.8}>높음 (80%+)</option>
            <option value={0.5}>중간 (50%+)</option>
          </select>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {filteredItems.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Shield className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p>체크리스트 항목이 없습니다</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-lavender-50/50">
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>해야 할 일</TableHead>
                  <TableHead className="w-32">대상</TableHead>
                  <TableHead className="w-32">기한</TableHead>
                  <TableHead className="w-24">신뢰도</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredItems.map((item, index) => (
                  <>
                    <TableRow 
                      key={item.id}
                      className="cursor-pointer hover:bg-lavender-50/30"
                      onClick={() => toggleRow(item.id)}
                    >
                      <TableCell className="font-medium">{index + 1}</TableCell>
                      <TableCell>
                        <div className="flex items-start gap-2">
                          <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                          <span className="line-clamp-2">{item.action}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {item.target && (
                          <div className="flex items-center gap-1 text-sm">
                            <Users className="w-3 h-3 text-muted-foreground" />
                            {item.target}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        {item.due_date && (
                          <div className="flex items-center gap-1 text-sm">
                            <Calendar className="w-3 h-3 text-muted-foreground" />
                            {item.due_date}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge className={`text-xs ${getConfidenceColor(item.confidence)}`}>
                          {(item.confidence * 100).toFixed(0)}%
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {expandedRows.has(item.id) ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </TableCell>
                    </TableRow>
                    
                    {/* 확장된 상세 정보 */}
                    {expandedRows.has(item.id) && (
                      <TableRow className="bg-muted/30">
                        <TableCell colSpan={6} className="py-4">
                          <div className="grid grid-cols-2 gap-4">
                            {item.scope && (
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">적용 범위</p>
                                <p className="text-sm flex items-center gap-2">
                                  <Shield className="w-4 h-4 text-primary" />
                                  {item.scope}
                                </p>
                              </div>
                            )}
                            
                            {item.penalty && (
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">위반 시 제재</p>
                                <p className="text-sm flex items-center gap-2 text-red-600">
                                  <FileWarning className="w-4 h-4" />
                                  {item.penalty}
                                </p>
                              </div>
                            )}
                            
                            {item.effective_date && (
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">시행일</p>
                                <p className="text-sm flex items-center gap-2">
                                  <Calendar className="w-4 h-4 text-primary" />
                                  {item.effective_date}
                                </p>
                              </div>
                            )}
                            
                            {item.evidence && (
                              <div className="col-span-2">
                                <p className="text-xs text-muted-foreground mb-1">근거</p>
                                <p className="text-sm bg-white p-3 rounded border">
                                  {item.evidence}
                                </p>
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* 요약 통계 */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-lavender-50/30">
          <div className="flex items-center gap-4 text-sm">
            <span className="text-muted-foreground">
              총 <strong>{filteredItems.length}</strong>개 항목
            </span>
            <span className="text-emerald-600">
              <CheckCircle2 className="w-4 h-4 inline mr-1" />
              높은 신뢰도: {filteredItems.filter(i => i.confidence >= 0.8).length}개
            </span>
            {filteredItems.some(i => i.penalty) && (
              <span className="text-red-600">
                <AlertTriangle className="w-4 h-4 inline mr-1" />
                제재 있음: {filteredItems.filter(i => i.penalty).length}개
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
