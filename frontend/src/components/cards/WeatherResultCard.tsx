import React from 'react';
import { Wind, Waves, Gauge, Compass, ShieldAlert, ShieldCheck, Activity, Info } from 'lucide-react';
import { WeatherSafetyAgentResponse } from '../../types/api';

interface WeatherResultCardProps {
  data: WeatherSafetyAgentResponse;
}

export const WeatherResultCard: React.FC<WeatherResultCardProps> = ({ data }) => {
  const risk = data.risk_level || 'Moderate';
  const conditions = data.conditions || data.weather_conditions;
  const score = data.safety_score ?? conditions?.overall_safety_score;
  const isLive = data.temporal_mode === 'LIVE' || data.observation_type === 'current_observation';
  const isHistorical = data.temporal_mode === 'HISTORICAL' || data.observation_type === 'historical_observation';

  const getRiskClass = (r: string) => {
    switch (r.toLowerCase()) {
      case 'low':
      case 'low risk':
        return 'status-high'; // Green
      case 'moderate':
      case 'moderate risk':
        return 'status-moderate'; // Amber
      case 'high':
      case 'high risk':
      case 'critical':
      case 'very high risk':
        return 'status-low'; // Red
      default:
        return 'status-insufficient';
    }
  };

  const isSafe = risk.toLowerCase().includes('low');

  return (
    <div className="result-card animate-fade-in">
      {/* Header */}
      <div className="result-card-header">
        <div className="result-card-title">
          <Wind size={16} color="var(--cyan-primary)" />
          <span>Marine Weather & Sea State Safety</span>
        </div>
        <span className={`temporal-tag ${isLive ? 'live' : isHistorical ? 'cache' : ''}`}>
          {isLive ? 'Live Marine Observation' : isHistorical ? `Historical — ${data.date || 'Oct 2025'}` : 'Weather Observation'}
        </span>
      </div>

      <div className="result-card-body">
        {/* Risk Highlight */}
        <div className="metric-highlight-panel">
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Safety Score
            </div>
            <div className="metric-highlight-value">
              {score !== null && score !== undefined ? `${score.toFixed(1)}/100` : '—'}
            </div>
          </div>
          <div className={`metric-highlight-category ${getRiskClass(risk)}`}>
            {risk.toUpperCase().includes('RISK') ? risk : `${risk} Risk`}
          </div>
        </div>

        {/* Provenance and Quality Metadata Badges */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', margin: '10px 0 14px' }}>
          {data.limiting_factor && (
            <span className="source-pill" style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--amber)', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
              Limiting Factor: {data.limiting_factor}
            </span>
          )}
          {data.confidence && (
            <span className="source-pill">
              Confidence: {data.confidence}
            </span>
          )}
          {data.data_quality && (
            <span className="source-pill">
              Data: {data.data_quality}
            </span>
          )}
          {data.source && (
            <span className="source-pill" style={{ background: 'rgba(6, 182, 212, 0.08)', color: 'var(--cyan-primary)' }}>
              {data.source}
            </span>
          )}
        </div>

        {/* Sea State Conditions Grid */}
        <div className="metrics-grid">
          {/* Wind Speed */}
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Wind size={12} />
              <span>Wind Speed</span>
            </div>
            <div className="metric-data">
              {conditions?.wind_speed_knots !== null && conditions?.wind_speed_knots !== undefined
                ? `${conditions.wind_speed_knots.toFixed(1)} kn`
                : '—'}
              {conditions?.wind_direction && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                  ({conditions.wind_direction})
                </span>
              )}
            </div>
          </div>

          {/* Significant Waves */}
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Waves size={12} />
              <span>Significant Waves</span>
            </div>
            <div className="metric-data">
              {conditions?.wave_height_meters !== null && conditions?.wave_height_meters !== undefined
                ? `${conditions.wave_height_meters.toFixed(2)} m`
                : '—'}
              {conditions?.wave_period_seconds && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                  · {conditions.wave_period_seconds.toFixed(1)}s
                </span>
              )}
            </div>
          </div>

          {/* Surface Pressure */}
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Gauge size={12} />
              <span>Surface Pressure</span>
            </div>
            <div className="metric-data">
              {conditions?.surface_pressure_hpa !== null && conditions?.surface_pressure_hpa !== undefined
                ? `${conditions.surface_pressure_hpa.toFixed(0)} hPa`
                : '—'}
            </div>
          </div>

          {/* Operational Advisory */}
          <div className="metric-item">
            <div className="metric-label">Operational Status</div>
            <div className="metric-data" style={{ fontSize: '13px', color: isSafe ? 'var(--emerald)' : 'var(--amber)' }}>
              {isSafe ? 'Normal Operations' : 'Safety Advisory Active'}
            </div>
          </div>
        </div>

        {/* Narratives */}
        <div className="card-narrative-section">
          {data.safety_narrative && (
            <div className="narrative-item scientific">
              <strong>Weather Assessment:</strong> {data.safety_narrative}
            </div>
          )}

          {data.safety_advice && (
            <div className="narrative-item advice">
              <strong>Decision Support Guidance:</strong> {data.safety_advice}
            </div>
          )}

          <div className="disclaimer-text">
            {data.disclaimer || 'This is a prototype decision-support indicator. It does not guarantee vessel safety or represent official maritime safety standards.'}
          </div>
        </div>
      </div>
    </div>
  );
};
