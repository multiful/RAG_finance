import { useState, useRef, useEffect } from 'react';
import { 
  Search, 
  Send, 
  FileText, 
  ExternalLink, 
  Loader2,
  AlertTriangle,
  Quote,
  Building2,
  Landmark,
  TrendingUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { askQuestionStream } from '@/lib/api';
import type { QAResponse } from '@/types';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  response?: QAResponse;
  timestamp: Date;
  isStreaming?: boolean;
}

export default function RAGQA() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
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

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    const assistantMsgId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMsgId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      response: undefined
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      let fullAnswer = '';
      await askQuestionStream(
        { question: userMessage.content },
        (event) => {
          setMessages(prev => prev.map(msg => {
            if (msg.id === assistantMsgId) {
              if (event.type === 'citations') {
                return {
                  ...msg,
                  response: {
                    answer: '',
                    summary: '',
                    industry_impact: {},
                    checklist: [],
                    citations: event.citations,
                    confidence: 0,
                  }
                };
              } else if (event.type === 'token') {
                fullAnswer += event.token;
                return {
                  ...msg,
                  content: fullAnswer
                };
              } else if (event.type === 'final') {
                return {
                  ...msg,
                  isStreaming: false,
                  response: {
                    ...msg.response!,
                    ...event.data,
                    answer: fullAnswer,
                    answerable: event.data.answerable ?? true
                  }
                };
              } else if (event.type === 'error') {
                return {
                  ...msg,
                  isStreaming: false,
                  content: event.content
                };
              }
            }
            return msg;
          }));
        }
      );
    } catch (error) {
      console.error('Error asking question:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMsgId 
          ? { ...msg, isStreaming: false, content: '죄송합니다. 답변을 생성하는 중 오류가 발생했습니다.' }
          : msg
      ));
    } finally {
      setLoading(false);
    }
  };

  const getIndustryIcon = (industry: string) => {
    switch (industry) {
      case 'INSURANCE':
        return <Building2 className="w-4 h-4" />;
      case 'BANKING':
        return <Landmark className="w-4 h-4" />;
      case 'SECURITIES':
        return <TrendingUp className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getIndustryLabel = (industry: string) => {
    switch (industry) {
      case 'INSURANCE':
        return '보험';
      case 'BANKING':
        return '은행';
      case 'SECURITIES':
        return '증권';
      default:
        return industry;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in h-[calc(100vh-140px)]">
      {/* Header */}
      <div>
        <h2 className="section-title">RAG 질의응답</h2>
        <p className="text-muted-foreground mt-1">
          근거 인용형 AI 답변 - 문서 기반 정확한 정보 제공
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        {/* Chat Area */}
        <Card className="card-elevated lg:col-span-2 flex flex-col h-full">
          <CardHeader className="border-b">
            <CardTitle className="text-lg flex items-center gap-2">
              <Search className="w-5 h-5 text-primary" />
              질문하기
            </CardTitle>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-hidden flex flex-col p-0">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-4">
                    <Search className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">
                    금융정책에 대해 질문하세요
                  </h3>
                  <p className="text-muted-foreground text-sm max-w-md">
                    금융위원회 볏  도자료, 공지사항 등을 기반으로 정확한 답변을 제공합니다.
                    모든 답변은 근거 문서와 함께 제시됩니다.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-6 justify-center">
                    {[
                      '보험사 납입면제 제도 변경사항은?',
                      '은행권 가계대출 규제 최신 동향',
                      '증권사 CMA 금리 인상 관련 공지'
                    ].map((q) => (
                      <button
                        key={q}
                        onClick={() => setInput(q)}
                        className="px-4 py-2 bg-muted rounded-full text-sm hover:bg-primary/10 hover:text-primary transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.type === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 ${
                        message.type === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      {message.type === 'assistant' && message.response ? (
                        <div className="space-y-4">
                          {/* Answerable Warning */}
                          {message.response.answerable === false && message.response.citations.length > 0 && (
                            <div className="bg-amber-50 border-l-4 border-amber-500 p-3 rounded-r-lg mb-4">
                              <p className="text-amber-800 text-xs font-bold flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                부분적인 정보만 확인됨
                              </p>
                              <p className="text-amber-700 text-[11px] mt-1">
                                질문에 대한 직접적인 답변을 문서에서 찾을 수 없습니다. 
                                우측의 관련 근거 문서를 참고하시기 바랍니다.
                              </p>
                            </div>
                          )}

                          {/* Summary */}
                          {message.response.summary && (
                            <div>
                              <p className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Quote className="w-4 h-4" />
                                요약
                              </p>
                              <p className="text-sm leading-relaxed">
                                {message.response.summary}
                              </p>
                            </div>
                          )}

                          {/* Industry Impact */}
                          {Object.keys(message.response.industry_impact || {}).length > 0 && (
                            <div>
                              <p className="text-sm font-medium mb-2">업권 영향</p>
                              <div className="flex flex-wrap gap-2">
                                {Object.entries(message.response.industry_impact)
                                  .filter(([, value]) => value > 0.3)
                                  .map(([industry, value]) => (
                                    <Badge 
                                      key={industry}
                                      variant="secondary"
                                      className="flex items-center gap-1"
                                    >
                                      {getIndustryIcon(industry)}
                                      {getIndustryLabel(industry)}
                                      <span className="ml-1">{(value * 100).toFixed(0)}%</span>
                                    </Badge>
                                  ))}
                              </div>
                            </div>
                          )}

                          {/* Full Answer */}
                          <div className={message.response.summary ? "pt-2 border-t border-border/50" : ""}>
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">
                              {message.content}
                            </p>
                          </div>

                          {/* Confidence & Uncertainty */}
                          {message.response.confidence > 0 && (
                            <div className="flex items-center gap-4 pt-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">신뢰도:</span>
                                <Progress 
                                  value={message.response.confidence * 100} 
                                  className="w-16 h-1.5"
                                />
                                <span className="text-xs">
                                  {(message.response.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                              {message.response.uncertainty_note && (
                                <div className="flex items-center gap-1 text-amber-600 text-xs">
                                  <AlertTriangle className="w-3 h-3" />
                                  {message.response.uncertainty_note}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form 
              onSubmit={handleSubmit}
              className="p-4 border-t flex gap-2"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="질문을 입력하세요..."
                disabled={loading}
                className="flex-1"
              />
              <Button 
                type="submit" 
                disabled={loading || !input.trim()}
                className="gradient-primary text-white"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Citations Panel */}
        <Card className="card-elevated flex flex-col h-full">
          <CardHeader className="border-b">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              근거 문서
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto p-4">
            {messages.length === 0 || messages[messages.length - 1].type === 'user' ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                <Quote className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-sm">
                  질문에 대한 근거 문서가<br />여기에 표시됩니다
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {messages[messages.length - 1].response?.citations.map((citation, index) => (
                  <div 
                    key={citation.chunk_id}
                    className="p-4 bg-muted/50 rounded-xl"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 rounded-full gradient-primary flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-sm">{citation.document_title}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(citation.published_at).toLocaleDateString('ko-KR')}
                        </p>
                        <div className="mt-3 p-3 bg-white rounded-lg border border-border">
                          <Quote className="w-4 h-4 text-muted-foreground mb-2" />
                          <p className="text-sm text-muted-foreground line-clamp-4">
                            {citation.snippet}
                          </p>
                        </div>
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-2"
                        >
                          <ExternalLink className="w-3 h-3" />
                          원문 보기
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
                
                {messages[messages.length - 1].response?.citations.length === 0 && (
                  <div className="flex items-center gap-2 text-amber-600 p-4 bg-amber-50 rounded-xl">
                    <AlertTriangle className="w-5 h-5" />
                    <p className="text-sm">근거 문서를 찾을 수 없습니다</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
