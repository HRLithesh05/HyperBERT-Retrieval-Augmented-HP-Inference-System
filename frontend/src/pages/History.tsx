import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { FileText, Clock, ArrowRight, Trash2 } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';

export default function History() {
  const navigate = useNavigate();
  const { history, sessionId: activeId } = useSession();

  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-6" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
          style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
          <Clock className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
        </div>
        <h2 className="font-display font-bold text-2xl" style={{ color: 'var(--text-heading)' }}>No Analysis History</h2>
        <p className="text-sm max-w-md text-center" style={{ color: 'var(--text-secondary)' }}>
          Upload your first BERT paper to start building your analysis history.
        </p>
        <button
          onClick={() => navigate('/upload')}
          className="interactive px-6 py-3 rounded-xl font-semibold text-white text-sm"
          style={{ background: 'var(--accent-gradient)' }}
        >
          Upload a Paper
        </button>
      </div>
    );
  }

  return (
    <div className="px-6 py-10 mx-auto" style={{ maxWidth: 800 }}>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display font-bold text-2xl" style={{ color: 'var(--text-heading)' }}>
            Analysis History
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            {history.length} paper{history.length !== 1 ? 's' : ''} analyzed
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="interactive px-4 py-2 rounded-xl text-sm font-semibold text-white"
          style={{ background: 'var(--accent-gradient)' }}
        >
          + New Analysis
        </button>
      </div>

      <div className="space-y-3">
        {history.map((session, idx) => (
          <motion.button
            key={session.sessionId}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            onClick={() => navigate(`/results/${session.sessionId}`)}
            className="interactive w-full flex items-center gap-4 p-5 rounded-2xl text-left transition-all"
            style={{
              background: session.sessionId === activeId ? 'rgba(139,92,246,0.06)' : 'var(--bg-surface-1)',
              border: session.sessionId === activeId
                ? '1px solid var(--accent-primary)'
                : '1px solid var(--border-glass)',
            }}
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.15)' }}>
              <FileText className="w-5 h-5" style={{ color: 'var(--accent-secondary)' }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                {session.paperTitle}
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {new Date(session.timestamp).toLocaleDateString('en-US', {
                  month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
                })}
                {session.sessionId === activeId && (
                  <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium"
                    style={{ background: 'rgba(139,92,246,0.15)', color: 'var(--accent-primary)' }}>
                    Active
                  </span>
                )}
              </p>
            </div>
            <ArrowRight className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
          </motion.button>
        ))}
      </div>
    </div>
  );
}
