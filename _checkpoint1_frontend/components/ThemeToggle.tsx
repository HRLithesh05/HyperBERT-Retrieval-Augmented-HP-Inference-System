import { Moon, Sun } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { motion, AnimatePresence } from 'framer-motion';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="relative w-10 h-10 rounded-full flex items-center justify-center overflow-hidden transition-colors interactive"
      style={{
        background: 'var(--bg-surface-2)',
        border: '1px solid var(--border-glass)',
      }}
      aria-label="Toggle theme"
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={theme}
          initial={{ y: -16, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 16, opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          {theme === 'dark'
            ? <Moon className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
            : <Sun className="w-5 h-5" style={{ color: 'var(--text-primary)' }} />
          }
        </motion.div>
      </AnimatePresence>
    </button>
  );
}
