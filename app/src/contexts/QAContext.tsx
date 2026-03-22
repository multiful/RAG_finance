/**
 * AI 질의(/qa) 세션 상태 — 라우트 이동 시에도 유지 (sessionStorage 동기화)
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { Citation } from '@/types';

const STORAGE_KEY = 'rag_finance_qa_v1';

export interface QAMessage {
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

interface PersistedPayload {
  messages: Array<Omit<QAMessage, 'timestamp'> & { timestamp: string }>;
  input: string;
  complianceMode: boolean;
  agentMode: boolean;
}

function loadFromStorage(): {
  messages: QAMessage[];
  input: string;
  complianceMode: boolean;
  agentMode: boolean;
} {
  if (typeof window === 'undefined') {
    return { messages: [], input: '', complianceMode: true, agentMode: false };
  }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { messages: [], input: '', complianceMode: true, agentMode: false };
    }
    const parsed = JSON.parse(raw) as PersistedPayload;
    const messages = (parsed.messages ?? []).map((m) => ({
      ...m,
      timestamp: new Date(m.timestamp),
    }));
    return {
      messages,
      input: parsed.input ?? '',
      complianceMode: parsed.complianceMode ?? true,
      agentMode: parsed.agentMode ?? false,
    };
  } catch {
    return { messages: [], input: '', complianceMode: false, agentMode: false };
  }
}

function saveToStorage(state: {
  messages: QAMessage[];
  input: string;
  complianceMode: boolean;
  agentMode: boolean;
}) {
  try {
    const payload: PersistedPayload = {
      messages: state.messages.map((m) => ({
        ...m,
        timestamp: m.timestamp.toISOString(),
      })),
      input: state.input,
      complianceMode: state.complianceMode,
      agentMode: state.agentMode,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // quota 등 — 무시
  }
}

interface QAContextValue {
  messages: QAMessage[];
  setMessages: React.Dispatch<React.SetStateAction<QAMessage[]>>;
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  complianceMode: boolean;
  setComplianceMode: React.Dispatch<React.SetStateAction<boolean>>;
  agentMode: boolean;
  setAgentMode: React.Dispatch<React.SetStateAction<boolean>>;
  selectedCitation: Citation | null;
  setSelectedCitation: React.Dispatch<React.SetStateAction<Citation | null>>;
  inspectorOpen: boolean;
  setInspectorOpen: React.Dispatch<React.SetStateAction<boolean>>;
  resetQASession: () => void;
}

const QAContext = createContext<QAContextValue | null>(null);

export function QAProvider({ children }: { children: ReactNode }) {
  const initial = useMemo(() => loadFromStorage(), []);
  const [messages, setMessages] = useState<QAMessage[]>(initial.messages);
  const [input, setInput] = useState(initial.input);
  const [loading, setLoading] = useState(false);
  const [complianceMode, setComplianceMode] = useState(initial.complianceMode);
  const [agentMode, setAgentMode] = useState(initial.agentMode);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  useEffect(() => {
    saveToStorage({ messages, input, complianceMode, agentMode });
  }, [messages, input, complianceMode, agentMode]);

  const resetQASession = useCallback(() => {
    setMessages([]);
    setInput('');
    setLoading(false);
    setComplianceMode(true);
    setAgentMode(false);
    setSelectedCitation(null);
    setInspectorOpen(false);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* noop */
    }
  }, []);

  const value = useMemo<QAContextValue>(
    () => ({
      messages,
      setMessages,
      input,
      setInput,
      loading,
      setLoading,
      complianceMode,
      setComplianceMode,
      agentMode,
      setAgentMode,
      selectedCitation,
      setSelectedCitation,
      inspectorOpen,
      setInspectorOpen,
      resetQASession,
    }),
    [
      messages,
      input,
      loading,
      complianceMode,
      agentMode,
      selectedCitation,
      inspectorOpen,
      resetQASession,
    ]
  );

  return <QAContext.Provider value={value}>{children}</QAContext.Provider>;
}

export function useQA() {
  const ctx = useContext(QAContext);
  if (!ctx) {
    throw new Error('useQA must be used within QAProvider');
  }
  return ctx;
}
