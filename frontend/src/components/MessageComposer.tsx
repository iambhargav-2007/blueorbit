import React, { useRef, useEffect } from 'react';
import { ArrowUp, Compass, Calendar, Loader2 } from 'lucide-react';

import { LocationContext } from '../types/api';

interface MessageComposerProps {
  input: string;
  onChangeInput: (val: string) => void;
  onSend: () => void;
  isLoading: boolean;
  location: { lat: number; lon: number } | null;
  locationContext?: LocationContext | null;
  dateStr: string | null;
  onOpenLocation: () => void;
  onOpenDate: () => void;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  input,
  onChangeInput,
  onSend,
  isLoading,
  location,
  locationContext,
  dateStr,
  onOpenLocation,
  onOpenDate,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        onSend();
      }
    }
  };

  const formatDateDisplay = (date: string | null) => {
    if (!date || date === 'today') return 'Today (LIVE)';
    if (date === '2025-10-15') return '2025-10-15 (Cache)';
    return date;
  };

  const formatLocationDisplay = () => {
    if (locationContext) {
      if (locationContext.source === 'gps') {
        const acc = locationContext.accuracy_m ? ` (~${Math.round(locationContext.accuracy_m)}m)` : '';
        return `GPS Position${acc}`;
      }
      return locationContext.display_name;
    }
    if (location) {
      return `${location.lat.toFixed(2)}°N, ${location.lon.toFixed(2)}°E`;
    }
    return 'Add Location';
  };

  return (
    <div className="composer-dock">
      <div className="composer-box">
        {/* Context Bar */}
        <div className="composer-context-bar">
          <div className="context-pill-group">
            <button
              type="button"
              className={`context-pill ${locationContext || location ? 'active' : ''}`}
              onClick={onOpenLocation}
              title="Set target sector coordinates"
            >
              <Compass size={12} />
              <span>{formatLocationDisplay()}</span>
            </button>

            <button
              type="button"
              className={`context-pill ${dateStr && dateStr !== 'today' ? 'active' : ''}`}
              onClick={onOpenDate}
              title="Set target temporal context"
            >
              <Calendar size={12} />
              <span>{formatDateDisplay(dateStr)}</span>
            </button>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Shift+Enter for newline
          </div>
        </div>

        {/* Input Area */}
        <div className="composer-input-area">
          <textarea
            ref={textareaRef}
            rows={1}
            className="composer-textarea"
            placeholder="Ask Blue Orbit about fishing potential, sea state safety, EEZ borders..."
            value={input}
            onChange={(e) => onChangeInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />

          <button
            type="button"
            className="btn-send"
            disabled={!input.trim() || isLoading}
            onClick={onSend}
            aria-label="Send query"
          >
            {isLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ArrowUp size={18} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
