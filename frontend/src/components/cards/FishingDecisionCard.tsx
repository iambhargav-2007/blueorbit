import React from 'react';
import { 
  Anchor, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle, 
  Wind, 
  Fish, 
  ShieldCheck, 
  ShieldAlert,
  Compass,
  AlertCircle
} from 'lucide-react';
import { FishingDecisionAgentResponse } from '../../types/api';

interface FishingDecisionCardProps {
  data: FishingDecisionAgentResponse;
}

export const FishingDecisionCard: React.FC<FishingDecisionCardProps> = ({ data }) => {
  const decisionObj = data.decision;
  if (!decisionObj) return null;

  const decision = decisionObj.decision || 'INSUFFICIENT_DATA';
  const score = decisionObj.overall_score;
  const isLive = decisionObj.temporal_mode === 'LIVE';
  const isHistorical = decisionObj.temporal_mode === 'HISTORICAL';

  const getDecisionTheme = (d: string) => {
    switch (d.toUpperCase()) {
      case 'FAVORABLE':
        return {
          label: 'FAVORABLE',
          icon: <CheckCircle2 size={18} color="var(--emerald)" />,
          colorClass: 'status-high',
          badgeBg: 'rgba(16, 185, 129, 0.15)',
          badgeBorder: 'rgba(16, 185, 129, 0.4)',
          textColor: 'var(--emerald)',
        };
      case 'CAUTION':
        return {
          label: 'CAUTION',
          icon: <AlertTriangle size={18} color="var(--amber)" />,
          colorClass: 'status-moderate',
          badgeBg: 'rgba(245, 158, 11, 0.15)',
          badgeBorder: 'rgba(245, 158, 11, 0.4)',
          textColor: 'var(--amber)',
        };
      case 'NOT_RECOMMENDED':
        return {
          label: 'NOT RECOMMENDED',
          icon: <XCircle size={18} color="var(--rose)" />,
          colorClass: 'status-low',
          badgeBg: 'rgba(244, 63, 94, 0.15)',
          badgeBorder: 'rgba(244, 63, 94, 0.4)',
          textColor: 'var(--rose)',
        };
      default:
        return {
          label: 'INSUFFICIENT DATA',
          icon: <HelpCircle size={18} color="var(--text-muted)" />,
          colorClass: 'status-insufficient',
          badgeBg: 'rgba(148, 163, 184, 0.12)',
          badgeBorder: 'rgba(148, 163, 184, 0.3)',
          textColor: 'var(--text-muted)',
        };
    }
  };

  const theme = getDecisionTheme(decision);

  return (
    <div className="result-card animate-fade-in" style={{ border: `1px solid ${theme.badgeBorder}` }}>
      {/* Header */}
      <div className="result-card-header">
        <div className="result-card-title">
          <Anchor size={16} color="var(--cyan-primary)" />
          <span style={{ fontWeight: 600 }}>Unified Fishing Decision Recommendation</span>
        </div>
        <span className={`temporal-tag ${isLive ? 'live' : isHistorical ? 'cache' : ''}`}>
          {isLive ? 'Live Marine Synthesis' : isHistorical ? `Historical — ${decisionObj.timestamp || 'Cache'}` : 'Decision Support'}
        </span>
      </div>

      <div className="result-card-body">
        {/* Primary Decision Banner */}
        <div 
          className="metric-highlight-panel" 
          style={{ 
            background: theme.badgeBg, 
            borderColor: theme.badgeBorder,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '14px 18px',
          }}
        >
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Aggregate Decision Support Index
            </div>
            <div className="metric-highlight-value" style={{ color: theme.textColor, fontSize: '26px' }}>
              {score !== null && score !== undefined ? `${score.toFixed(1)} / 100` : '—'}
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div 
              style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                gap: '6px', 
                padding: '6px 12px', 
                borderRadius: '8px', 
                background: 'rgba(15, 23, 42, 0.6)', 
                border: `1px solid ${theme.badgeBorder}`,
                fontWeight: 700,
                fontSize: '14px',
                color: theme.textColor
              }}
            >
              {theme.icon}
              <span>{theme.label}</span>
            </div>
          </div>
        </div>

        {/* Metadata Pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', margin: '12px 0' }}>
          {decisionObj.limiting_factor && (
            <span className="source-pill" style={{ background: 'rgba(6, 182, 212, 0.1)', color: 'var(--cyan-primary)', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
              Limiting Factor: {decisionObj.limiting_factor}
            </span>
          )}
          <span className="source-pill">
            Confidence: {decisionObj.confidence}
          </span>
          {decisionObj.data_sources && decisionObj.data_sources.length > 0 && (
            <span className="source-pill" style={{ color: 'var(--text-muted)' }}>
              Sources: {decisionObj.data_sources.join(', ')}
            </span>
          )}
        </div>

        {/* Pillar Breakdown Grid */}
        <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '14px' }}>
          {/* Habitat Pillar */}
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Fish size={12} color="var(--cyan-primary)" />
              <span>Habitat Potential</span>
            </div>
            <div className="metric-data" style={{ fontSize: '13px' }}>
              {decisionObj.habitat_status || '—'}
              {decisionObj.habitat_score !== null && decisionObj.habitat_score !== undefined && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                  ({decisionObj.habitat_score.toFixed(0)})
                </span>
              )}
            </div>
          </div>

          {/* Weather Pillar */}
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Wind size={12} color="var(--amber)" />
              <span>Weather Risk</span>
            </div>
            <div className="metric-data" style={{ fontSize: '13px' }}>
              {decisionObj.weather_risk || '—'}
              {decisionObj.weather_score !== null && decisionObj.weather_score !== undefined && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                  ({decisionObj.weather_score.toFixed(0)})
                </span>
              )}
            </div>
          </div>

          {/* Geofence Pillar */}
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Compass size={12} color="var(--emerald)" />
              <span>EEZ Status</span>
            </div>
            <div className="metric-data" style={{ fontSize: '13px' }}>
              {decisionObj.geofence_status || '—'}
            </div>
          </div>
        </div>

        {/* Why / Justification Section */}
        {decisionObj.reasons && decisionObj.reasons.length > 0 && (
          <div style={{ margin: '12px 0 10px', padding: '10px 14px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Decision Factors & Rationale
            </div>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-normal)', lineHeight: 1.5 }}>
              {decisionObj.reasons.map((r, i) => (
                <li key={i} style={{ marginBottom: '3px' }}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Warnings / Advisories Section */}
        {decisionObj.warnings && decisionObj.warnings.length > 0 && (
          <div style={{ margin: '10px 0', padding: '10px 14px', background: 'rgba(245, 158, 11, 0.08)', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, color: 'var(--amber)', textTransform: 'uppercase', marginBottom: '4px' }}>
              <AlertCircle size={13} />
              <span>Operational & Safety Advisories</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--text-normal)', lineHeight: 1.45 }}>
              {decisionObj.warnings.map((w, i) => (
                <li key={i} style={{ marginBottom: '2px' }}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Natural Language Narratives */}
        <div className="card-narrative-section">
          {data.narrative && (
            <div className="narrative-item scientific">
              <strong>Assessment:</strong> {data.narrative}
            </div>
          )}

          {data.advice && (
            <div className="narrative-item advice">
              <strong>Fisherman Guidance:</strong> {data.advice}
            </div>
          )}

          <div className="disclaimer-text">
            {data.disclaimer || 'Prototype decision-support indicator based on available environmental observations. Does not guarantee fish abundance, catch success, or vessel safety.'}
          </div>
        </div>
      </div>
    </div>
  );
};
