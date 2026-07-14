import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Play, Square, Loader2, ExternalLink, AlertTriangle, BookOpen, Download } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import { downloadUrl } from '@/lib/api';

export default function NotebookViewer() {
  const { id: urlId } = useParams<{ id: string }>();
  const { sessionId: ctxId } = useSession();
  const id = (urlId && urlId !== 'demo') ? urlId : ctxId;

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
    <div style={{ height: 'calc(100vh - 64px)', background: 'var(--bg-base)', display: 'flex', flexDirection: 'column' }}>
      {/* Compact toolbar — always visible */}
      <div className="px-4 py-2 flex items-center justify-between" style={{
        borderBottom: '1px solid var(--border-glass)',
        background: 'var(--bg-surface-1)',
        flexShrink: 0,
      }}>
        <div className="flex items-center gap-3">
          <Link to={`/results/${id || 'demo'}`} className="interactive flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </Link>
          <div className="h-4 w-px" style={{ background: 'var(--border-glass)' }} />
          <BookOpen className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
          <span className="font-display font-bold text-sm" style={{ color: 'var(--text-heading)' }}>
            Training Notebook
          </span>
          <div className={`px-2 py-0.5 rounded-full text-[10px] font-medium`} style={{
            background: status === 'running' ? 'rgba(16,185,129,0.1)' : status === 'launching' ? 'rgba(245,158,11,0.1)' : 'rgba(100,116,139,0.1)',
            color: status === 'running' ? 'var(--status-success)' : status === 'launching' ? 'var(--status-warning)' : 'var(--text-muted)',
          }}>
            {status === 'running' && '● Running'}
            {status === 'launching' && '◌ Starting…'}
            {status === 'idle' && '○ Stopped'}
            {status === 'error' && '✕ Error'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {id && (
            <a href={downloadUrl.notebook(id)} download
              className="interactive flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium"
              style={{ color: 'var(--text-secondary)', border: '1px solid var(--border-glass)' }}>
              <Download className="w-3 h-3" /> Download .ipynb
            </a>
          )}
          {status === 'running' && jupyterUrl && (
            <a href={jupyterUrl} target="_blank" rel="noopener noreferrer"
              className="interactive flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium"
              style={{ color: 'var(--accent-secondary)', border: '1px solid var(--border-glass)' }}>
              <ExternalLink className="w-3 h-3" /> Open in Tab
            </a>
          )}
          {status !== 'running' && status !== 'launching' && (
            <button onClick={launchNotebook}
              className="interactive flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold text-white"
              style={{ background: 'var(--accent-gradient)' }}>
              <Play className="w-3 h-3" /> Launch Jupyter
            </button>
          )}
          {status === 'running' && (
            <button onClick={stopNotebook}
              className="interactive flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold"
              style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--status-danger)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <Square className="w-3 h-3" /> Stop
            </button>
          )}
        </div>
      </div>

      {/* Main content — takes ALL remaining space */}
      <div className="flex-1 relative overflow-hidden">
        {/* Idle state — compact */}
        {status === 'idle' && (
          <div className="flex flex-col items-center justify-center gap-5 h-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="text-center max-w-md"
            >
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
                style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
                <BookOpen className="w-8 h-8" style={{ color: 'var(--accent-primary)' }} />
              </div>
              <h2 className="font-display font-bold text-xl mb-2" style={{ color: 'var(--text-heading)' }}>
                Training Notebook Ready
              </h2>
              <p className="text-xs mb-4" style={{ color: 'var(--text-secondary)' }}>
                Your inferred hyperparameters, confidence annotations, and training code are packaged in a Jupyter notebook.
              </p>
              <button onClick={launchNotebook}
                className="interactive inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-white text-sm"
                style={{ background: 'var(--accent-gradient)', boxShadow: '0 4px 20px rgba(124,58,237,0.35)' }}>
                <Play className="w-4 h-4" /> Launch JupyterLab
              </button>
              <p className="text-[10px] mt-3" style={{ color: 'var(--text-muted)' }}>
                Requires <code className="font-mono px-1 py-0.5 rounded" style={{ background: 'var(--bg-surface-3)' }}>jupyterlab</code> installed · or download the .ipynb above
              </p>
            </motion.div>
          </div>
        )}

        {/* Launching */}
        {status === 'launching' && (
          <div className="flex flex-col items-center justify-center gap-3 h-full">
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
              <Loader2 className="w-8 h-8" style={{ color: 'var(--accent-primary)' }} />
            </motion.div>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Starting JupyterLab…</p>
          </div>
        )}

        {/* Running — full-height iframe */}
        {status === 'running' && jupyterUrl && (
          <iframe
            src={jupyterUrl}
            title="JupyterLab"
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          />
        )}

        {/* Error */}
        {status === 'error' && (
          <div className="flex flex-col items-center justify-center gap-3 h-full">
            <AlertTriangle className="w-10 h-10" style={{ color: 'var(--status-warning)' }} />
            <p className="font-semibold text-sm" style={{ color: 'var(--text-heading)' }}>Could not launch JupyterLab</p>
            <p className="text-xs text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>{error}</p>
            <div className="text-xs p-3 rounded-xl max-w-sm" style={{ background: 'var(--bg-surface-2)', color: 'var(--text-muted)' }}>
              <p className="font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Fix:</p>
              <ol className="list-decimal list-inside space-y-0.5">
                <li>Install: <code className="font-mono px-1 py-0.5 rounded" style={{ background: 'var(--bg-surface-3)' }}>pip install jupyterlab</code></li>
                <li>Ensure backend is running on port 5000</li>
              </ol>
            </div>
            <button onClick={launchNotebook}
              className="interactive px-4 py-2 rounded-xl text-xs font-semibold text-white mt-1"
              style={{ background: 'var(--accent-gradient)' }}>
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
