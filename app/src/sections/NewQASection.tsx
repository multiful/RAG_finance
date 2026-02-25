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
  Shield,
  BadgeCheck,
  Download,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { SourceCardGrid } from '@/components/dashboard/SourceCard';
import CitationHighlighter, { ConfidenceGauge } from '@/components/CitationHighlighter';
import { toast } from 'sonner';
import { askQuestion, askAgentQuestion } from '@/lib/api';
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
  agent_metadata?: {
    question_type?: string;
    agent_iterations?: number;
    engine?: string;
  };
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
  const [complianceMode, setComplianceMode] = useState(false);
  const [agentMode, setAgentMode] = useState(true);
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
      let assistantMessage: Message;
      
      if (agentMode) {
        const response = await askAgentQuestion(userMessage.content);
        assistantMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: response.answer,
          citations: response.citations,
          confidence: response.confidence,
          groundedness_score: response.groundedness_score,
          citation_coverage: response.citation_coverage,
          hallucination_flag: (response.confidence ?? 0) < 0.4,
          timestamp: new Date(),
          agent_metadata: {
            question_type: response.metadata?.question_type,
            agent_iterations: response.metadata?.agent_iterations,
            engine: response.metadata?.engine,
          },
        };
      } else {
        const response = await askQuestion({ 
          question: userMessage.content,
          compliance_mode: complianceMode
        });
        assistantMessage = {
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
      }

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const detail = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string | unknown } } }).response?.data?.detail
        : null;
      const errText = typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail[0] && typeof detail[0] === 'object' && 'msg' in detail[0]
          ? String((detail[0] as { msg: string }).msg)
          : err instanceof Error
            ? err.message
            : '요청을 처리할 수 없습니다.';
      toast.error(errText, { duration: 6000 });
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `죄송합니다. 오류가 발생했습니다.\n\n${errText}\n\nAPI 키 설정, 네트워크, 서버 상태를 확인해 주세요.`,
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

  const exportAuditLog = () => {
    const auditLog = {
      export_date: new Date().toISOString(),
      session_id: `session_${Date.now()}`,
      compliance_mode: complianceMode,
      total_queries: messages.filter(m => m.type === 'user').length,
      conversations: messages.map((m, idx) => ({
        sequence: idx + 1,
        type: m.type,
        content: m.content,
        timestamp: m.timestamp.toISOString(),
        ...(m.type === 'assistant' && {
          quality_metrics: {
            confidence: m.confidence,
            groundedness_score: m.groundedness_score,
            citation_coverage: m.citation_coverage,
            hallucination_flag: m.hallucination_flag
          },
          citations: m.citations?.map(c => ({
            document_id: c.document_id,
            document_title: c.document_title,
            chunk_id: c.chunk_id,
            published_at: c.published_at,
            url: c.url
          }))
        })
      }))
    };

    const blob = new Blob([JSON.stringify(auditLog, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_log_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const lastAssistant =
    messages.length > 0 && messages[messages.length - 1].type === 'assistant'
      ? messages[messages.length - 1]
      : null;

  return (
    <div className="h-[calc(100vh-180px)] max-w-7xl mx-auto flex flex-col gap-6">
      {/* Premium Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Search className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                AI 질의
              </h2>
              <p className="text-sm text-slate-500">
                공식 문서 기반 · 출처 추적 · 실시간 분석
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Agent Mode Toggle */}
          <div className={`
            flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300
            ${agentMode 
              ? 'bg-gradient-to-r from-purple-50 to-indigo-50 border-2 border-purple-200' 
              : 'bg-white border border-slate-200'
            }
          `}>
            <div className={`
              p-2 rounded-xl transition-all duration-300
              ${agentMode 
                ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/30' 
                : 'bg-slate-100 text-slate-400'
              }
            `}>
              <Radar className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <Label htmlFor="agent-mode" className="text-sm font-semibold text-slate-900 cursor-pointer">
                LangGraph 에이전트
              </Label>
              <span className="text-xs text-slate-500">멀티 스텝 분석</span>
            </div>
            <Switch 
              id="agent-mode" 
              checked={agentMode} 
              onCheckedChange={setAgentMode}
            />
          </div>

          {/* Compliance Mode Toggle */}
          <div className={`
            flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300
            ${complianceMode 
              ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200' 
              : 'bg-white border border-slate-200'
            }
          `}>
            <div className={`
              p-2 rounded-xl transition-all duration-300
              ${complianceMode 
                ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30' 
                : 'bg-slate-100 text-slate-400'
              }
            `}>
              <Shield className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <Label htmlFor="compliance-mode" className="text-sm font-semibold text-slate-900 cursor-pointer">
                컴플라이언스
              </Label>
              <span className="text-xs text-slate-500">출처 추적</span>
            </div>
            <Switch 
              id="compliance-mode" 
              checked={complianceMode} 
              onCheckedChange={setComplianceMode}
            />
          </div>
        </div>
      </div>

      {/* Premium Source Guarantee Banner */}
      <div className="relative overflow-hidden rounded-2xl">
        <div className="absolute inset-0 bg-gradient-to-r from-slate-900 via-slate-800 to-blue-900" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMiI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyek0zNiAzMHYySDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />
        
        <div className="relative p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 backdrop-blur-sm flex items-center justify-center border border-emerald-400/30">
              <BadgeCheck className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base font-bold text-white">공식 출처 기반 응답</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold border border-emerald-400/30">
                  VERIFIED SOURCE
                </span>
              </div>
              <p className="text-sm text-slate-400">
                금융위원회·금융감독원 공식 문서만을 기반으로 분석하며, 모든 답변에 출처가 명시됩니다.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-center px-5 py-3 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10">
              <p className="text-xl font-bold text-emerald-400">100%</p>
              <p className="text-[10px] font-semibold text-slate-500 uppercase">공식 문서</p>
            </div>
            <div className="text-center px-5 py-3 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10">
              <p className="text-xl font-bold text-blue-400">100%</p>
              <p className="text-[10px] font-semibold text-slate-500 uppercase">출처 추적</p>
            </div>
          </div>
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
                      {Object.entries(INDUSTRY_TEMPLATES).map(([key, { icon: Icon, label }]) => (
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
                          <div className="flex flex-wrap items-center gap-3 pb-4 border-b border-slate-50">
                            {/* Agent Badge */}
                            {message.agent_metadata?.engine && (
                              <Badge className="bg-purple-100 text-purple-700 border-none font-bold text-[10px] px-2 py-0.5">
                                <Radar className="w-3 h-3 mr-1" />
                                {message.agent_metadata.question_type || 'Agent'}
                                {message.agent_metadata.agent_iterations && ` · ${message.agent_metadata.agent_iterations}회`}
                              </Badge>
                            )}
                            
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

                            {(() => {
                              const isErrorResponse = /처리 중 오류|Recursion limit|오류가 발생|요청을 처리할 수 없습니다/i.test(message.content || '');
                              if (isErrorResponse) {
                                return (
                                  <Badge className="bg-amber-50 text-amber-700 border border-amber-200 font-semibold text-[10px] px-2 py-0">
                                    <AlertTriangle className="w-3 h-3 mr-1" />
                                    오류 안내
                                  </Badge>
                                );
                              }
                              if (message.hallucination_flag) {
                                return (
                                  <Badge variant="destructive" className="bg-rose-50 text-rose-600 border-none font-black text-[10px] px-2 py-0">
                                    <AlertTriangle className="w-3 h-3 mr-1" />
                                    Integrity Warning
                                  </Badge>
                                );
                              }
                              return null;
                            })()}

                            {!message.hallucination_flag && !/처리 중 오류|Recursion limit|오류가 발생|요청을 처리할 수 없습니다/i.test(message.content || '') &&
                              (message.confidence ?? 0) >= 0.7 && (
                                <Badge className="bg-emerald-50 text-emerald-600 border-none font-black text-[10px] px-2 py-0">
                                  <CheckCircle2 className="w-3 h-3 mr-1" />
                                  Verified
                                </Badge>
                              )}
                          </div>

{/* Answer with Citation Highlighting */}
                                          <div className="text-base font-medium whitespace-pre-wrap">
                                            <CitationHighlighter
                                              content={message.content}
                                              citations={message.citations || []}
                                              onCitationClick={openInspector}
                                            />
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
            {messages.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={exportAuditLog}
                className="text-xs font-bold border-slate-200 hover:bg-emerald-50 hover:text-emerald-600 hover:border-emerald-200"
              >
                <Download className="w-3 h-3 mr-1" />
                감사 로그 내보내기
              </Button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto pr-2 space-y-4">
            {/* Session Statistics */}
            {messages.length > 0 && (
              <Card className="border-none shadow-sm bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-3xl p-5">
                <h4 className="text-xs font-black uppercase tracking-widest mb-3 opacity-70">
                  Session Statistics
                </h4>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <p className="text-2xl font-black">{messages.filter(m => m.type === 'user').length}</p>
                    <p className="text-[10px] font-bold opacity-70">질문</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-black">
                      {messages.filter(m => m.type === 'assistant' && m.citations).reduce((acc, m) => acc + (m.citations?.length || 0), 0)}
                    </p>
                    <p className="text-[10px] font-bold opacity-70">참조 문서</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-black">
                      {messages.filter(m => m.type === 'assistant').length > 0 
                        ? Math.round(
                            messages
                              .filter(m => m.type === 'assistant' && m.groundedness_score)
                              .reduce((acc, m) => acc + (m.groundedness_score || 0), 0) /
                            messages.filter(m => m.type === 'assistant' && m.groundedness_score).length * 100
                          ) || 0
                        : 0}%
                    </p>
                    <p className="text-[10px] font-bold opacity-70">평균 신뢰도</p>
                  </div>
                </div>
              </Card>
            )}

            {lastAssistant ? (
              <div className="space-y-6 animate-in fade-in duration-500">
<Card className="border-none shadow-sm bg-slate-900 text-white rounded-3xl p-6">
                                  <h4 className="text-xs font-black uppercase tracking-widest mb-4 opacity-60">
                                    Response Quality
                                  </h4>
                                  <div className="grid grid-cols-2 gap-3 mb-4">
                                    <ConfidenceGauge 
                                      score={lastAssistant.groundedness_score ?? 0} 
                                      label="Groundedness" 
                                    />
                                    <ConfidenceGauge 
                                      score={lastAssistant.confidence ?? 0} 
                                      label="Confidence" 
                                    />
                                  </div>
                                  <div className="space-y-3 pt-3 border-t border-white/10">
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
                                    <div className="text-[10px] text-white/60">
                                      {lastAssistant.citations?.length || 0}개 문서 참조
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
