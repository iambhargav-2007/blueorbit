import React from 'react';
import { Plus, MessageSquare, Compass, Shield, X } from 'lucide-react';
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
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <button className="btn-new-chat" onClick={onNewChat}>
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>

        <div className="sidebar-content">
          <div className="sidebar-section-title">Recent Conversations</div>

          {sessions.length === 0 ? (
            <div style={{ padding: '12px 10px', fontSize: '12px', color: 'var(--text-muted)' }}>
              No previous chats in this session.
            </div>
          ) : (
            sessions.map((sess) => (
              <button
                key={sess.id}
                className={`session-item ${sess.id === currentSessionId ? 'active' : ''}`}
                onClick={() => {
                  onSelectSession(sess.id);
                  onClose();
                }}
              >
                <MessageSquare size={14} style={{ flexShrink: 0 }} />
                <span className="session-title-text">{sess.title || 'Marine Analysis'}</span>
              </button>
            ))
          )}

          {activeLocation && (
            <>
              <div className="sidebar-section-title" style={{ marginTop: '20px' }}>
                Active Sector
              </div>
              <div
                style={{
                  padding: '10px 12px',
                  background: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--cyan-light)',
                }}
              >
                <Compass size={14} />
                <span>
                  {activeLocation.lat.toFixed(2)}°N, {activeLocation.lon.toFixed(2)}°E
                </span>
              </div>
            </>
          )}
        </div>

        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
            <Shield size={13} color="var(--cyan-primary)" />
            <span>ORCA Decision Engine</span>
          </div>
          <div>SIH 2026 · Indian West Coast</div>
        </div>
      </aside>

      {isOpen && (
        <div
          className="popover-backdrop mobile-only"
          onClick={onClose}
          style={{ zIndex: 25 }}
        />
      )}
    </>
  );
};
