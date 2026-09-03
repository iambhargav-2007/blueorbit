import React from 'react';
import { Orbit, Activity, Menu, RefreshCw } from 'lucide-react';

interface TopBarProps {
  isBackendHealthy: boolean;
  onRefreshHealth: () => void;
  onToggleSidebar: () => void;
  isCheckingHealth: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  isBackendHealthy,
  onRefreshHealth,
  onToggleSidebar,
  isCheckingHealth,
}) => {
  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <button
          className="btn-icon mobile-only"
          onClick={onToggleSidebar}
          aria-label="Toggle Sidebar"
          title="Toggle Sidebar"
        >
          <Menu size={18} />
        </button>

        <div className="brand-wrapper">
          <div className="brand-icon">
            <Orbit size={18} />
          </div>
          <div className="brand-title">
            BLUE ORBIT
            <span className="brand-badge">ORCA</span>
          </div>
        </div>
      </div>

      <div className="top-bar-right">
        <div
          className="backend-indicator"
          title="FastAPI Backend Status (http://localhost:8000)"
        >
          <span className={`backend-dot ${isBackendHealthy ? '' : 'offline'}`} />
          <span>{isBackendHealthy ? 'Backend Active' : 'Backend Offline'}</span>
          <button
            onClick={onRefreshHealth}
            className="btn-icon"
            style={{ padding: '2px', marginLeft: '4px' }}
            disabled={isCheckingHealth}
            aria-label="Re-check Backend Connection"
            title="Re-check Backend Connection"
          >
            <RefreshCw size={12} className={isCheckingHealth ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>
    </header>
  );
};
