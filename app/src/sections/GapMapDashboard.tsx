/**
 * Risk–Policy Gap Map 분석 결과 (KAI page_18)
 * - 리스크 축별 GI vs LC 막대 차트
 * - Gap Score 상위 3 사각지대 카드
 * - 산출 공식: Gap = GI × (1 - LC)
 */
import { useEffect, useState, useCallback } from 'react';
import { BarChart3, AlertTriangle, Info, FlaskConical, Loader2, FileText } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  getGapMap,
  getTopBlindSpots,
  getGapMapDomesticInternationalComparison,
  sandboxSimulate,
  getLCEvidence,
  getGapMapGiComponents,
} from '@/lib/api';
import type {
  RiskAxisScore,
  BlindSpotItem,
  GapMapDomesticInternationalComparison,
  LCEvidenceItem,
  GiComponentRow,
} from '@/lib/api';
import type { SandboxSimulateResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import api from '@/lib/api';

const GI_COLOR = '#1B4D3E';
const LC_COLOR = '#94a3b8';
const HIGH_GAP_COLOR = '#D35400';
const MID_GAP_COLOR = '#D4AC0D';
const LOW_GAP_COLOR = '#1B4D3E';

function gapColor(gap: number) {
  if (gap >= 0.5) return HIGH_GAP_COLOR;
  if (gap >= 0.3) return MID_GAP_COLOR;
  return LOW_GAP_COLOR;
}

export default function GapMapDashboard() {
  const [items, setItems] = useState<RiskAxisScore[]>([]);
  const [blindSpots, setBlindSpots] = useState<BlindSpotItem[]>([]);
  const [formula, setFormula] = useState<string>('');
  const [dataSource, setDataSource] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [simulateLoading, setSimulateLoading] = useState(false);
  const [simulateResult, setSimulateResult] = useState<SandboxSimulateResponse | null>(null);
  const [comparison, setComparison] = useState<GapMapDomesticInternationalComparison | null>(null);
  const [lcEvidenceOpen, setLcEvidenceOpen] = useState(false);
  const [lcEvidence, setLcEvidence] = useState<LCEvidenceItem[]>([]);
  const [lcEvidenceLoading, setLcEvidenceLoading] = useState(false);
  const [giComponents, setGiComponents] = useState<GiComponentRow[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [mapRes, spotsRes, comparisonRes, giRes] = await Promise.all([
        getGapMap(),
        getTopBlindSpots(3),
        getGapMapDomesticInternationalComparison(90),
        getGapMapGiComponents().catch(() => ({ items: [] as GiComponentRow[] })),
      ]);
      setItems(mapRes.items);
      setBlindSpots(spotsRes.items);
      setFormula(mapRes.formula || 'Gap = GI × (1 - LC)');
      setDataSource(mapRes.data_source);
      setComparison(comparisonRes);
      setGiComponents(giRes.items ?? []);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Gap Map 데이터를 불러오지 못했습니다.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const runSandboxSimulation = useCallback(async () => {
    const top5 = [...items].sort((a, b) => b.gap - a.gap).slice(0, 5).map((i) => i.axis_id);
    if (!top5.length) {
      toast.error('Gap Map 데이터가 없습니다.');
      return;
    }
    setSimulateLoading(true);
    setSimulateResult(null);
    try {
      const res = await sandboxSimulate({ blind_spot_axes: top5 });
      setSimulateResult(res);
      toast.success('샌드박스 시뮬레이션이 완료되었습니다.');
    } catch (e) {
      toast.error('시뮬레이션 요청에 실패했습니다.');
    } finally {
      setSimulateLoading(false);
    }
  }, [items]);

  if (loading) {
    return (
      <div className="p-6 space-y-6 animate-page-enter">
        <div>
          <Skeleton className="h-8 w-96 mb-2" />
          <Skeleton className="h-5 w-72" />
        </div>
        <Skeleton className="h-[380px] w-full rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 animate-page-enter">
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="pt-6">
            <p className="text-amber-800 font-medium flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              {error}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const chartData = items.map((r) => ({
    name: r.axis_id,
    axis_label: `${r.axis_id} ${r.name_ko.length > 12 ? r.name_ko.slice(0, 12) + '…' : r.name_ko}`,
    GI: Math.round(r.gi * 100) / 100,
    LC: Math.round(r.lc * 100) / 100,
    Gap: Math.round(r.gap * 100) / 100,
    gapColor: gapColor(r.gap),
  }));

  return (
    <div className="p-6 space-y-6 animate-page-enter">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <BarChart3 className="w-7 h-7 text-emerald-700" />
          Risk–Policy Gap Map 분석 결과
        </h1>
        <p className="text-slate-600 mt-1 font-medium">
          스테이블코인·STO 결합 환경에서, 국제(FSB·BIS 등)가 중요하게 보는 리스크를 우리나라가 얼마나 잘 보완하고 있는지 축별로 진단합니다.
        </p>
        <p className="text-slate-500 mt-1 text-sm">
          GI=국제적 중요도, LC=국내 법제 커버리지. <strong>Gap이 큰 축 = 국제 기준에 비해 국내 규제가 미흡한 축</strong>(우리나라가 보완해야 할 영역).
          {dataSource && (
            <span className="ml-2 text-slate-600">
              데이터 출처: {dataSource === 'database' ? 'DB(연구·관리 입력값)' : '연구 기준값(KAI page_18 상수)'}
            </span>
          )}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Dialog open={lcEvidenceOpen} onOpenChange={async (open) => {
            setLcEvidenceOpen(open);
            if (open && lcEvidence.length === 0) {
              setLcEvidenceLoading(true);
              try {
                const res = await getLCEvidence();
                setLcEvidence(res.items || []);
              } catch {
                toast.error('LC 근거를 불러오지 못했습니다.');
              } finally {
                setLcEvidenceLoading(false);
              }
            }
          }}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="gap-1.5">
                <FileText className="w-4 h-4" />
                LC 근거 보기 (RCC)
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>LC 값 근거 (법령·조항·출처)</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-slate-500 mb-4">
                각 리스크 축의 LC(국내 법제 커버리지) 값에 대한 근거입니다. 법령명·조항·출처를 관리자가 입력·관리할 수 있습니다.
              </p>
              {lcEvidenceLoading ? (
                <div className="flex items-center gap-2 text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin" /> 불러오는 중…
                </div>
              ) : (
                <div className="space-y-4">
                  {lcEvidence.map((e) => (
                    <Card key={e.axis_id}>
                      <CardHeader className="py-3">
                        <CardTitle className="text-sm flex items-center justify-between">
                          <span>{e.axis_id} {e.name_ko}</span>
                          <span className="font-normal text-slate-500">LC = {e.lc.toFixed(2)}</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0 text-sm">
                        {e.lc_evidence ? <p className="text-slate-700 whitespace-pre-wrap">{e.lc_evidence}</p> : <p className="text-slate-400">근거 미입력</p>}
                        {e.source_or_note && <p className="text-slate-500 mt-1 text-xs">{e.source_or_note}</p>}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
              <div className="flex gap-2 pt-4 border-t">
                <Button variant="outline" size="sm" onClick={async () => {
                  try {
                    const url = `${api.defaults.baseURL}/gap-map/lc-evidence/export?format=csv`;
                    const res = await api.get(url, { responseType: 'blob' });
                    const blob = new Blob([res.data], { type: 'text/csv' });
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = 'gap_map_lc_evidence.csv';
                    a.click();
                    URL.revokeObjectURL(a.href);
                    toast.success('CSV 내보내기 완료');
                  } catch {
                    toast.error('내보내기 실패');
                  }
                }}>
                  내보내기 (CSV)
                </Button>
                <Button variant="outline" size="sm" onClick={async () => {
                  try {
                    const data = await getLCEvidence();
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = 'gap_map_lc_evidence.json';
                    a.click();
                    URL.revokeObjectURL(a.href);
                    toast.success('JSON 내보내기 완료');
                  } catch {
                    toast.error('내보내기 실패');
                  }
                }}>
                  내보내기 (JSON)
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {giComponents.length > 0 && (
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-slate-900">GI 산출 구조 (국제 문헌 기반 세부 지표)</CardTitle>
            <p className="text-sm text-slate-600 font-normal">
              GI = 0.3×Freq + 0.3×Rec + 0.2×Inc + 0.2×Sys (0~1). 아래는 Supabase <code className="text-xs bg-slate-100 px-1 rounded">gap_map_gi_components</code> 실데이터입니다.
            </p>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[72px]">축</TableHead>
                  <TableHead>Freq</TableHead>
                  <TableHead>Rec</TableHead>
                  <TableHead>Inc</TableHead>
                  <TableHead>Sys</TableHead>
                  <TableHead>GI(계산)</TableHead>
                  <TableHead className="min-w-[140px]">근거 문헌 메모</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {giComponents.map((row) => (
                  <TableRow key={row.axis_id}>
                    <TableCell className="font-mono text-xs">{row.axis_id}</TableCell>
                    <TableCell>{row.freq.toFixed(2)}</TableCell>
                    <TableCell>{row.rec.toFixed(2)}</TableCell>
                    <TableCell>{row.inc.toFixed(2)}</TableCell>
                    <TableCell>{row.sys.toFixed(2)}</TableCell>
                    <TableCell className="font-semibold text-emerald-800">{row.gi_computed.toFixed(4)}</TableCell>
                    <TableCell className="text-xs text-slate-600 max-w-[240px] truncate" title={row.source_doc || ''}>
                      {row.source_doc || '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {comparison && (comparison.domestic.document_count > 0 || comparison.international.document_count > 0) && (
        <Card className="border-emerald-100 bg-emerald-50/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-emerald-900">
              <FileText className="w-5 h-5" />
              국내·국제 규제 문서 비교 (최근 {comparison.period_days}일)
            </CardTitle>
            <p className="text-sm text-slate-600">국내·국제 수집 문서 대조 반영</p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-white border border-emerald-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">국내 (금융위·금감원)</p>
                <p className="text-2xl font-bold text-emerald-800 mt-1">{comparison.domestic.document_count}건</p>
                {comparison.domestic.sources.length > 0 && (
                  <p className="text-xs text-slate-500 mt-1 truncate" title={comparison.domestic.sources.join(', ')}>
                    {comparison.domestic.sources.slice(0, 3).join(', ')}
                  </p>
                )}
              </div>
              <div className="p-4 rounded-xl bg-white border border-slate-200">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">국제 (FSB·BIS 등)</p>
                <p className="text-2xl font-bold text-slate-800 mt-1">{comparison.international.document_count}건</p>
                {comparison.international.sources.length > 0 && (
                  <p className="text-xs text-slate-500 mt-1 truncate" title={comparison.international.sources.join(', ')}>
                    {comparison.international.sources.slice(0, 3).join(', ')}
                  </p>
                )}
              </div>
            </div>
            <p className="text-sm text-slate-600 mt-3">{comparison.summary}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2 text-emerald-900">
            <BarChart3 className="w-5 h-5" />
            스테이블코인·STO 결합 리스크 축별 GI vs LC
          </CardTitle>
          <p className="text-sm text-slate-600 font-normal mt-1">GI 높고 LC 낮은 축 = 규제 미흡 축</p>
        </CardHeader>
        <CardContent>
          <div className="h-[380px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 12, right: 12, left: 12, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="axis_label"
                  tick={{ fontSize: 11 }}
                  angle={-35}
                  textAnchor="end"
                  height={70}
                />
                <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number) => [value.toFixed(2), '']}
                  labelFormatter={(_, payload) => payload?.[0]?.payload?.name && items.find((i) => i.axis_id === payload[0].payload.name)?.name_ko}
                />
                <Legend />
                <Bar dataKey="GI" name="Global Importance (GI)" fill={GI_COLOR} radius={[4, 4, 0, 0]} />
                <Bar dataKey="LC" name="Local Coverage (LC)" fill={LC_COLOR} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-8 text-sm font-medium mt-2">
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm bg-[#1B4D3E]" /> Global Importance (GI)
            </span>
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-sm bg-[#94a3b8]" /> Local Coverage (LC)
            </span>
          </div>
          <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead>축</TableHead>
                  <TableHead>리스크 요약</TableHead>
                  <TableHead className="text-right">GI</TableHead>
                  <TableHead className="text-right">LC</TableHead>
                  <TableHead className="text-right">Gap</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.axis_id}>
                    <TableCell className="font-mono text-xs">{row.axis_id}</TableCell>
                    <TableCell className="text-sm max-w-md">{row.name_ko}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.gi.toFixed(4)}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.lc.toFixed(4)}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums text-amber-900">{row.gap.toFixed(4)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-amber-500 bg-amber-50/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-amber-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              국제 기준 대비 국내 규제 미흡 축 (Gap 상위)
            </CardTitle>
            <p className="text-xs text-amber-700/90 font-normal mt-1">
              국제적으로는 중요한데 우리나라 법제가 아직 잘 커버하지 못하는 리스크 축입니다. 우선 보완이 필요합니다.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {blindSpots.map((item) => (
              <div
                key={item.axis_id}
                className="p-3 rounded-lg bg-white border border-amber-100 space-y-1"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-amber-700">{item.axis_id}. {item.name_ko}</span>
                  <span className="text-lg font-black text-amber-900">{item.gap.toFixed(2)}</span>
                </div>
                {item.description && (
                  <p className="text-xs text-slate-600">{item.description}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="md:col-span-2 border-l-4 border-l-slate-300">
          <CardContent className="pt-6">
            <p className="text-sm font-bold text-slate-500 mb-2">산출 공식</p>
            <code className="block bg-slate-100 p-3 rounded-lg text-sm font-mono text-slate-800">
              {formula}
            </code>
            <p className="text-xs text-slate-500 mt-3 flex items-start gap-2">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span><strong>GI</strong>: 국제(FSB·BIS·IMF 등) 문헌·권고에서 스테이블코인·STO 결합 리스크로 중요도(0~1). <strong>LC</strong>: 우리나라 법제가 해당 축을 얼마나 직접 규율하는지(0=미포섭, 1=직접 규율). <strong>Gap</strong>= GI×(1−LC) → 국제 기준에 비해 국내가 미흡한 정도.</span>
            </p>
            <div className="mt-4 pt-4 border-t border-slate-200">
              <p className="text-sm font-semibold text-slate-700 mb-2">Gap 해석 (국제 대비 국내 보완 여부)</p>
              <ul className="text-xs text-slate-600 space-y-1">
                <li><strong>고위험(Gap≥0.5):</strong> 국제적으로 중요한데 국내 규율이 미흡 → 우리나라가 보완해야 할 축</li>
                <li><strong>중위험(0.3≤Gap&lt;0.5):</strong> 국제 기준 대비 간접·일반 원칙 수준만 있거나 커버리지 부족</li>
                <li><strong>저위험(Gap&lt;0.3):</strong> 국내 법제로 상당 부분 포섭되어 있음</li>
                <li>LC 0에 가까우면 미포섭, 1에 가까우면 직접 규율로 잘 커버됨.</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sandbox 시나리오 시뮬레이션 (방안 B) */}
      <Card className="border-l-4 border-l-indigo-500">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2 text-indigo-900">
            <FlaskConical className="w-5 h-5" />
            샌드박스 시나리오 시뮬레이션
          </CardTitle>
          <p className="text-sm text-slate-500">상위 사각지대 기준 검토 포인트·권고 RAG 생성</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={runSandboxSimulation}
            disabled={simulateLoading || items.length === 0}
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            {simulateLoading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                시뮬레이션 중...
              </>
            ) : (
              <>
                <FlaskConical className="w-4 h-4 mr-2" />
                시뮬레이션 실행
              </>
            )}
          </Button>
          {simulateResult && (
            <div className="space-y-4 pt-4 border-t border-slate-200">
              {simulateResult.scenario_summary && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    시나리오 요약
                  </h4>
                  <p className="text-sm text-slate-700 bg-slate-50 p-3 rounded-lg">{simulateResult.scenario_summary}</p>
                </div>
              )}
              {simulateResult.review_points?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-800 mb-2">검토 포인트</h4>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700">
                    {simulateResult.review_points.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
              {simulateResult.mitigation_options?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-800 mb-2">보완·대응 방안</h4>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700">
                    {simulateResult.mitigation_options.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
