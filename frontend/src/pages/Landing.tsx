import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { UploadCloud, Search, DownloadCloud, ArrowRight, BarChart2 } from 'lucide-react';
import { getCorpusStats } from '@/lib/api';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay, ease: [0.25, 0.46, 0.45, 0.94] as any },
});

const defaultStats = [
  { value: '435', label: 'Papers Analyzed' },
  { value: '12', label: 'HP Parameters' },
  { value: '4', label: 'Academic Sources' },
  { value: '100%', label: 'Traceable Decisions' },
];

const steps = [
  {
    icon: UploadCloud,
    num: '01',
    title: 'Upload Your Paper',
    desc: 'Drag and drop any BERT fine-tuning PDF. We extract text, tables, and hyperparameters using precise regex pattern matching.',
    color: 'var(--accent-primary)',
  },
  {
    icon: Search,
    num: '02',
    title: 'Transparent Analysis',
    desc: 'See exactly what was found, what\'s missing, and how each value was inferred. Every decision has a full evidence trail with citations.',
    color: 'var(--accent-secondary)',
  },
  {
    icon: DownloadCloud,
    num: '03',
    title: 'Reproduce With Confidence',
    desc: 'Download a ready-to-run Jupyter notebook, Python script, or YAML config — annotated with confidence scores.',
    color: 'var(--accent-tertiary)',
  },
];

export default function Landing() {
  const [stats, setStats] = useState(defaultStats);

  useEffect(() => {
    getCorpusStats()
      .then(data => {
        if (data?.total_papers) {
          setStats([
            { value: String(data.total_papers), label: 'Papers Analyzed' },
            { value: '12', label: 'HP Parameters' },
            { value: String(data.task_distribution?.length || 4), label: 'Task Categories' },
            { value: '100%', label: 'Traceable Decisions' },
          ]);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div
      className="relative overflow-hidden"
      style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}
    >
      {/* Animated background orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute w-[650px] h-[650px] rounded-full animate-blob"
          style={{
            top: '2%', left: '10%',
            background: 'radial-gradient(circle, rgba(99,102,241,0.14) 0%, rgba(59,130,246,0.06) 45%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        <div
          className="absolute w-[550px] h-[550px] rounded-full animate-blob animation-delay-2000"
          style={{
            top: '18%', right: '5%',
            background: 'radial-gradient(circle, rgba(6,182,212,0.12) 0%, rgba(99,102,241,0.05) 50%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        <div
          className="absolute w-[480px] h-[480px] rounded-full animate-blob animation-delay-4000"
          style={{
            bottom: '8%', left: '35%',
            background: 'radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
      </div>

      {/* Hero */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center px-6 pt-24 pb-20">
        {/* Badge */}
        <motion.div {...fadeUp(0)} className="mb-8">
          <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium shadow-sm"
            style={{
              background: 'var(--bg-surface-2)',
              border: '1px solid var(--border-highlight)',
              color: 'var(--text-secondary)',
            }}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ background: 'var(--status-success)', boxShadow: '0 0 8px var(--status-success)' }}
            />
            Backed by 435 Research Papers
          </span>
        </motion.div>

        {/* Title */}
        <motion.h1 {...fadeUp(0.1)} className="font-display font-bold leading-tight mb-6"
          style={{ fontSize: 'clamp(2.5rem, 6vw, 4.5rem)', maxWidth: 900 }}
        >
          Reproduce Any BERT Paper
          <br />
          <span className="text-gradient">With Full Transparency</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p {...fadeUp(0.2)}
          style={{ fontSize: '1.125rem', color: 'var(--text-secondary)', maxWidth: 600, marginBottom: '2.5rem', lineHeight: 1.7 }}
        >
          Upload a BERT fine-tuning paper. We extract every hyperparameter, infer what's missing from 435 similar papers, and show you exactly why — with full evidence trails and confidence scores.
        </motion.p>

        {/* CTAs */}
        <motion.div {...fadeUp(0.3)} className="flex flex-col sm:flex-row items-center gap-4">
          <Link
            to="/upload"
            className="group interactive flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200"
            style={{
              background: 'var(--accent-gradient)',
              boxShadow: '0 4px 18px -2px rgba(99,102,241,0.45)',
            }}
            onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 6px 24px -2px rgba(99,102,241,0.65)')}
            onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 4px 18px -2px rgba(99,102,241,0.45)')}
          >
            Upload a Paper
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link
            to="/corpus"
            className="interactive px-8 py-4 rounded-xl font-semibold transition-all duration-200"
            style={{
              border: '1px solid var(--border-highlight)',
              color: 'var(--text-primary)',
              background: 'transparent',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-surface-2)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            Explore the Corpus
          </Link>
          <Link
            to="/evaluation"
            className="interactive flex items-center gap-2 px-6 py-4 rounded-xl font-semibold transition-all duration-200"
            style={{
              border: '1px solid var(--border-highlight)',
              color: 'var(--text-secondary)',
              background: 'transparent',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-surface-2)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <BarChart2 className="w-4 h-4" /> View Evaluation
          </Link>
        </motion.div>
      </div>

      {/* Stats bar */}
      <motion.div
        {...fadeUp(0.5)}
        className="relative z-10 mx-auto px-6 mb-20"
        style={{ maxWidth: 900 }}
      >
        <div
          className="grid grid-cols-2 md:grid-cols-4 rounded-2xl overflow-hidden"
          style={{ background: 'var(--bg-surface-1)', border: '1px solid var(--border-glass)', backdropFilter: 'blur(12px)' }}
        >
          {stats.map((stat, i) => (
            <div
              key={stat.label}
              className="flex flex-col items-center py-8 px-4 text-center"
              style={{
                borderRight: i < stats.length - 1 ? '1px solid var(--border-glass)' : 'none',
              }}
            >
              <span
                className="font-display font-bold text-3xl mb-1 text-gradient"
              >
                {stat.value}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                {stat.label}
              </span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* How it works */}
      <div className="relative z-10 px-6 pb-32" style={{ maxWidth: 1100, margin: '0 auto' }}>
        <motion.h2 {...fadeUp(0.4)} className="text-center font-display font-semibold text-2xl mb-12">
          How It Works
        </motion.h2>
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <motion.div
              key={step.num}
              {...fadeUp(0.5 + i * 0.1)}
              className="glass-card p-8 group interactive relative overflow-hidden"
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
            >
              <div
                className="absolute top-0 left-0 w-full h-0.5"
                style={{ background: `linear-gradient(90deg, ${step.color}, transparent)` }}
              />
              <div
                className="inline-flex px-2 py-0.5 rounded text-xs font-mono font-bold mb-6"
                style={{ color: step.color, background: `${step.color}18` }}
              >
                {step.num}
              </div>
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center mb-5"
                style={{ background: `${step.color}18`, border: `1px solid ${step.color}30` }}
              >
                <step.icon className="w-6 h-6" style={{ color: step.color }} />
              </div>
              <h3 className="font-display font-semibold text-lg mb-3">{step.title}</h3>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.65, fontSize: '0.9rem' }}>{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
