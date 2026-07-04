import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Play, Square, Loader2, ExternalLink, AlertTriangle, BookOpen } from 'lucide-react';

export default function NotebookViewer() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<'idle' | 'launching' | 'running' | 'error'>('idle');
  const [jupyterUrl, setJupyterUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const launchNotebook = async () => {
    if (!id) return;
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
    setStatus('idle');
    setJupyterUrl(null);
  };

  return (
    <div style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)', display: 'flex', flexDirection: 'column' }}>
      {/* Header bar */}
      <div className="px-6 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border-glass)', background: 'var(--bg-surface-1)' }}>
        <div className="flex items-center gap-4">
          <Link to={`/results/${id}`} className="interactive flex items-center gap-1.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <ArrowLeft className="w-4 h-4" /> Results
          </Link>
          <div className="h-5 w-px" style={{ background: 'var(--border-glass)' }} />
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
            <span className="font-display font-bold text-sm" style={{ color: 'var(--text-heading)' }}>
              Training Notebook
            </span>
          </div>
          <div className={`px-2.5 py-1 rounded-full text-xs font-medium ${
            status === 'running' ? '' : status === 'launching' ? '' : ''
          }`} style={{
            background: status === 'running' ? 'rgba(16,185,129,0.1)' : status === 'launching' ? 'rgba(245,158,11,0.1)' : 'rgba(100,116,139,0.1)',
            color: status === 'running' ? 'var(--status-success)' : status === 'launching' ? 'var(--status-warning)' : 'var(--text-muted)',
          }}>
            {status === 'running' && '● Running'}
            {status === 'launching' && '◌ Launching…'}
            {status === 'idle' && '○ Stopped'}
            {status === 'error' && '✕ Error'}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {status === 'running' && jupyterUrl && (
            <a href={jupyterUrl} target="_blank" rel="noopener noreferrer"
              className="interactive flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
              style={{ color: 'var(--accent-secondary)', border: '1px solid var(--border-glass)' }}>
              <ExternalLink className="w-3.5 h-3.5" /> Open in New Tab
            </a>
          )}
          {status !== 'running' && status !== 'launching' && (
            <button onClick={launchNotebook}
              className="interactive flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white"
              style={{ background: 'var(--accent-gradient)' }}>
              <Play className="w-3.5 h-3.5" /> Launch Jupyter
            </button>
          )}
          {status === 'running' && (
            <button onClick={stopNotebook}
              className="interactive flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold"
              style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--status-danger)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <Square className="w-3.5 h-3.5" /> Stop Server
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 relative">
        {/* Idle state */}
        {status === 'idle' && (
          <div className="flex flex-col items-center justify-center gap-6 h-full" style={{ minHeight: 'calc(100vh - 130px)' }}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="text-center max-w-lg"
            >
              <div className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-6"
                style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
                <BookOpen className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
              </div>
              <h2 className="font-display font-bold text-2xl mb-3" style={{ color: 'var(--text-heading)' }}>
                Run Your Generated Notebook
              </h2>
              <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
                HyperBERT generated a Jupyter notebook with your inferred hyperparameters, confidence annotations, and ready-to-run training code. Launch JupyterLab to execute it right here.
              </p>
              <button onClick={launchNotebook}
                className="interactive inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm"
                style={{ background: 'var(--accent-gradient)', boxShadow: '0 4px 20px rgba(124,58,237,0.35)' }}>
                <Play className="w-4 h-4" /> Launch JupyterLab
              </button>
              <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
                Requires <code className="font-mono px-1 py-0.5 rounded" style={{ background: 'var(--bg-surface-3)' }}>jupyterlab</code> installed in your Python environment.
              </p>
            </motion.div>
          </div>
        )}

        {/* Launching state */}
        {status === 'launching' && (
          <div className="flex flex-col items-center justify-center gap-4 h-full" style={{ minHeight: 'calc(100vh - 130px)' }}>
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
              <Loader2 className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
            </motion.div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Starting JupyterLab server…</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>This usually takes 3-5 seconds</p>
          </div>
        )}

        {/* Running — iframe */}
        {status === 'running' && jupyterUrl && (
          <iframe
            src={jupyterUrl}
            title="JupyterLab"
            className="w-full border-0"
            style={{ height: 'calc(100vh - 130px)' }}
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          />
        )}

        {/* Error */}
        {status === 'error' && (
          <div className="flex flex-col items-center justify-center gap-4 h-full" style={{ minHeight: 'calc(100vh - 130px)' }}>
            <AlertTriangle className="w-12 h-12" style={{ color: 'var(--status-warning)' }} />
            <p className="font-semibold" style={{ color: 'var(--text-heading)' }}>Could not launch JupyterLab</p>
            <p className="text-sm text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>{error}</p>
            <div className="text-xs p-4 rounded-xl max-w-lg" style={{ background: 'var(--bg-surface-2)', color: 'var(--text-muted)' }}>
              <p className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>To fix this:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Install JupyterLab: <code className="font-mono px-1 py-0.5 rounded" style={{ background: 'var(--bg-surface-3)' }}>pip install jupyterlab</code></li>
                <li>Make sure the backend server is running on port 5000</li>
                <li>Try clicking Launch again</li>
              </ol>
            </div>
            <button onClick={launchNotebook}
              className="interactive px-5 py-2 rounded-xl text-sm font-semibold text-white mt-2"
              style={{ background: 'var(--accent-gradient)' }}>
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
