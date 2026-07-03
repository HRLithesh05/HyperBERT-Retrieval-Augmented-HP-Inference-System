/**
 * SessionContext — Persists the current analysis session ID across all pages.
 * Stored in React Context + localStorage so navigation between
 * Results / Compare / Notebook / Downloads never loses the active session.
 */
import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

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
}

const SessionContext = createContext<SessionState>({
  sessionId: null,
  setSession: () => {},
  clearSession: () => {},
  guestUsageCount: 0,
  incrementUsage: () => {},
});

const STORAGE_KEY = 'hyperbert_session_id';
const USAGE_KEY = 'hyperbert_guest_usage';

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

  const setSession = (id: string) => {
    setSessionId(id);
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
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
