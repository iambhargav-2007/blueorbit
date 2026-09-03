import React, { useState } from 'react';
import { 
  MapPin, 
  X, 
  ChevronRight, 
  ChevronDown, 
  ShieldCheck, 
  ShieldAlert, 
  Wind, 
  Fish, 
  Compass, 
  Orbit, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle,
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import { PointAnalysisResponse } from '../../types/api';

interface SelectedLocationPanelProps {
  analysis: PointAnalysisResponse | null;
  isLoading: boolean;
  onClose: () => void;
  onAskOrca: (locationName: string, lat: number, lon: number) => void;
}

export const SelectedLocationPanel: React.FC<SelectedLocationPanelProps> = ({
  analysis,
  isLoading,
  onClose,
  onAskOrca,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!analysis && !isLoading) {
    return (
      <div className="spatial-floating-panel empty animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)' }}>
          <Compass size={16} color="var(--cyan-primary)" />
          <span style={{ fontSize: '12.5px' }}>Click anywhere on the maritime map to analyze ocean conditions</span>
        </div>
      </div>
    );
  }

  const loc = analysis?.location;
  const decision = analysis?.decision;
  const geo = analysis?.geofence;
  const marine = analysis?.marine;
  const weather = analysis?.weather;
  const isLive = analysis?.temporal_mode === 'LIVE';

  const getDecisionBadge = (d?: string | null) => {
    switch ((d || '').toUpperCase()) {
      case 'FAVORABLE':
        return {
          label: 'FAVORABLE',
          icon: <CheckCircle2 size={15} color="var(--emerald)" />,
          color: 'var(--emerald)',
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.3)',
        };
      case 'CAUTION':
        return {
          label: 'CAUTION',
          icon: <AlertTriangle size={15} color="var(--amber)" />,
          color: 'var(--amber)',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.3)',
        };
      case 'NOT_RECOMMENDED':
        return {
          label: 'NOT RECOMMENDED',
          icon: <XCircle size={15} color="var(--rose)" />,
          color: 'var(--rose)',
          bg: 'rgba(244, 63, 94, 0.12)',
          border: 'rgba(244, 63, 94, 0.3)',
        };
      default:
        return {
          label: 'INSUFFICIENT DATA',
          icon: <HelpCircle size={15} color="var(--text-muted)" />,
          color: 'var(--text-muted)',
          bg: 'rgba(148, 163, 184, 0.1)',
          border: 'rgba(148, 163, 184, 0.25)',
        };
    }
  };

  const badge = getDecisionBadge(decision?.decision);

  return (
    <div className="spatial-floating-panel active animate-fade-in">
      {/* Header */}
      <div className="spatial-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="spatial-pin-badge">
            <MapPin size={14} color="var(--cyan-primary)" />
          </div>
          <div>
            <div className="spatial-panel-title">
              {loc?.display_name || 'Selected Maritime Point'}
            </div>
            <div className="spatial-panel-coords">
              {loc ? `${loc.latitude.toFixed(3)}° N · ${loc.longitude.toFixed(3)}° E` : '—'}
            </div>
          </div>
        </div>

        <button className="btn-icon-subtle" onClick={onClose} aria-label="Close location panel">
          <X size={15} />
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="spatial-analyzing-state">
          <div className="spatial-radar-spinner">
            <Loader2 size={18} className="animate-spin" color="var(--cyan-primary)" />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-normal)' }}>
              Analyzing Marine Sector...
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
              Synthesizing Copernicus SST, chlorophyll, weather safety & EEZ boundary
            </div>
          </div>
        </div>
      )}

      {/* Results Content */}
      {!isLoading && analysis && (
        <div className="spatial-panel-body">
          {/* Decision Highlight Banner */}
          {decision && (
            <div 
              className="spatial-decision-banner"
              style={{ background: badge.bg, borderColor: badge.border }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: badge.color, fontWeight: 700, fontSize: '13px' }}>
                {badge.icon}
                <span>{badge.label}</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {decision.overall_score !== null && decision.overall_score !== undefined ? (
                  <span>Decision Index: <strong style={{ color: badge.color }}>{decision.overall_score.toFixed(1)}/100</strong></span>
                ) : (
                  <span>Data Incomplete</span>
                )}
              </div>
            </div>
          )}

          {/* Core Pillar Metrics */}
          <div className="spatial-metrics-grid">
            {/* EEZ Status */}
            <div className="spatial-metric-card">
              <div className="spatial-metric-label">
                <Compass size={12} color="var(--cyan-primary)" />
                <span>EEZ Boundary</span>
              </div>
              <div className="spatial-metric-val">
                {geo?.status === 'SAFE' ? (
                  <span style={{ color: 'var(--emerald)' }}>● Inside EEZ</span>
                ) : geo?.status === 'WARNING' ? (
                  <span style={{ color: 'var(--amber)' }}>▲ Buffer Warning</span>
                ) : (
                  <span style={{ color: 'var(--rose)' }}>✖ Outside EEZ</span>
                )}
              </div>
              <div className="spatial-metric-sub">
                {geo?.distance_to_boundary_km !== null && geo?.distance_to_boundary_km !== undefined
                  ? `${geo.distance_to_boundary_km.toFixed(1)} km to line`
                  : 'Boundary checked'}
              </div>
            </div>

            {/* Habitat Potential */}
            <div className="spatial-metric-card">
              <div className="spatial-metric-label">
                <Fish size={12} color="var(--emerald)" />
                <span>Habitat Potential</span>
              </div>
              <div className="spatial-metric-val">
                {marine?.fishing_potential || decision?.habitat_status || '—'}
              </div>
              <div className="spatial-metric-sub">
                {marine?.temperature !== null && marine?.temperature !== undefined ? `${marine.temperature.toFixed(1)}°C SST` : '—'}
                {marine?.chlorophyll !== null && marine?.chlorophyll !== undefined ? ` · ${marine.chlorophyll.toFixed(2)} mg/m³` : ''}
              </div>
            </div>

            {/* Marine Weather Safety */}
            <div className="spatial-metric-card">
              <div className="spatial-metric-label">
                <Wind size={12} color="var(--amber)" />
                <span>Weather Risk</span>
              </div>
              <div className="spatial-metric-val">
                {weather?.risk_level || decision?.weather_risk || '—'}
              </div>
              <div className="spatial-metric-sub">
                {weather?.weather_conditions?.wind_speed_knots !== undefined
                  ? `${weather.weather_conditions.wind_speed_knots.toFixed(0)} kn wind`
                  : weather?.wind_speed_knots !== undefined
                  ? `${weather.wind_speed_knots.toFixed(0)} kn wind`
                  : '—'}
                {weather?.weather_conditions?.wave_height_meters !== undefined
                  ? ` · ${weather.weather_conditions.wave_height_meters.toFixed(1)}m wave`
                  : weather?.wave_height_meters !== undefined
                  ? ` · ${weather.wave_height_meters.toFixed(1)}m wave`
                  : ''}
              </div>
            </div>
          </div>

          {/* Provenance Tag */}
          <div className="spatial-provenance-row">
            <span className="source-pill" style={{ fontSize: '10.5px', padding: '2px 8px' }}>
              {isLive ? 'Live Marine Synthesis' : `Historical Observation · ${analysis.timestamp}`}
            </span>
            {decision?.limiting_factor && (
              <span className="source-pill" style={{ fontSize: '10.5px', padding: '2px 8px', color: 'var(--cyan-primary)' }}>
                Factor: {decision.limiting_factor}
              </span>
            )}
          </div>

          {/* Expandable Reasons & Advisories */}
          {decision && ((decision.reasons && decision.reasons.length > 0) || (decision.warnings && decision.warnings.length > 0)) && (
            <div style={{ marginTop: '8px' }}>
              <button 
                className="spatial-expand-btn"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                <span>{isExpanded ? 'Hide Decision Factors' : 'View Factors & Guidance'}</span>
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>

              {isExpanded && (
                <div className="spatial-expanded-factors animate-fade-in">
                  {decision.reasons && decision.reasons.length > 0 && (
                    <div style={{ marginBottom: '6px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '3px' }}>
                        Rationale:
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11.5px', color: 'var(--text-normal)', lineHeight: 1.4 }}>
                        {decision.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {decision.warnings && decision.warnings.length > 0 && (
                    <div>
                      <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--amber)', marginBottom: '3px' }}>
                        Advisories:
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11px', color: 'var(--text-normal)', lineHeight: 1.35 }}>
                        {decision.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Action: Ask ORCA in Assistant */}
          {loc && (
            <div style={{ marginTop: '10px' }}>
              <button 
                className="btn-primary" 
                style={{ width: '100%', fontSize: '12px', padding: '8px 12px', justifyContent: 'center' }}
                onClick={() => onAskOrca(loc.display_name, loc.latitude, loc.longitude)}
              >
                <MessageSquare size={14} />
                <span>Ask ORCA About This Sector</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
