import { useState, useEffect } from 'react';
import { useParams, Link, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2, XCircle, ArrowLeft, Zap, Brain, Database,
  Loader2, AlertTriangle, ChevronDown, BarChart2,
} from 'lucide-react';
import { getComparison } from '@/lib/api';
import { useSession } from '@/contexts/SessionContext';

/* ── Helper: confidence color ─────────────────────────────── */
function confColor(pct: number) {
  if (pct >= 70) return 'var(--status-success)';
  if (pct >= 30) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

function sourceLabel(src: string) {
  if (src === 'extracted_from_paper') return { text: 'From Paper', color: 'var(--accent-secondary)' };
  if (src === 'inferred_from_corpus') return { text: 'RAG Inferred', color: 'var(--accent-primary)' };
  return { text: 'BERT Default', color: 'var(--text-muted)' };
}

/* ── Main Page ──────────────────────────────────────────────── */
export default function ComparisonDashboard() {
  const { id } = useParams<{ id: string }>();
  const { sessionId: ctxSessionId, hasRealSession } = useSession();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedParam, setExpandedParam] = useState<string | null>(null);

  // Use real session from context if URL has 'demo'
  const effectiveId = (!id || id === 'demo') && hasRealSession ? ctxSessionId! : id;

  // Redirect to real session URL if needed
  if (effectiveId && effectiveId !== id) {
    return <Navigate to={`/compare/${effectiveId}`} replace />;
  }

  useEffect(() => {
    if (!effectiveId || effectiveId === 'demo') {
      setLoading(false);
      setError('No analysis session found — upload a paper first to see a live RAG vs LLM comparison.');
      return;
    }
    setLoading(true);
    getComparison(effectiveId)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [effectiveId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
          <Loader2 className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
        </motion.div>
        <p style={{ color: 'var(--text-secondary)' }}>Querying LLM and comparing against RAG inference…</p>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>This may take 5-15 seconds on first load</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <AlertTriangle className="w-12 h-12" style={{ color: 'var(--status-warning)' }} />
        <p className="text-lg font-semibold" style={{ color: 'var(--text-heading)' }}>Comparison Unavailable</p>
        <p className="text-sm max-w-md text-center" style={{ color: 'var(--text-secondary)' }}>{error}</p>
        <Link to="/upload" className="interactive px-5 py-2.5 rounded-xl text-sm font-semibold text-white" style={{ background: 'var(--accent-gradient)' }}>
          Upload a Paper
        </Link>
      </div>
    );
  }

  const comparison = data?.llm_comparison?.comparison;
  const llmResult = data?.llm_comparison?.llm_result;
  const paper = data?.paper || {};
  const summary = comparison?.summary || {};
  const perParam = comparison?.per_param || {};
  const params = Object.keys(perParam);

  const agreePct = summary.agreement_pct ?? 0;
  const agreed = summary.agreed ?? 0;
  const disagreed = summary.disagreed ?? 0;
  const total = summary.total_compared ?? 0;

  return (
    <div style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
      <div className="container mx-auto px-6 py-10" style={{ maxWidth: 1100 }}>
        {/* Back nav */}
        <Link
          to={`/results/${id}`}
          className="interactive inline-flex items-center gap-2 text-sm font-medium mb-6"
          style={{ color: 'var(--text-secondary)' }}
        >
          <ArrowLeft className="w-4 h-4" /> Back to Results
        </Link>

        {/* ── Header ── */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="font-display font-bold text-3xl mb-2" style={{ color: 'var(--text-heading)' }}>
            RAG vs LLM Comparison
          </h1>
          <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
            Transparent corpus-based inference vs black-box LLM suggestion — head to head.
          </p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Paper: <span style={{ color: 'var(--text-primary)' }}>{paper.title?.slice(0, 80) || 'Unknown'}</span>
            {' · '}Task: <span style={{ color: 'var(--accent-primary)' }}>{paper.task || '—'}</span>
          </p>
        </motion.div>

        {/* ── Summary cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">
          {/* Agreement gauge */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
            className="glass-panel p-6 flex flex-col items-center text-center"
          >
            <div className="relative w-24 h-24 mb-4">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border-glass)" strokeWidth="8" />
                <motion.circle
                  cx="50" cy="50" r="42" fill="none"
                  stroke={agreePct >= 70 ? 'var(--status-success)' : agreePct >= 40 ? 'var(--status-warning)' : 'var(--status-danger)'}
                  strokeWidth="8" strokeLinecap="round"
                  strokeDasharray={`${agreePct * 2.64} 264`}
                  initial={{ strokeDasharray: '0 264' }}
                  animate={{ strokeDasharray: `${agreePct * 2.64} 264` }}
                  transition={{ duration: 1.2, ease: 'easeOut' }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-display font-bold text-2xl" style={{ color: 'var(--text-heading)' }}>{agreePct}%</span>
              </div>
            </div>
            <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Agreement Rate</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {agreed} agree · {disagreed} disagree of {total} compared
            </p>
          </motion.div>

          {/* RAG info */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="glass-panel p-6 flex flex-col items-center text-center"
          >
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
              style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)' }}>
              <Database className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
            </div>
            <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>RAG System</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              FAISS retrieval + S1-S4 cascade + weighted aggregation
            </p>
            <div className="mt-2 px-3 py-1 rounded-full text-xs font-medium"
              style={{ background: 'rgba(139,92,246,0.1)', color: 'var(--accent-primary)' }}>
              ✓ Evidence-backed · Transparent
            </div>
          </motion.div>

          {/* LLM info */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="glass-panel p-6 flex flex-col items-center text-center"
          >
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
              style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.25)' }}>
              <Brain className="w-7 h-7" style={{ color: 'var(--status-warning)' }} />
            </div>
            <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>LLM Baseline</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {llmResult?.source || 'gemini-2.0-flash'} · {llmResult?.latency_ms || '—'}ms latency
            </p>
            <div className="mt-2 px-3 py-1 rounded-full text-xs font-medium"
              style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--status-warning)' }}>
              ✗ No citations · Black box
            </div>
          </motion.div>
        </div>

        {/* ── Comparison table ── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="glass-panel overflow-hidden mb-8"
        >
          {/* Table header */}
          <div className="grid gap-0" style={{ gridTemplateColumns: '1fr 140px 140px 90px 50px' }}>
            <div className="px-6 py-4 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-glass)' }}>
              Parameter
            </div>
            <div className="px-4 py-4 text-xs font-semibold uppercase tracking-wider text-center" style={{ color: 'var(--accent-primary)', borderBottom: '1px solid var(--border-glass)' }}>
              <span className="flex items-center justify-center gap-1"><Database className="w-3.5 h-3.5" /> RAG</span>
            </div>
            <div className="px-4 py-4 text-xs font-semibold uppercase tracking-wider text-center" style={{ color: 'var(--status-warning)', borderBottom: '1px solid var(--border-glass)' }}>
              <span className="flex items-center justify-center gap-1"><Brain className="w-3.5 h-3.5" /> LLM</span>
            </div>
            <div className="px-4 py-4 text-xs font-semibold uppercase tracking-wider text-center" style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-glass)' }}>
              Confidence
            </div>
            <div className="px-4 py-4 text-xs font-semibold uppercase tracking-wider text-center" style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-glass)' }}>
              Match
            </div>
          </div>

          {/* Table rows */}
          {params.map((param, i) => {
            const entry = perParam[param];
            const ragConf = entry.rag_confidence ?? 0;
            const src = sourceLabel(entry.rag_source);
            const isExpanded = expandedParam === param;

            return (
              <div key={param}>
                <motion.div
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 + i * 0.03 }}
                  className="grid gap-0 items-center cursor-pointer transition-colors"
                  style={{
                    gridTemplateColumns: '1fr 140px 140px 90px 50px',
                    borderBottom: '1px solid var(--border-glass)',
                    background: isExpanded ? 'var(--bg-surface-2)' : 'transparent',
                  }}
                  onClick={() => setExpandedParam(isExpanded ? null : param)}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-surface-2)')}
                  onMouseLeave={e => (e.currentTarget.style.background = isExpanded ? 'var(--bg-surface-2)' : 'transparent')}
                >
                  {/* Param name */}
                  <div className="px-6 py-4 flex items-center gap-3">
                    <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} style={{ color: 'var(--text-muted)' }} />
                    <div>
                      <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                        {param.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </p>
                      <p className="text-xs" style={{ color: src.color }}>{src.text}</p>
                    </div>
                  </div>

                  {/* RAG value */}
                  <div className="px-4 py-4 text-center">
                    <span className="font-mono text-sm font-semibold px-2.5 py-1 rounded-lg"
                      style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                      {entry.rag_value != null ? String(entry.rag_value) : '—'}
                    </span>
                  </div>

                  {/* LLM value */}
                  <div className="px-4 py-4 text-center">
                    <span className="font-mono text-sm font-semibold px-2.5 py-1 rounded-lg"
                      style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                      {entry.llm_value != null ? String(entry.llm_value) : '—'}
                    </span>
                  </div>

                  {/* Confidence */}
                  <div className="px-4 py-4 text-center">
                    <span className="text-xs font-mono font-semibold" style={{ color: confColor(ragConf) }}>
                      {ragConf.toFixed(0)}%
                    </span>
                  </div>

                  {/* Agreement */}
                  <div className="px-4 py-4 flex justify-center">
                    {entry.has_both ? (
                      entry.agrees
                        ? <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--status-success)' }} />
                        : <XCircle className="w-5 h-5" style={{ color: 'var(--status-danger)' }} />
                    ) : (
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </div>
                </motion.div>

                {/* Expanded detail */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                      style={{ borderBottom: '1px solid var(--border-glass)', background: 'var(--bg-surface-2)' }}
                    >
                      <div className="px-10 py-5 grid grid-cols-2 gap-8">
                        {/* RAG detail */}
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--accent-primary)' }}>
                            RAG Inference Detail
                          </p>
                          <div className="space-y-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
                            <p>• Source: <span style={{ color: 'var(--text-primary)' }}>{entry.rag_source?.replace(/_/g, ' ')}</span></p>
                            <p>• Confidence: <span style={{ color: confColor(ragConf) }}>{ragConf.toFixed(1)}%</span></p>
                            <p>• Value backed by corpus evidence with citations</p>
                            <p>• Method: weighted median/mode over similar papers</p>
                          </div>
                        </div>
                        {/* LLM detail */}
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--status-warning)' }}>
                            LLM Suggestion Detail
                          </p>
                          <div className="space-y-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
                            <p>• Source: <span style={{ color: 'var(--text-primary)' }}>{llmResult?.source || 'LLM'}</span></p>
                            <p>• No confidence score — LLMs don't provide calibrated uncertainty</p>
                            <p>• No citations — cannot trace back to source papers</p>
                            <p>• Based on training data memorization, not retrieval</p>
                          </div>
                        </div>
                      </div>
                      {/* Verdict */}
                      <div className="px-10 pb-5">
                        <div className="px-4 py-3 rounded-xl text-xs" style={{
                          background: entry.agrees ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                          border: `1px solid ${entry.agrees ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                          color: entry.agrees ? 'var(--status-success)' : 'var(--status-danger)',
                        }}>
                          {entry.agrees
                            ? `✓ Both systems agree on ${param.replace(/_/g, ' ')} = ${entry.rag_value}. This convergence from two independent methods increases confidence.`
                            : `✗ Systems disagree: RAG says ${entry.rag_value} (from corpus evidence), LLM says ${entry.llm_value} (from memorization). The RAG value is traceable and has citations.`
                          }
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </motion.div>

        {/* ── Methodology note ── */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
          className="glass-panel p-6"
        >
          <h3 className="font-display font-bold text-base mb-3" style={{ color: 'var(--text-heading)' }}>
            <BarChart2 className="w-4 h-4 inline-block mr-2" style={{ color: 'var(--accent-primary)' }} />
            Why This Comparison Matters
          </h3>
          <div className="grid sm:grid-cols-2 gap-6 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <div>
              <p className="font-semibold mb-1" style={{ color: 'var(--accent-primary)' }}>RAG (HyperBERT)</p>
              <ul className="space-y-1 text-xs">
                <li>✓ Every value has a citation from a real paper</li>
                <li>✓ Confidence is decomposed (similarity, agreement, support)</li>
                <li>✓ Reasoning is fully transparent and auditable</li>
                <li>✓ Domain constraints prevent invalid combinations</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold mb-1" style={{ color: 'var(--status-warning)' }}>LLM (Black Box)</p>
              <ul className="space-y-1 text-xs">
                <li>✗ No citations — "trust me" approach</li>
                <li>✗ No calibrated confidence — just outputs values</li>
                <li>✗ May hallucinate unusual configurations</li>
                <li>✗ Cannot explain why a value was chosen</li>
              </ul>
            </div>
          </div>
          <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
            When both systems agree, confidence is high. When they disagree, the RAG system's evidence-backed reasoning
            is more trustworthy because each value can be traced to specific papers in the corpus.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
