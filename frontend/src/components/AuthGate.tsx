/**
 * AuthGate — A glass-morphism sign-in modal and guard component.
 * 
 * Usage:
 *   <AuthGate feature="notebook">
 *     <NotebookViewer />      ← only renders if authenticated
 *   </AuthGate>
 * 
 * Or as a standalone modal:
 *   <SignInModal open={showModal} onClose={() => setShowModal(false)} reason="launch notebook" />
 */
import { motion, AnimatePresence } from 'framer-motion';
import { LogIn, X, Shield, Sparkles } from 'lucide-react';
import { useAuth, GUEST_PAPER_LIMIT } from '@/contexts/AuthContext';
import { type ReactNode } from 'react';

/* ─── Sign-In Modal ─────────────────────────────────────────── */
export function SignInModal({ open, onClose, reason }: {
  open: boolean;
  onClose: () => void;
  reason?: string;
}) {
  const { loginWithGoogle, loginWithPopup, remainingFree, isAuthenticated } = useAuth();

  if (isAuthenticated || !open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ backdropFilter: 'blur(12px)', background: 'rgba(0,0,0,0.6)' }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.92, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.92, opacity: 0 }}
          transition={{ type: 'spring', duration: 0.4, bounce: 0.2 }}
          className="glass-panel relative w-full max-w-md mx-4 p-8"
          style={{ border: '1px solid var(--border-highlight)' }}
          onClick={e => e.stopPropagation()}
        >
          {/* Close button */}
          <button onClick={onClose} className="absolute top-4 right-4 interactive"
            style={{ color: 'var(--text-muted)' }}>
            <X className="w-5 h-5" />
          </button>

          {/* Icon */}
          <div className="flex justify-center mb-5">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.25)' }}>
              <Shield className="w-8 h-8" style={{ color: 'var(--accent-primary)' }} />
            </div>
          </div>

          {/* Title */}
          <h2 className="font-display font-bold text-xl text-center mb-2"
            style={{ color: 'var(--text-heading)' }}>
            Sign in to continue
          </h2>
          <p className="text-sm text-center mb-6" style={{ color: 'var(--text-secondary)' }}>
            {reason
              ? `Sign in is required to ${reason}.`
              : `You've used ${GUEST_PAPER_LIMIT - remainingFree} of ${GUEST_PAPER_LIMIT} free analyses.`}
          </p>

          {/* Benefits */}
          <div className="rounded-xl p-4 mb-6" style={{ background: 'var(--bg-surface-3)' }}>
            <p className="text-xs font-semibold uppercase mb-2" style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
              <Sparkles className="w-3 h-3 inline-block mr-1" /> With an account you get
            </p>
            <ul className="space-y-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
              <li>✓ Unlimited paper analyses</li>
              <li>✓ Launch & run Jupyter notebooks</li>
              <li>✓ View analysis history</li>
              <li>✓ Export all configurations</li>
            </ul>
          </div>

          {/* Google Sign-In */}
          <button
            onClick={loginWithGoogle}
            className="interactive w-full flex items-center justify-center gap-3 py-3 rounded-xl font-semibold text-sm mb-3 transition-all"
            style={{
              background: 'white', color: '#333',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>

          {/* Or divider */}
          <div className="flex items-center gap-3 mb-3">
            <div className="flex-1 h-px" style={{ background: 'var(--border-glass)' }} />
            <span className="text-[10px] uppercase" style={{ color: 'var(--text-muted)' }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'var(--border-glass)' }} />
          </div>

          {/* Email sign-in */}
          <button
            onClick={() => loginWithPopup()}
            className="interactive w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all"
            style={{ border: '1px solid var(--border-glass)', color: 'var(--text-primary)', background: 'var(--bg-surface-2)' }}
          >
            <LogIn className="w-4 h-4" /> Sign in with Email
          </button>

          <p className="text-[10px] text-center mt-4" style={{ color: 'var(--text-muted)' }}>
            Free tier: {GUEST_PAPER_LIMIT} papers without sign-in
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

/* ─── AuthGate — wraps protected content ─────────────────────── */
export function AuthGate({ children, feature }: { children: ReactNode; feature: string }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <div className="animate-spin w-8 h-8 border-2 rounded-full"
          style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 px-4" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <SignInModal open={true} onClose={() => {}} reason={feature} />
      </div>
    );
  }

  return <>{children}</>;
}
