/**
 * 규제 문서 차이점 추출 (Policy Simulate)
 * 문서 A(기준) vs 문서 B(비교) 선택 → LLM이 두 문서의 차이점을 포괄적으로 추출. 국내·국제 문서 비교 가능.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitCompare, Loader2, FileText, AlertTriangle, RefreshCw, ClipboardList } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { getDocuments, policySimulate, type PolicyDiffResponse } from '@/lib/api';
import type { Document } from '@/types';
import { toast } from 'sonner';

const RISK_COLOR: Record<string, string> = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-emerald-100 text-emerald-700',
};
const CHANGE_TYPE_LABEL: Record<string, string> = {
  added: '추가',
  modified: '수정',
  removed: '삭제',
};

export default function PolicySimulatePage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [topicStablecoinStoOnly, setTopicStablecoinStoOnly] = useState(false);
  const [oldId, setOldId] = useState<string>('');
  const [newId, setNewId] = useState<string>('');
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<PolicyDiffResponse | null>(null);
  const [theme, setTheme] = useState<string>('default');
  const navigate = useNavigate();

  const loadDocuments = useCallback(() => {
    setLoadingDocs(true);
    getDocuments({
      page: 1,
      page_size: 200,
      ...(topicStablecoinStoOnly ? { topic: 'stablecoin_sto' } : {}),
    })
      .then((res) => setDocuments(res.documents || []))
      .catch(() => toast.error('문서 목록을 불러오지 못했습니다.'))
      .finally(() => setLoadingDocs(false));
  }, [topicStablecoinStoOnly]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const isInternational = (cat: string | undefined) => {
    if (!cat) return false;
    const lower = cat.toLowerCase();
    return lower.includes('fsb') || lower.includes('bis') || lower.includes('policy') || lower.includes('research') || lower.includes('press');
  };

  const handleSimulate = async () => {
    if (!oldId || !newId) {
      toast.error('기준 문서와 비교 문서를 모두 선택하세요.');
      return;
    }
    if (oldId === newId) {
      toast.error('서로 다른 두 문서를 선택하세요.');
      return;
    }
    setSimulating(true);
    setResult(null);
    try {
      const data = await policySimulate(oldId, newId, theme === 'default' ? undefined : theme);
      setResult(data);
      toast.success('차이점 추출이 완료되었습니다.');
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : '차이점 추출 요청에 실패했습니다.';
      toast.error(typeof msg === 'string' ? msg : '차이점 추출에 실패했습니다.');
    } finally {
      setSimulating(false);
    }
  };

  const oldDoc = documents.find((d) => d.document_id === oldId);
  const newDoc = documents.find((d) => d.document_id === newId);

  return (
    <div className="p-6 space-y-6 animate-page-enter max-w-5xl mx-auto">
      <Card className="border-none shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-indigo-600" />
            규제 문서 차이점 추출
          </CardTitle>
          <CardDescription>두 문서 선택 시 조항·주제·용어·범위 차이를 포괄적으로 추출합니다. 국내·국제 비교 가능.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingDocs ? (
            <div className="flex items-center gap-2 text-slate-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              문서 목록 불러오는 중...
            </div>
          ) : documents.length === 0 ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800 text-sm flex flex-col gap-2">
              <p className="font-medium">선택 가능한 문서가 없습니다.</p>
              <p>설정 → 데이터 수집에서 지금 수집 후 새로고침. (시드: app/backend에서 python -m scripts.seed_data 실행 후 새로고침)</p>
              <Button type="button" variant="outline" size="sm" onClick={loadDocuments} className="self-start">
                <RefreshCw className="w-4 h-4 mr-2" />
                문서 목록 새로고침
              </Button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3 flex-wrap">
                <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={topicStablecoinStoOnly}
                    onChange={(e) => setTopicStablecoinStoOnly(e.target.checked)}
                    className="rounded border-slate-300"
                  />
                  가상자산·토큰증권·스테이블코인 관련 문서만 보기
                </label>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <span className="text-xs text-slate-500">분석 테마 (선택)</span>
                  <Select value={theme} onValueChange={setTheme}>
                    <SelectTrigger className="w-[180px] h-8 text-xs">
                      <SelectValue placeholder="기본 분석" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">기본 분석</SelectItem>
                      <SelectItem value="virtual_asset">가상자산·토큰증권 투자자 보호</SelectItem>
                      <SelectItem value="insurance_capital">보험사 자본·지급여력(K-ICS)</SelectItem>
                      <SelectItem value="esg_disclosure">ESG 공시·지배구조</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button type="button" variant="ghost" size="sm" onClick={loadDocuments} disabled={loadingDocs}>
                  <RefreshCw className={`w-4 h-4 mr-1 ${loadingDocs ? 'animate-spin' : ''}`} />
                  새로고침
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>문서 A (기준)</Label>
                  <Select value={oldId} onValueChange={setOldId}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="기준 문서 선택" />
                    </SelectTrigger>
                    <SelectContent>
                      {documents.map((d) => (
                        <SelectItem key={d.document_id} value={d.document_id}>
                          <span className="flex items-center gap-2">
                            {isInternational(d.category) ? (
                              <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200">
                                국제
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-600">
                                국내
                              </Badge>
                            )}
                            <span className="truncate max-w-[200px]" title={d.title}>{d.title}</span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {oldDoc?.category && (
                    <p className="text-xs text-slate-500">카테고리: {oldDoc.category}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>문서 B (비교)</Label>
                  <Select value={newId} onValueChange={setNewId}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="비교 문서 선택" />
                    </SelectTrigger>
                    <SelectContent>
                      {documents.map((d) => (
                        <SelectItem key={d.document_id} value={d.document_id}>
                          <span className="flex items-center gap-2">
                            {isInternational(d.category) ? (
                              <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-700 border-blue-200">
                                국제
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-600">
                                국내
                              </Badge>
                            )}
                            <span className="truncate max-w-[200px]" title={d.title}>{d.title}</span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {newDoc?.category && (
                    <p className="text-xs text-slate-500">카테고리: {newDoc.category}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 pt-2">
                <Button
                  onClick={handleSimulate}
                  disabled={simulating || !oldId || !newId || oldId === newId}
                  className="bg-indigo-600 hover:bg-indigo-700"
                >
                  {simulating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      분석 중...
                    </>
                  ) : (
                    <>
                      <GitCompare className="w-4 h-4 mr-2" />
                      차이점 추출 실행
                    </>
                  )}
                </Button>
                {(oldDoc || newDoc) && (
                  <span className="text-xs text-slate-500">
                    {oldDoc && newDoc && isInternational(oldDoc.category) !== isInternational(newDoc.category)
                      ? '· 국제 vs 국내 비교'
                      : ''}
                  </span>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {result && (
        <Card className="border-none shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="w-4 h-4" />
              차이점 추출 결과
            </CardTitle>
            <CardDescription>{result.old_doc_title} → {result.new_doc_title}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-medium text-slate-700">전체 리스크</span>
              <Badge className={RISK_COLOR[result.overall_risk] || 'bg-slate-100 text-slate-700'}>
                {result.overall_risk.toUpperCase()}
              </Badge>
            </div>
            {result.industry_impact_delta && Object.keys(result.industry_impact_delta).length > 0 && (
              <div className="flex flex-wrap gap-2 text-xs text-slate-600">
                <span className="font-medium text-slate-700">업권별 영향 추정:</span>
                {Object.entries(result.industry_impact_delta).map(([k, v]) => {
                  const label =
                    k === 'BANKING' ? '은행' :
                    k === 'INSURANCE' ? '보험' :
                    k === 'SECURITIES' ? '증권' :
                    k;
                  return (
                    <Badge key={k} variant="outline" className="bg-slate-50 border-slate-200 text-xs">
                      {label} {v > 0 ? `+${v}` : v}
                    </Badge>
                  );
                })}
              </div>
            )}
            {result.summary && (
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{result.summary}</p>
              </div>
            )}
            {result.action_items && result.action_items.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <ClipboardList className="w-4 h-4 text-indigo-600" />
                  추천 조치사항 (초안)
                </h4>
                <ul className="space-y-1">
                  {result.action_items.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                      <span className="mt-1 w-1.5 h-1.5 rounded-full bg-indigo-500" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.suggested_checklist_links && result.suggested_checklist_links.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-900">후속 액션</h4>
                <div className="flex flex-wrap gap-2">
                  {result.suggested_checklist_links.map((link, idx) => (
                    <Button
                      key={idx}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="text-xs"
                      onClick={() => {
                        const type = link.type;
                        if (type === 'sandbox_checklist') navigate('/sandbox/checklist');
                        else if (type === 'gap_map') navigate('/gap-map');
                        else if (type === 'analytics_industry') navigate('/analytics');
                        else if (type === 'theme_review') toast.info('테마별 리뷰는 위 추천 조치사항을 참고하세요.');
                      }}
                    >
                      {link.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            {result.changes && result.changes.length > 0 ? (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-slate-900">추출된 차이점 (조항·주제·용어 등)</h4>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200">
                        <th className="text-left p-3 font-medium text-slate-700">조항</th>
                        <th className="text-left p-3 font-medium text-slate-700">유형</th>
                        <th className="text-left p-3 font-medium text-slate-700">요약</th>
                        <th className="text-left p-3 font-medium text-slate-700">리스크</th>
                        <th className="text-left p-3 font-medium text-slate-700">영향 업무</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.changes.map((c, i) => (
                        <tr key={i} className="border-b border-slate-100 last:border-0">
                          <td className="p-3 text-slate-800">{c.clause}</td>
                          <td className="p-3">{CHANGE_TYPE_LABEL[c.change_type] || c.change_type}</td>
                          <td className="p-3 text-slate-600 max-w-xs truncate" title={c.description}>{c.description}</td>
                          <td className="p-3">
                            <Badge className={`text-xs ${RISK_COLOR[c.risk_level] || ''}`}>
                              {c.risk_level}
                            </Badge>
                          </td>
                          <td className="p-3 text-slate-600 max-w-xs truncate" title={c.impacted_process}>{c.impacted_process}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 p-4 rounded-lg bg-amber-50 border border-amber-100 text-amber-800 text-sm">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>추출된 차이점이 없거나 분석할 수 없습니다.</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
