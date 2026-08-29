import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  ArrowRight, FileText, Search, Shield, AlertTriangle,
  CheckCircle2, BookOpen, Brain, Database, Cpu,
} from 'lucide-react';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: [0.25, 0.46, 0.45, 0.94] as any },
});

const modules = [
  {
    id: 'M1', name: 'PDF Analyzer', icon: FileText,
    color: '#8b5cf6',
    desc: 'Extracts text, tables, title, and abstract from an uploaded BERT paper. Uses regex patterns to identify explicitly reported hyperparameters.',
    tech: 'PyMuPDF, pdfplumber, regex',
  },
  {
    id: 'M2', name: 'Completeness Checker', icon: Search,
    color: '#06b6d4',
    desc: 'Computes an R-Score (Reproducibility Score) by checking which of the 12 standard hyperparameters are missing from the paper.',
    tech: 'Weighted checklist, R-Score formula',
  },
  {
    id: 'M3', name: 'FAISS Retrieval Engine', icon: Database,
    color: '#10b981',
    desc: 'Searches a 465-paper corpus using semantic vector similarity (384-dim sentence embeddings). Uses a 4-strategy cascade: Task+Model+Dataset → Task+Model → Task → Global.',
    tech: 'FAISS, Sentence-Transformers (all-MiniLM-L6-v2)',
  },
  {
    id: 'M4', name: 'Domain Constraints', icon: Shield,
    color: '#3b82f6',
    desc: 'Enforces BERT-specific domain rules. Example: if optimizer is Adam (not AdamW), weight decay must be 0. Prevents physically impossible configurations.',
    tech: 'Rule-based constraint engine',
  },
  {
    id: 'M5', name: 'Contradiction Detection', icon: AlertTriangle,
    color: '#f59e0b',
    desc: 'Identifies conflicting hyperparameter values across evidence papers. Flags outliers and disagreements for manual review.',
    tech: 'Statistical outlier detection, IQR analysis',
  },
  {
    id: 'M6', name: 'Range Validator', icon: CheckCircle2,
    color: '#10b981',
    desc: 'Self-critique: verifies all final values are within known BERT ranges (e.g., learning rate between 1e-6 and 1e-3). Auto-corrects out-of-range values.',
    tech: 'Range lookup table, auto-correction',
  },
  {
    id: 'M7', name: 'Notebook Generator', icon: BookOpen,
    color: '#8b5cf6',
    desc: 'Generates a ready-to-run Jupyter notebook with task-aware branching (token classification / NER with BIO-alignment vs sequence classification). Annotates every HP with confidence.',
    tech: 'nbformat, HuggingFace Transformers template',
  },
  {
    id: 'M8', name: 'Meta-Reasoning Agent', icon: Brain,
    color: '#ec4899',
    desc: 'Reviews confidence scores per HP. For low-confidence values, consults LLM (Gemini/Groq) as a second opinion. Boosts confidence when RAG and LLM agree. Logs every decision with reasoning.',
    tech: 'Adaptive agent, Gemini 2.0 Flash API, Groq API',
  },
];

export default function Methodology() {
  return (
    <div style={{ background: 'var(--bg-base)', minHeight: 'calc(100vh - 64px)' }}>
      <div className="mx-auto px-6 py-12" style={{ maxWidth: 1000 }}>

        {/* Header */}
        <motion.div {...fadeUp(0)} className="text-center mb-14">
          <h1 className="font-display font-bold text-4xl mb-4" style={{ color: 'var(--text-heading)' }}>
            How HyperBERT Works
          </h1>
          <p className="text-base mx-auto" style={{ color: 'var(--text-secondary)', maxWidth: 600, lineHeight: 1.7 }}>
            An 8-module pipeline that reads a BERT paper, finds what's missing,
            and infers every hyperparameter with full evidence trails.
          </p>
        </motion.div>

        {/* Problem Statement */}
        <motion.div {...fadeUp(0.1)} className="glass-panel p-8 mb-10">
          <h2 className="font-display font-bold text-xl mb-4 flex items-center gap-2" style={{ color: 'var(--text-heading)' }}>
            <AlertTriangle className="w-5 h-5" style={{ color: 'var(--status-warning)' }} />
            The Problem
          </h2>
          <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            <strong style={{ color: 'var(--text-primary)' }}>92% of BERT fine-tuning papers don't report all 12 standard hyperparameters</strong> (Dodge et al., 2019).
            This makes results unreproducible — a researcher cannot re-train the model without guessing critical values
            like learning rate, batch size, and warmup ratio. LLMs can suggest defaults, but their answers have{' '}
            <strong style={{ color: 'var(--status-danger)' }}>no citations, no evidence trails, and no confidence scores</strong>.
          </p>
          <p className="text-sm" style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            HyperBERT solves this by using{' '}
            <strong style={{ color: 'var(--accent-primary)' }}>Retrieval-Augmented Inference</strong> — finding similar papers in a 465-paper corpus
            and statistically inferring the missing values (achieving <strong>75.1% exact match accuracy</strong> in leave-one-out evaluation). Every decision is transparent, cited, and verifiable.
          </p>
        </motion.div>

        {/* Pipeline diagram */}
        <motion.div {...fadeUp(0.15)} className="mb-10">
          <h2 className="font-display font-bold text-xl mb-6 text-center" style={{ color: 'var(--text-heading)' }}>
            The 8-Module Pipeline
          </h2>
          <div className="space-y-4">
            {modules.map((mod, i) => (
              <motion.div
                key={mod.id}
                {...fadeUp(0.1 + i * 0.05)}
                className="glass-panel p-5 flex items-start gap-5 group interactive"
                style={{ borderLeft: `3px solid ${mod.color}` }}
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: `${mod.color}15`, border: `1px solid ${mod.color}30` }}>
                  <mod.icon className="w-6 h-6" style={{ color: mod.color }} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded"
                      style={{ background: `${mod.color}18`, color: mod.color }}>
                      {mod.id}
                    </span>
                    <h3 className="font-display font-bold text-base" style={{ color: 'var(--text-heading)' }}>
                      {mod.name}
                    </h3>
                  </div>
                  <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    {mod.desc}
                  </p>
                  <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    Tech: {mod.tech}
                  </p>
                </div>
                {i < modules.length - 1 && (
                  <div className="self-center flex-shrink-0">
                    <ArrowRight className="w-4 h-4" style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* RAG vs LLM */}
        <motion.div {...fadeUp(0.5)} className="glass-panel p-8 mb-10">
          <h2 className="font-display font-bold text-xl mb-5" style={{ color: 'var(--text-heading)' }}>
            Why RAG, Not Just an LLM?
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="rounded-xl p-5" style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <h4 className="font-bold text-sm mb-3 flex items-center gap-2" style={{ color: 'var(--status-success)' }}>
                <Database className="w-4 h-4" /> HyperBERT (RAG)
              </h4>
              <ul className="space-y-2 text-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                <li>✅ Every value cites specific papers</li>
                <li>✅ Confidence = similarity × agreement × support</li>
                <li>✅ Transparent reasoning trace (5-7 steps)</li>
                <li>✅ Domain constraints prevent invalid configs</li>
                <li>✅ Detects contradictions across evidence</li>
                <li>✅ Works offline (no API key needed)</li>
              </ul>
            </div>
            <div className="rounded-xl p-5" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.15)' }}>
              <h4 className="font-bold text-sm mb-3 flex items-center gap-2" style={{ color: 'var(--status-danger)' }}>
                <Cpu className="w-4 h-4" /> LLM-Only Approach
              </h4>
              <ul className="space-y-2 text-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                <li>❌ No citations — "trust me" answers</li>
                <li>❌ No confidence decomposition</li>
                <li>❌ No reasoning trace</li>
                <li>❌ May hallucinate invalid combinations</li>
                <li>❌ Cannot detect contradictions</li>
                <li>❌ Requires API key and internet</li>
              </ul>
            </div>
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div {...fadeUp(0.6)} className="text-center">
          <Link
            to="/upload"
            className="interactive inline-flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-white text-sm"
            style={{ background: 'var(--accent-gradient)', boxShadow: '0 4px 20px rgba(124,58,237,0.35)' }}
          >
            Try It Now <ArrowRight className="w-4 h-4" />
          </Link>
        </motion.div>
      </div>
    </div>
  );
}
