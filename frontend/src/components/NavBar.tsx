import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { Database, UploadCloud, BarChart2, Brain, LogIn, LogOut, User, FileText } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useSession } from '@/contexts/SessionContext';

export function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, loginWithGoogle, logout } = useAuth();
  const { sessionId, clearSession } = useSession();

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

  // Session-aware nav links — click Results/Notebook/Compare using the active session
  const sessionLink = (basePath: string, label: string, Icon: React.FC<{ className?: string }>) => {
    const path = sessionId ? `${basePath}/${sessionId}` : basePath;
    const active = location.pathname.startsWith(basePath);
    return (
      <Link
        to={path}
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
          <Link to="/" className="flex items-center gap-2.5 interactive group">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-300 group-hover:scale-105"
              style={{
                background: 'var(--accent-gradient)',
                boxShadow: '0 0 16px -2px rgba(99,102,241,0.45)',
              }}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                <rect x="4" y="4" width="3.5" height="16" rx="1.75" fill="white" />
                <rect x="16.5" y="4" width="3.5" height="16" rx="1.75" fill="white" />
                <rect x="6" y="10" width="12" height="4" rx="1.5" fill="white" />
                <circle cx="12" cy="12" r="1.5" fill="#090d16" />
              </svg>
            </div>
            <span className="font-display font-bold text-xl tracking-tight text-gradient">
              HyperBERT
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-6">
            {navLink('/upload', 'Upload', UploadCloud)}
            {/* Results link auto-attaches session ID if available */}
            {sessionId && sessionLink('/results', 'Results', FileText)}
            {navLink('/corpus', 'Corpus', Database)}
            {navLink('/evaluation', 'Evaluation', BarChart2)}
            {navLink('/methodology', 'About', Brain)}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* Active session indicator */}
          {sessionId && (
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-lg"
              style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--status-success)' }} />
              <span className="text-[10px] font-medium" style={{ color: 'var(--status-success)' }}>Session Active</span>
              <button onClick={() => { clearSession(); navigate('/upload'); }}
                className="text-[10px] interactive px-1 rounded"
                style={{ color: 'var(--text-muted)' }}
                title="Clear session and start new analysis">✕</button>
            </div>
          )}

          <ThemeToggle />

          {/* Auth section */}
          {!isLoading && (
            isAuthenticated ? (
              <div className="flex items-center gap-2">
                {user?.picture ? (
                  <img src={user.picture} alt="" className="w-7 h-7 rounded-full" referrerPolicy="no-referrer" crossOrigin="anonymous" style={{ border: '2px solid var(--accent-primary)' }} />
                ) : (
                  <div className="w-7 h-7 rounded-full flex items-center justify-center"
                    style={{ background: 'var(--accent-primary)', color: 'white' }}>
                    <User className="w-3.5 h-3.5" />
                  </div>
                )}
                <span className="text-xs font-medium hidden sm:block" style={{ color: 'var(--text-secondary)', maxWidth: 100 }}>
                  {user?.name?.split(' ')[0] || 'User'}
                </span>
                <button onClick={logout} className="interactive p-1.5 rounded-lg transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                  title="Sign out">
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={loginWithGoogle}
                className="interactive flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all"
                style={{
                  background: 'rgba(139,92,246,0.08)',
                  border: '1px solid rgba(139,92,246,0.25)',
                  color: 'var(--accent-primary)',
                }}
              >
                <LogIn className="w-3.5 h-3.5" /> Sign In
              </button>
            )
          )}
        </div>
      </div>
    </header>
  );
}
