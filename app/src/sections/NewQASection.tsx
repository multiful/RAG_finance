/**
 * New QA Section with SourceCard integration.
 */
import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { SourceCardGrid } from '@/components/dashboard/SourceCard';
import { askQuestion } from '@/lib/api';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  citations?: any[];
  confidence?: number;
  groundedness_score?: number;
  hallucination_flag?: boolean;
  timestamp: Date;
}

export default function NewQASection() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<number | null>(null);
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

    try {
      const response = await askQuestion({ question: userMessage.content });
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence,
        groundedness_score: 0.87, // Mock for now
        hallucination_flag: false,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '죄송합니다. 답변을 생성하는 중 오류가 발생했습니다.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-120px)] grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* Chat Area */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        <div>
          <h2 className="section-title">RAG 질의응답</h2>
          <p className="text-muted-foreground text-sm">
            근거 인용형 AI 답변 - 문서 기반 정확한 정보 제공
          </p>
        </div>

        <Card className="flex-1 flex flex-col card-elevated">
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-4">
                  <Send className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-lg font-medium mb-2">금융정책에 대해 질문하세요</h3>
                <p className="text-muted-foreground text-sm max-w-md mb-6">
                  모든 답변은 근거 문서와 함께 제시됩니다.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
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
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[90%] rounded-2xl p-4 ${
                      message.type === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-white border border-lavender-100 shadow-sm'
                    }`}
                  >
                    {message.type === 'assistant' && (
                      <div className="space-y-3">
                        {/* Quality Metrics */}
                        <div className="flex items-center gap-3 pb-3 border-b border-lavender-100">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">근거일치:</span>
                            <Badge className={message.groundedness_score && message.groundedness_score >= 0.8 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>
                              {((message.groundedness_score || 0) * 100).toFixed(0)}%
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">신뢰도:</span>
                            <Progress value={(message.confidence || 0) * 100} className="w-16 h-1.5" />
                          </div>
                          {message.hallucination_flag && (
                            <Badge variant="destructive" className="text-xs">
                              <AlertTriangle className="w-3 h-3 mr-1" />
                              환각 의심
                            </Badge>
                          )}
                        </div>

                        {/* Answer */}
                        <div className="text-sm leading-relaxed whitespace-pre-wrap">
                          {message.content}
                        </div>

                        {/* Citations Preview */}
                        {message.citations && message.citations.length > 0 && (
                          <div className="pt-3 border-t border-lavender-100">
                            <p className="text-xs text-muted-foreground mb-2">
                              근거 문서 ({message.citations.length}개)
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {message.citations.slice(0, 3).map((citation) => (
                                <button
                                  key={citation.chunk_id}
                                  onClick={() => setSelectedCitation(citation.index)}
                                  className="text-xs px-2 py-1 bg-lavender-100 text-primary rounded-full hover:bg-primary/20 transition-colors"
                                >
                                  [{citation.index}] {citation.document_title.slice(0, 20)}...
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                    {message.type === 'user' && <p>{message.content}</p>}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </CardContent>

          {/* Input */}
          <div className="p-4 border-t">
            <form onSubmit={handleSubmit} className="flex gap-2">
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
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </form>
          </div>
        </Card>
      </div>

      {/* Sources Panel */}
      <div className="lg:col-span-2">
        <div className="mb-4">
          <h3 className="font-medium">근거 문서</h3>
          <p className="text-sm text-muted-foreground">
            {messages.length > 0 && messages[messages.length - 1].type === 'assistant'
              ? `${messages[messages.length - 1].citations?.length || 0}개 문서 참조`
              : '질문에 대한 근거 문서가 여기에 표시됩니다'
            }
          </p>
        </div>

        <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-200px)]">
          {messages.length > 0 && 
           messages[messages.length - 1].type === 'assistant' &&
           messages[messages.length - 1].citations ? (
            <SourceCardGrid
              citations={messages[messages.length - 1].citations?.map((c, i) => ({
                ...c,
                index: i + 1
              })) || []}
              selectedIndex={selectedCitation || undefined}
              onSelect={setSelectedCitation}
            />
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-sm">질문을 입력하면<br />근거 문서가 표시됩니다</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
