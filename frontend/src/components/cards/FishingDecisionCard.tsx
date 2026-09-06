import React, { useState } from 'react';
import {
  Anchor, CheckCircle2, AlertTriangle, XCircle, HelpCircle,
  Wind, Fish, Compass, AlertCircle, ChevronDown, ChevronUp
} from 'lucide-react';
import { FishingDecisionAgentResponse } from '../../types/api';

interface FishingDecisionCardProps {
  data: FishingDecisionAgentResponse;
}

type DecisionKey = 'FAVORABLE' | 'CAUTION' | 'NOT_RECOMMENDED' | 'INSUFFICIENT_DATA';

const DECISION_CONFIG: Record<DecisionKey, {
  label: string;
  icon: React.ReactNode;
  heroClass: string;
  verdictClass: string;
}> = {
  FAVORABLE: {
    label: 'Favorable',
    icon: <CheckCircle2 size={16} />,
    heroClass: 'favorable',
    verdictClass: 'favorable',
  },
  CAUTION: {
    label: 'Caution',
    icon: <AlertTriangle size={16} />,
    heroClass: 'caution',
    verdictClass: 'caution',
  },
  NOT_RECOMMENDED: {
    label: 'Not Recommended',
    icon: <XCircle size={16} />,
    heroClass: 'danger',
    verdictClass: 'danger',
  },
  INSUFFICIENT_DATA: {
    label: 'Insufficient Data',
    icon: <HelpCircle size={16} />,
    heroClass: 'neutral',
    verdictClass: 'neutral',
  },
};

export const FishingDecisionCard: React.FC<FishingDecisionCardProps> = ({ data }) => {
  const [showDetails, setShowDetails] = useState(false);
  const decisionObj = data.decision;
  if (!decisionObj) return null;

  const decisionKey = (decisionObj.decision?.toUpperCase().replace(' ', '_') || 'INSUFFICIENT_DATA') as DecisionKey;
  const cfg = DECISION_CONFIG[decisionKey] || DECISION_CONFIG.INSUFFICIENT_DATA;

  const score = decisionObj.overall_score;
  const isLive = decisionObj.temporal_mode === 'LIVE';
  const isHistorical = decisionObj.temporal_mode === 'HISTORICAL';

  return (
    <div className="result-card animate-fade-in" id="fishing-decision-card">
      {/* Header */}
      <div className="result-card-header">
        <div className="result-card-title">
          <Anchor size={14} color="var(--accent)" />
          <span>Fishing Decision</span>
        </div>
        <span className={`temporal-tag ${isLive ? 'live' : isHistorical ? 'cache' : ''}`}>
          {isLive ? 'Live Synthesis' : isHistorical ? `Historical` : 'Decision'}
        </span>
      </div>

      <div className="result-card-body">
        {/* Decision Hero with Left Border Accent — Dominant */}
        <div className={`decision-accent-hero ${cfg.heroClass}`}>
          <div>
            <div className="decision-accent-label">
              Fishing Recommendation
            </div>
            <div className={`decision-verdict ${cfg.verdictClass}`} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              {cfg.icon}
              <span>{cfg.label}</span>
            </div>
            {decisionObj.limiting_factor && (
              <div className="decision-limiting-factor">
                Limiting factor: <span>{decisionObj.limiting_factor}</span>
              </div>
            )}
          </div>
          {score !== null && score !== undefined && (
            <div className="decision-score-block">
              <div className="decision-score">{score.toFixed(0)}</div>
              <div className="decision-score-label">Decision Score</div>
            </div>
          )}
        </div>

        {/* 3 Pillars — Single row separated by clean dividers, not three separate bordered tiles */}
        <div className="metrics-row-divided">
          <div className="divided-metric-col">
            <div className="metric-label">
              <Fish size={10} />
              Habitat
            </div>
            <div className="metric-data sm">{decisionObj.habitat_status || '—'}</div>
            <div className="metric-sub">
              {decisionObj.habitat_score != null ? `${decisionObj.habitat_score.toFixed(0)} / 100` : 'Copernicus'}
            </div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label">
              <Wind size={10} />
              Weather Risk
            </div>
            <div className="metric-data sm">{decisionObj.weather_risk || '—'}</div>
            <div className="metric-sub">
              {decisionObj.weather_score != null ? `${decisionObj.weather_score.toFixed(0)} / 100` : 'Sea state'}
            </div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label">
              <Compass size={10} />
              EEZ Status
            </div>
            <div className="metric-data sm">{decisionObj.geofence_status || '—'}</div>
            <div className="metric-sub">Jurisdiction</div>
          </div>
        </div>

        {/* Expandable: Reasons + Warnings + Narratives */}
        <button
          className="spatial-expand-btn"
          onClick={() => setShowDetails(!showDetails)}
          aria-expanded={showDetails}
          id="decision-expand-details"
        >
          <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
            {showDetails ? 'Hide details' : 'View decision factors'}
          </span>
          {showDetails ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {showDetails && (
          <div className="animate-fade-in" style={{ marginTop: 10 }}>
            {/* Reasons */}
            {decisionObj.reasons && decisionObj.reasons.length > 0 && (
              <div className="card-section">
                <div className="card-section-label">Decision Factors</div>
                <ul style={{ margin: 0, paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {decisionObj.reasons.map((r, i) => (
                    <li key={i} style={{ fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings */}
            {decisionObj.warnings && decisionObj.warnings.length > 0 && (
              <div className="card-section">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <AlertCircle size={12} color="var(--warning)" />
                  <div className="card-section-label" style={{ color: 'var(--warning)', marginBottom: 0 }}>
                    Safety Advisories
                  </div>
                </div>
                <ul style={{ margin: 0, paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {decisionObj.warnings.map((w, i) => (
                    <li key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.45 }}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Narratives */}
            {(data.narrative || data.advice) && (
              <div className="card-section card-narrative-section" style={{ border: 'none', paddingTop: 0 }}>
                {data.narrative && (
                  <div className="narrative-item scientific">
                    {data.narrative}
                  </div>
                )}
                {data.advice && (
                  <div className="narrative-item advice">
                    {data.advice}
                  </div>
                )}
              </div>
            )}

            <div className="disclaimer-text" style={{ marginTop: 8 }}>
              {data.disclaimer || 'Prototype decision-support indicator. Does not guarantee fish abundance, catch success, or vessel safety.'}
            </div>
          </div>
        )}

        {/* Data source */}
        {decisionObj.data_sources && decisionObj.data_sources.length > 0 && (
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 10 }}>
            {decisionObj.data_sources.map((src, i) => (
              <span key={i} className="source-pill">{src}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
