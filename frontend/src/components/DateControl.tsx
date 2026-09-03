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
      <div className="popover-panel animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="popover-header">
          <div className="popover-title">
            <Calendar size={18} color="var(--cyan-primary)" />
            <span>Observation Date Context</span>
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              background: selectedOption === 'today' ? 'var(--bg-elevated)' : 'transparent',
              border: `1px solid ${selectedOption === 'today' ? 'var(--cyan-primary)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <input
              type="radio"
              name="date-option"
              checked={selectedOption === 'today'}
              onChange={() => setSelectedOption('today')}
            />
            <div>
              <div style={{ fontWeight: 600, color: 'var(--cyan-light)' }}>Current Observation (Today / LIVE)</div>
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
              background: selectedOption === 'historical' ? 'var(--bg-elevated)' : 'transparent',
              border: `1px solid ${selectedOption === 'historical' ? 'var(--cyan-primary)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <input
              type="radio"
              name="date-option"
              checked={selectedOption === 'historical'}
              onChange={() => setSelectedOption('historical')}
            />
            <div>
              <div style={{ fontWeight: 600, color: 'var(--amber)' }}>October 2025 Baseline Cache</div>
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
              background: selectedOption === 'custom' ? 'var(--bg-elevated)' : 'transparent',
              border: `1px solid ${selectedOption === 'custom' ? 'var(--cyan-primary)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            <input
              type="radio"
              name="date-option"
              checked={selectedOption === 'custom'}
              onChange={() => setSelectedOption('custom')}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>Custom Specific Date</div>
              {selectedOption === 'custom' && (
                <input
                  type="date"
                  className="text-input"
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
  );
};
