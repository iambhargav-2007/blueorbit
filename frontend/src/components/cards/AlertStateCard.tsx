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
}) => {
  const variantMap = {
    clarification:      { cls: 'info',    icon: <Info size={15} color="var(--accent)" /> },
    unsupported_future: { cls: 'warning',  icon: <CalendarX size={15} color="var(--warning)" /> },
    insufficient_data:  { cls: 'neutral',  icon: <AlertTriangle size={15} color="var(--text-muted)" /> },
    error:              { cls: 'error',   icon: <AlertCircle size={15} color="var(--danger)" /> },
  };

  const { cls, icon } = variantMap[type] || variantMap.error;

  return (
    <div className={`alert-card ${cls} animate-fade-in`}>
      <div className="alert-icon" aria-hidden="true">{icon}</div>
      <div style={{ flex: 1 }}>
        <div className="alert-title">{title}</div>
        <div className="alert-description">{message}</div>

        {missingFields && missingFields.length > 0 && (
          <div style={{ display: 'flex', gap: 5, marginTop: 8, flexWrap: 'wrap' }}>
            {missingFields.map((field) => (
              <span
                key={field}
                style={{
                  fontSize: 10.5,
                  fontFamily: 'var(--font-mono)',
                  padding: '2px 7px',
                  borderRadius: 'var(--r-sm)',
                  background: 'var(--neutral-dim)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--neutral-border)',
                }}
              >
                {field}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
