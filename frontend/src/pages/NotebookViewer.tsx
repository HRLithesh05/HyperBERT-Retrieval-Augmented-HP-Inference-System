import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Square, Loader2, ExternalLink, AlertTriangle, BookOpen, RefreshCw } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';

export default function NotebookViewer() {
  const { id: urlId } = useParams<{ id: string }>();
  const { sessionId: ctxId } = useSession();
  const id = (urlId && urlId !== 'demo') ? urlId : ctxId;

  const [status, setStatus] = useState<'launching' | 'running' | 'error'>('launching');
  const [jupyterUrl, setJupyterUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const launchedRef = useRef(false);

  const launchNotebook = async () => {
    if (!id) {
      setError('No analysis session found. Upload a paper first.');
      setStatus('error');
      return;
    }
    setStatus('launching');
    setError(null);

    try {
      const res = await fetch(`/api/launch-notebook/${id}`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: 'Launch failed' }));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
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
  };

  // Auto-launch on mount — zero-click experience
  useEffect(() => {
    if (!launchedRef.current && id) {
      launchedRef.current = true;
      launchNotebook();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div style={{ height: 'calc(100vh - 64px)', background: 'var(--bg-base)', display: 'flex', flexDirection: 'column' }}>
      {/* Compact header bar — minimal height to maximize notebook space */}
      <div className="px-4 py-2 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border-glass)', background: 'var(--bg-surface-1)', height: 40, flexShrink: 0 }}>
        <div className="flex items-center gap-3">
          <Link to={`/results/${id || ''}`} className="interactive flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <ArrowLeft className="w-3.5 h-3.5" /> Results
          </Link>
          <div className="h-4 w-px" style={{ background: 'var(--border-glass)' }} />
          <BookOpen className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
          <span className="font-display font-bold text-xs" style={{ color: 'var(--text-heading)' }}>
            Training Notebook
          </span>
          <div className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{
            background: status === 'running' ? 'rgba(16,185,129,0.1)' : status === 'launching' ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)',
            color: status === 'running' ? 'var(--status-success)' : status === 'launching' ? 'var(--status-warning)' : 'var(--status-danger)',
          }}>
            {status === 'running' && '● Running'}
            {status === 'launching' && '◌ Starting…'}
            {status === 'error' && '✕ Error'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status === 'running' && jupyterUrl && (
            <a href={jupyterUrl} target="_blank" rel="noopener noreferrer"
              className="interactive flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium"
              style={{ color: 'var(--accent-secondary)', border: '1px solid var(--border-glass)' }}>
              <ExternalLink className="w-3 h-3" /> New Tab
            </a>
          )}
          {status === 'running' && (
            <button onClick={stopNotebook}
              className="interactive flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold"
              style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--status-danger)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <Square className="w-3 h-3" /> Stop
            </button>
          )}
        </div>
      </div>

      {/* Main content — fills all remaining space */}
      <div className="flex-1 relative" style={{ minHeight: 0 }}>
        {/* Launching state */}
        {status === 'launching' && (
          <div className="flex flex-col items-center justify-center gap-4 h-full">
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
              <Loader2 className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
            </motion.div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Starting JupyterLab…</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Auto-installing if needed. This may take 10-20 seconds on first launch.</p>
          </div>
        )}

        {/* Running — iframe fills all available space */}
        {status === 'running' && jupyterUrl && (
          <iframe
            src={jupyterUrl}
            title="JupyterLab"
            className="w-full h-full border-0"
            allow="clipboard-read; clipboard-write"
          />
        )}

        {/* Error */}
        {status === 'error' && (
          <div className="flex flex-col items-center justify-center gap-4 h-full">
            <AlertTriangle className="w-12 h-12" style={{ color: 'var(--status-warning)' }} />
            <p className="font-semibold" style={{ color: 'var(--text-heading)' }}>Could not launch JupyterLab</p>
            <p className="text-sm text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>{error}</p>
            <button onClick={launchNotebook}
              className="interactive inline-flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-semibold text-white mt-2"
              style={{ background: 'var(--accent-gradient)' }}>
              <RefreshCw className="w-4 h-4" /> Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
