import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { Database, UploadCloud, Zap, BarChart2, Brain, FileText, Clock, LogIn, LogOut, User } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';
import { isAuthConfigured } from '@/lib/auth0-config';

// Conditionally import useAuth0 — only when configured
let useAuth0Hook: any = null;
try {
  const mod = await import('@auth0/auth0-react');
  useAuth0Hook = mod.useAuth0;
} catch {
  // Auth0 not installed — that's fine
}

function AuthButtons() {
  if (!isAuthConfigured || !useAuth0Hook) return null;

  const { isAuthenticated, loginWithRedirect, logout, user } = useAuth0Hook();

  if (isAuthenticated) {
    return (
      <div className="flex items-center gap-2">
        <Link to="/history" className="interactive flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium"
          style={{ color: 'var(--text-secondary)' }}>
          <Clock className="w-3.5 h-3.5" /> History
        </Link>
        <div className="flex items-center gap-2 px-2 py-1 rounded-lg" style={{ background: 'var(--bg-surface-2)' }}>
          {user?.picture ? (
            <img src={user.picture} alt="" className="w-5 h-5 rounded-full" />
          ) : (
            <User className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          )}
          <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
            {user?.name?.split(' ')[0] || 'User'}
          </span>
        </div>
        <button
          onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
          className="interactive flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-medium"
          style={{ color: 'var(--text-muted)' }}
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => loginWithRedirect()}
      className="interactive flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white"
      style={{ background: 'var(--accent-gradient)' }}
    >
      <LogIn className="w-3.5 h-3.5" /> Sign In
    </button>
  );
}

export function NavBar() {
  const location = useLocation();
  const { hasRealSession, sessionId } = useSession();

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
            {hasRealSession && navLink(`/results/${sessionId}`, 'Results', FileText)}
            {navLink('/corpus', 'Corpus', Database)}
            {navLink('/evaluation', 'Evaluation', BarChart2)}
            {navLink('/methodology', 'About', Brain)}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <AuthButtons />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
