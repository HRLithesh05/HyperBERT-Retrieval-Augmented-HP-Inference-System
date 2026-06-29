import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { Database, UploadCloud, Zap, BarChart2, Brain } from 'lucide-react';

export function NavBar() {
  const location = useLocation();

  const navLink = (to: string, label: string, Icon: React.FC<{ className?: string }>) => {
    const active = location.pathname === to || location.pathname.startsWith(to + '/');
    return (
      <Link
        to={to}
        className="flex items-center gap-1.5 text-sm font-medium transition-colors interactive"
        style={{ color: active ? 'var(--accent-primary)' : 'var(--text-secondary)' }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
        onMouseLeave={e => (e.currentTarget.style.color = active ? 'var(--accent-primary)' : 'var(--text-secondary)')}
      >
        <Icon className="w-4 h-4" />
        {label}
      </Link>
    );
  };

  return (
    <header
      className="sticky top-0 z-50 w-full"
      style={{
        background: 'var(--bg-surface-1)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border-glass)',
      }}
    >
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 interactive">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: 'var(--accent-gradient)' }}
            >
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight text-gradient">
              HyperBERT
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-6">
            {navLink('/upload', 'Upload', UploadCloud)}
            {navLink('/corpus', 'Corpus', Database)}
            {navLink('/evaluation', 'Evaluation', BarChart2)}
            {navLink('/methodology', 'About', Brain)}
          </nav>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
