import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, CheckCircle2, Circle, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { analyzePDFStream, analyzePDF } from '@/lib/api';
import { useSession } from '@/contexts/SessionContext';
import { useAuth } from '@/contexts/AuthContext';
import { SignInModal } from '@/components/AuthGate';

const modules = [
  { id: 1, name: 'PDF Analyzer', summary: '14,200 chars, 3 tables extracted', detail: 'Parsing text, tables & raw hyperparameters' },
  { id: 2, name: 'Completeness Check', summary: 'R-Score: 0.129 — 11 HPs missing', detail: 'Computing R-Score and identifying missing parameters' },
  { id: 3, name: 'Evidence Retrieval', summary: 'S2 matched 6 NER+BERT papers', detail: 'Searching 435 papers in FAISS index (384-dim vectors)' },
  { id: 4, name: 'Domain Constraints', summary: 'weight_decay adjusted (Adam→0)', detail: 'Applying BERT domain rules (AdamW/WD coupling)' },
  { id: 5, name: 'Contradiction Check', summary: 'No contradictions detected', detail: 'IQR outlier detection across evidence values' },
  { id: 6, name: 'Self-Critique Validator', summary: 'All bounds valid — PASS', detail: 'Final domain bounds validation for all 12 parameters' },
  { id: 7, name: 'Notebook Generator', summary: 'training_notebook.ipynb created', detail: 'Generating annotated Jupyter notebook with citations' },
];

export default function UploadProcess() {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(-1);
  const [moduleSummaries, setModuleSummaries] = useState<string[]>(Array(7).fill(''));
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const navigate = useNavigate();
  const { sessionId: ctxSessionId, setSession, incrementUsage } = useSession();
  const { canAnalyze, remainingFree, isGuest, isAuthenticated } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [modelReady, setModelReady] = useState(true); // assume ready

  // Poll backend for model readiness
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (!cancelled) setModelReady(data.retriever_ready);
        if (!data.retriever_ready && !cancelled) {
          setTimeout(check, 3000); // Re-check every 3s
        }
      } catch { /* backend not up yet */ }
    };
    check();
    return () => { cancelled = true; };
  }, []);

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted.length) return;
    // Check guest limit before proceeding
    if (!canAnalyze) {
      setShowAuthModal(true);
      return;
    }
    const pdf = accepted[0];
    setFile(pdf);
    setProgress(0);
    setError(null);

    try {
      // Use SSE streaming for real-time progress synced with backend terminal
      const result = await analyzePDFStream(pdf, (module, step, message) => {
        const idx = step <= 7 ? step - 1 : 6;
        setProgress(step <= 7 ? step : 7);
        setModuleSummaries(prev => {
          const next = [...prev];
          if (idx >= 0 && idx < 7) {
            next[idx] = message.slice(0, 50);
          }
          return next;
        });
      });

      setSessionId(result.session_id);
      setSession(result.session_id);
      incrementUsage();
      setProgress(modules.length);
    } catch (e: any) {
      console.error("SSE stream error, falling back:", e);
      // Fallback to non-streaming API
      try {
        const result = await analyzePDF(pdf);
        setSessionId(result.session_id);
        setSession(result.session_id);
        incrementUsage();

        // Replay the audit_log to animate modules one-by-one
        const byModule: Record<string, string> = {};
        for (const log of result.audit_log) {
          byModule[log.module] = log.message;
        }
        for (let i = 0; i < modules.length; i++) {
          await new Promise(r => setTimeout(r, 600 + Math.random() * 200));
          setProgress(i + 1);
          const mKey = `M${i + 1}`;
          if (byModule[mKey]) {
            setModuleSummaries(prev => {
              const next = [...prev];
              next[i] = byModule[mKey].slice(0, 45);
              return next;
            });
          }
        }
      } catch (e2: any) {
        setError(e2.message || "Pipeline failed. Make sure the backend is running on port 5000.");
        // Still animate for demo mode if backend is offline
        let i = 0;
        const tick = async () => {
          i++;
          setProgress(i);
          setModuleSummaries(prev => { const n = [...prev]; n[i-1] = modules[i-1]?.summary || ''; return n; });
          if (i < modules.length) setTimeout(tick, 1000 + Math.random() * 300);
          else setSessionId('demo');
        };
        setTimeout(tick, 800);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled: file !== null,
  });

  const done = progress >= modules.length && sessionId !== null;

  // Auto-navigate to results after pipeline completes
  useEffect(() => {
    if (done && sessionId && sessionId !== 'demo') {
      const timer = setTimeout(() => navigate(`/results/${sessionId}`), 1500);
      return () => clearTimeout(timer);
    }
  }, [done, sessionId, navigate]);

  return (
    <div
      className="relative flex flex-col items-center justify-center px-4 py-16"
      style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}
    >
      <AnimatePresence mode="wait">
        {!file ? (
          /* ─── DROP ZONE ─── */
          <motion.div
            key="drop"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92, filter: 'blur(8px)' }}
            style={{ width: '100%', maxWidth: 680 }}
          >
            <h1 className="font-display font-bold text-3xl text-center mb-2"
              style={{ color: 'var(--text-heading)' }}>
              Analyze a Paper
            </h1>
            <p className="text-center mb-4" style={{ color: 'var(--text-secondary)' }}>
              Upload your BERT fine-tuning paper and we'll infer all missing hyperparameters.
            </p>

            {/* Model loading status */}
            <div className="flex items-center justify-center gap-2 mb-4">
              <div className={`w-2 h-2 rounded-full ${!modelReady ? 'animate-pulse' : ''}`}
                style={{ background: modelReady ? 'var(--status-success)' : 'var(--status-warning)' }} />
              <span className="text-xs" style={{ color: modelReady ? 'var(--status-success)' : 'var(--status-warning)' }}>
                {modelReady ? 'AI model ready' : 'AI model loading — analysis will be slower'}
              </span>
            </div>

            {/* Resume previous session */}
            {ctxSessionId && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                className="w-full mb-6 px-5 py-4 rounded-2xl flex items-center justify-between"
                style={{
                  background: 'rgba(16,185,129,0.06)',
                  border: '1px solid rgba(16,185,129,0.2)',
                }}
              >
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    Previous analysis available
                  </p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    Session: {ctxSessionId.slice(0, 8)}… — Click to view results
                  </p>
                </div>
                <button
                  onClick={() => navigate(`/results/${ctxSessionId}`)}
                  className="interactive flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white"
                  style={{ background: 'var(--accent-gradient)' }}
                >
                  <ArrowRight className="w-3.5 h-3.5" /> Resume
                </button>
              </motion.div>
            )}

            <div
              {...getRootProps()}
              className="interactive relative flex flex-col items-center justify-center gap-4 p-16 rounded-3xl transition-all duration-300"
              style={{
                border: `2px dashed ${isDragActive ? 'var(--accent-primary)' : 'var(--border-highlight)'}`,
                background: isDragActive ? 'rgba(139,92,246,0.06)' : 'var(--bg-surface-1)',
                boxShadow: isDragActive ? '0 0 40px rgba(139,92,246,0.2), inset 0 0 40px rgba(139,92,246,0.05)' : 'none',
                cursor: 'pointer',
              }}
            >
              <input {...getInputProps()} />
              <motion.div animate={{ y: isDragActive ? -8 : 0 }} transition={{ type: 'spring', stiffness: 300 }}>
                <UploadCloud
                  className="w-16 h-16 transition-colors duration-300"
                  style={{ color: isDragActive ? 'var(--accent-primary)' : 'var(--text-muted)' }}
                />
              </motion.div>
              <div className="text-center">
                <p className="text-xl font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                  {isDragActive ? 'Release to analyze' : 'Drop your BERT paper PDF here'}
                </p>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  or click to browse — .pdf only, up to 50MB
                </p>
              </div>
            </div>
          </motion.div>
        ) : (
          /* ─── PROCESSING ─── */
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full relative overflow-hidden rounded-2xl"
            style={{
              maxWidth: 680,
              background: 'var(--bg-surface-1)',
              border: '1px solid var(--border-glass)',
              backdropFilter: 'blur(20px)',
            }}
          >
            {/* Laser scan line */}
            {!done && (
              <div
                className="absolute left-0 w-full h-0.5 pointer-events-none z-10 animate-laser"
                style={{ background: 'linear-gradient(90deg, transparent, var(--accent-primary), transparent)' }}
              />
            )}

            {/* File info header */}
            <div className="px-8 pt-8 pb-6" style={{ borderBottom: '1px solid var(--border-glass)' }}>
              <div className="flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)' }}
                >
                  <FileText className="w-6 h-6" style={{ color: 'var(--accent-secondary)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate" style={{ color: 'var(--text-primary)' }}>{file.name}</p>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB · {done ? 'Analysis complete' : 'Processing…'}
                  </p>
                </div>
              </div>
            </div>

            {/* Module list */}
            <div className="px-8 py-6 space-y-5">
              {modules.map((mod, idx) => {
                const isComplete = progress > idx;
                const isActive = progress === idx;

                return (
                  <motion.div
                    key={mod.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: (progress < idx) ? 0.35 : 1, x: 0 }}
                    transition={{ delay: idx * 0.07 }}
                    className="flex items-start gap-4"
                  >
                    {/* Status icon */}
                    <div className="mt-0.5 w-6 flex-shrink-0">
                      {isComplete ? (
                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 400 }}>
                          <CheckCircle2 className="w-6 h-6" style={{ color: 'var(--status-success)' }} />
                        </motion.div>
                      ) : isActive ? (
                        <div
                          className="w-6 h-6 rounded-full border-2 animate-spin"
                          style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }}
                        />
                      ) : (
                        <Circle className="w-6 h-6" style={{ color: 'var(--border-highlight)' }} />
                      )}
                    </div>

                    {/* Module info */}
                    <div className="flex-1">
                      <p
                        className="font-medium text-sm"
                        style={{ color: isActive ? 'var(--accent-primary)' : 'var(--text-primary)' }}
                      >
                        M{mod.id}: {mod.name}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {mod.detail}
                      </p>
                    </div>

                    {/* Result summary (slides in) */}
                    <AnimatePresence>
                      {isComplete && (
                        <motion.span
                          initial={{ opacity: 0, x: 12 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="text-xs font-medium text-right flex-shrink-0 max-w-[140px]"
                          style={{ color: 'var(--status-success)' }}
                        >
                          {moduleSummaries[idx] || mod.summary}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>

            {/* Error banner */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="mx-8 mb-4 px-4 py-3 rounded-xl text-sm"
                  style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)', color: 'var(--status-danger)' }}
                >
                  ⚠ {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Done CTA */}
            <AnimatePresence>
              {done && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="px-8 pb-8"
                >
                  <div className="pt-6" style={{ borderTop: '1px solid var(--border-glass)' }}>
                    <button
                      onClick={() => navigate(`/results/${sessionId || 'demo'}`)}
                      className="interactive w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white transition-all"
                      style={{
                        background: 'var(--accent-gradient)',
                        boxShadow: '0 4px 20px rgba(124,58,237,0.35)',
                      }}
                    >
                      View Results <ArrowRight className="w-5 h-5" />
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Guest usage counter */}
      {isGuest && !file && (
        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          className="text-xs mt-6" style={{ color: 'var(--text-muted)' }}
        >
          {remainingFree > 0
            ? `${remainingFree} free analysis${remainingFree === 1 ? '' : 'es'} remaining`
            : 'Free limit reached — sign in for unlimited access'}
        </motion.p>
      )}

      {/* Auth modal */}
      <SignInModal open={showAuthModal} onClose={() => setShowAuthModal(false)} />
    </div>
  );
}
