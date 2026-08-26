import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts';
import {
  CheckCircle2, AlertTriangle, FileText, Download,
  Activity, ChevronDown, Edit2, Play, Eye, BarChart2,
} from 'lucide-react';
import { getSession, downloadUrl, type AnalysisResult } from '@/lib/api';
import { useSession } from '@/contexts/SessionContext';

/* ────────────────────────────────
   Mock data (will be replaced by API)
──────────────────────────────── */
const radarData = [
  { subject: 'HP Coverage', A: 8 },
  { subject: 'Task Clarity', A: 90 },
  { subject: 'Model ID', A: 100 },
  { subject: 'Dataset Info', A: 20 },
  { subject: 'Reproducibility', A: 35 },
];

const hpRows = [
  {
    id: 'batch_size', name: 'Batch Size', value: '32', source: 'inferred', confidence: 59.5,
    papers: 6,
    trace: [
      'Searched 435 papers in FAISS index (384-dim sentence vectors)',
      'Strategy S2 (Task + Model) matched 6 NER+BERT papers',
      'Found batch_size in 4/6 papers: [16, 32, 32, 64]',
      'Computed weighted scores: Paper1=0.78, Paper2=0.92, Paper3=0.85, Paper4=0.71',
      'Applied weighted median → 32',
      'Confidence: similarity=0.82 × agreement=0.71 × support=0.45 → 59.5%',
    ],
    decomp: { similarity: 82, agreement: 71, support: 45 },
    distribution: [{ v: '16', count: 1 }, { v: '32', count: 2 }, { v: '64', count: 1 }],
  },
  {
    id: 'optimizer', name: 'Optimizer', value: 'Adam', source: 'paper', confidence: 100,
    papers: null,
    trace: ['Extracted directly from paper text: "we use Adam optimizer"'],
    decomp: { similarity: 100, agreement: 100, support: 100 },
    distribution: [],
  },
  {
    id: 'learning_rate', name: 'Learning Rate', value: '2e-5', source: 'default', confidence: 20,
    papers: null,
    trace: ['No evidence found in 6 matched papers for learning_rate', 'Falling back to BERT default (Devlin et al., 2019)'],
    decomp: { similarity: 0, agreement: 0, support: 20 },
    distribution: [],
  },
  {
    id: 'epochs', name: 'Epochs', value: '10', source: 'inferred', confidence: 56,
    papers: 6,
    trace: ['Found epochs in 3/6 papers: [3, 10, 10]', 'Weighted median → 10'],
    decomp: { similarity: 75, agreement: 68, support: 40 },
    distribution: [{ v: '3', count: 1 }, { v: '10', count: 2 }],
  },
  {
    id: 'weight_decay', name: 'Weight Decay', value: '0.0', source: 'inferred', confidence: 53,
    papers: 6,
    trace: ['Evidence median was 0.01, but Module 4 adjusted: Adam→WD=0 (Loshchilov & Hutter, 2019)'],
    decomp: { similarity: 65, agreement: 55, support: 40 },
    distribution: [],
  },
  {
    id: 'max_seq_length', name: 'Max Seq Length', value: '512', source: 'inferred', confidence: 58,
    papers: 6,
    trace: ['Found max_seq_length in 2/6 papers: [256, 512]', 'Weighted median → 512'],
    decomp: { similarity: 78, agreement: 60, support: 35 },
    distribution: [{ v: '256', count: 1 }, { v: '512', count: 1 }],
  },
  {
    id: 'dropout', name: 'Dropout', value: '0.1', source: 'inferred', confidence: 56,
    papers: 6,
    trace: ['Found dropout in 3/6 papers: [0.1, 0.1, 0.2]', 'Weighted median → 0.1'],
    decomp: { similarity: 70, agreement: 72, support: 40 },
    distribution: [{ v: '0.1', count: 2 }, { v: '0.2', count: 1 }],
  },
  {
    id: 'scheduler', name: 'Scheduler', value: 'linear', source: 'default', confidence: 20,
    papers: null,
    trace: ['Not found in evidence papers', 'BERT default: linear schedule (Devlin et al., 2019)'],
    decomp: { similarity: 0, agreement: 0, support: 20 },
    distribution: [],
  },
];

const evidencePapers = [
  { title: 'BERT for NER in Clinical Texts', sim: 0.92, batch: 32, epochs: 10, lr: '2e-5', wd: 0, opt: 'AdamW' },
  { title: 'Fine-Tuning BERT on Low-Resource NER', sim: 0.85, batch: 32, epochs: 10, lr: '3e-5', wd: 0.01, opt: 'Adam' },
  { title: 'Named Entity Recognition with BERT', sim: 0.78, batch: 16, epochs: 3, lr: '2e-5', wd: 0, opt: 'AdamW' },
  { title: 'Multilingual BERT for NER', sim: 0.71, batch: 64, epochs: null, lr: '5e-5', wd: 0.01, opt: 'Adam' },
  { title: 'Domain Adaptation of BERT for NER', sim: 0.65, batch: 32, epochs: 10, lr: '2e-5', wd: 0, opt: 'AdamW' },
  { title: 'BERT-CRF for Sequence Labeling', sim: 0.60, batch: null, epochs: 10, lr: '2e-5', wd: 0, opt: 'Adam' },
];

/* ────────────────────────────────
   Helper sub-components
──────────────────────────────── */
type ExpandType = 'trace' | 'dist' | 'edit' | null;

function SourceBadge({ source, papers }: { source: string; papers: number | null }) {
  const cfg = {
    paper: { label: 'From Paper', bg: 'rgba(5,150,105,0.12)', color: 'var(--status-success)', border: 'rgba(5,150,105,0.25)' },
    inferred: { label: `Inferred (${papers})`, bg: 'rgba(217,119,6,0.12)', color: 'var(--status-warning)', border: 'rgba(217,119,6,0.25)' },
    default: { label: 'BERT Default', bg: 'rgba(220,38,38,0.1)', color: 'var(--status-danger)', border: 'rgba(220,38,38,0.22)' },
  }[source as 'paper' | 'inferred' | 'default'] ?? { label: source, bg: 'transparent', color: '#888', border: '#888' };

  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-semibold"
      style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}
    >
      {cfg.label}
    </span>
  );
}

function ConfBar({ pct, dim }: { pct: number; dim?: boolean }) {
  const color = pct >= 70 ? 'var(--status-success)' : pct >= 30 ? 'var(--status-warning)' : 'var(--status-danger)';
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-3)' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.9, ease: 'easeOut' }}
          style={{ height: '100%', background: dim ? '#555' : color, borderRadius: 9999 }}
        />
      </div>
      <span className="text-xs font-mono w-8 text-right flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
        {pct}%
      </span>
    </div>
  );
}

/* ────────────────────────────────
   Main Page
──────────────────────────────── */
export default function ResultsDashboard() {
  const { id: urlId } = useParams<{ id: string }>();
  const { sessionId: ctxId } = useSession();
  // Use URL param if it's a real UUID, otherwise fall back to context
  const id = (urlId && urlId !== 'demo') ? urlId : ctxId;
  const navigate = useNavigate();
  const [liveData, setLiveData] = useState<AnalysisResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<{ id: string; type: ExpandType }>({ id: '', type: null });
  const [auditOpen, setAuditOpen] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  // Load live data if a real session ID is provided
  useEffect(() => {
    if (!id || id === 'demo') return;
    getSession(id)
      .then(setLiveData)
      .catch(e => setLoadError(e.message));
  }, [id]);

  // Merge live API data into the UI structures
  const paperInfo = liveData?.paper;
  const liveHpRows = liveData ? Object.entries(liveData.config).map(([key, entry]) => ({
    id: key,
    name: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    value: String(entry.value ?? '—'),
    source: entry.source === 'extracted_from_paper' ? 'paper'
           : entry.source === 'inferred_from_corpus' ? 'inferred' : 'default',
    confidence: entry.confidence_pct,
    papers: entry.papers,
    trace: entry.inference_trace,
    decomp: entry.confidence_decomposition,
    distribution: entry.distribution,
  })) : hpRows;

  const liveEvidencePapers = liveData?.evidence_papers?.map((p: any) => ({
    title: p.title, sim: p.similarity?.toFixed(2) ?? '—',
    batch: p.hyperparameters?.batch_size ?? null,
    epochs: p.hyperparameters?.epochs ?? null,
    lr: p.hyperparameters?.learning_rate ?? null,
    wd: p.hyperparameters?.weight_decay ?? null,
    opt: p.hyperparameters?.optimizer ?? null,
  })) || evidencePapers;

  const liveConstraints = liveData?.constraints?.length
    ? liveData.constraints
    : [{ param: 'weight_decay', rule: 'Optimizer Coupling', old_value: '0.01', new_value: '0.0', explanation: 'Adam (not AdamW) uses WD=0', citation: 'Loshchilov & Hutter, 2019' }];

  const liveAuditLog = liveData?.audit_log?.map(l => ({
    m: l.module, c: 'var(--text-secondary)', msg: l.message,
  })) || [
    { m: 'M1', c: 'var(--accent-secondary)', msg: 'Extracted 14,200 characters from PDF' },
    { m: 'M2', c: 'var(--status-warning)', msg: 'R-Score: 0.129 — 11 HPs missing' },
    { m: 'M3', c: 'var(--status-success)', msg: 'S2 matched 6 NER+BERT papers' },
    { m: 'M4', c: 'var(--accent-primary)', msg: 'Applied Adam↔WD constraint' },
    { m: 'M5', c: 'var(--text-muted)', msg: 'No contradictions detected' },
    { m: 'M6', c: 'var(--status-success)', msg: 'Validation PASSED' },
    { m: 'M7', c: 'var(--accent-tertiary)', msg: 'Generated training_notebook.ipynb' },
  ];

  const liveRadarData = liveData ? [
    { subject: 'HP Cover.', A: liveData.paper.reproducibility_score },
    { subject: 'Task', A: liveData.paper.task ? 90 : 10 },
    { subject: 'Model', A: liveData.paper.model ? 100 : 20 },
    { subject: 'Dataset', A: liveData.paper.dataset ? 80 : 5 },
    { subject: 'Reprod.', A: liveData.completeness.completeness_pct },
  ] : radarData;

  const displayTitle = paperInfo?.title || 'Comparative Study of Pre-Trained BERT and Large Language Models';
  const displayTask = paperInfo?.task?.toUpperCase() || 'NER';
  const displayModel = paperInfo?.model || 'BERT Base Cased';
  const displayDataset = paperInfo?.dataset || 'unspecified';
  const displayScore = paperInfo?.reproducibility_score ?? 8;
  const displayExplicit = paperInfo?.explicit_hp_count ?? 1;

  const toggleExpand = (id: string, type: ExpandType) => {
    setExpanded(prev => prev.id === id && prev.type === type ? { id: '', type: null } : { id, type });
  };

  return (
    <div style={{ background: 'var(--bg-base)', minHeight: 'calc(100vh - 64px)' }}>
      <div className="mx-auto px-4 py-8" style={{ maxWidth: 1200 }}>

        {/* Load error banner */}
        {loadError && (
          <div className="mb-6 px-4 py-3 rounded-xl text-sm flex items-center gap-2"
            style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)', color: 'var(--status-danger)' }}>
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            Could not load session: {loadError}. Showing demo data.
          </div>
        )}

        {/* ── Page Header ── */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
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
              onClick={() => {
                if (id) window.location.href = downloadUrl.yaml(id);
              }}
              disabled={!id}
              className="interactive flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)', color: 'var(--text-primary)', opacity: id ? 1 : 0.5 }}
            >
              <Download className="w-4 h-4" /> Export Config
            </button>
            <button
              onClick={() => navigate(`/notebook/${id || 'demo'}`)}
              className="interactive flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white"
              style={{ background: 'var(--accent-gradient)', boxShadow: '0 4px 16px rgba(124,58,237,0.3)' }}
            >
              <Play className="w-4 h-4" /> View Notebook
            </button>
            {liveData && (
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
                <div className="flex flex-wrap gap-2 mb-3">
                  {[
                    { label: displayTask, color: 'var(--accent-secondary)' },
                    { label: displayModel, color: 'var(--accent-primary)' },
                    { label: `Dataset: ${displayDataset}`, color: 'var(--text-muted)' },
                  ].map(b => (
                    <span key={b.label} className="px-2.5 py-1 rounded-lg text-xs font-semibold"
                      style={{ background: `${b.color}18`, color: b.color, border: `1px solid ${b.color}30` }}>
                      {b.label}
                    </span>
                  ))}
                </div>
                <h2 className="font-display font-bold text-xl mb-3" style={{ color: 'var(--text-heading)' }}>
                  {displayTitle}
                </h2>
                <div className="rounded-xl p-3 text-sm" style={{ background: 'var(--bg-surface-3)', color: 'var(--text-secondary)' }}>
                  This paper explicitly reported <strong style={{ color: 'var(--text-primary)' }}>{displayExplicit} of 12</strong> hyperparameters.
                  <span style={{ color: displayScore < 30 ? 'var(--status-danger)' : 'var(--status-warning)' }}> {displayScore < 30 ? 'Low' : 'Partial'} reproducibility.</span>
                </div>
              </div>
              {/* Radar chart */}
              <div style={{ width: 200, flexShrink: 0 }}>
                <p className="text-xs font-semibold uppercase text-center mb-2" style={{ color: 'var(--text-muted)' }}>
                  Reproducibility Profile
                </p>
                <ResponsiveContainer width="100%" height={190}>
                  <RadarChart cx="50%" cy="50%" outerRadius="55%" data={liveRadarData}>
                    <PolarGrid stroke="var(--border-glass)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 8 }} />
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
            <h3 className="text-sm font-semibold uppercase mb-4 flex items-center gap-2"
              style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
              <Activity className="w-4 h-4" /> Retrieval Strategy
            </h3>
            <div className="space-y-2">
              {(liveData ? Object.entries(liveData.strategy_cascade).map(([key, s]) => ({
                label: `${key.replace('_', ' ')}: ${s.label}`,
                status: s.status,
                reason: s.status === 'skipped' ? 'Insufficient evidence' : s.status === 'pending' ? 'Not needed' : null,
                papers: s.papers || null,
              })) : [
                { label: 'S1: Task+Model+Dataset', status: 'skipped', reason: 'No dataset detected', papers: null },
                { label: 'S2: Task+Model', status: 'selected', reason: null, papers: 6 },
                { label: 'S3: Task Only', status: 'pending', reason: 'Not needed', papers: null },
                { label: 'S4: Global', status: 'pending', reason: 'Not needed', papers: null },
              ]).map((s, i) => (
                <div key={i}>
                  <div
                    className="p-3 rounded-xl text-xs transition-all"
                    style={{
                      border: s.status === 'selected' ? '1px solid rgba(16,185,129,0.4)' : '1px solid var(--border-glass)',
                      background: s.status === 'selected' ? 'rgba(16,185,129,0.08)' : 'var(--bg-surface-3)',
                      opacity: s.status === 'pending' ? 0.4 : 1,
                    }}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-semibold" style={{ color: s.status === 'selected' ? 'var(--status-success)' : 'var(--text-primary)' }}>
                        {s.label}
                      </span>
                      {s.status === 'selected' && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white"
                          style={{ background: 'var(--status-success)' }}>SELECTED</span>
                      )}
                    </div>
                    {s.reason && <p style={{ color: 'var(--text-muted)' }}>{s.reason}</p>}
                    {s.papers && <p style={{ color: 'var(--status-success)' }}>{s.papers} papers matched</p>}
                  </div>
                  {i < 3 && (
                    <div className="flex justify-center my-1">
                      <ChevronDown className="w-3 h-3" style={{ color: 'var(--border-highlight)' }} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Card 3: HP Table ── */}
        <div className="glass-panel p-6 mb-6 overflow-hidden">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-display font-bold text-lg" style={{ color: 'var(--text-heading)' }}>
              Inferred Configuration
            </h3>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Click 🔍 for trace · 📊 for distribution · ✏️ to edit
            </span>
          </div>

          <div>
            {/* Header row */}
            <div
              className="grid text-xs font-semibold uppercase pb-3 mb-1"
              style={{ gridTemplateColumns: '1fr 90px 130px 1fr 90px', gap: '1rem', color: 'var(--text-muted)', letterSpacing: '0.05em', borderBottom: '1px solid var(--border-glass)' }}
            >
              <div>Parameter</div>
              <div>Value</div>
              <div>Source</div>
              <div>Confidence</div>
              <div className="text-right">Actions</div>
            </div>

            {liveHpRows.map(row => {
              const isTrace = expanded.id === row.id && expanded.type === 'trace';
              const isDist = expanded.id === row.id && expanded.type === 'dist';
              const isEdit = expanded.id === row.id && expanded.type === 'edit';

              return (
                <div key={row.id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  {/* Main row */}
                  <div
                    className="grid items-center py-4 transition-colors"
                    style={{ gridTemplateColumns: '1fr 90px 130px 1fr 90px', gap: '1rem' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-surface-3)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>{row.name}</div>
                    <div className="font-mono text-sm font-bold" style={{ color: 'var(--text-heading)' }}>
                      {editValues[row.id] !== undefined ? editValues[row.id] : row.value}
                    </div>
                    <div><SourceBadge source={row.source} papers={row.papers} /></div>
                    <ConfBar pct={row.confidence} />
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => toggleExpand(row.id, 'trace')}
                        className="interactive p-1.5 rounded-lg transition-colors" title="Show reasoning trace"
                        style={{ background: isTrace ? 'var(--accent-primary)' : 'var(--bg-surface-3)', color: isTrace ? 'white' : 'var(--text-muted)' }}>
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      {row.distribution.length > 0 && (
                        <button onClick={() => toggleExpand(row.id, 'dist')}
                          className="interactive p-1.5 rounded-lg transition-colors" title="Show distribution"
                          style={{ background: isDist ? 'var(--accent-secondary)' : 'var(--bg-surface-3)', color: isDist ? 'white' : 'var(--text-muted)' }}>
                          <BarChart2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button onClick={() => toggleExpand(row.id, 'edit')}
                        className="interactive p-1.5 rounded-lg transition-colors" title="Edit value"
                        style={{ background: isEdit ? 'var(--accent-tertiary)' : 'var(--bg-surface-3)', color: isEdit ? 'white' : 'var(--text-muted)' }}>
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Expandable panels */}
                  <AnimatePresence>
                    {isTrace && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}
                        className="overflow-hidden">
                        <div className="px-4 pb-5 pt-3" style={{ background: 'var(--bg-surface-2)' }}>
                          <p className="text-xs font-semibold uppercase mb-3" style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                            Inference Trace
                          </p>
                          <div className="relative pl-4" style={{ borderLeft: '2px solid var(--accent-primary)', marginLeft: 4 }}>
                            {row.trace.map((step, i) => (
                              <motion.div
                                key={i}
                                initial={{ opacity: 0, x: -8 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.08 }}
                                className="mb-2 last:mb-0"
                              >
                                <div className="absolute w-2 h-2 rounded-full" style={{ background: 'var(--accent-primary)', left: -5, marginTop: 4 }} />
                                <span className="text-xs font-mono" style={{ color: i === row.trace.length - 1 ? 'var(--accent-secondary)' : 'var(--text-secondary)' }}>
                                  {step}
                                </span>
                              </motion.div>
                            ))}
                          </div>
                          {/* Confidence decomposition */}
                          <div className="mt-4 grid grid-cols-3 gap-4">
                            {(['similarity', 'agreement', 'support'] as const).map(k => (
                              <div key={k}>
                                <p className="text-[10px] uppercase font-semibold mb-1.5" style={{ color: 'var(--text-muted)' }}>{k}</p>
                                <ConfBar pct={row.decomp[k]} />
                              </div>
                            ))}
                          </div>
                          <p className="text-[10px] mt-2" style={{ color: 'var(--text-muted)' }}>
                            Confidence = 0.4×Similarity + 0.3×Agreement + 0.3×Support
                          </p>
                        </div>
                      </motion.div>
                    )}

                    {isDist && row.distribution.length > 0 && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} className="overflow-hidden">
                        <div className="px-4 pb-5 pt-3" style={{ background: 'var(--bg-surface-2)' }}>
                          <p className="text-xs font-semibold uppercase mb-3" style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                            Value Distribution across Evidence Papers
                          </p>
                          <ResponsiveContainer width="100%" height={120}>
                            <BarChart data={row.distribution} barCategoryGap="30%">
                              <XAxis dataKey="v" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                              <Tooltip
                                contentStyle={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)', borderRadius: 8, color: 'var(--text-primary)' }}
                              />
                              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                {row.distribution.map((d, i) => (
                                  <Cell key={i}
                                    fill={d.v === row.value ? 'var(--accent-primary)' : 'var(--accent-secondary)'}
                                    fillOpacity={d.v === row.value ? 1 : 0.5}
                                  />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                          <p className="text-[10px] mt-1" style={{ color: 'var(--accent-primary)' }}>
                            ★ Inferred value: {row.value}
                          </p>
                        </div>
                      </motion.div>
                    )}

                    {isEdit && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} className="overflow-hidden">
                        <div className="px-4 pb-5 pt-3" style={{ background: 'var(--bg-surface-2)' }}>
                          <p className="text-xs font-semibold uppercase mb-3" style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                            Override Value
                          </p>
                          <div className="flex items-center gap-3 flex-wrap">
                            <input
                              className="interactive flex-1 px-3 py-2 rounded-lg text-sm font-mono outline-none focus:ring-2"
                              style={{
                                background: 'var(--bg-surface-3)',
                                border: '1px solid var(--border-highlight)',
                                color: 'var(--text-primary)',
                                minWidth: 120,
                              }}
                              value={editValues[row.id] ?? row.value}
                              onChange={e => setEditValues(prev => ({ ...prev, [row.id]: e.target.value }))}
                              placeholder={row.value}
                            />
                            <button
                              className="interactive px-3 py-2 rounded-lg text-xs font-semibold text-white"
                              style={{ background: 'var(--accent-gradient)' }}
                              onClick={() => {}}
                            >
                              Use My Value
                            </button>
                            <button
                              className="interactive px-3 py-2 rounded-lg text-xs font-semibold"
                              style={{ background: 'var(--bg-surface-3)', color: 'var(--text-secondary)', border: '1px solid var(--border-glass)' }}
                              onClick={() => setEditValues(prev => { const n = { ...prev }; delete n[row.id]; return n; })}
                            >
                              Reset to {row.value}
                            </button>
                          </div>
                          <p className="text-[10px] mt-2" style={{ color: 'var(--text-muted)' }}>
                            Recommended: <span className="font-mono">{row.value}</span> — confidence {row.confidence}%
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Card 4: Evidence Table ── */}
        <div className="glass-panel p-6 mb-6 overflow-x-auto">
          <h3 className="font-display font-bold text-lg mb-5" style={{ color: 'var(--text-heading)' }}>
            Evidence Papers{' '}
            <span className="ml-2 px-2 py-0.5 rounded text-sm font-mono" style={{ background: 'rgba(59,130,246,0.12)', color: 'var(--accent-secondary)' }}>
              {liveEvidencePapers.length}
            </span>
          </h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-glass)' }}>
                {['#', 'Paper', 'Similarity', 'batch_size', 'epochs', 'learning_rate', 'wd', 'optimizer'].map(h => (
                  <th key={h} className="text-left pb-2 pr-4" style={{ color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {liveEvidencePapers.map((p, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border-glass)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-surface-3)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td className="py-3 pr-4" style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                  <td className="py-3 pr-4 max-w-[220px] truncate" style={{ color: 'var(--text-primary)' }}>{p.title}</td>
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-3)' }}>
                        <div style={{ width: `${p.sim * 100}%`, height: '100%', background: 'var(--accent-primary)', borderRadius: 9999 }} />
                      </div>
                      <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{p.sim}</span>
                    </div>
                  </td>
                  {[p.batch, p.epochs, p.lr, p.wd, p.opt].map((v, j) => (
                    <td key={j} className="py-3 pr-4 font-mono" style={{ color: v != null ? 'var(--status-warning)' : 'var(--text-muted)' }}>
                      {v ?? '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── Row: Constraints + Validation ── */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* Constraints */}
          <div className="glass-panel p-6">
            <h3 className="text-sm font-semibold uppercase mb-4" style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
              Domain Constraints Applied
            </h3>
            {liveConstraints.map((c, idx) => (
              <div key={idx} className="rounded-xl p-4 relative overflow-hidden mb-3 last:mb-0" style={{ background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.2)' }}>
                <div className="absolute left-0 top-0 bottom-0 w-0.5" style={{ background: 'var(--accent-secondary)' }} />
                <div className="pl-3">
                  <p className="font-semibold text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
                    {c.rule || 'Domain Rule'}
                  </p>
                  <p className="text-xs font-mono mb-2" style={{ color: 'var(--status-warning)' }}>
                    {c.param}: {String(c.old_value ?? '?')} → {String(c.new_value ?? '?')}
                  </p>
                  <p className="text-xs italic mb-2" style={{ color: 'var(--text-muted)' }}>
                    "{c.explanation}"
                  </p>
                  {c.citation && (
                    <p className="text-xs font-semibold" style={{ color: 'var(--accent-secondary)' }}>📖 {c.citation}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Validation */}
          <div className="glass-panel p-6 flex flex-col items-center justify-center text-center">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
              style={{ background: 'rgba(16,185,129,0.12)', border: '2px solid rgba(16,185,129,0.3)' }}
            >
              <CheckCircle2 className="w-8 h-8" style={{ color: 'var(--status-success)' }} />
            </div>
            <h3 className="font-display font-bold text-xl mb-2" style={{ color: 'var(--text-heading)' }}>
              Validation Passed
            </h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              All inferred hyperparameters are within standard BERT domain bounds.
            </p>
          </div>
        </div>

        {/* ── Card 5: Exports ── */}
        <div className="glass-panel p-6 mb-6">
          <h3 className="font-display font-bold text-lg mb-6" style={{ color: 'var(--text-heading)' }}>
            Export & Download
          </h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: '📓', name: 'Jupyter Notebook', ext: '.ipynb', desc: 'Ready-to-run training notebook with confidence annotations', primary: true, url: downloadUrl.notebook(id || '') },
              { icon: '🐍', name: 'Python Script', ext: '.py', desc: 'HuggingFace TrainingArguments script with inline comments', primary: false, url: downloadUrl.script(id || '') },
              { icon: '📋', name: 'YAML Config', ext: '.yaml', desc: 'Machine-readable config for automation pipelines', primary: false, url: downloadUrl.yaml(id || '') },
              { icon: '📄', name: 'JSON Config', ext: '.json', desc: 'Full parameter configuration with confidence scores', primary: false, url: downloadUrl.config(id || '') },
            ].map(item => (
              <div
                key={item.ext}
                className="interactive p-5 rounded-2xl flex flex-col gap-3 transition-all group"
                style={{
                  border: item.primary ? '1px solid var(--accent-primary)' : '1px solid var(--border-glass)',
                  background: item.primary ? 'rgba(139,92,246,0.06)' : 'var(--bg-surface-2)',
                  boxShadow: item.primary ? '0 0 20px rgba(139,92,246,0.12)' : 'none',
                }}
              >
                <div className="text-3xl">{item.icon}</div>
                <div>
                  <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>{item.name}</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{item.desc}</p>
                </div>
                <button
                  onClick={async () => {
                    try {
                      const res = await fetch(item.url);
                      if (!res.ok) throw new Error('Download failed');
                      const blob = await res.blob();
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${item.name.toLowerCase().replace(/\s+/g, '_')}${item.ext}`;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                    } catch (e) {
                      console.error('Download failed:', e);
                    }
                  }}
                  className="interactive mt-auto flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white transition-all"
                  style={{
                    background: item.primary ? 'var(--accent-gradient)' : 'var(--bg-surface-3)',
                    color: item.primary ? 'white' : 'var(--text-secondary)',
                    border: item.primary ? 'none' : '1px solid var(--border-glass)',
                  }}
                >
                  <Download className="w-3.5 h-3.5" /> Download {item.ext}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* ── Card 5b: Quick Actions — Compare & Notebook ── */}
        <div className="grid sm:grid-cols-2 gap-5 mb-6">
          <button
            onClick={() => navigate(`/compare/${id || 'demo'}`)}
            className="interactive glass-panel p-6 flex items-start gap-4 text-left transition-all group"
            style={{ border: '1px solid rgba(245,158,11,0.2)' }}
          >
            <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)' }}>
              <BarChart2 className="w-6 h-6" style={{ color: 'var(--status-warning)' }} />
            </div>
            <div>
              <p className="font-display font-bold text-base mb-1" style={{ color: 'var(--text-heading)' }}>
                Compare with LLM
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                See RAG inference vs Gemini/Groq suggestions side-by-side with per-HP agreement analysis
              </p>
            </div>
          </button>
          <button
            onClick={() => navigate(`/notebook/${id || 'demo'}`)}
            className="interactive glass-panel p-6 flex items-start gap-4 text-left transition-all group"
            style={{ border: '1px solid rgba(16,185,129,0.2)' }}
          >
            <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <Play className="w-6 h-6" style={{ color: 'var(--status-success)' }} />
            </div>
            <div>
              <p className="font-display font-bold text-base mb-1" style={{ color: 'var(--text-heading)' }}>
                Launch Notebook
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Open the generated training notebook in JupyterLab and run it right in your browser
              </p>
            </div>
          </button>
        </div>

        {/* ── Card 6: Audit Trail ── */}
        <div className="glass-panel overflow-hidden mb-8">
          <button
            className="interactive w-full flex items-center justify-between px-6 py-4 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onClick={() => setAuditOpen(!auditOpen)}
          >
            <span className="flex items-center gap-2 font-semibold text-sm">
              <FileText className="w-4 h-4" /> Full Pipeline Audit Trail
            </span>
            <motion.div animate={{ rotate: auditOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <ChevronDown className="w-4 h-4" />
            </motion.div>
          </button>
          <AnimatePresence>
            {auditOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="px-6 pb-6 font-mono text-xs space-y-1" style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '1rem' }}>
                  {liveAuditLog.map((line, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="font-bold w-6 flex-shrink-0" style={{ color: line.c }}>[{line.m}]</span>
                      <span style={{ color: 'var(--text-muted)' }}>{line.msg}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
