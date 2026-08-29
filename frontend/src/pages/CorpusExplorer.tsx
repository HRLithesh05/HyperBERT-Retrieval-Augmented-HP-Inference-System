import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, BookOpen, ChevronDown, ChevronUp, BarChart2, X, Loader2, AlertTriangle } from 'lucide-react';
import { getCorpusPapers, getCorpusStats } from '@/lib/api';

/* ── Fallback demo data (when backend / MongoDB unavailable) ── */
const demoStats = {
  total_papers: 465,
  task_distribution: [
    { task: 'Text Classification', count: 290 },
    { task: 'Relation Extraction', count: 60 },
    { task: 'NER', count: 51 },
    { task: 'Question Answering', count: 42 },
    { task: 'Natural Language Inference', count: 16 },
    { task: 'Semantic Similarity', count: 6 },
  ],
  model_distribution: [
    { model: 'bert-base-uncased', count: 329 },
    { model: 'roberta', count: 80 },
    { model: 'albert', count: 31 },
    { model: 'biobert', count: 9 },
    { model: 'distilbert', count: 7 },
    { model: 'scibert', count: 7 },
  ],
  hp_coverage: {
    learning_rate: { pct: 45 },
    batch_size: { pct: 42 },
    epochs: { pct: 38 },
    optimizer: { pct: 31 },
    weight_decay: { pct: 18 },
    max_seq_length: { pct: 22 },
    dropout: { pct: 15 },
    scheduler: { pct: 12 },
    warmup_steps: { pct: 10 },
    gradient_clipping: { pct: 6 },
    seed: { pct: 8 },
    warmup_ratio: { pct: 7 },
  },
};

const PER_PAGE = 12;

interface Paper {
  title: string;
  task: string;
  model: string;
  source: string;
  year?: number;
  rscore: number;
  hyperparameters?: Record<string, any>;
}

export default function CorpusExplorer() {
  const [query, setQuery] = useState('');
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [chartsOpen, setChartsOpen] = useState(true);

  // API state
  const [papers, setPapers] = useState<Paper[]>([]);
  const [totalPapers, setTotalPapers] = useState(0);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [searchTimeout, setSearchTimeout] = useState<ReturnType<typeof setTimeout> | null>(null);

  // Fetch corpus stats on mount
  useEffect(() => {
    getCorpusStats()
      .then(setStats)
      .catch(() => setStats(demoStats));
  }, []);

  // Fetch papers (debounced when query changes)
  const fetchPapers = useCallback(async () => {
    setLoading(true);
    setApiError(null);
    try {
      const result = await getCorpusPapers({
        q: query || undefined,
        task: selectedTasks[0] || undefined,
        model: selectedModels[0] || undefined,
        page,
        per_page: PER_PAGE,
      });
      setPapers(result.papers || []);
      setTotalPapers(result.total || 0);
    } catch (e: any) {
      setApiError(e.message || 'Could not connect to backend');
      setPapers([]);
      setTotalPapers(0);
    } finally {
      setLoading(false);
    }
  }, [query, selectedTasks, selectedModels, page]);

  useEffect(() => {
    if (searchTimeout) clearTimeout(searchTimeout);
    const t = setTimeout(fetchPapers, 350);
    setSearchTimeout(t);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchPapers]);

  const toggleFilter = (arr: string[], val: string, setter: (v: string[]) => void) => {
    setter(arr.includes(val) ? arr.filter(x => x !== val) : [...arr, val]);
    setPage(0);
  };

  const liveStats = stats || demoStats;
  const taskDistData = liveStats.task_distribution || demoStats.task_distribution;
  const hpCoverageData = liveStats.hp_coverage || demoStats.hp_coverage;
  const totalStat = liveStats.total_papers || demoStats.total_papers;
  const taskNames = taskDistData.map((t: any) => t.task || t.name).slice(0, 6);
  const modelNames = (liveStats.model_distribution || demoStats.model_distribution).map((m: any) => m.model).slice(0, 8);
  const pages = Math.ceil(totalPapers / PER_PAGE);

  const taskColors = ['#8b5cf6', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

  const CheckBox = ({ label, active, onToggle }: { label: string; active: boolean; onToggle: () => void }) => (
    <label
      className="interactive flex items-center gap-2 text-sm py-1 cursor-pointer"
      style={{ color: active ? 'var(--text-primary)' : 'var(--text-secondary)' }}
    >
      <div
        className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0 transition-all"
        style={{
          background: active ? 'var(--accent-primary)' : 'var(--bg-surface-3)',
          border: `1px solid ${active ? 'var(--accent-primary)' : 'var(--border-highlight)'}`,
        }}
        onClick={onToggle}
      >
        {active && <span className="text-white text-[10px] font-bold">✓</span>}
      </div>
      {label}
    </label>
  );

  return (
    <div style={{ background: 'var(--bg-base)', minHeight: 'calc(100vh - 64px)' }}>
      <div className="mx-auto px-4 py-8 flex gap-6" style={{ maxWidth: 1400 }}>

        {/* ── Sidebar ── */}
        <aside className="w-64 flex-shrink-0 hidden lg:block">
          <div className="sticky top-24 space-y-5">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search papers…"
                value={query}
                onChange={e => { setQuery(e.target.value); setPage(0); }}
                className="interactive w-full pl-9 pr-4 py-2 rounded-xl text-sm outline-none transition-all"
                style={{
                  background: 'var(--bg-surface-2)',
                  border: '1px solid var(--border-glass)',
                  color: 'var(--text-primary)',
                }}
              />
            </div>

            {/* Filter panels */}
            <div className="glass-panel p-4 space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase mb-3 flex items-center gap-2" style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
                  <Filter className="w-3 h-3" /> Task
                </p>
                {taskNames.map((t: string) => (
                  <CheckBox key={t} label={t}
                    active={selectedTasks.includes(t)} onToggle={() => toggleFilter(selectedTasks, t, setSelectedTasks)} />
                ))}
              </div>
              <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '1rem' }}>
                <p className="text-xs font-semibold uppercase mb-3" style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}>Model</p>
                {modelNames.map((m: string) => (
                  <CheckBox key={m} label={m} active={selectedModels.includes(m)}
                    onToggle={() => toggleFilter(selectedModels, m, setSelectedModels)} />
                ))}
              </div>
              {(selectedTasks.length > 0 || selectedModels.length > 0) && (
                <button
                  className="interactive w-full flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold"
                  style={{ background: 'var(--bg-surface-3)', color: 'var(--text-secondary)', border: '1px solid var(--border-glass)' }}
                  onClick={() => { setSelectedTasks([]); setSelectedModels([]); }}
                >
                  <X className="w-3 h-3" /> Clear Filters
                </button>
              )}
            </div>

            {/* Charts */}
            <div className="glass-panel overflow-hidden">
              <button
                className="interactive w-full flex items-center justify-between px-4 py-3 text-xs font-semibold uppercase"
                style={{ color: 'var(--text-secondary)', letterSpacing: '0.05em', borderBottom: chartsOpen ? '1px solid var(--border-glass)' : 'none' }}
                onClick={() => setChartsOpen(!chartsOpen)}
              >
                <span className="flex items-center gap-2"><BarChart2 className="w-3 h-3" /> Corpus Stats</span>
                {chartsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
              <AnimatePresence>
                {chartsOpen && (
                  <motion.div
                    initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
                    transition={{ duration: 0.25 }} className="overflow-hidden"
                  >
                    <div className="p-4 space-y-6">
                      <div>
                        <p className="text-[10px] uppercase font-semibold mb-2" style={{ color: 'var(--text-muted)' }}>Task Distribution</p>
                        {taskDistData.slice(0, 6).map((t: any, i: number) => (
                          <div key={t.task || t.name} className="flex items-center gap-2 mb-1.5">
                            <div className="w-14 text-[10px] font-medium text-right flex-shrink-0 truncate" style={{ color: 'var(--text-secondary)' }}>{t.task || t.name}</div>
                            <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-3)' }}>
                              <motion.div
                                initial={{ width: 0 }} animate={{ width: `${(t.count / totalStat) * 100}%` }}
                                transition={{ duration: 0.8, ease: 'easeOut' }}
                                style={{ height: '100%', background: taskColors[i % taskColors.length], borderRadius: 9999 }}
                              />
                            </div>
                            <span className="text-[10px] font-mono w-6 flex-shrink-0" style={{ color: 'var(--text-muted)' }}>{t.count}</span>
                          </div>
                        ))}
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-semibold mb-2" style={{ color: 'var(--text-muted)' }}>HP Coverage</p>
                        {Object.entries(hpCoverageData).slice(0, 8).map(([name, data]: [string, any]) => (
                          <div key={name} className="flex items-center gap-2 mb-1.5">
                            <div className="w-14 text-[10px] text-right flex-shrink-0 truncate" style={{ color: 'var(--text-secondary)' }}>{name}</div>
                            <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-3)' }}>
                              <motion.div
                                initial={{ width: 0 }} animate={{ width: `${data.pct}%` }}
                                transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
                                style={{ height: '100%', background: 'var(--accent-primary)', borderRadius: 9999 }}
                              />
                            </div>
                            <span className="text-[10px] font-mono w-7 flex-shrink-0" style={{ color: 'var(--text-muted)' }}>{data.pct}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </aside>

        {/* ── Main Content ── */}
        <main className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
            <div>
              <h1 className="font-display font-bold text-3xl" style={{ color: 'var(--text-heading)' }}>Corpus Explorer</h1>
              <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                Browse the {totalStat}-paper BERT knowledge base
              </p>
            </div>
            <span
              className="px-3 py-1 rounded-full text-sm font-medium"
              style={{ background: 'rgba(139,92,246,0.12)', color: 'var(--accent-primary)', border: '1px solid rgba(139,92,246,0.25)' }}
            >
              {totalPapers > 0 ? `${totalPapers} papers` : `${totalStat} papers`}
            </span>
          </div>

          {/* Error Banner */}
          {apiError && (
            <div className="mb-6 px-4 py-3 rounded-xl text-sm flex items-center gap-2"
              style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', color: 'var(--status-warning)' }}>
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              Backend unavailable: {apiError}. Make sure MongoDB and the Flask server are running.
            </div>
          )}

          {/* Loading Skeleton */}
          {loading && (
            <div className="flex items-center justify-center py-20 gap-3" style={{ color: 'var(--text-muted)' }}>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading papers…</span>
            </div>
          )}

          {/* Paper cards */}
          {!loading && (
            <div className="space-y-4">
              <AnimatePresence mode="popLayout">
                {papers.map((paper, i) => {
                  const isOpen = expandedIdx === i;
                  const hps = paper.hyperparameters || {};
                  return (
                    <motion.div
                      key={`${paper.title}-${i}`}
                      layout
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.97 }}
                      transition={{ duration: 0.25, delay: i * 0.04 }}
                      className="glass-card overflow-hidden"
                    >
                      <div className="p-5">
                        <div className="flex items-start gap-4">
                          <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.2)' }}
                          >
                            <BookOpen className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-base mb-2 leading-snug" style={{ color: 'var(--text-primary)' }}>
                              {paper.title}
                            </h3>
                            <div className="flex flex-wrap gap-2 mb-3">
                              {[
                                { label: paper.task || 'Unknown', color: 'var(--accent-secondary)' },
                                { label: paper.model || 'BERT', color: 'var(--accent-primary)' },
                                { label: paper.source || 'Unknown', color: 'var(--text-muted)' },
                                ...(paper.year ? [{ label: String(paper.year), color: 'var(--accent-tertiary)' }] : []),
                              ].map(b => (
                                <span key={b.label} className="px-2 py-0.5 rounded text-xs font-semibold"
                                  style={{ background: `${b.color}18`, color: b.color, border: `1px solid ${b.color}25` }}>
                                  {b.label}
                                </span>
                              ))}
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>R-Score</span>
                              <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-surface-3)' }}>
                                <div style={{
                                  width: `${(paper.rscore || 0) * 100}%`, height: '100%',
                                  background: (paper.rscore || 0) > 0.5 ? 'var(--status-success)' : (paper.rscore || 0) > 0.25 ? 'var(--status-warning)' : 'var(--status-danger)',
                                  borderRadius: 9999,
                                }} />
                              </div>
                              <span className="text-xs font-mono font-semibold w-10" style={{ color: 'var(--text-secondary)' }}>
                                {(paper.rscore || 0).toFixed(2)}
                              </span>
                            </div>
                          </div>
                          <button
                            className="interactive flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium flex-shrink-0 transition-all"
                            style={{
                              background: isOpen ? 'var(--accent-primary)' : 'var(--bg-surface-3)',
                              color: isOpen ? 'white' : 'var(--text-secondary)',
                              border: '1px solid var(--border-glass)',
                            }}
                            onClick={() => setExpandedIdx(isOpen ? null : i)}
                          >
                            {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            {isOpen ? 'Collapse' : 'View HPs'}
                          </button>
                        </div>

                        {/* Expanded HPs */}
                        <AnimatePresence>
                          {isOpen && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.25 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--border-glass)' }}>
                                <p className="text-xs font-semibold uppercase mb-3" style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
                                  Extracted Hyperparameters
                                </p>
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                                  {Object.entries(hps).map(([k, v]) => (
                                    <div key={k} className="rounded-lg p-3" style={{ background: 'var(--bg-surface-3)' }}>
                                      <p className="text-[10px] uppercase font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>{k}</p>
                                      <p className="font-mono font-bold text-sm" style={{ color: v != null ? 'var(--status-success)' : 'var(--text-muted)' }}>
                                        {v != null ? String(v) : '—'}
                                      </p>
                                    </div>
                                  ))}
                                  {Object.keys(hps).length === 0 && (
                                    <p className="text-xs col-span-full" style={{ color: 'var(--text-muted)' }}>
                                      No hyperparameters extracted from this paper.
                                    </p>
                                  )}
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              {/* Empty state */}
              {!loading && papers.length === 0 && !apiError && (
                <div className="text-center py-20">
                  <BookOpen className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                  <p className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>No papers found</p>
                  <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Try adjusting your search or filters.</p>
                </div>
              )}
            </div>
          )}

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                className="interactive px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: 'var(--bg-surface-2)', color: page === 0 ? 'var(--text-muted)' : 'var(--text-primary)', border: '1px solid var(--border-glass)' }}
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                ← Previous
              </button>
              <span className="text-sm px-4" style={{ color: 'var(--text-secondary)' }}>
                Page {page + 1} of {pages}
              </span>
              <button
                className="interactive px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{ background: 'var(--bg-surface-2)', color: page >= pages - 1 ? 'var(--text-muted)' : 'var(--text-primary)', border: '1px solid var(--border-glass)' }}
                onClick={() => setPage(p => Math.min(pages - 1, p + 1))}
                disabled={page >= pages - 1}
              >
                Next →
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
