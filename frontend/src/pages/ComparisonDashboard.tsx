import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2, XCircle, ArrowLeft, Zap, Brain, Database,
  Loader2, AlertTriangle, ChevronDown, BarChart2, Play,
  Wifi, WifiOff, Server, Clock, Shield, Eye, Sparkles,
  ArrowRight, RefreshCw, Info, TrendingUp, Minus,
} from 'lucide-react';
import { getComparison, getOllamaStatus, runLiveComparison } from '@/lib/api';
import { useSession } from '@/contexts/SessionContext';

/* ── Helpers ──────────────────────────────────────────────────────── */

function confColor(pct: number) {
  if (pct >= 70) return 'var(--status-success)';
  if (pct >= 30) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

function sourceLabel(src: string) {
  if (src === 'extracted_from_paper') return { text: 'From Paper', color: '#3b82f6', bg: 'rgba(59,130,246,0.1)' };
  if (src === 'inferred_from_corpus') return { text: 'RAG Inferred', color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)' };
  if (src === 'llm_extracted') return { text: 'LLM Extracted', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' };
  return { text: 'BERT Default', color: 'var(--text-muted)', bg: 'rgba(100,116,139,0.1)' };
}

function formatParamName(p: string) {
  return p.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatValue(v: any): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') {
    if (v < 0.01 && v > 0) return v.toExponential(1);
    if (Number.isInteger(v)) return v.toString();
    return v.toFixed(4).replace(/\.?0+$/, '');
  }
  return String(v);
}

/* ── Animated Number ─────────────────────────────────────────────── */
function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const duration = 1200;
    const startTime = performance.now();
    const step = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * value));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [value]);
  return <>{display}{suffix}</>;
}

/* ── Ollama Status Badge ─────────────────────────────────────────── */
function OllamaStatusBadge({ status }: { status: any }) {
  if (!status) return null;
  const running = status.running;
  const hasQwen = status.has_qwen;

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
        style={{
          background: running ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${running ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)'}`,
          color: running ? 'var(--status-success)' : 'var(--status-danger)',
        }}>
        {running ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
        Ollama {running ? 'Connected' : 'Offline'}
      </div>
      {running && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
          style={{
            background: hasQwen ? 'rgba(139,92,246,0.08)' : 'rgba(245,158,11,0.08)',
            border: `1px solid ${hasQwen ? 'rgba(139,92,246,0.25)' : 'rgba(245,158,11,0.25)'}`,
            color: hasQwen ? 'var(--accent-primary)' : 'var(--status-warning)',
          }}>
          <Server className="w-3 h-3" />
          {hasQwen ? 'Qwen3-4B Ready' : 'Qwen3 Not Found'}
        </div>
      )}
    </div>
  );
}

/* ── Confidence Ring SVG ─────────────────────────────────────────── */
function ConfidenceRing({ pct, size = 120, strokeWidth = 10, label }: {
  pct: number; size?: number; strokeWidth?: number; label?: string;
}) {
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const color = pct >= 70 ? 'var(--status-success)' : pct >= 40 ? 'var(--status-warning)' : 'var(--status-danger)';

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border-glass)" strokeWidth={strokeWidth} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * circumference} ${circumference}`}
          initial={{ strokeDasharray: `0 ${circumference}` }}
          animate={{ strokeDasharray: `${(pct / 100) * circumference} ${circumference}` }}
          transition={{ duration: 1.5, ease: 'easeOut', delay: 0.3 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display font-bold text-2xl" style={{ color: 'var(--text-heading)' }}>
          <AnimatedNumber value={Math.round(pct)} suffix="%" />
        </span>
        {label && <span className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{label}</span>}
      </div>
    </div>
  );
}

/* ── Confidence Bar ──────────────────────────────────────────────── */
function ConfidenceBar({ value, color, label }: { value: number; color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] w-16 text-right" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border-glass)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.5 }}
        />
      </div>
      <span className="text-[10px] font-mono w-8" style={{ color }}>{value}%</span>
    </div>
  );
}

/* ── Parameter Card ──────────────────────────────────────────────── */
function ParamCard({
  param, entry, index, isExpanded, onToggle,
}: {
  param: string; entry: any; index: number; isExpanded: boolean; onToggle: () => void;
}) {
  const src = sourceLabel(entry.rag_source);
  const ragConf = entry.rag_confidence ?? 0;
  const agrees = entry.agrees;
  const hasBoth = entry.has_both;
  const traces = entry.inference_trace || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.05, duration: 0.4 }}
      className="glass-panel overflow-hidden"
      style={{
        border: agrees ? '1px solid rgba(16,185,129,0.15)' : hasBoth ? '1px solid rgba(239,68,68,0.15)' : '1px solid var(--border-glass)',
      }}
    >
      {/* Card Header */}
      <div
        className="px-5 py-4 flex items-center gap-4 transition-colors interactive"
        style={{ cursor: 'pointer' }}
        onClick={onToggle}
        onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-surface-2)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        {/* Agreement indicator */}
        <div className="flex-shrink-0">
          {hasBoth ? (
            agrees ? (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 + index * 0.05, type: 'spring' }}
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}
              >
                <CheckCircle2 className="w-5 h-5" style={{ color: 'var(--status-success)' }} />
              </motion.div>
            ) : (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 + index * 0.05, type: 'spring' }}
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}
              >
                <XCircle className="w-5 h-5" style={{ color: 'var(--status-danger)' }} />
              </motion.div>
            )
          ) : (
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)' }}>
              <Minus className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            </div>
          )}
        </div>

        {/* Param info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-sm" style={{ color: 'var(--text-heading)' }}>
              {formatParamName(param)}
            </h3>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
              style={{ background: src.bg, color: src.color }}>
              {src.text}
            </span>
          </div>
          {/* Side-by-side values */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Database className="w-3 h-3" style={{ color: 'var(--accent-primary)' }} />
              <span className="font-mono text-sm font-semibold px-2 py-0.5 rounded-md"
                style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                {formatValue(entry.rag_value)}
              </span>
            </div>
            <ArrowRight className="w-3 h-3 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
            <div className="flex items-center gap-1.5">
              <Brain className="w-3 h-3" style={{ color: 'var(--status-warning)' }} />
              <span className="font-mono text-sm font-semibold px-2 py-0.5 rounded-md"
                style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                {formatValue(entry.llm_value)}
              </span>
            </div>
          </div>
        </div>

        {/* Confidence + expand */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="text-right">
            <span className="font-mono text-sm font-bold" style={{ color: confColor(ragConf) }}>
              {ragConf.toFixed?.(0) ?? ragConf}%
            </span>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>confidence</p>
          </div>
          <ChevronDown
            className={`w-4 h-4 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
            style={{ color: 'var(--text-muted)' }}
          />
        </div>
      </div>

      {/* Expanded Detail */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div style={{ borderTop: '1px solid var(--border-glass)', background: 'var(--bg-surface-2)' }}>
              <div className="px-5 py-5 grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* RAG Detail */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                      style={{ background: 'rgba(139,92,246,0.12)' }}>
                      <Database className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
                    </div>
                    <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--accent-primary)' }}>
                      RAG Inference
                    </p>
                  </div>

                  <div className="glass-card p-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Value</span>
                      <span className="font-mono text-sm font-bold" style={{ color: 'var(--accent-primary)' }}>
                        {formatValue(entry.rag_value)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Source</span>
                      <span className="text-xs font-medium" style={{ color: src.color }}>
                        {entry.rag_source?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Confidence</span>
                      <span className="text-xs font-bold" style={{ color: confColor(ragConf) }}>
                        {ragConf.toFixed?.(1) ?? ragConf}%
                      </span>
                    </div>
                  </div>

                  {/* Inference trace */}
                  {traces.length > 0 && (
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>
                        <Eye className="w-3 h-3 inline-block mr-1" />
                        Inference Trace
                      </p>
                      <div className="space-y-1">
                        {traces.map((t: string, i: number) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.1 * i }}
                            className="flex gap-2 text-[11px]"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            <span className="flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold"
                              style={{ background: 'rgba(139,92,246,0.1)', color: 'var(--accent-primary)' }}>
                              {i + 1}
                            </span>
                            <span className="font-mono leading-relaxed">{t}</span>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                      style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                      ✓ Evidence-backed
                    </span>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                      style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                      ✓ Traceable
                    </span>
                  </div>
                </div>

                {/* LLM Detail */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                      style={{ background: 'rgba(245,158,11,0.12)' }}>
                      <Brain className="w-3.5 h-3.5" style={{ color: 'var(--status-warning)' }} />
                    </div>
                    <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--status-warning)' }}>
                      LLM Suggestion
                    </p>
                  </div>

                  <div className="glass-card p-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Value</span>
                      <span className="font-mono text-sm font-bold" style={{ color: 'var(--status-warning)' }}>
                        {formatValue(entry.llm_value)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Source</span>
                      <span className="text-xs font-medium" style={{ color: 'var(--status-warning)' }}>
                        Ollama · Qwen3-4B
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Confidence</span>
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        N/A — no calibrated uncertainty
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1.5 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                    <p>• Based on training data memorization</p>
                    <p>• No citations or corpus evidence available</p>
                    <p>• Cannot explain reasoning for this value</p>
                    <p>• May produce hallucinated configurations</p>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                      style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                      ✗ No citations
                    </span>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                      style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                      ✗ Black box
                    </span>
                  </div>
                </div>
              </div>

              {/* Verdict */}
              <div className="px-5 pb-5">
                <div className="px-4 py-3 rounded-xl text-xs" style={{
                  background: agrees ? 'rgba(16,185,129,0.06)' : hasBoth ? 'rgba(239,68,68,0.06)' : 'rgba(100,116,139,0.06)',
                  border: `1px solid ${agrees ? 'rgba(16,185,129,0.15)' : hasBoth ? 'rgba(239,68,68,0.15)' : 'rgba(100,116,139,0.15)'}`,
                  color: agrees ? 'var(--status-success)' : hasBoth ? 'var(--status-danger)' : 'var(--text-muted)',
                }}>
                  {agrees
                    ? `✓ Both systems agree: ${formatParamName(param)} = ${formatValue(entry.rag_value)}. Convergence from two independent methods increases confidence in this value.`
                    : hasBoth
                      ? `✗ Disagreement: RAG says ${formatValue(entry.rag_value)} (from corpus evidence), LLM says ${formatValue(entry.llm_value)} (from memorization). The RAG value is traceable and has citations.`
                      : `— Only one system produced a value for this parameter.`
                  }
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Skeleton Loader ─────────────────────────────────────────────── */
function SkeletonCard() {
  return (
    <div className="glass-panel p-5 animate-shimmer">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl" style={{ background: 'var(--bg-surface-3)' }} />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-32 rounded-md" style={{ background: 'var(--bg-surface-3)' }} />
          <div className="h-3 w-48 rounded-md" style={{ background: 'var(--bg-surface-3)' }} />
        </div>
        <div className="w-12 h-8 rounded-md" style={{ background: 'var(--bg-surface-3)' }} />
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   MAIN PAGE
   ══════════════════════════════════════════════════════════════════ */

export default function ComparisonDashboard() {
  const { id: urlId } = useParams<{ id: string }>();
  const { sessionId: ctxId } = useSession();
  const id = (urlId && urlId !== 'demo') ? urlId : ctxId;

  // State
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<any>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveData, setLiveData] = useState<any>(null);
  const [expandedParam, setExpandedParam] = useState<string | null>(null);

  // Load initial session data and Ollama status
  useEffect(() => {
    if (!id || id === 'demo') {
      setLoading(false);
      setError('Demo mode — upload a paper to see a live RAG vs LLM comparison.');
      return;
    }

    const init = async () => {
      setLoading(true);
      try {
        const [compData, status] = await Promise.all([
          getComparison(id).catch(() => null),
          getOllamaStatus().catch(() => ({ running: false, models: [], has_qwen: false, error: 'Failed to check' })),
        ]);
        if (compData) setData(compData);
        setOllamaStatus(status);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [id]);

  // Run live comparison with Ollama
  const handleLiveComparison = useCallback(async () => {
    if (!id || liveLoading) return;
    setLiveLoading(true);
    setLiveData(null);
    try {
      const result = await runLiveComparison(id);
      setLiveData(result);
      setOllamaStatus(result.ollama_status);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLiveLoading(false);
    }
  }, [id, liveLoading]);

  // Determine which comparison data to display (prefer live)
  const activeData = liveData || data;
  const comparison = activeData?.llm_comparison?.comparison;
  const llmResult = activeData?.llm_comparison?.llm_result;
  const paper = activeData?.paper || {};
  const summary = comparison?.summary || {};
  const perParam = comparison?.per_param || {};
  const params = Object.keys(perParam);
  const isLive = !!liveData;

  const agreePct = summary.agreement_pct ?? 0;
  const agreed = summary.agreed ?? 0;
  const disagreed = summary.disagreed ?? 0;
  const total = summary.total_compared ?? 0;

  /* ── Loading state ────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
          className="w-16 h-16 rounded-2xl flex items-center justify-center"
          style={{ background: 'var(--accent-gradient)' }}
        >
          <Loader2 className="w-8 h-8 text-white" />
        </motion.div>
        <p className="font-semibold" style={{ color: 'var(--text-heading)' }}>Loading Comparison Data</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Fetching session data and checking Ollama status…
        </p>
      </div>
    );
  }

  /* ── Error / No Session ───────────────────────────────────── */
  if (error && !activeData) {
    return (
      <div className="flex flex-col items-center justify-center gap-5" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="w-20 h-20 rounded-2xl flex items-center justify-center"
          style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}
        >
          <AlertTriangle className="w-10 h-10" style={{ color: 'var(--status-warning)' }} />
        </motion.div>
        <div className="text-center">
          <p className="text-xl font-display font-bold mb-2" style={{ color: 'var(--text-heading)' }}>
            Comparison Unavailable
          </p>
          <p className="text-sm max-w-md" style={{ color: 'var(--text-secondary)' }}>{error}</p>
        </div>
        <Link to="/upload" className="interactive px-6 py-3 rounded-xl text-sm font-semibold text-white"
          style={{ background: 'var(--accent-gradient)' }}>
          Upload a Paper
        </Link>
      </div>
    );
  }

  /* ── Main Content ─────────────────────────────────────────── */
  return (
    <div style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
      <div className="container mx-auto px-6 py-8" style={{ maxWidth: 1200 }}>
        {/* Back nav */}
        <Link
          to={`/results/${id}`}
          className="interactive inline-flex items-center gap-2 text-sm font-medium mb-6"
          style={{ color: 'var(--text-secondary)' }}
        >
          <ArrowLeft className="w-4 h-4" /> Back to Results
        </Link>

        {/* ════════════════════════════════════════════════════════
           HERO HEADER
           ════════════════════════════════════════════════════════ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: 'var(--accent-gradient)' }}>
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <h1 className="font-display font-bold text-3xl" style={{ color: 'var(--text-heading)' }}>
                  RAG vs LLM <span className="text-gradient">Comparison</span>
                </h1>
              </div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Transparent corpus-based retrieval augmented inference vs local LLM suggestion — head to head.
              </p>
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Paper: <span style={{ color: 'var(--text-primary)' }}>{paper.title?.slice(0, 60) || 'Unknown'}
                    {paper.title?.length > 60 ? '…' : ''}</span>
                </span>
                {paper.task && (
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                    style={{ background: 'rgba(139,92,246,0.1)', color: 'var(--accent-primary)' }}>
                    {paper.task}
                  </span>
                )}
                {paper.model && (
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                    style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-secondary)' }}>
                    {paper.model}
                  </span>
                )}
              </div>
            </div>

            {/* Live Comparison Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleLiveComparison}
              disabled={liveLoading || !ollamaStatus?.running}
              className="interactive flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all flex-shrink-0"
              style={{
                background: ollamaStatus?.running
                  ? 'var(--accent-gradient)'
                  : 'var(--bg-surface-3)',
                opacity: liveLoading ? 0.7 : 1,
                color: ollamaStatus?.running ? 'white' : 'var(--text-muted)',
              }}
            >
              {liveLoading ? (
                <>
                  <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
                    <Loader2 className="w-4 h-4" />
                  </motion.div>
                  Querying Qwen3-4B…
                </>
              ) : (
                <>
                  {isLive ? <RefreshCw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  {isLive ? 'Re-run Comparison' : 'Run Live Comparison'}
                </>
              )}
            </motion.button>
          </div>

          {/* Status Bar */}
          <div className="flex items-center gap-4 flex-wrap">
            <OllamaStatusBadge status={ollamaStatus} />
            {isLive && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
                style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)', color: 'var(--status-success)' }}
              >
                <Zap className="w-3 h-3" />
                Live Results
              </motion.div>
            )}
            {llmResult?.latency_ms && (
              <span className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                <Clock className="w-3 h-3" />
                {llmResult.latency_ms}ms latency
              </span>
            )}
          </div>
        </motion.div>

        {/* ════════════════════════════════════════════════════════
           SUMMARY CARDS
           ════════════════════════════════════════════════════════ */}
        {params.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
            {/* Agreement Gauge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-panel p-6 flex flex-col items-center text-center"
            >
              <ConfidenceRing pct={agreePct} label="Agreement" />
              <p className="font-semibold text-sm mt-3" style={{ color: 'var(--text-primary)' }}>
                Agreement Rate
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                <span style={{ color: 'var(--status-success)' }}>{agreed} agree</span>
                {' · '}
                <span style={{ color: 'var(--status-danger)' }}>{disagreed} disagree</span>
                {' · '}{total} compared
              </p>
            </motion.div>

            {/* RAG System Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="glass-panel p-6 flex flex-col items-center text-center"
            >
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)' }}>
                <Database className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
              </div>
              <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>RAG System</p>
              <p className="text-[11px] mb-3" style={{ color: 'var(--text-muted)' }}>
                FAISS retrieval + S1-S4 cascade + weighted aggregation
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                  style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                  ✓ Evidence-backed
                </span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                  style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                  ✓ Transparent
                </span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                  style={{ background: 'rgba(139,92,246,0.08)', color: 'var(--accent-primary)' }}>
                  ✓ Citations
                </span>
              </div>
            </motion.div>

            {/* LLM System Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-panel p-6 flex flex-col items-center text-center"
            >
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3"
                style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.25)' }}>
                <Brain className="w-7 h-7" style={{ color: 'var(--status-warning)' }} />
              </div>
              <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>
                LLM Baseline
              </p>
              <p className="text-[11px] mb-3" style={{ color: 'var(--text-muted)' }}>
                {llmResult?.source || 'ollama-qwen3:4b'}
                {llmResult?.latency_ms ? ` · ${llmResult.latency_ms}ms` : ''}
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                  style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                  ✗ No citations
                </span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                  style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                  ✗ Black box
                </span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium"
                  style={{ background: 'rgba(245,158,11,0.08)', color: 'var(--status-warning)' }}>
                  Local LLM
                </span>
              </div>
            </motion.div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
           LOADING STATE (Live comparison in progress)
           ════════════════════════════════════════════════════════ */}
        {liveLoading && (
          <div className="space-y-3 mb-8">
            <div className="flex items-center gap-3 mb-4">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
              >
                <Loader2 className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
              </motion.div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-heading)' }}>
                Querying Qwen3-4B via Ollama…
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                This usually takes 5-15 seconds
              </p>
            </div>
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <SkeletonCard />
              </motion.div>
            ))}
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
           NO DATA YET — Prompt to run comparison
           ════════════════════════════════════════════════════════ */}
        {params.length === 0 && !liveLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel p-10 text-center mb-8"
          >
            <div className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-5"
              style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)' }}>
              <Sparkles className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
            </div>
            <h2 className="font-display font-bold text-xl mb-3" style={{ color: 'var(--text-heading)' }}>
              Ready to Compare
            </h2>
            <p className="text-sm mb-6 max-w-md mx-auto" style={{ color: 'var(--text-secondary)' }}>
              Click <strong>"Run Live Comparison"</strong> to query Qwen3-4B via Ollama and compare its suggestions against the RAG-inferred hyperparameters.
            </p>
            {!ollamaStatus?.running && (
              <div className="px-4 py-3 rounded-xl text-xs mb-5 mx-auto" style={{
                maxWidth: 400,
                background: 'rgba(245,158,11,0.06)',
                border: '1px solid rgba(245,158,11,0.15)',
                color: 'var(--status-warning)',
              }}>
                <p className="font-semibold mb-1">⚠ Ollama is not running</p>
                <p>Start Ollama and ensure Qwen3-4B is pulled:</p>
                <code className="block mt-1 font-mono text-[11px]" style={{ color: 'var(--text-primary)' }}>
                  ollama pull qwen3:4b
                </code>
              </div>
            )}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleLiveComparison}
              disabled={!ollamaStatus?.running || liveLoading}
              className="interactive px-8 py-3.5 rounded-xl text-sm font-bold text-white"
              style={{
                background: ollamaStatus?.running ? 'var(--accent-gradient)' : 'var(--bg-surface-3)',
                color: ollamaStatus?.running ? 'white' : 'var(--text-muted)',
              }}
            >
              <Play className="w-4 h-4 inline-block mr-2" />
              Run Live Comparison
            </motion.button>
          </motion.div>
        )}

        {/* ════════════════════════════════════════════════════════
           PARAMETER CARDS
           ════════════════════════════════════════════════════════ */}
        {params.length > 0 && !liveLoading && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <BarChart2 className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                <h2 className="font-display font-bold text-lg" style={{ color: 'var(--text-heading)' }}>
                  Parameter-by-Parameter Comparison
                </h2>
              </div>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {params.length} parameters · Click to expand
              </span>
            </div>
            <div className="space-y-3">
              {params.map((param, i) => (
                <ParamCard
                  key={param}
                  param={param}
                  entry={perParam[param]}
                  index={i}
                  isExpanded={expandedParam === param}
                  onToggle={() => setExpandedParam(expandedParam === param ? null : param)}
                />
              ))}
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
           METHODOLOGY FOOTER
           ════════════════════════════════════════════════════════ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-panel p-6 mb-8"
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: 'var(--accent-gradient)' }}>
              <Shield className="w-4 h-4 text-white" />
            </div>
            <h3 className="font-display font-bold text-base" style={{ color: 'var(--text-heading)' }}>
              Why This Comparison Matters
            </h3>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 mb-3">
                <Database className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                <p className="font-semibold text-sm" style={{ color: 'var(--accent-primary)' }}>RAG (HyperBERT)</p>
              </div>
              <ul className="space-y-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-success)' }} />
                  Every value has a citation from a real paper
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-success)' }} />
                  Confidence is decomposed (similarity, agreement, support)
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-success)' }} />
                  Reasoning is fully transparent and auditable
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-success)' }} />
                  Domain constraints prevent invalid combinations
                </li>
              </ul>
            </div>
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4" style={{ color: 'var(--status-warning)' }} />
                <p className="font-semibold text-sm" style={{ color: 'var(--status-warning)' }}>LLM (Qwen3-4B)</p>
              </div>
              <ul className="space-y-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <li className="flex items-start gap-2">
                  <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-danger)' }} />
                  No citations — "trust me" approach
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-danger)' }} />
                  No calibrated confidence — just outputs values
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-danger)' }} />
                  May hallucinate unusual configurations
                </li>
                <li className="flex items-start gap-2">
                  <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: 'var(--status-danger)' }} />
                  Cannot explain why a value was chosen
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-4 px-4 py-3 rounded-xl text-xs" style={{
            background: 'rgba(139,92,246,0.04)',
            border: '1px solid rgba(139,92,246,0.1)',
            color: 'var(--text-secondary)',
          }}>
            <Info className="w-3.5 h-3.5 inline-block mr-1.5" style={{ color: 'var(--accent-primary)' }} />
            When both systems agree, confidence is high. When they disagree, the RAG system's evidence-backed reasoning
            is more trustworthy because each value can be traced to specific papers in the corpus.
          </div>
        </motion.div>
      </div>
    </div>
  );
}
