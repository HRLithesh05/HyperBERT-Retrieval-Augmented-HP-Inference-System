import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface SessionData {
  sessionId: string;
  paperTitle: string;
  timestamp: number;
}

interface SessionContextType {
  /** The current active session ID, or null if none */
  sessionId: string | null;
  /** The paper title for the active session */
  paperTitle: string | null;
  /** Whether the current session is a real (non-demo) session */
  hasRealSession: boolean;
  /** All past sessions (most recent first) */
  history: SessionData[];
  /** Set the active session after a successful analysis */
  setSession: (id: string, title: string) => void;
  /** Clear the active session */
  clearSession: () => void;
  /** Get the number of analyses performed (for auth gating) */
  analysisCount: number;
}

const SessionContext = createContext<SessionContextType | null>(null);

const STORAGE_KEY = 'hyperbert_sessions';
const ACTIVE_KEY = 'hyperbert_active_session';

function loadHistory(): SessionData[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(sessions: SessionData[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

function loadActive(): { sessionId: string; paperTitle: string } | null {
  try {
    const raw = localStorage.getItem(ACTIVE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveActive(sessionId: string, paperTitle: string) {
  localStorage.setItem(ACTIVE_KEY, JSON.stringify({ sessionId, paperTitle }));
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<SessionData[]>(() => loadHistory());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [paperTitle, setPaperTitle] = useState<string | null>(null);

  // Restore active session on mount
  useEffect(() => {
    const active = loadActive();
    if (active) {
      setSessionId(active.sessionId);
      setPaperTitle(active.paperTitle);
    }
  }, []);

  const setSession = (id: string, title: string) => {
    setSessionId(id);
    setPaperTitle(title);
    saveActive(id, title);

    // Add to history (avoid duplicates)
    setHistory(prev => {
      const filtered = prev.filter(s => s.sessionId !== id);
      const updated = [{ sessionId: id, paperTitle: title, timestamp: Date.now() }, ...filtered];
      // Keep last 50 sessions
      const trimmed = updated.slice(0, 50);
      saveHistory(trimmed);
      return trimmed;
    });
  };

  const clearSession = () => {
    setSessionId(null);
    setPaperTitle(null);
    localStorage.removeItem(ACTIVE_KEY);
  };

  const hasRealSession = sessionId !== null && sessionId !== 'demo';

  return (
    <SessionContext.Provider value={{
      sessionId,
      paperTitle,
      hasRealSession,
      history,
      setSession,
      clearSession,
      analysisCount: history.length,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within a SessionProvider');
  return ctx;
}
