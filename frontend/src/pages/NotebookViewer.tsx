import { useState, useEffect, useRef } from 'react';
import { useParams, Link, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Square, Loader2, ExternalLink, AlertTriangle, BookOpen, RefreshCw } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';

export default function NotebookViewer() {
  const { id } = useParams<{ id: string }>();
  const { sessionId: ctxSessionId, hasRealSession, paperTitle } = useSession();
  const [status, setStatus] = useState<'launching' | 'running' | 'error'>('launching');
  const [jupyterUrl, setJupyterUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const launchedRef = useRef(false);

  // Resolve effective session ID
  const effectiveId = (!id || id === 'demo') && hasRealSession ? ctxSessionId! : id;

  // Redirect to real session if needed
  if (effectiveId && effectiveId !== id) {
    return <Navigate to={`/notebook/${effectiveId}`} replace />;
  }

  const launchNotebook = async () => {
    if (!effectiveId || effectiveId === 'demo') {
      setError('No analysis session found. Upload a paper first.');
      setStatus('error');
      return;
    }
    setStatus('launching');
    setError(null);

    try {
      const res = await fetch(`/api/launch-notebook/${effectiveId}`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: 'Launch failed' }));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      // Backend returns the proxied URL directly (e.g. /jupyter/lab/tree/...)
      setJupyterUrl(data.url);
      setStatus('running');
    } catch (e: any) {
      setError(e.message);
      setStatus('error');
    }
  };

  const stopNotebook = async () => {
    try {
      await fetch(`/api/stop-notebook`, { method: 'POST' });
    } catch {}
    setStatus('launching');
    setJupyterUrl(null);
    launchedRef.current = false;
  };

  // Auto-launch on mount — zero-click experience
  useEffect(() => {
    if (!launchedRef.current && effectiveId && effectiveId !== 'demo') {
      launchedRef.current = true;
      launchNotebook();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveId]);

  const displayTitle = paperTitle || 'Training Notebook';

  return (
    <div style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)', display: 'flex', flexDirection: 'column' }}>
      {/* Compact mini-toolbar (40px) */}
      <div className="px-4 flex items-center justify-between" style={{
        height: 40,
        borderBottom: '1px solid var(--border-glass)',
        background: 'var(--bg-surface-1)',
        flexShrink: 0,
      }}>
        <div className="flex items-center gap-3 min-w-0">
          <Link to={`/results/${effectiveId}`} className="interactive flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <ArrowLeft className="w-3.5 h-3.5" /> Results
          </Link>
          <div className="h-4 w-px" style={{ background: 'var(--border-glass)' }} />
          <BookOpen className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
          <span className="text-xs font-medium truncate" style={{ color: 'var(--text-heading)', maxWidth: 300 }}>
            {displayTitle}
          </span>
          <div className={`px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0`} style={{
            background: status === 'running' ? 'rgba(16,185,129,0.15)' : status === 'launching' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
            color: status === 'running' ? 'var(--status-success)' : status === 'launching' ? 'var(--status-warning)' : 'var(--status-danger)',
          }}>
            {status === 'running' && '● Running'}
            {status === 'launching' && '◌ Starting…'}
            {status === 'error' && '✕ Error'}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {status === 'running' && jupyterUrl && (
            <a href={jupyterUrl} target="_blank" rel="noopener noreferrer"
              className="interactive flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium"
              style={{ color: 'var(--accent-secondary)', border: '1px solid var(--border-glass)' }}>
              <ExternalLink className="w-3 h-3" /> New Tab
            </a>
          )}
          {status === 'running' && (
            <button onClick={stopNotebook}
              className="interactive flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium"
              style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--status-danger)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <Square className="w-3 h-3" /> Stop
            </button>
          )}
        </div>
      </div>

      {/* Main content — takes all remaining space */}
      <div style={{ flex: 1, position: 'relative' }}>
        {/* Launching state */}
        {status === 'launching' && (
          <div className="flex flex-col items-center justify-center gap-4" style={{ height: '100%', minHeight: 'calc(100vh - 104px)' }}>
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
              <Loader2 className="w-8 h-8" style={{ color: 'var(--accent-primary)' }} />
            </motion.div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Starting JupyterLab…</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Auto-installing dependencies if needed. May take 10-20s on first launch.</p>
          </div>
        )}

        {/* Running — iframe takes full remaining height */}
        {status === 'running' && jupyterUrl && (
          <iframe
            src={jupyterUrl}
            title="JupyterLab"
            style={{ width: '100%', height: 'calc(100vh - 104px)', border: 'none' }}
            allow="clipboard-read; clipboard-write"
          />
        )}

        {/* Error */}
        {status === 'error' && (
          <div className="flex flex-col items-center justify-center gap-4" style={{ height: '100%', minHeight: 'calc(100vh - 104px)' }}>
            <AlertTriangle className="w-10 h-10" style={{ color: 'var(--status-warning)' }} />
            <p className="font-semibold text-sm" style={{ color: 'var(--text-heading)' }}>Could not launch JupyterLab</p>
            <p className="text-xs text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>{error}</p>
            <button onClick={launchNotebook}
              className="interactive inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white mt-2"
              style={{ background: 'var(--accent-gradient)' }}>
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
