/**
 * AuthGuard — Wraps gated features (notebook, history).
 * Shows a sign-in prompt for unauthenticated users.
 * Passes through if Auth0 isn't configured (dev mode).
 */
import { type ReactNode } from 'react';
import { useAuth, isAuthConfigured } from '@/contexts/AuthContext';
import { Lock, LogIn } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  children: ReactNode;
  feature?: string;
}

export default function AuthGuard({ children, feature = 'this feature' }: Props) {
  const { isAuthenticated, isLoading, loginWithGoogle } = useAuth();

  // If Auth0 isn't configured, allow everything (dev mode)
  if (!isAuthConfigured()) {
    return <>{children}</>;
  }

  // Still loading auth state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <div className="animate-spin w-8 h-8 rounded-full border-2 border-t-transparent"
          style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  // User is authenticated — render children
  if (isAuthenticated) {
    return <>{children}</>;
  }

  // Not authenticated — show sign-in prompt
  return (
    <div className="flex items-center justify-center px-4" style={{ minHeight: 'calc(100vh - 64px)', background: 'var(--bg-base)' }}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-10 max-w-md w-full text-center"
      >
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
          style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
          <Lock className="w-8 h-8" style={{ color: 'var(--accent-primary)' }} />
        </div>

        <h2 className="font-display font-bold text-2xl mb-3" style={{ color: 'var(--text-heading)' }}>
          Sign In Required
        </h2>
        <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
          Access to {feature} requires a free account. Sign in with Google to continue.
        </p>

        <button
          onClick={loginWithGoogle}
          className="interactive inline-flex items-center gap-3 px-6 py-3 rounded-xl text-sm font-semibold w-full justify-center transition-all"
          style={{
            background: 'var(--accent-gradient)',
            color: 'white',
          }}
        >
          <LogIn className="w-5 h-5" />
          Continue with Google
        </button>

        <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
          Free forever • No credit card required
        </p>
      </motion.div>
    </div>
  );
}
