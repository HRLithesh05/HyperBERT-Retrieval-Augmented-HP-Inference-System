/**
 * SessionSidebar — Collapsible sidebar showing past analysis history.
 * 
 * Displays sessions sorted by recency with paper title, task badge,
 * completeness %, and timestamp. Clicking navigates to the results page.
 */
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, ChevronLeft, ChevronRight, FileText, Loader2 } from 'lucide-react';
import { useSession } from '@/contexts/SessionContext';

const TASK_COLORS: Record<string, string> = {
  text_classification: '#6366f1',
  sentiment_analysis: '#8b5cf6',
  ner: '#06b6d4',
  question_answering: '#3b82f6',
  nli: '#4f46e5',
  semantic_textual_similarity: '#10b981',
  relation_extraction: '#f59e0b',
  token_classification: '#0ea5e9',
  summarization: '#6366f1',
};

function formatTimeAgo(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `${diffDay}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export function SessionSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const { sessionHistory, historyLoading, sessionId: activeSession } = useSession();
  const navigate = useNavigate();
  const location = useLocation();

  // Only show on results-related pages
  const showSidebar = location.pathname.startsWith('/results') ||
                      location.pathname.startsWith('/compare') ||
                      location.pathname.startsWith('/notebook') ||
                      location.pathname.startsWith('/upload');

  if (!showSidebar) return null;

  return (
    <>
      {/* Toggle button */}
      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          left: isOpen ? 288 : 0,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 50,
          background: 'var(--bg-surface-2)',
          border: '1px solid var(--border-glass)',
          borderLeft: isOpen ? '1px solid var(--border-glass)' : 'none',
          borderRadius: isOpen ? '0 8px 8px 0' : '0 8px 8px 0',
          padding: '12px 6px',
          cursor: 'pointer',
          color: 'var(--text-secondary)',
          backdropFilter: 'blur(12px)',
          transition: 'left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: 'var(--shadow-card)',
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        title={isOpen ? 'Close history' : 'Open analysis history'}
      >
        {isOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </motion.button>

      {/* Sidebar panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            style={{
              position: 'fixed',
              left: 0,
              top: 0,
              bottom: 0,
              width: 288,
              zIndex: 45,
              background: 'var(--bg-base)',
              borderRight: '1px solid var(--border-glass)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              boxShadow: '4px 0 24px rgba(0,0,0,0.1)',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '20px 16px 12px',
              borderBottom: '1px solid var(--border-glass)',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 4,
              }}>
                <Clock size={16} style={{ color: 'var(--accent-primary)' }} />
                <span style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: 'var(--text-heading)',
                  letterSpacing: '-0.01em',
                }}>
                  Analysis History
                </span>
              </div>
              <span style={{
                fontSize: 12,
                color: 'var(--text-muted)',
              }}>
                {sessionHistory.length} {sessionHistory.length === 1 ? 'analysis' : 'analyses'}
              </span>
            </div>

            {/* Session list */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '8px',
            }}>
              {historyLoading ? (
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: 100,
                  color: 'var(--text-muted)',
                }}>
                  <Loader2 size={20} className="animate-spin" />
                </div>
              ) : sessionHistory.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: '32px 16px',
                  color: 'var(--text-muted)',
                  fontSize: 13,
                }}>
                  <FileText size={32} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                  <p>No analyses yet</p>
                  <p style={{ fontSize: 11, marginTop: 4 }}>
                    Upload a paper to get started
                  </p>
                </div>
              ) : (
                sessionHistory.map((session, i) => {
                  const isActive = session.session_id === activeSession;
                  const taskColor = TASK_COLORS[session.paper_task || ''] || 'var(--text-muted)';

                  return (
                    <motion.button
                      key={session.session_id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      onClick={() => navigate(`/results/${session.session_id}`)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: isActive ? '1px solid var(--accent-primary)' : '1px solid transparent',
                        background: isActive ? 'var(--bg-surface-2)' : 'transparent',
                        cursor: 'pointer',
                        marginBottom: 4,
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLElement).style.background = 'var(--bg-surface-1)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLElement).style.background = 'transparent';
                        }
                      }}
                    >
                      {/* Title */}
                      <div style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        lineHeight: 1.3,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        marginBottom: 6,
                      }}>
                        {session.paper_title || 'Untitled'}
                      </div>

                      {/* Meta row */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 6,
                      }}>
                        {/* Task badge */}
                        {session.paper_task && (
                          <span style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: 4,
                            background: `${taskColor}18`,
                            color: taskColor,
                            textTransform: 'uppercase',
                            letterSpacing: '0.03em',
                            maxWidth: 100,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}>
                            {session.paper_task.replace(/_/g, ' ')}
                          </span>
                        )}

                        {/* Completeness + time */}
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          fontSize: 11,
                          color: 'var(--text-muted)',
                          flexShrink: 0,
                        }}>
                          <span style={{
                            color: session.completeness_pct >= 70 ? 'var(--status-success)' :
                                   session.completeness_pct >= 40 ? 'var(--status-warning)' :
                                   'var(--status-danger)',
                            fontWeight: 500,
                          }}>
                            {Math.round(session.completeness_pct)}%
                          </span>
                          <span>·</span>
                          <span>{formatTimeAgo(session.created_at)}</span>
                        </div>
                      </div>
                    </motion.button>
                  );
                })
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Backdrop on mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="lg:hidden"
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 44,
              background: 'rgba(0,0,0,0.3)',
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
