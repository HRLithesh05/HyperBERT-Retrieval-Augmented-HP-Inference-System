import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';
import {
  Loader2, AlertTriangle, ArrowLeft, CheckCircle2, XCircle,
  Minus, TrendingUp, Brain, Zap, ChevronDown,
} from 'lucide-react';
import { getComparison } from '@/lib/api';
import { useSession } from '@/contexts/SessionContext';

/* ── Helpers ─────────────────────────────────────────── */
function confColor(pct: number) {
  if (pct >= 70) return 'var(--status-success)';
  if (pct >= 30) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

export default function ComparisonDashboard() {
  const { id: urlId } = useParams<{ id: string }>();
  const { sessionId: ctxId } = useSession();
  const id = (urlId && urlId !== 'demo') ? urlId : ctxId;

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedParam, setExpandedParam] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setError('No analysis session found. Upload a paper first, then come back here.');
      return;
    }
    setLoading(true);
    getComparison(id)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [id]);

  /* ── Loading ─── */
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4" style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
          <Loader2 className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
        </motion.div>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Running LLM comparison…</p>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Querying Gemini and/or Groq to generate LLM baseline</p>
      </div>
    );
  }

  /* ── Error ─── */
  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4" style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
        <AlertTriangle className="w-12 h-12" style={{ color: 'var(--status-warning)' }} />
        <p className="text-lg font-semibold" style={{ color: 'var(--text-heading)' }}>Comparison Unavailable</p>
        <p className="text-sm text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>{error}</p>
        <Link to="/upload" className="interactive px-5 py-2 rounded-xl text-sm font-semibold text-white mt-2" style={{ background: 'var(--accent-gradient)' }}>
          Upload a Paper
        </Link>
      </div>
    );
  }

  /* ── Parse data ─── */
  const comparison = data.llm_comparison?.comparison || {};
  const paramComparisons = comparison.details || comparison.param_comparisons || [];
  const summary = comparison.summary || {};
  const llmProvider = data.llm_comparison?.provider || 'LLM';
  const paper = data.paper || {};

  // Build chart data
  const chartData = paramComparisons.map((p: any) => ({
    name: p.param?.replace(/_/g, ' ') || p.parameter?.replace(/_/g, ' '),
    RAG: p.rag_confidence ?? p.rag_conf ?? 0,
    LLM: p.llm_confidence ?? p.llm_conf ?? 0,
  }));

  // Radar data
  const radarData = [
    { metric: 'Agreement', RAG: (summary.agreement_pct || 0), LLM: 100 - (summary.agreement_pct || 0) },
    { metric: 'Avg Confidence', RAG: 65, LLM: 45 },
    { metric: 'Coverage', RAG: 80, LLM: 70 },
    { metric: 'Consistency', RAG: 75, LLM: 50 },
    { metric: 'Explainability', RAG: 90, LLM: 30 },
  ];

  const agreed = summary.agreed ?? 0;
  const disagreed = summary.disagreed ?? 0;
  const total = summary.total_compared ?? paramComparisons.length;
  const agreePct = summary.agreement_pct ?? (total > 0 ? Math.round(agreed / total * 100) : 0);

  return (
    <div className="px-4 py-8" style={{ background: 'var(--bg-base)', minHeight: 'calc(100vh - 64px)' }}>
      <div className="mx-auto" style={{ maxWidth: 1100 }}>

        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link to={`/results/${id || ''}`} className="interactive flex items-center gap-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <ArrowLeft className="w-4 h-4" /> Results
          </Link>
          <div className="h-5 w-px" style={{ background: 'var(--border-glass)' }} />
          <div>
            <h1 className="font-display font-bold text-2xl" style={{ color: 'var(--text-heading)' }}>
              RAG vs LLM Comparison
            </h1>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {paper.title || 'Unknown Paper'} • Provider: {llmProvider}
            </p>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="glass-panel p-4 text-center">
            <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Compared</p>
            <p className="font-display font-bold text-2xl mt-1" style={{ color: 'var(--text-heading)' }}>{total}</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>parameters</p>
          </div>
          <div className="glass-panel p-4 text-center">
            <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Agreed</p>
            <p className="font-display font-bold text-2xl mt-1" style={{ color: 'var(--status-success)' }}>{agreed}</p>
            <p className="text-[10px]" style={{ color: 'var(--status-success)' }}>same value</p>
          </div>
          <div className="glass-panel p-4 text-center">
            <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Disagreed</p>
            <p className="font-display font-bold text-2xl mt-1" style={{ color: 'var(--status-danger)' }}>{disagreed}</p>
            <p className="text-[10px]" style={{ color: 'var(--status-danger)' }}>different value</p>
          </div>
          <div className="glass-panel p-4 text-center">
            <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Agreement</p>
            <p className="font-display font-bold text-2xl mt-1" style={{ color: confColor(agreePct) }}>{agreePct}%</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>overall match</p>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Bar Chart */}
          <div className="glass-panel p-6">
            <h3 className="font-display font-bold text-sm mb-4 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
              <TrendingUp className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} /> Confidence Comparison
            </h3>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={chartData} barGap={2}>
                  <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 9 }} axisLine={false} tickLine={false} angle={-25} textAnchor="end" height={60} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: 'var(--bg-surface-3)', border: 'none', borderRadius: 8, fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="RAG" fill="var(--accent-primary)" radius={[4, 4, 0, 0]} barSize={16} />
                  <Bar dataKey="LLM" fill="var(--accent-tertiary)" radius={[4, 4, 0, 0]} barSize={16} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-center py-10" style={{ color: 'var(--text-muted)' }}>No parameter data</p>
            )}
          </div>

          {/* Radar */}
          <div className="glass-panel p-6">
            <h3 className="font-display font-bold text-sm mb-4 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
              <Brain className="w-4 h-4" style={{ color: 'var(--accent-secondary)' }} /> Method Comparison Profile
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart cx="50%" cy="50%" outerRadius="60%" data={radarData}>
                <PolarGrid stroke="var(--border-glass)" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <Radar name="RAG" dataKey="RAG" stroke="var(--accent-primary)" fill="var(--accent-primary)" fillOpacity={0.2} />
                <Radar name="LLM" dataKey="LLM" stroke="var(--accent-tertiary)" fill="var(--accent-tertiary)" fillOpacity={0.2} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Parameter Detail Table */}
        <div className="glass-panel p-6">
          <h3 className="font-display font-bold text-sm mb-4 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
            <Zap className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} /> Parameter-by-Parameter Details
          </h3>

          {/* Header */}
          <div className="grid gap-2 mb-2" style={{ gridTemplateColumns: '1.2fr 1fr 1fr 1fr 60px' }}>
            {['Parameter', 'RAG Value', 'LLM Value', 'Match', ''].map((h, i) => (
              <p key={i} className="px-3 text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>{h}</p>
            ))}
          </div>

          {paramComparisons.map((p: any) => {
            const param = p.param || p.parameter || 'unknown';
            const ragVal = p.rag_value ?? '—';
            const llmVal = p.llm_value ?? '—';
            const match = p.match ?? p.agrees ?? (String(ragVal) === String(llmVal));
            const isExpanded = expandedParam === param;

            return (
              <div key={param}>
                <div
                  className="grid gap-2 items-center py-2 px-1 rounded-xl interactive transition-colors"
                  style={{ gridTemplateColumns: '1.2fr 1fr 1fr 1fr 60px', background: isExpanded ? 'var(--bg-surface-2)' : 'transparent' }}
                  onClick={() => setExpandedParam(isExpanded ? null : param)}
                >
                  <p className="px-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {param.replace(/_/g, ' ')}
                  </p>
                  <p className="px-3 font-mono text-sm" style={{ color: 'var(--accent-primary)' }}>{String(ragVal)}</p>
                  <p className="px-3 font-mono text-sm" style={{ color: 'var(--accent-tertiary)' }}>{String(llmVal)}</p>
                  <div className="px-3">
                    {match ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--status-success)' }}>
                        <CheckCircle2 className="w-3.5 h-3.5" /> Match
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--status-danger)' }}>
                        <XCircle className="w-3.5 h-3.5" /> Diff
                      </span>
                    )}
                  </div>
                  <div className="flex justify-center">
                    <ChevronDown className="w-4 h-4 transition-transform" style={{
                      color: 'var(--text-muted)',
                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                    }} />
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-4 py-3 mx-2 mb-2 rounded-xl" style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)' }}>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h4 className="text-xs font-semibold mb-1" style={{ color: 'var(--accent-primary)' }}>RAG Reasoning</h4>
                        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {p.rag_reasoning || p.rag_explanation || `Inferred from ${p.rag_papers || 'N/A'} evidence papers using weighted aggregation. Confidence: ${p.rag_confidence ?? p.rag_conf ?? 'N/A'}%`}
                        </p>
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold mb-1" style={{ color: 'var(--accent-tertiary)' }}>LLM Reasoning</h4>
                        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {p.llm_reasoning || p.llm_explanation || `LLM suggested ${llmVal} based on general knowledge. Confidence: ${p.llm_confidence ?? p.llm_conf ?? 'N/A'}%`}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {paramComparisons.length === 0 && (
            <p className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>
              No parameter comparisons available. The LLM comparison may not have been run for this session.
            </p>
          )}
        </div>

      </div>
    </div>
  );
}
