/**
 * SessionContext — Persists the current analysis session ID across all pages.
 * Stored in React Context + localStorage so navigation between
 * Results / Compare / Notebook / Downloads never loses the active session.
 *
 * Also tracks:
 *   - guest_id: Anonymous user identity (UUID) for per-user session history
 *   - sessionHistory: Past analyses fetched from backend MongoDB
 */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { getSessions, type SessionSummary } from '@/lib/api';

interface SessionState {
  /** The current active session ID (UUID from backend) */
  sessionId: string | null;
  /** Set a new active session after upload completes */
  setSession: (id: string) => void;
  /** Clear the session (e.g. when user wants to analyze a new paper) */
  clearSession: () => void;
  /** Track guest usage count */
  guestUsageCount: number;
  incrementUsage: () => void;
  /** Anonymous user identifier (persistent across visits) */
  guestId: string;
  /** Past analysis sessions from backend */
  sessionHistory: SessionSummary[];
  /** Refresh history from backend */
  refreshHistory: () => Promise<void>;
  /** Whether history is currently loading */
  historyLoading: boolean;
}

const SessionContext = createContext<SessionState>({
  sessionId: null,
  setSession: () => {},
  clearSession: () => {},
  guestUsageCount: 0,
  incrementUsage: () => {},
  guestId: '',
  sessionHistory: [],
  refreshHistory: async () => {},
  historyLoading: false,
});

const STORAGE_KEY = 'hyperbert_session_id';
const USAGE_KEY = 'hyperbert_guest_usage_v2';
const GUEST_ID_KEY = 'hyperbert_guest_id';

function getOrCreateGuestId(): string {
  try {
    const existing = localStorage.getItem(GUEST_ID_KEY);
    if (existing) return existing;
    const id = crypto.randomUUID();
    localStorage.setItem(GUEST_ID_KEY, id);
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  const [guestUsageCount, setGuestUsageCount] = useState<number>(() => {
    try {
      return parseInt(localStorage.getItem(USAGE_KEY) || '0', 10);
    } catch {
      return 0;
    }
  });

  const [guestId] = useState<string>(() => getOrCreateGuestId());
  const [sessionHistory, setSessionHistory] = useState<SessionSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Sync to localStorage on change
  useEffect(() => {
    try {
      if (sessionId) {
        localStorage.setItem(STORAGE_KEY, sessionId);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {}
  }, [sessionId]);

  useEffect(() => {
    try {
      localStorage.setItem(USAGE_KEY, String(guestUsageCount));
    } catch {}
  }, [guestUsageCount]);

  const refreshHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const result = await getSessions(guestId);
      setSessionHistory(result.sessions);
    } catch (err) {
      console.error('Failed to fetch session history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [guestId]);

  // Fetch history on mount
  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const setSession = (id: string) => {
    setSessionId(id);
    // Refresh history after new session is created
    setTimeout(() => refreshHistory(), 500);
  };

  const clearSession = () => {
    setSessionId(null);
  };

  const incrementUsage = () => {
    setGuestUsageCount(prev => prev + 1);
  };

  return (
    <SessionContext.Provider value={{
      sessionId,
      setSession,
      clearSession,
      guestUsageCount,
      incrementUsage,
      guestId,
      sessionHistory,
      refreshHistory,
      historyLoading,
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
