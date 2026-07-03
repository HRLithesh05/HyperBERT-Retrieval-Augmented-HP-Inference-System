import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts';
import {
  CheckCircle2, AlertTriangle, FileText, Download,
  ChevronDown, Play, BarChart2, Loader2, BookOpen,
  Shield, Zap, Database, ArrowRight, ExternalLink,
} from 'lucide-react';
import { getSession, downloadUrl, type AnalysisResult, type HPEntry } from '@/lib/api';
import { useSession } from '@/contexts/SessionContext';

/* ── Source badge colors ────────────────────────────── */
function sourceStyle(src: string) {
  if (src === 'extracted_from_paper') return { bg: 'rgba(16,185,129,0.12)', color: 'var(--status-success)', label: 'From Paper' };
  if (src === 'inferred_from_corpus') return { bg: 'rgba(139,92,246,0.12)', color: 'var(--accent-primary)', label: 'RAG Inferred' };
  return { bg: 'rgba(100,116,139,0.12)', color: 'var(--text-muted)', label: 'BERT Default' };
}

function confColor(pct: number) {
  if (pct >= 70) return 'var(--status-success)';
  if (pct >= 30) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

const barColors = ['var(--accent-primary)', 'var(--accent-secondary)', 'var(--accent-tertiary)', 'var(--status-warning)', 'var(--status-success)'];

/* ── Main Page ────────────────────────────────────────── */
export default function ResultsDashboard() {
  const { id: urlId } = useParams<{ id: string }>();
  const { sessionId: ctxId } = useSession();
  const id = (urlId && urlId !== 'demo') ? urlId : ctxId;
  const navigate = useNavigate();

  const [data, setData] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setError('No analysis session found. Upload a paper first.');
      return;
    }
    setLoading(true);
    getSession(id)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [id]);

  /* ── Loading / Error states ─── */
  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
          <Loader2 className="w-10 h-10" style={{ color: 'var(--accent-primary)' }} />
        </motion.div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-4" style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
        <AlertTriangle className="w-12 h-12" style={{ color: 'var(--status-warning)' }} />
        <p className="text-lg font-semibold" style={{ color: 'var(--text-heading)' }}>Could not load results</p>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{error}</p>
        <button onClick={() => navigate('/upload')} className="interactive px-5 py-2 rounded-xl text-sm font-semibold text-white mt-2" style={{ background: 'var(--accent-gradient)' }}>
          Upload a Paper
        </button>
      </div>
    );
  }

  /* ── Derived data ──────────────────────── */
  const paper = data.paper;
  const config = data.config;
  const hpEntries = Object.entries(config);
  const displayTitle = paper.title || 'Untitled Paper';
  const displayScore = paper.reproducibility_score;

  const liveRadarData = [
    { subject: 'HP Coverage', A: data.completeness.completeness_pct },
    { subject: 'Task Clarity', A: paper.task ? 90 : 20 },
    { subject: 'Model ID', A: paper.model ? 100 : 10 },
    { subject: 'Dataset Info', A: paper.dataset ? 80 : 15 },
    { subject: 'Reproducibility', A: displayScore },
  ];

  const strategyCascade = Object.entries(data.strategy_cascade || {});

  return (
    <div className="px-4 py-8" style={{ background: 'var(--bg-base)', minHeight: 'calc(100vh - 64px)' }}>
      <div className="mx-auto" style={{ maxWidth: 1280 }}>

        {/* ── Header ── */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <div>
            <h1 className="font-display font-bold text-3xl" style={{ color: 'var(--text-heading)' }}>
              Inference Dashboard
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              {displayTitle}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => id && window.open(downloadUrl.yaml(id), '_blank')}
              className="interactive flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)', color: 'var(--text-primary)' }}
            >
              <Download className="w-4 h-4" /> Export Config
            </button>
            <button
              onClick={() => navigate(`/notebook/${id || ''}`)}
              className="interactive flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white"
              style={{ background: 'var(--accent-gradient)', boxShadow: '0 4px 16px rgba(124,58,237,0.3)' }}
            >
              <Play className="w-4 h-4" /> View Notebook
            </button>
            {id && (
              <button
                onClick={() => navigate(`/compare/${id}`)}
                className="interactive flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
                style={{ background: 'rgba(6,182,212,0.12)', border: '1px solid rgba(6,182,212,0.3)', color: 'var(--accent-tertiary)' }}
              >
                <BarChart2 className="w-4 h-4" /> RAG vs LLM
              </button>
            )}
          </div>
        </div>

        {/* ── Row 1: Paper Summary + Strategy ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">

          {/* Paper Summary Card */}
          <div className="lg:col-span-2 glass-panel p-6">
            <div className="flex flex-col md:flex-row gap-6">
              <div className="flex-1">
                <h2 className="font-display font-bold text-xl mb-3" style={{ color: 'var(--text-heading)' }}>
                  {displayTitle}
                </h2>
                <div className="flex flex-wrap gap-2 mb-4">
                  {paper.task && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(139,92,246,0.12)', color: 'var(--accent-primary)' }}>
                      {paper.task}
                    </span>
                  )}
                  {paper.model && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(59,130,246,0.12)', color: 'var(--accent-secondary)' }}>
                      {paper.model}
                    </span>
                  )}
                  {paper.dataset && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium" style={{ background: 'rgba(6,182,212,0.12)', color: 'var(--accent-tertiary)' }}>
                      {paper.dataset}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl" style={{ background: 'var(--bg-surface-2)' }}>
                    <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>R-Score</p>
                    <p className="font-mono font-bold text-lg" style={{ color: 'var(--accent-primary)' }}>
                      {data.completeness.rscore.toFixed(3)}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl" style={{ background: 'var(--bg-surface-2)' }}>
                    <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Explicit HPs</p>
                    <p className="font-mono font-bold text-lg" style={{ color: 'var(--status-success)' }}>
                      {paper.explicit_hp_count}/{paper.total_hp_count}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl" style={{ background: 'var(--bg-surface-2)' }}>
                    <p className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Pipeline</p>
                    <p className="font-mono font-bold text-lg" style={{ color: 'var(--text-primary)' }}>
                      {data.pipeline_seconds}s
                    </p>
                  </div>
                </div>
                <div className="mt-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ color: displayScore < 30 ? 'var(--status-danger)' : 'var(--status-warning)' }}> {displayScore < 30 ? 'Low' : 'Partial'} reproducibility.</span>
                </div>
              </div>
              {/* Radar chart */}
              <div style={{ width: 280, flexShrink: 0 }}>
                <p className="text-xs font-semibold uppercase text-center mb-2" style={{ color: 'var(--text-muted)' }}>
                  Reproducibility Profile
                </p>
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart cx="50%" cy="50%" outerRadius="55%" data={liveRadarData}>
                    <PolarGrid stroke="var(--border-glass)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                    <Radar dataKey="A" stroke="var(--accent-primary)" fill="var(--accent-primary)" fillOpacity={0.25}
                      animationDuration={1000} />
                  </RadarChart>
                </ResponsiveContainer>
                <p className="text-xs text-center font-mono font-bold text-gradient">{displayScore}% Reproducible</p>
              </div>
            </div>
          </div>

          {/* Strategy Cascade Card */}
          <div className="glass-panel p-6">
            <h3 className="font-display font-bold text-sm mb-4 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
              <Zap className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} /> Strategy Cascade
            </h3>
            <div className="space-y-2">
              {strategyCascade.map(([key, info], i) => (
                <div key={key} className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold"
                    style={{
                      background: info.status === 'selected' ? 'var(--accent-gradient)' : 'var(--bg-surface-2)',
                      color: info.status === 'selected' ? 'white' : 'var(--text-muted)',
                    }}>
                    S{i + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium" style={{ color: info.status === 'selected' ? 'var(--text-heading)' : 'var(--text-muted)' }}>
                      {info.label}
                    </p>
                    {info.status === 'selected' && (
                      <p className="text-[10px]" style={{ color: 'var(--accent-primary)' }}>
                        {info.papers} papers matched
                      </p>
                    )}
                  </div>
                  {info.status === 'selected' && <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--status-success)' }} />}
                  {info.status === 'skipped' && <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>skipped</span>}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Row 2: HP Table ── */}
        <div className="glass-panel p-6 mb-6">
          <h3 className="font-display font-bold text-lg mb-4 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
            <Database className="w-5 h-5" style={{ color: 'var(--accent-secondary)' }} /> Hyperparameter Configuration
          </h3>

          {/* Table header */}
          <div className="grid gap-2" style={{ gridTemplateColumns: '1.5fr 1fr 1fr 1fr 60px' }}>
            <div className="px-3 py-2 text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Parameter</div>
            <div className="px-3 py-2 text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Value</div>
            <div className="px-3 py-2 text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Source</div>
            <div className="px-3 py-2 text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Confidence</div>
            <div />
          </div>

          {/* Rows */}
          {hpEntries.map(([param, entry]) => {
            const ss = sourceStyle(entry.source);
            const isExpanded = expandedRow === param;
            return (
              <div key={param}>
                <div
                  className="grid gap-2 items-center py-2 px-1 rounded-xl transition-colors interactive"
                  style={{ gridTemplateColumns: '1.5fr 1fr 1fr 1fr 60px', background: isExpanded ? 'var(--bg-surface-2)' : 'transparent' }}
                  onClick={() => setExpandedRow(isExpanded ? null : param)}
                >
                  <div className="px-3">
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{param.replace(/_/g, ' ')}</p>
                    {entry.papers && <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{entry.papers} papers</p>}
                  </div>
                  <div className="px-3">
                    <span className="font-mono text-sm font-bold" style={{ color: 'var(--text-heading)' }}>
                      {entry.value !== null ? String(entry.value) : '—'}
                    </span>
                  </div>
                  <div className="px-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: ss.bg, color: ss.color }}>
                      {ss.label}
                    </span>
                  </div>
                  <div className="px-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'var(--bg-surface-3)' }}>
                        <div className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${entry.confidence_pct}%`, background: confColor(entry.confidence_pct) }} />
                      </div>
                      <span className="text-xs font-mono font-bold" style={{ color: confColor(entry.confidence_pct) }}>
                        {entry.confidence_pct}%
                      </span>
                    </div>
                  </div>
                  <div className="flex justify-center">
                    <ChevronDown className="w-4 h-4 transition-transform" style={{
                      color: 'var(--text-muted)',
                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                    }} />
                  </div>
                </div>

                {/* Expanded detail */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 py-4 mx-2 mb-2 rounded-xl" style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)' }}>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Inference Trace */}
                          <div>
                            <h4 className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--accent-primary)' }}>Inference Trace</h4>
                            <div className="space-y-1">
                              {entry.inference_trace.map((step, i) => (
                                <div key={i} className="flex items-start gap-2">
                                  <ArrowRight className="w-3 h-3 mt-0.5 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
                                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{step}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Distribution chart + Confidence decomposition */}
                          <div>
                            {entry.distribution && entry.distribution.length > 0 && (
                              <div className="mb-4">
                                <h4 className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--accent-secondary)' }}>Evidence Distribution</h4>
                                <ResponsiveContainer width="100%" height={100}>
                                  <BarChart data={entry.distribution}>
                                    <XAxis dataKey="v" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <YAxis hide />
                                    <Tooltip contentStyle={{ background: 'var(--bg-surface-3)', border: 'none', borderRadius: 8, fontSize: 11 }} />
                                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                      {entry.distribution.map((_, i) => (
                                        <Cell key={i} fill={barColors[i % barColors.length]} />
                                      ))}
                                    </Bar>
                                  </BarChart>
                                </ResponsiveContainer>
                              </div>
                            )}
                            <h4 className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--accent-tertiary)' }}>Confidence Breakdown</h4>
                            <div className="space-y-1.5">
                              {Object.entries(entry.confidence_decomposition).map(([key, val]) => (
                                <div key={key} className="flex items-center gap-2">
                                  <span className="text-[10px] w-16 capitalize" style={{ color: 'var(--text-muted)' }}>{key}</span>
                                  <div className="flex-1 h-1.5 rounded-full" style={{ background: 'var(--bg-surface-3)' }}>
                                    <div className="h-full rounded-full" style={{ width: `${val}%`, background: confColor(val) }} />
                                  </div>
                                  <span className="text-[10px] font-mono" style={{ color: 'var(--text-secondary)' }}>{val}%</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>

        {/* ── Row 3: Constraints + Validation + Downloads ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">

          {/* Constraints */}
          <div className="glass-panel p-6">
            <h3 className="font-display font-bold text-sm mb-3 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
              <Shield className="w-4 h-4" style={{ color: 'var(--status-warning)' }} /> Domain Constraints
            </h3>
            {data.constraints.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No constraints were applied.</p>
            ) : (
              <div className="space-y-2">
                {data.constraints.map((c, i) => (
                  <div key={i} className="p-2 rounded-lg text-xs" style={{ background: 'var(--bg-surface-2)' }}>
                    <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {c.param}: {String(c.old_value)} → {String(c.new_value)}
                    </p>
                    <p style={{ color: 'var(--text-muted)' }}>{c.explanation}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Validation */}
          <div className="glass-panel p-6">
            <h3 className="font-display font-bold text-sm mb-3 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
              <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--status-success)' }} /> Validation
            </h3>
            <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg" style={{ background: data.validation.verdict === 'PASS' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)' }}>
              {data.validation.verdict === 'PASS'
                ? <CheckCircle2 className="w-4 h-4" style={{ color: 'var(--status-success)' }} />
                : <AlertTriangle className="w-4 h-4" style={{ color: 'var(--status-warning)' }} />
              }
              <span className="text-xs font-bold" style={{ color: data.validation.verdict === 'PASS' ? 'var(--status-success)' : 'var(--status-warning)' }}>
                {data.validation.verdict}
              </span>
            </div>
            {data.validation.warnings.length > 0 && (
              <div className="space-y-1">
                {data.validation.warnings.map((w: any, i: number) => (
                  <p key={i} className="text-xs" style={{ color: 'var(--status-warning)' }}>⚠ {typeof w === 'string' ? w : w.message || JSON.stringify(w)}</p>
                ))}
              </div>
            )}
            <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>{data.contradiction_summary}</p>
          </div>

          {/* Downloads */}
          <div className="glass-panel p-6">
            <h3 className="font-display font-bold text-sm mb-3 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
              <Download className="w-4 h-4" style={{ color: 'var(--accent-secondary)' }} /> Export & Download
            </h3>
            <div className="space-y-2">
              {[
                { label: 'Jupyter Notebook', desc: '.ipynb', icon: BookOpen, url: id ? downloadUrl.notebook(id) : '' },
                { label: 'Training Script', desc: '.py', icon: FileText, url: id ? downloadUrl.script(id) : '' },
                { label: 'YAML Config', desc: '.yaml', icon: FileText, url: id ? downloadUrl.yaml(id) : '' },
                { label: 'JSON Config', desc: '.json', icon: FileText, url: id ? downloadUrl.config(id) : '' },
              ].map(item => (
                <a
                  key={item.label}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="interactive flex items-center gap-3 p-2.5 rounded-xl transition-colors"
                  style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)' }}
                >
                  <item.icon className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
                  <div className="flex-1">
                    <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{item.label}</p>
                    <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{item.desc}</p>
                  </div>
                  <ExternalLink className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                </a>
              ))}
            </div>
          </div>
        </div>

        {/* ── Row 4: Audit Log ── */}
        <div className="glass-panel p-6">
          <h3 className="font-display font-bold text-sm mb-3 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
            <FileText className="w-4 h-4" style={{ color: 'var(--text-muted)' }} /> Pipeline Audit Trail
          </h3>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {data.audit_log.map((entry, i) => (
              <div key={i} className="flex items-start gap-3 py-1">
                <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold flex-shrink-0"
                  style={{ background: 'var(--bg-surface-2)', color: 'var(--accent-primary)' }}>
                  {entry.module}
                </span>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{entry.message}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
