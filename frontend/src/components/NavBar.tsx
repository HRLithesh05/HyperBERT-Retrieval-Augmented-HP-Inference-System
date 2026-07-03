import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { Database, UploadCloud, Zap, BarChart2, Brain, LogIn, LogOut, User } from 'lucide-react';
import { useAuth, isAuthConfigured } from '@/contexts/AuthContext';

export function NavBar() {
  const location = useLocation();
  const { user, isAuthenticated, loginWithGoogle, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

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
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {isAuthConfigured() && (
            <>
              {isAuthenticated && user ? (
                <div className="relative">
                  <button
                    onClick={() => setMenuOpen(!menuOpen)}
                    className="interactive flex items-center gap-2 px-2 py-1 rounded-xl transition-all"
                    style={{ border: '1px solid var(--border-glass)' }}
                  >
                    {user.picture ? (
                      <img src={user.picture} alt="" className="w-7 h-7 rounded-full" referrerPolicy="no-referrer" />
                    ) : (
                      <div className="w-7 h-7 rounded-full flex items-center justify-center"
                        style={{ background: 'var(--accent-gradient)' }}>
                        <User className="w-4 h-4 text-white" />
                      </div>
                    )}
                    <span className="text-xs font-medium hidden sm:block" style={{ color: 'var(--text-primary)', maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {user.given_name || user.name?.split(' ')[0] || 'User'}
                    </span>
                  </button>
                  {menuOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                      <div className="absolute right-0 top-full mt-2 w-52 py-2 rounded-xl shadow-lg z-50"
                        style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-glass)' }}>
                        <div className="px-3 py-2 text-xs" style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-glass)' }}>
                          <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{user.name}</p>
                          <p className="mt-0.5">{user.email}</p>
                        </div>
                        <button
                          onClick={() => { logout(); setMenuOpen(false); }}
                          className="interactive w-full px-3 py-2 text-left flex items-center gap-2 text-xs font-medium hover:opacity-80"
                          style={{ color: 'var(--status-danger)' }}
                        >
                          <LogOut className="w-3.5 h-3.5" /> Sign Out
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <button
                  onClick={loginWithGoogle}
                  className="interactive flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all"
                  style={{ background: 'var(--accent-gradient)', color: 'white' }}
                >
                  <LogIn className="w-3.5 h-3.5" /> Sign In
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}
