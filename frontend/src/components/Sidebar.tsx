import React from 'react';
import { Plus, MessageSquare, Compass, Anchor, X } from 'lucide-react';
import { SessionRecord } from '../types/api';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: SessionRecord[];
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  activeLocation: { lat: number; lon: number } | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  activeLocation,
}) => {
  return (
    <>
      <aside className={`sidebar ${isOpen ? 'open' : ''}`} aria-label="Navigation sidebar">
        {/* Header */}
        <div className="sidebar-header">
          <button id="btn-new-chat" className="btn-new-chat" onClick={onNewChat}>
            <Plus size={14} />
            <span>New Chat</span>
          </button>
        </div>

        <div className="sidebar-content">
          {/* Recent conversations */}
          {sessions.length > 0 && (
            <>
              <div className="sidebar-section-title">Recent</div>
              {sessions.map((sess) => (
                <button
                  key={sess.id}
                  className={`session-item ${sess.id === currentSessionId ? 'active' : ''}`}
                  onClick={() => { onSelectSession(sess.id); onClose(); }}
                  aria-current={sess.id === currentSessionId ? 'page' : undefined}
                >
                  <MessageSquare size={12} style={{ flexShrink: 0, opacity: 0.6 }} />
                  <span className="session-title-text">{sess.title || 'Marine Analysis'}</span>
                </button>
              ))}
            </>
          )}

          {sessions.length === 0 && (
            <div style={{ padding: '20px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-dim)', lineHeight: 1.5 }}>
                No recent sessions.<br />Start a conversation.
              </div>
            </div>
          )}

          {/* Active sector */}
          {activeLocation && (
            <>
              <div className="sidebar-section-title" style={{ marginTop: 20 }}>Active Sector</div>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 10px',
                background: 'var(--bg-raised)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--r-md)',
                fontSize: 11.5,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-primary)',
              }}>
                <Compass size={12} color="var(--accent)" />
                <span>{activeLocation.lat.toFixed(2)}°N · {activeLocation.lon.toFixed(2)}°E</span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 2 }}>
            <Anchor size={12} color="var(--text-muted)" />
            <span>ORCA Engine</span>
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>SIH 2026 · Indian West Coast</div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="popover-backdrop mobile-only"
          onClick={onClose}
          style={{ zIndex: 40 }}
          aria-hidden="true"
        />
      )}
    </>
  );
};
