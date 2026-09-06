import React from 'react';
import { Orbit, Menu, RefreshCw, Compass, MessageSquare, Sun, Moon } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface TopBarProps {
  isBackendHealthy: boolean;
  onRefreshHealth: () => void;
  onToggleSidebar: () => void;
  isCheckingHealth: boolean;
  activeView: 'map' | 'chat';
  onChangeView: (view: 'map' | 'chat') => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  isBackendHealthy,
  onRefreshHealth,
  onToggleSidebar,
  isCheckingHealth,
  activeView,
  onChangeView,
}) => {
  const { theme, toggleTheme } = useTheme();
  return (
    <header className="top-bar">
      {/* Left — Brand */}
      <div className="top-bar-left">
        <button
          className="btn-icon mobile-only"
          onClick={onToggleSidebar}
          aria-label="Toggle Sidebar"
        >
          <Menu size={16} />
        </button>

        <div className="brand-wrapper" onClick={() => onChangeView('map')}>
          <div className="brand-icon">
            <Orbit size={14} />
          </div>
          <div className="brand-title">
            BLUE ORBIT
            <span className="brand-badge">ORCA</span>
          </div>
        </div>
      </div>

      {/* Center — View switcher */}
      <div className="view-mode-tabs">
        <button
          id="tab-spatial-map"
          className={`view-mode-tab ${activeView === 'map' ? 'active' : ''}`}
          onClick={() => onChangeView('map')}
          aria-label="Spatial Map"
        >
          <Compass size={13} />
          <span>Spatial Map</span>
        </button>
        <button
          id="tab-decision-assistant"
          className={`view-mode-tab ${activeView === 'chat' ? 'active' : ''}`}
          onClick={() => onChangeView('chat')}
          aria-label="Decision Assistant"
        >
          <MessageSquare size={13} />
          <span>Decision Assistant</span>
        </button>
      </div>

      {/* Right — Status */}
      {/* Right — Status & Theme */}
      <div className="top-bar-right">
        <button
          className="btn-icon"
          onClick={toggleTheme}
          style={{ width: 28, height: 28, marginRight: 8, background: 'var(--bg-hover)' }}
          title="Toggle Light/Dark Mode"
          aria-label="Toggle Theme"
        >
          {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
        </button>
        <div
          className="backend-indicator"
          title="FastAPI Backend — http://localhost:8000"
          aria-live="polite"
        >
          <span className={`backend-dot ${isBackendHealthy ? '' : 'offline'}`} aria-hidden="true" />
          <span>{isBackendHealthy ? 'Backend Active' : 'Offline'}</span>
          <button
            onClick={onRefreshHealth}
            className="btn-icon"
            style={{ width: 20, height: 20, marginLeft: 2 }}
            disabled={isCheckingHealth}
            aria-label="Retry backend connection"
          >
            <RefreshCw size={11} className={isCheckingHealth ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>
    </header>
  );
};
