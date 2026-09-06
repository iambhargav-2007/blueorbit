import React, { useState } from 'react';
import { Calendar, X } from 'lucide-react';

interface DateControlProps {
  currentDateStr: string | null;
  onSaveDate: (dateStr: string | null) => void;
  onClose: () => void;
}

export const DateControl: React.FC<DateControlProps> = ({
  currentDateStr,
  onSaveDate,
  onClose,
}) => {
  const [selectedOption, setSelectedOption] = useState<'today' | 'historical' | 'custom'>(
    !currentDateStr || currentDateStr === 'today'
      ? 'today'
      : currentDateStr === '2025-10-15'
      ? 'historical'
      : 'custom'
  );
  const [customDate, setCustomDate] = useState<string>(
    currentDateStr && currentDateStr !== 'today' ? currentDateStr : '2025-10-15'
  );

  const handleApply = () => {
    if (selectedOption === 'today') {
      onSaveDate('today');
    } else if (selectedOption === 'historical') {
      onSaveDate('2025-10-15');
    } else {
      onSaveDate(customDate);
    }
    onClose();
  };

  const handleClear = () => {
    onSaveDate(null);
    onClose();
  };

  return (
    <div className="popover-backdrop" onClick={onClose}>
      <div className="popover-panel" onClick={(e) => e.stopPropagation()}>
        <div className="popover-header">
          <div className="popover-title">
            <Calendar size={16} color="var(--accent)" />
            <span>Observation Date Context</span>
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div className="popover-body">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              background: selectedOption === 'today' ? 'var(--bg-raised)' : 'transparent',
              border: `1px solid ${selectedOption === 'today' ? 'var(--border-strong)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--r-md)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <input
              type="radio"
              name="date-option"
              checked={selectedOption === 'today'}
              onChange={() => setSelectedOption('today')}
              style={{ accentColor: 'var(--accent)' }}
            />
            <div>
              <div style={{ fontWeight: 500, color: selectedOption === 'today' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Current Observation (Today / LIVE)</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Direct live Copernicus Marine retrieval for today
              </div>
            </div>
          </label>

          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              background: selectedOption === 'historical' ? 'var(--bg-surface-elevated)' : 'transparent',
              border: `1px solid ${selectedOption === 'historical' ? 'var(--border-strong)' : 'var(--border-default)'}`,
              borderRadius: 'var(--r-md)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <input
              type="radio"
              name="date-option"
              checked={selectedOption === 'historical'}
              onChange={() => setSelectedOption('historical')}
              style={{ accentColor: 'var(--accent)' }}
            />
            <div>
              <div style={{ fontWeight: 500, color: selectedOption === 'historical' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>October 2025 Baseline Cache</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Target date: 2025-10-15 (Standard historical baseline)
              </div>
            </div>
          </label>

          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              background: selectedOption === 'custom' ? 'var(--bg-surface-elevated)' : 'transparent',
              border: `1px solid ${selectedOption === 'custom' ? 'var(--border-strong)' : 'var(--border-default)'}`,
              borderRadius: 'var(--r-md)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <input
              type="radio"
              name="date-option"
              checked={selectedOption === 'custom'}
              onChange={() => setSelectedOption('custom')}
              style={{ accentColor: 'var(--accent)' }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, color: selectedOption === 'custom' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Custom Specific Date</div>
              {selectedOption === 'custom' && (
                <input
                  type="date"
                  className="form-input"
                  style={{ marginTop: '6px', width: '100%' }}
                  value={customDate}
                  onChange={(e) => setCustomDate(e.target.value)}
                />
              )}
            </div>
          </label>
        </div>

        <div className="popover-actions">
          {currentDateStr && (
            <button type="button" className="btn-secondary" onClick={handleClear}>
              Clear
            </button>
          )}
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={handleApply}>
            Apply Date
          </button>
        </div>
        </div>
      </div>
    </div>
  );
};
