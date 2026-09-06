import React, { useState } from 'react';
import {
  MapPin, X, ChevronRight, ChevronDown,
  Wind, Fish, Compass, CheckCircle2, AlertTriangle,
  XCircle, HelpCircle, MessageSquare
} from 'lucide-react';
import { PointAnalysisResponse } from '../../types/api';

interface SelectedLocationPanelProps {
  analysis: PointAnalysisResponse | null;
  isLoading: boolean;
  onClose: () => void;
  onAskOrca: (locationName: string, lat: number, lon: number) => void;
}

type DecisionKey = 'FAVORABLE' | 'CAUTION' | 'NOT_RECOMMENDED' | string;

const DECISION_MAP: Record<string, { label: string; icon: React.ReactNode; color: string; heroClass: string }> = {
  FAVORABLE: {
    label: 'Favorable',
    icon: <CheckCircle2 size={14} />,
    color: 'var(--success)',
    heroClass: 'favorable',
  },
  CAUTION: {
    label: 'Caution',
    icon: <AlertTriangle size={14} />,
    color: 'var(--warning)',
    heroClass: 'caution',
  },
  NOT_RECOMMENDED: {
    label: 'Not Recommended',
    icon: <XCircle size={14} />,
    color: 'var(--danger)',
    heroClass: 'danger',
  },
};

export const SelectedLocationPanel: React.FC<SelectedLocationPanelProps> = ({
  analysis,
  isLoading,
  onClose,
  onAskOrca,
}) => {
  const [showFactors, setShowFactors] = useState(false);

  /* ── Empty (no selection) ── */
  if (!analysis && !isLoading) {
    return (
      <div className="spatial-floating-panel empty animate-fade-in" style={{ top: 60, right: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Compass size={14} color="var(--accent)" />
          <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
            Click the map to inspect marine conditions
          </span>
        </div>
      </div>
    );
  }

  const loc      = analysis?.location;
  const decision = analysis?.decision;
  const geo      = analysis?.geofence;
  const marine   = analysis?.marine;
  const weather  = analysis?.weather;
  const isLive   = analysis?.temporal_mode === 'LIVE';

  const decisionKey = (decision?.decision || '').toUpperCase().replace(' ', '_');
  const cfg = DECISION_MAP[decisionKey] || {
    label: 'Insufficient Data',
    icon: <HelpCircle size={14} />,
    color: 'var(--text-muted)',
    heroClass: 'neutral',
  };

  const hasFactors = decision && (
    (decision.reasons && decision.reasons.length > 0) ||
    (decision.warnings && decision.warnings.length > 0)
  );

  return (
    <div className="spatial-floating-panel animate-slide-in" id="location-inspector-panel">
      {/* Header */}
      <div className="spatial-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div className="spatial-pin-badge" aria-hidden="true">
            <MapPin size={13} color="var(--accent)" />
          </div>
          <div>
            <div className="spatial-panel-title">
              {loc?.display_name || 'Maritime Sector'}
            </div>
            <div className="spatial-panel-coords">
              {loc
                ? `${loc.latitude.toFixed(3)}° N · ${loc.longitude.toFixed(3)}° E`
                : isLoading ? 'Resolving…' : '—'}
            </div>
          </div>
        </div>
        <button className="btn-icon-subtle" onClick={onClose} aria-label="Close panel">
          <X size={14} />
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="spatial-analyzing-state">
          <div className="spatial-spinner" aria-hidden="true" />
          <div>
            <div className="spatial-analyzing-label">Analyzing marine sector</div>
            <div className="spatial-analyzing-sub">SST · Chlorophyll · Sea state · EEZ</div>
          </div>
        </div>
      )}

      {/* Results */}
      {!isLoading && analysis && (
        <div className="spatial-panel-body">
          {/* Decision Section - Dominant */}
          {decision && (
            <div className="inspector-decision-section">
              <div className="inspector-decision-header">
                <div>
                  <div className="inspector-decision-label">SECTOR ASSESSMENT</div>
                  <div className="inspector-verdict-title" style={{ color: cfg.color }}>
                    {cfg.icon}
                    <span>{cfg.label}</span>
                  </div>
                </div>
                {decision.overall_score != null && (
                  <div className="inspector-score-box">
                    <span className="inspector-score-value">{decision.overall_score.toFixed(0)}</span>
                    <span className="inspector-score-total">/ 100</span>
                  </div>
                )}
              </div>

              {decision.limiting_factor && (
                <div className="inspector-limiting-factor">
                  Limiting factor: <span>{decision.limiting_factor}</span>
                </div>
              )}
            </div>
          )}

          <div className="inspector-divider" />

          {/* 3-Column Metrics - Clean columns separated by thin vertical dividers */}
          <div className="inspector-columns-row">
            {/* EEZ Column */}
            <div className="inspector-col">
              <div className="inspector-col-label">EEZ Status</div>
              <div className="inspector-col-val">
                {geo?.status === 'SAFE' || geo?.geofence_status === 'SAFE' || loc?.is_inside_eez
                  ? <span style={{ color: 'var(--success)' }}>Inside</span>
                  : geo?.status === 'WARNING'
                  ? <span style={{ color: 'var(--warning)' }}>Buffer</span>
                  : <span style={{ color: 'var(--danger)' }}>Outside</span>
                }
              </div>
              <div className="inspector-col-sub">
                {loc?.distance_to_boundary_km != null
                  ? `${loc.distance_to_boundary_km.toFixed(0)} km to line`
                  : geo?.distance_to_boundary_km != null
                  ? `${geo.distance_to_boundary_km.toFixed(0)} km to line`
                  : 'Sovereign EEZ'}
              </div>
            </div>

            <div className="inspector-col-divider" />

            {/* Habitat Column */}
            <div className="inspector-col">
              <div className="inspector-col-label">Suitability</div>
              <div className="inspector-col-val">
                {marine?.fishing_potential || decision?.habitat_status || '—'}
              </div>
              <div className="inspector-col-sub">
                {marine?.temperature != null ? `${marine.temperature.toFixed(1)}°C SST` : 'Copernicus'}
              </div>
            </div>

            <div className="inspector-col-divider" />

            {/* Weather Column */}
            <div className="inspector-col">
              <div className="inspector-col-label">Sea State</div>
              <div className="inspector-col-val">
                {weather?.risk_level ? weather.risk_level.replace(' Risk', '') : (decision?.weather_risk ? decision.weather_risk.replace(' Risk', '') : '—')}
              </div>
              <div className="inspector-col-sub">
                {(weather?.weather_conditions?.wind_speed_knots ?? weather?.wind_speed_knots) != null
                  ? `${(weather?.weather_conditions?.wind_speed_knots ?? weather?.wind_speed_knots)!.toFixed(0)} kn`
                  : ''
                }
                {(weather?.weather_conditions?.wave_height_meters ?? weather?.wave_height_meters) != null
                  ? ` · ${(weather?.weather_conditions?.wave_height_meters ?? weather?.wave_height_meters)!.toFixed(1)}m`
                  : ''
                }
              </div>
            </div>
          </div>

          <div className="inspector-divider" />

          {/* Provenance */}
          <div className="inspector-provenance-row">
            <span className="inspector-meta-tag">
              {isLive ? 'LIVE · COPERNICUS' : `HISTORICAL · ${analysis.timestamp || ''}`}
            </span>
          </div>

          {/* Expandable factors */}
          {hasFactors && (
            <>
              <button
                className="spatial-expand-btn"
                onClick={() => setShowFactors(!showFactors)}
                aria-expanded={showFactors}
              >
                <span>View Decision Factors &amp; Advisories</span>
                {showFactors ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>

              {showFactors && (
                <div className="animate-fade-in" style={{ marginTop: 10 }}>
                  {decision.reasons && decision.reasons.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 5, letterSpacing: '0.04em' }}>
                        Decision Rationale
                      </div>
                      <ul style={{ margin: 0, paddingLeft: 15, display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {decision.reasons.map((r: string, i: number) => (
                          <li key={i} style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {decision.warnings && decision.warnings.length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 5, letterSpacing: '0.04em' }}>
                        Safety Advisories
                      </div>
                      <ul style={{ margin: 0, paddingLeft: 15, display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {decision.warnings.map((w: string, i: number) => (
                          <li key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Ask ORCA CTA */}
          {loc && (
            <button
              className="inspector-cta-btn"
              id="btn-ask-orca-spatial"
              onClick={() => onAskOrca(loc.display_name, loc.latitude, loc.longitude)}
              aria-label="Open Decision Assistant for this sector"
            >
              <MessageSquare size={13} />
              <span>Ask ORCA About This Sector</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
