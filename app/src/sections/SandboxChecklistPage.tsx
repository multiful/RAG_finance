/**
 * Sandbox Risk-Based Checklist (KAI page_20, page_22)
 * - 설계 원칙 3개 카드
 * - 실무 질문 목록 (R3·R4 기술 무결성, R5·R9 책임 소재)
 * - 예/아니오/부분적 선택 → 제출 후 Gap 보완 제안
 */
import { useEffect, useState, useCallback } from 'react';
import { ClipboardCheck, Send, Loader2, CheckCircle2, FlaskConical, FileText, PlayCircle, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import {
  getSandboxChecklist,
  submitSandboxAssessment,
  getSandboxRemediation,
  sandboxSimulate,
  type SandboxChecklistTemplate,
  type SandboxRemediationSuggestion,
  type SandboxSimulateResponse,
} from '@/lib/api';
import { toast } from 'sonner';

type AnswerValue = 'yes' | 'no' | 'partial';

export default function SandboxChecklistPage() {
  const [template, setTemplate] = useState<SandboxChecklistTemplate | null>(null);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [remediation, setRemediation] = useState<SandboxRemediationSuggestion[] | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [simulateLoading, setSimulateLoading] = useState(false);
  const [simulateResult, setSimulateResult] = useState<SandboxSimulateResponse | null>(null);

  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSandboxChecklist();
      setTemplate(data);
      setAnswers({});
      setRemediation(null);
      setSubmitted(false);
    } catch (e) {
      toast.error('체크리스트 템플릿을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  const handleAnswer = (questionId: string, value: AnswerValue) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async () => {
    if (!template) return;
    const allowedValues = ['yes', 'no', 'partial'] as const;
    const list = template.questions.map((q) => ({
      question_id: q.question_id,
      value: allowedValues.includes((answers[q.question_id] ?? 'yes') as typeof allowedValues[number])
        ? (answers[q.question_id] as typeof allowedValues[number])
        : 'yes',
    }));
    if (list.length === 0) {
      toast.error('진단 항목이 없습니다.');
      return;
    }
    setSubmitting(true);
    try {
      await submitSandboxAssessment(list);
      const suggestions = await getSandboxRemediation(list);
      setRemediation(suggestions);
      setSubmitted(true);
      toast.success('자가진단이 제출되었습니다.');
    } catch (e) {
      toast.error('제출에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const runSandboxSimulation = useCallback(async () => {
    if (!remediation?.length) {
      toast.error('먼저 자가진단을 제출한 뒤 시뮬레이션을 실행하세요.');
      return;
    }
    setSimulateLoading(true);
    setSimulateResult(null);
    try {
      const blind_spot_axes = [...new Set(remediation.map((s) => s.axis_id))];
      const checklist_weaknesses = remediation.map((s) => ({
        question_id: s.question_id || s.axis_id,
        question_ko: s.question_ko,
        response: s.response,
      }));
      const res = await sandboxSimulate({ blind_spot_axes, checklist_weaknesses });
      setSimulateResult(res);
      toast.success('샌드박스 시뮬레이션이 완료되었습니다.');
    } catch (e) {
      toast.error('시뮬레이션 요청에 실패했습니다.');
    } finally {
      setSimulateLoading(false);
    }
  }, [remediation]);

  if (loading || !template) {
    return (
      <div className="p-6 space-y-6 animate-page-enter">
        <Skeleton className="h-8 w-80 mb-2" />
        <Skeleton className="h-4 w-96" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  const questionsByGroup = template.groups.map((g) => ({
    ...g,
    questions: template.questions.filter((q) => q.group_id === g.id),
  }));

  return (
    <div className="p-6 space-y-8 animate-page-enter">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <ClipboardCheck className="w-7 h-7 text-emerald-700" />
          Sandbox용 Risk-Based Checklist
        </h1>
        <p className="text-slate-500 mt-1">
          스테이블코인·STO 결합 환경 리스크에 대한 자가 진단. 국제 기준 대비 국내 규제 Gap 해소를 위한 체크리스트입니다.
        </p>
        {/* 데모 시나리오 안내 및 한 번에 적용 */}
        <div className="mt-4 p-4 rounded-xl bg-indigo-50 border border-indigo-100">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-indigo-900 mb-1">데모 시나리오 (4단계)</p>
              <p className="text-xs text-indigo-800 mb-3">
                1) 아래 &quot;데모 시나리오 적용&quot; 클릭 → 2) 자가진단 제출 → 3) 샌드박스 시뮬레이션 실행 → 4) 검토 포인트·보완 방안 확인
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-indigo-300 text-indigo-700 hover:bg-indigo-100"
                onClick={() => {
                  if (!template) return;
                  const demoAnswers: Record<string, AnswerValue> = {};
                  const firstPerGroup = new Set<string>();
                  template.questions.forEach((q) => {
                    const key = q.group_id;
                    if (!firstPerGroup.has(key)) {
                      firstPerGroup.add(key);
                      demoAnswers[q.question_id] = 'no';
                    }
                  });
                  setAnswers(demoAnswers);
                  setSubmitted(false);
                  setRemediation(null);
                  setSimulateResult(null);
                  toast.success('데모 시나리오가 적용되었습니다. 자가진단 제출 후 시뮬레이션을 실행하세요.');
                }}
              >
                <PlayCircle className="w-4 h-4 mr-2" />
                데모 시나리오 적용
              </Button>
            </div>
          </div>
        </div>
      </header>

      <section>
        <h2 className="text-lg font-semibold text-slate-800 mb-4">설계 원칙</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {template.design_principles.map((p) => (
            <Card key={p.id} className="border-l-4 border-l-emerald-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{p.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-600">{p.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-800 mb-4">실무 진단 항목</h2>
        <p className="text-sm text-slate-500 mb-4">
          각 항목에 대해 예 / 아니오 / 부분적 중 선택해 주세요. &quot;아니오&quot; 또는 &quot;부분적&quot; 응답은 Gap 보완 제안과 연결됩니다.
        </p>
        <div className="space-y-8">
          {questionsByGroup.map((group) => (
            <Card key={group.id}>
              <CardHeader>
                <CardTitle className="text-base text-emerald-900">{group.label}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {group.questions.map((q) => (
                  <div key={q.question_id} className="space-y-2 border-b border-slate-100 pb-4 last:border-0 last:pb-0">
                    <div className="flex items-start gap-2">
                      <span className="font-semibold text-slate-800">{q.question_ko}</span>
                    </div>
                    <p className="text-sm text-slate-500">{q.description_ko}</p>
                    <RadioGroup
                      value={answers[q.question_id] ?? ''}
                      onValueChange={(v) => handleAnswer(q.question_id, v as AnswerValue)}
                      className="flex flex-wrap gap-4"
                    >
                      {template.answer_options.map((opt) => (
                        <div key={opt.value} className="flex items-center space-x-2">
                          <RadioGroupItem value={opt.value} id={`${q.question_id}-${opt.value}`} />
                          <Label htmlFor={`${q.question_id}-${opt.value}`} className="cursor-pointer">
                            {opt.label_ko}
                          </Label>
                        </div>
                      ))}
                    </RadioGroup>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="mt-6 flex justify-end">
          <Button
            onClick={handleSubmit}
            disabled={submitting}
            className="bg-emerald-700 hover:bg-emerald-800"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Send className="w-4 h-4 mr-2" />
            )}
            자가진단 제출
          </Button>
        </div>
      </section>

      {submitted && remediation !== null && (
        <Card className="border-l-4 border-l-amber-500 bg-amber-50/20">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-amber-800">
              <CheckCircle2 className="w-5 h-5" />
              Gap 보완 계획 제안
            </CardTitle>
            <p className="text-sm text-slate-600 font-normal">
              &quot;아니오&quot;/&quot;부분적&quot; 응답에 대해 해당 리스크 축의 보완 권고를 표시합니다.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {remediation.length === 0 ? (
              <p className="text-slate-600">모든 항목이 &quot;예&quot;로 응답되어 추가 보완 제안이 없습니다.</p>
            ) : (
              remediation.map((s, i) => (
                <div
                  key={`${s.axis_id}-${i}`}
                  className="p-4 rounded-lg bg-white border border-amber-100 flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-800">{s.axis_id}</span>
                    <span className="text-sm text-slate-500">
                      해당 질문: {s.question_ko} / 응답: {s.response} (Gap: {s.gap_score.toFixed(2)})
                    </span>
                  </div>
                  <p className="text-sm text-slate-700">{s.suggestion_ko}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}

      {submitted && remediation !== null && remediation.length > 0 && (
        <Card className="border-l-4 border-l-indigo-500">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-indigo-900">
              <FlaskConical className="w-5 h-5" />
              샌드박스 시나리오 시뮬레이션
            </CardTitle>
            <p className="text-sm text-slate-500 font-normal">
              위 보완 제안(약점)을 반영해, 샌드박스 적용 시나리오의 검토 포인트·완화 가능성·권고를 RAG 기반으로 생성합니다.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={runSandboxSimulation}
              disabled={simulateLoading}
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
      )}
    </div>
  );
}
