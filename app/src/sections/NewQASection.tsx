import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Search,
  Info,
  Radar,
  Building2,
  Landmark,
  TrendingUp,
  ChevronDown,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { SourceCardGrid } from '@/components/dashboard/SourceCard';
import { askQuestion } from '@/lib/api';
import type { Citation } from '@/types';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  groundedness_score?: number;
  citation_coverage?: number;
  hallucination_flag?: boolean;
  timestamp: Date;
}

interface QATemplate {
  category: string;
  questions: string[];
}

const INDUSTRY_TEMPLATES: Record<string, { icon: React.ElementType; label: string; color: string; templates: QATemplate[] }> = {
  insurance: {
    icon: Building2,
    label: '보험업',
    color: 'bg-blue-500',
    templates: [
      {
        category: 'K-ICS / 자본규제',
        questions: [
          'K-ICS 2.0 도입에 따른 보험사 자본적정성 평가 기준은?',
          'K-ICS와 기존 RBC 제도의 주요 차이점은?',
          'K-ICS 경과조치 기간 중 보험사 대응 의무는?',
        ],
      },
      {
        category: '보험업감독규정',
        questions: [
          '보험업감독규정 최근 개정사항 요약해줘',
          '보험상품 신고/심사 제도 변경사항은?',
          '보험사 내부통제기준 강화 내용은?',
        ],
      },
      {
        category: '소비자보호',
        questions: [
          '금융소비자보호법에 따른 보험 판매 규제는?',
          '보험계약 청약철회권 관련 규정 변경사항은?',
          '고령 소비자 보호를 위한 보험 판매 기준은?',
        ],
      },
    ],
  },
  banking: {
    icon: Landmark,
    label: '은행업',
    color: 'bg-green-500',
    templates: [
      {
        category: 'LCR/NSFR 유동성',
        questions: [
          'LCR(유동성커버리지비율) 산정 기준 변경사항은?',
          'NSFR(순안정자금조달비율) 규제 적용 현황은?',
          '시스템적 중요 은행의 추가 유동성 요건은?',
        ],
      },
      {
        category: '가계대출 규제',
        questions: [
          'DSR 규제 현황과 최근 변경사항은?',
          'LTV 규제 지역별 적용 기준은?',
          '스트레스 DSR 도입 내용과 시행 일정은?',
        ],
      },
      {
        category: '내부통제/리스크',
        questions: [
          '은행 내부통제기준 최근 강화 내용은?',
          '금리 리스크 관리 기준 변경사항은?',
          '운영리스크 자본 산출 방식 개정 내용은?',
        ],
      },
    ],
  },
  securities: {
    icon: TrendingUp,
    label: '증권업',
    color: 'bg-purple-500',
    templates: [
      {
        category: '자본시장법',
        questions: [
          '자본시장법 최근 주요 개정사항은?',
          '증권사 영업용순자본비율 규제 변경은?',
          '파생상품 투자자 보호 강화 내용은?',
        ],
      },
      {
        category: '공매도/시장규제',
        questions: [
          '공매도 규제 현황과 향후 방향은?',
          '불공정거래 규제 강화 내용은?',
          '외국인 투자자 관련 규제 변경사항은?',
        ],
      },
      {
        category: '기업금융',
        questions: [
          '대주주 적격성 심사 기준 변경사항은?',
          'IPO 관련 규제 최근 변경사항은?',
          'M&A 공시 의무 강화 내용은?',
        ],
      },
    ],
  },
  general: {
    icon: Search,
    label: '공통',
    color: 'bg-slate-500',
    templates: [
      {
        category: '금융소비자보호',
        questions: [
          '금융소비자보호법 핵심 내용과 금융기관 의무는?',
          '적합성/적정성 원칙 적용 기준은?',
          '설명의무 위반 시 제재 내용은?',
        ],
      },
      {
        category: 'ESG/지속가능',
        questions: [
          'ESG 공시 의무화 로드맵과 일정은?',
          '녹색금융 분류체계 적용 기준은?',
          '기후리스크 관리 가이드라인 내용은?',
        ],
      },
      {
        category: '디지털금융',
        questions: [
          '가상자산 관련 최신 규제 동향은?',
          '마이데이터 사업자 의무사항은?',
          '오픈뱅킹 확대 적용 내용은?',
        ],
      },
    ],
  },
};

export default function NewQASection() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await askQuestion({ question: userMessage.content });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence,
        groundedness_score: response.groundedness_score,
        citation_coverage: response.citation_coverage,
        hallucination_flag: (response.confidence ?? 0) < 0.4,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '죄송합니다. 근거 문서를 분석하는 중 오류가 발생했습니다.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const openInspector = (citation: Citation) => {
    setSelectedCitation(citation);
    setInspectorOpen(true);
  };

  const lastAssistant =
    messages.length > 0 && messages[messages.length - 1].type === 'assistant'
      ? messages[messages.length - 1]
      : null;

  return (
    <div className="h-[calc(100vh-140px)] max-w-6xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">
            Q&amp;A Workspace
          </h2>
          <p className="text-slate-500 mt-2 text-lg">
            금융정책 문서 기반 인공지능 분석 및 근거 기반 답변
          </p>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-8 overflow-hidden">
        {/* Chat Area */}
        <div className="lg:col-span-3 flex flex-col gap-4 overflow-hidden">
          <Card className="flex-1 flex flex-col border-none shadow-xl shadow-slate-200/50 bg-white rounded-[2rem] overflow-hidden">
            <CardContent className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-hide">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col p-4">
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 rounded-[2rem] bg-indigo-50 flex items-center justify-center mx-auto mb-4 shadow-inner">
                      <Send className="w-7 h-7 text-indigo-500" />
                    </div>
                    <h3 className="text-lg font-black text-slate-900 mb-2">
                      업권별 질문 템플릿
                    </h3>
                    <p className="text-slate-500 font-medium text-sm">
                      자주 묻는 질문을 선택하거나 직접 입력하세요
                    </p>
                  </div>
                  
                  <Tabs defaultValue="general" className="flex-1">
                    <TabsList className="grid grid-cols-4 mb-4">
                      {Object.entries(INDUSTRY_TEMPLATES).map(([key, { icon: Icon, label, color }]) => (
                        <TabsTrigger 
                          key={key} 
                          value={key}
                          className="text-xs font-bold data-[state=active]:bg-slate-900 data-[state=active]:text-white"
                        >
                          <Icon className="w-3 h-3 mr-1" />
                          {label}
                        </TabsTrigger>
                      ))}
                    </TabsList>
                    
                    {Object.entries(INDUSTRY_TEMPLATES).map(([key, { templates, color }]) => (
                      <TabsContent key={key} value={key} className="mt-0 space-y-4 overflow-y-auto max-h-[400px]">
                        {templates.map((template) => (
                          <div key={template.category} className="space-y-2">
                            <h4 className="text-xs font-black text-slate-400 uppercase tracking-wider px-2">
                              {template.category}
                            </h4>
                            <div className="space-y-2">
                              {template.questions.map((q) => (
                                <button
                                  key={q}
                                  onClick={() => setInput(q)}
                                  className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl text-sm font-medium text-slate-600 hover:bg-white hover:border-primary hover:text-primary hover:shadow-md transition-all text-left flex items-center gap-3 group"
                                  type="button"
                                >
                                  <div className={`w-2 h-2 rounded-full ${color} opacity-60 group-hover:opacity-100 transition-opacity`} />
                                  <span className="flex-1">{q}</span>
                                  <ChevronDown className="w-4 h-4 opacity-0 group-hover:opacity-100 -rotate-90 transition-all" />
                                </button>
                              ))}
                            </div>
                          </div>
                        ))}
                      </TabsContent>
                    ))}
                  </Tabs>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.type === 'user' ? 'justify-end' : 'justify-start'
                    } animate-in slide-in-from-bottom-2 duration-300`}
                  >
                    <div
                      className={`max-w-[90%] rounded-[2rem] p-6 ${
                        message.type === 'user'
                          ? 'bg-slate-900 text-white shadow-xl shadow-slate-200'
                          : 'bg-white border border-slate-100 shadow-lg shadow-slate-100'
                      }`}
                    >
                      {message.type === 'assistant' && (
                        <div className="space-y-4">
                          {/* Quality Metrics */}
                          <div className="flex items-center gap-4 pb-4 border-b border-slate-50">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                Groundedness
                              </span>
                              <Badge
                                className={`px-2 py-0 border-none font-black text-[10px] ${
                                  (message.groundedness_score ?? 0) >= 0.7
                                    ? 'bg-emerald-50 text-emerald-600'
                                    : 'bg-amber-50 text-amber-600'
                                }`}
                              >
                                {(((message.groundedness_score ?? 0) * 100) as number).toFixed(0)}%
                              </Badge>
                            </div>

                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                Confidence
                              </span>
                              <div className="w-16 h-1 bg-slate-50 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-indigo-500"
                                  style={{
                                    width: `${(message.confidence ?? 0) * 100}%`,
                                  }}
                                />
                              </div>
                            </div>

                            {message.hallucination_flag && (
                              <Badge
                                variant="destructive"
                                className="bg-rose-50 text-rose-600 border-none font-black text-[10px] px-2 py-0"
                              >
                                <AlertTriangle className="w-3 h-3 mr-1" />
                                Integrity Warning
                              </Badge>
                            )}

                            {!message.hallucination_flag &&
                              (message.confidence ?? 0) >= 0.7 && (
                                <Badge className="bg-emerald-50 text-emerald-600 border-none font-black text-[10px] px-2 py-0">
                                  <CheckCircle2 className="w-3 h-3 mr-1" />
                                  Verified
                                </Badge>
                              )}
                          </div>

                          {/* Answer */}
                          <div className="text-base font-medium leading-relaxed text-slate-800 whitespace-pre-wrap">
                            {message.content}
                          </div>

                          {/* Citations Preview */}
                          {message.citations && message.citations.length > 0 && (
                            <div className="pt-4 border-t border-slate-50">
                              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">
                                Evidence Chain ({message.citations.length})
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {message.citations.map((citation, idx) => (
                                  <button
                                    key={citation.chunk_id}
                                    onClick={() => openInspector(citation)}
                                    className="text-[10px] font-bold px-3 py-1.5 bg-slate-50 text-slate-500 rounded-lg hover:bg-primary/10 hover:text-primary transition-all border border-slate-100 flex items-center gap-2"
                                    type="button"
                                  >
                                    <FileText className="w-3 h-3" />
                                    [{idx + 1}] {citation.document_title.slice(0, 15)}...
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {message.type === 'user' && (
                        <p className="font-bold text-base">{message.content}</p>
                      )}
                    </div>
                  </div>
                ))
              )}

              <div ref={messagesEndRef} />
            </CardContent>

            {/* Input */}
            <div className="p-6 bg-slate-50/50 border-t border-slate-50">
              <form onSubmit={handleSubmit} className="flex gap-3 relative">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="금융 정책에 대해 물어보세요..."
                  disabled={loading}
                  className="flex-1 h-14 pl-6 pr-16 bg-white border-slate-200 rounded-2xl shadow-sm focus-visible:ring-primary font-medium"
                />
                <Button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="absolute right-2 top-2 h-10 w-10 p-0 gradient-primary text-white rounded-xl shadow-lg shadow-primary/20"
                >
                  {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </Button>
              </form>
              <p className="text-center text-[10px] font-bold text-slate-400 mt-3 uppercase tracking-widest">
                Production-grade RAG | Evidence-Chain Enforcement Enabled
              </p>
            </div>
          </Card>
        </div>

        {/* Info Panel */}
        <div className="lg:col-span-2 flex flex-col gap-6 overflow-hidden">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Info className="w-5 h-5 text-primary" />
              Session Insights
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 space-y-4">
            {lastAssistant ? (
              <div className="space-y-6 animate-in fade-in duration-500">
                <Card className="border-none shadow-sm bg-indigo-900 text-white rounded-3xl p-6">
                  <h4 className="text-xs font-black uppercase tracking-widest mb-4 opacity-60">
                    Response Quality
                  </h4>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-[10px] font-bold mb-1">
                        <span>CITATION COVERAGE</span>
                        <span>
                          {(((lastAssistant.citation_coverage ?? 0) * 100) as number).toFixed(0)}%
                        </span>
                      </div>
                      <Progress
                        value={(lastAssistant.citation_coverage ?? 0) * 100}
                        className="h-1 bg-white/10"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[10px] font-bold mb-1">
                        <span>GROUNDEDNESS SCORE</span>
                        <span>
                          {(((lastAssistant.groundedness_score ?? 0) * 100) as number).toFixed(0)}%
                        </span>
                      </div>
                      <Progress
                        value={(lastAssistant.groundedness_score ?? 0) * 100}
                        className="h-1 bg-white/10"
                      />
                    </div>
                  </div>
                </Card>

                <div className="space-y-4">
                  <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest px-2">
                    References
                  </h4>

                  <SourceCardGrid
                    citations={
                      lastAssistant.citations?.map((c, i) => ({
                        ...c,
                        index: i + 1,
                      })) || []
                    }
                    onSelect={(idx) => {
                      const cit = lastAssistant.citations?.[idx - 1];
                      if (cit) openInspector(cit);
                    }}
                  />
                </div>
              </div>
            ) : (
              <Card className="h-full border-2 border-dashed border-slate-200 bg-slate-50/50 rounded-[2rem] flex flex-col items-center justify-center text-center p-10">
                <div className="w-20 h-20 rounded-3xl bg-white shadow-sm flex items-center justify-center mb-6">
                  <Search className="w-10 h-10 text-slate-200" />
                </div>
                <h4 className="text-lg font-bold text-slate-900 mb-2">
                  근거 분석 대기 중
                </h4>
                <p className="text-slate-500 font-medium">
                  질문을 입력하면 답변 생성에 사용된 핵심 문서 조각들과 품질 지표가 여기에
                  표시됩니다.
                </p>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Source Inspector Sheet */}
      <Sheet open={inspectorOpen} onOpenChange={setInspectorOpen}>
        <SheetContent className="sm:max-w-xl w-full p-0 border-l border-slate-200 rounded-l-[3rem]">
          {selectedCitation && (
            <div className="h-full flex flex-col">
              <SheetHeader className="p-8 border-b border-slate-100 bg-slate-50/50">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center shadow-lg">
                    <FileText className="w-5 h-5 text-white" />
                  </div>
                  <Badge
                    variant="outline"
                    className="border-slate-200 text-slate-500 font-bold uppercase tracking-tighter"
                  >
                    Document Source
                  </Badge>
                </div>

                <SheetTitle className="text-2xl font-black text-slate-900 leading-tight">
                  {selectedCitation.document_title}
                </SheetTitle>

                <SheetDescription className="text-slate-500 font-medium flex items-center gap-2 mt-2">
                  Published at{' '}
                  {new Date(selectedCitation.published_at).toLocaleDateString()}
                </SheetDescription>
              </SheetHeader>

              <div className="flex-1 overflow-y-auto p-8 space-y-8 scrollbar-hide">
                <section>
                  <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">
                    Retrieved Context Chunk
                  </h4>
                  <div className="bg-slate-50 rounded-[2rem] p-8 border border-slate-100 text-slate-800 leading-relaxed font-medium whitespace-pre-wrap">
                    {selectedCitation.snippet}
                  </div>
                </section>

                <section className="space-y-4">
                  <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    Metadata
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-2xl bg-white border border-slate-100 shadow-sm">
                      <p className="text-[9px] font-black text-slate-400 uppercase">
                        Chunk ID
                      </p>
                      <p className="text-xs font-bold text-slate-700 truncate">
                        {selectedCitation.chunk_id}
                      </p>
                    </div>
                    <div className="p-4 rounded-2xl bg-white border border-slate-100 shadow-sm">
                      <p className="text-[9px] font-black text-slate-400 uppercase">
                        Document ID
                      </p>
                      <p className="text-xs font-bold text-slate-700 truncate">
                        {selectedCitation.document_id}
                      </p>
                    </div>
                  </div>
                </section>

                <div className="pt-8 border-t border-slate-100">
                  <Button
                    variant="outline"
                    className="w-full h-14 rounded-2xl border-slate-200 text-slate-600 font-black text-sm hover:bg-slate-50 flex items-center gap-3"
                    onClick={() => window.open(selectedCitation.url, '_blank')}
                    type="button"
                  >
                    원문 문서 보기 (금융위원회)
                    <Radar className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
