/**
 * SourceCard: 검색된 원문 문단을 하이라이트해서 보여주는 카드.
 */
import { useState } from 'react';
import { FileText, ExternalLink, ChevronDown, ChevronUp, Quote } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Citation {
  index: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  published_at: string;
  url: string;
  snippet?: string;
}

interface SourceCardProps {
  citation: Citation;
  highlightedText?: string;
  isHighlighted?: boolean;
}

export default function SourceCard({ 
  citation, 
  highlightedText = '',
  isHighlighted = false 
}: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);

  // 하이라이트 처리
  const highlightSnippet = (text: string, highlight: string) => {
    if (!highlight || !text) return text;
    
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === highlight.toLowerCase() ? (
        <mark key={i} className="bg-amber-200 text-amber-900 px-0.5 rounded">
          {part}
        </mark>
      ) : part
    );
  };

  return (
    <Card 
      className={`
        transition-all duration-200 overflow-hidden
        ${isHighlighted 
          ? 'ring-2 ring-primary shadow-lg' 
          : 'hover:shadow-md border-lavender-100'
        }
      `}
    >
      <CardHeader className="py-3 px-4 bg-gradient-to-r from-lavender-50 to-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full gradient-primary flex items-center justify-center text-white text-sm font-bold">
              {citation.index}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{citation.document_title}</p>
              <p className="text-xs text-muted-foreground">
                {citation.published_at ? new Date(citation.published_at).toLocaleDateString('ko-KR') : '날짜 없음'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:text-primary/80"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4">
        <div className="relative">
          <Quote className="absolute -top-1 -left-1 w-5 h-5 text-lavender-300" />
          
          <div className={`
            pl-6 text-sm text-muted-foreground leading-relaxed
            ${expanded ? '' : 'line-clamp-4'}
          `}>
            {citation.snippet ? (
              highlightSnippet(citation.snippet, highlightedText)
            ) : (
              '내용을 불러올 수 없습니다.'
            )}
          </div>

          {citation.snippet && citation.snippet.length > 200 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="mt-2 h-8 text-xs"
            >
              {expanded ? (
                <>
                  <ChevronUp className="w-3 h-3 mr-1" />
                  접기
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3 mr-1" />
                  더 보기
                </>
              )}
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-lavender-100">
          <Badge variant="outline" className="text-xs">
            <FileText className="w-3 h-3 mr-1" />
            {citation.chunk_id?.slice(0, 8)}...
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

// 여러 SourceCard를 그리드로 표시
interface SourceCardGridProps {
  citations: Citation[];
  highlightedText?: string;
  selectedIndex?: number;
  onSelect?: (index: number) => void;
}

export function SourceCardGrid({ 
  citations, 
  highlightedText = '',
  selectedIndex,
  onSelect 
}: SourceCardGridProps) {
  return (
    <div className="grid grid-cols-1 gap-3">
      {citations.map((citation) => (
        <div 
          key={citation.chunk_id}
          onClick={() => onSelect?.(citation.index)}
          className="cursor-pointer"
        >
          <SourceCard
            citation={citation}
            highlightedText={highlightedText}
            isHighlighted={selectedIndex === citation.index}
          />
        </div>
      ))}
    </div>
  );
}
