/**
 * Citation Highlighter Component
 * 
 * Renders answer text with interactive citation markers that highlight
 * the source when hovered/clicked.
 */
import { useState, useCallback, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { FileText, ExternalLink, Clock } from 'lucide-react';
import type { Citation } from '@/types';

interface CitationHighlighterProps {
  content: string;
  citations: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

interface ParsedSegment {
  type: 'text' | 'citation';
  content: string;
  citationIndex?: number;
}

function parseContentWithCitations(content: string): ParsedSegment[] {
  const segments: ParsedSegment[] = [];
  const citationPattern = /\[(?:출처\s*)?(\d+)\]/g;
  
  let lastIndex = 0;
  let match;
  
  while ((match = citationPattern.exec(content)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      segments.push({
        type: 'text',
        content: content.slice(lastIndex, match.index)
      });
    }
    
    // Add citation marker
    segments.push({
      type: 'citation',
      content: match[0],
      citationIndex: parseInt(match[1]) - 1
    });
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < content.length) {
    segments.push({
      type: 'text',
      content: content.slice(lastIndex)
    });
  }
  
  return segments;
}

function CitationMarker({ 
  index, 
  citation, 
  isHighlighted, 
  onHover, 
  onClick 
}: { 
  index: number;
  citation?: Citation;
  isHighlighted: boolean;
  onHover: (index: number | null) => void;
  onClick: () => void;
}) {
  if (!citation) {
    return (
      <span className="text-slate-400 text-xs">[{index + 1}]</span>
    );
  }
  
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={`
            inline-flex items-center justify-center
            min-w-[1.5rem] h-5 px-1.5
            text-[10px] font-bold
            rounded-md
            transition-all duration-200
            ${isHighlighted 
              ? 'bg-primary text-white shadow-lg shadow-primary/30 scale-110' 
              : 'bg-primary/10 text-primary hover:bg-primary/20'
            }
          `}
          onMouseEnter={() => onHover(index)}
          onMouseLeave={() => onHover(null)}
          onClick={onClick}
        >
          {index + 1}
        </button>
      </PopoverTrigger>
      <PopoverContent 
        className="w-80 p-0 shadow-xl border-slate-200" 
        align="start"
        sideOffset={5}
      >
        <div className="bg-slate-50 px-4 py-3 border-b border-slate-100">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-4 h-4 text-slate-400" />
            <Badge variant="outline" className="text-[10px] font-bold">
              출처 {index + 1}
            </Badge>
          </div>
          <h4 className="font-bold text-sm text-slate-900 line-clamp-2">
            {citation.document_title}
          </h4>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
            <Clock className="w-3 h-3" />
            {new Date(citation.published_at).toLocaleDateString('ko-KR')}
          </div>
        </div>
        <div className="p-4">
          <p className="text-xs text-slate-600 leading-relaxed line-clamp-4">
            {citation.snippet}
          </p>
          <a 
            href={citation.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-3 text-[10px] font-bold text-primary hover:underline"
          >
            원문 보기 <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default function CitationHighlighter({ 
  content, 
  citations,
  onCitationClick 
}: CitationHighlighterProps) {
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);
  
  const segments = useMemo(() => parseContentWithCitations(content), [content]);
  
  const handleCitationClick = useCallback((index: number) => {
    const citation = citations[index];
    if (citation && onCitationClick) {
      onCitationClick(citation);
    }
  }, [citations, onCitationClick]);
  
  return (
    <div className="leading-relaxed">
      {segments.map((segment, i) => {
        if (segment.type === 'text') {
          return (
            <span 
              key={i} 
              className={`
                transition-colors duration-200
                ${highlightedIndex !== null ? 'text-slate-400' : 'text-slate-800'}
              `}
            >
              {segment.content}
            </span>
          );
        }
        
        const citationIndex = segment.citationIndex ?? 0;
        const citation = citations[citationIndex];
        
        return (
          <CitationMarker
            key={i}
            index={citationIndex}
            citation={citation}
            isHighlighted={highlightedIndex === citationIndex}
            onHover={setHighlightedIndex}
            onClick={() => handleCitationClick(citationIndex)}
          />
        );
      })}
    </div>
  );
}

export function ConfidenceGauge({ score, label }: { score: number; label: string }) {
  const percentage = Math.round(score * 100);
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (percentage / 100) * circumference;
  
  const getColor = (pct: number) => {
    if (pct >= 80) return { stroke: '#10b981', bg: 'bg-emerald-50', text: 'text-emerald-600' };
    if (pct >= 60) return { stroke: '#f59e0b', bg: 'bg-amber-50', text: 'text-amber-600' };
    return { stroke: '#ef4444', bg: 'bg-red-50', text: 'text-red-600' };
  };
  
  const colors = getColor(percentage);
  
  return (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-xl ${colors.bg}`}>
      <svg className="w-12 h-12 -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          className="text-slate-200"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={colors.stroke}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div>
        <div className={`text-xl font-black ${colors.text}`}>
          {percentage}%
        </div>
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          {label}
        </div>
      </div>
    </div>
  );
}
