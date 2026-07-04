import React from 'react';
import { motion } from 'framer-motion';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  delay?: number;
  hoverable?: boolean;
}

export function GlassCard({ children, className = '', delay = 0, hoverable = true, style, ...props }: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: 'easeOut' }}
      whileHover={hoverable ? { y: -4, transition: { duration: 0.2 } } : undefined}
      className={`glass-card overflow-hidden group relative ${className}`}
      style={style}
      {...(props as any)}
    >
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-xl pointer-events-none"
        style={{ background: 'var(--accent-gradient)' }}
      />
      <div className="absolute inset-0 opacity-0 group-hover:opacity-[0.06] transition-opacity duration-500 rounded-xl pointer-events-none"
        style={{ background: 'var(--accent-gradient)' }}
      />
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
}
