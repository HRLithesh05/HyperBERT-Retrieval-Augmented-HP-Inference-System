import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export function CustomCursor() {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [hovering, setHovering] = useState(false);

  useEffect(() => {
    const move = (e: MouseEvent) => setPos({ x: e.clientX, y: e.clientY });
    const over = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      setHovering(
        t.closest('button, a, .interactive') !== null ||
        t.tagName === 'BUTTON' ||
        t.tagName === 'A'
      );
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseover', over);
    return () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseover', over);
    };
  }, []);

  return (
    <>
      {/* Inner dot */}
      <motion.div
        className="fixed top-0 left-0 w-2 h-2 rounded-full pointer-events-none z-[9999]"
        style={{ background: 'var(--accent-primary)', mixBlendMode: 'normal' }}
        animate={{ x: pos.x - 4, y: pos.y - 4 }}
        transition={{ type: 'tween', ease: 'backOut', duration: 0.08 }}
      />
      {/* Outer ring */}
      <motion.div
        className="fixed top-0 left-0 rounded-full pointer-events-none z-[9998]"
        style={{
          width: hovering ? 48 : 32,
          height: hovering ? 48 : 32,
          border: `2px solid ${hovering ? 'var(--accent-tertiary)' : 'var(--accent-secondary)'}`,
          background: hovering ? 'rgba(139,92,246,0.08)' : 'transparent',
          backdropFilter: hovering ? 'blur(4px)' : 'none',
          mixBlendMode: 'difference',
        }}
        animate={{
          x: pos.x - (hovering ? 24 : 16),
          y: pos.y - (hovering ? 24 : 16),
        }}
        transition={{ type: 'spring', damping: 22, stiffness: 280, mass: 0.4 }}
      />
    </>
  );
}
