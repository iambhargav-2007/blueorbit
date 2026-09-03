import React from 'react';
import { AlertCircle, AlertTriangle, CalendarX, Info } from 'lucide-react';

interface AlertStateCardProps {
  type: 'clarification' | 'unsupported_future' | 'insufficient_data' | 'error';
  title: string;
  message: string;
  missingFields?: string[];
  onQuickAction?: (field: string) => void;
}

export const AlertStateCard: React.FC<AlertStateCardProps> = ({
  type,
  title,
  message,
  missingFields,
  onQuickAction,
}) => {
  const getStyleClass = () => {
    switch (type) {
      case 'clarification':
        return 'info';
      case 'unsupported_future':
        return 'warning';
      case 'insufficient_data':
        return 'warning';
      case 'error':
      default:
        return 'error';
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'clarification':
        return <Info size={20} color="var(--cyan-light)" />;
      case 'unsupported_future':
        return <CalendarX size={20} color="var(--amber)" />;
      case 'insufficient_data':
        return <AlertTriangle size={20} color="var(--amber)" />;
      case 'error':
      default:
        return <AlertCircle size={20} color="var(--rose)" />;
    }
  };

  return (
    <div className={`alert-state-card ${getStyleClass()} animate-fade-in`}>
      <div style={{ flexShrink: 0, marginTop: '2px' }}>{getIcon()}</div>
      <div style={{ flex: 1 }}>
        <div className="alert-title">{title}</div>
        <div className="alert-description">{message}</div>

        {missingFields && missingFields.length > 0 && (
          <div style={{ display: 'flex', gap: '6px', marginTop: '8px', flexWrap: 'wrap' }}>
            {missingFields.map((field) => (
              <span
                key={field}
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: '#fff',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                }}
              >
                Required: {field}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
