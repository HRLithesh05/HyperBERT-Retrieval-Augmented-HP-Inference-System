import { type ReactNode } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Lock, LogIn } from 'lucide-react';
import { isAuthConfigured } from '@/lib/auth0-config';

interface AuthGateProps {
  children: ReactNode;
  /** Feature name shown in the gate message */
  feature: string;
  /** If true, always shows the gate (e.g., for analysis limit) */
  forceGate?: boolean;
}

/**
 * Wraps protected features with an auth gate overlay.
 * When Auth0 is not configured, it passes through (dev mode).
 * When Auth0 IS configured but user is not authenticated, shows sign-in prompt.
 */
export default function AuthGate({ children, feature, forceGate = false }: AuthGateProps) {
  // If Auth0 is not configured, allow everything (dev/demo mode)
  if (!isAuthConfigured) {
    return <>{children}</>;
  }

  return <AuthGateInner feature={feature} forceGate={forceGate}>{children}</AuthGateInner>;
}

function AuthGateInner({ children, feature, forceGate }: AuthGateProps) {
  const { isAuthenticated, loginWithRedirect, isLoading } = useAuth0();

  // If authenticated and not forced, show children
  if (isAuthenticated && !forceGate) {
    return <>{children}</>;
  }

  // If loading, show children with slight opacity
  if (isLoading) {
    return <div style={{ opacity: 0.5 }}>{children}</div>;
  }

  return (
    <div style={{ position: 'relative' }}>
      {/* Blurred content behind the gate */}
      <div style={{ filter: 'blur(6px)', pointerEvents: 'none', opacity: 0.4 }}>
        {children}
      </div>

      {/* Gate overlay */}
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="text-center max-w-sm p-8 rounded-2xl"
            style={{
              background: 'var(--bg-surface-1)',
              border: '1px solid var(--border-glass)',
              backdropFilter: 'blur(20px)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            }}
          >
            <div className="w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)' }}>
              <Lock className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
            </div>
            <h3 className="font-display font-bold text-lg mb-2" style={{ color: 'var(--text-heading)' }}>
              Sign in Required
            </h3>
            <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
              {feature} requires a free HyperBERT account. Sign in with Google or GitHub to continue.
            </p>
            <button
              onClick={() => loginWithRedirect()}
              className="interactive inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm w-full justify-center"
              style={{ background: 'var(--accent-gradient)', boxShadow: '0 4px 20px rgba(124,58,237,0.35)' }}
            >
              <LogIn className="w-4 h-4" /> Sign In / Sign Up
            </button>
            <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>
              Free forever · No credit card required
            </p>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
