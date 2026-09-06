import React from 'react';
import { Wind, Waves, Gauge, ShieldAlert, ShieldCheck } from 'lucide-react';
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

  const riskLower = risk.toLowerCase();
  const isLowRisk = riskLower.includes('low');
  const isHighRisk = riskLower.includes('very high') || riskLower.includes('critical');
  const isModerate = riskLower.includes('moderate');

  const heroClass = isLowRisk ? 'favorable' : isHighRisk ? 'danger' : 'caution';
  const verdictClass = heroClass;
  const RiskIcon = isLowRisk ? ShieldCheck : ShieldAlert;

  return (
    <div className="result-card animate-fade-in" id="weather-result-card">
      <div className="result-card-header">
        <div className="result-card-title">
          <Wind size={14} color="var(--accent)" />
          <span>Weather Safety</span>
        </div>
        <span className={`temporal-tag ${isLive ? 'live' : isHistorical ? 'cache' : ''}`}>
          {isLive ? 'Live Observation' : isHistorical ? `Historical · ${data.date || 'Oct 2025'}` : 'Observation'}
        </span>
      </div>

      <div className="result-card-body">
        {/* Flattened Risk Hero with Left Border Accent — no box-within-a-box */}
        <div className={`decision-accent-hero ${heroClass}`}>
          <div>
            <div className="decision-accent-label">
              Sea State Risk
            </div>
            <div className={`decision-verdict ${verdictClass}`} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <RiskIcon size={15} />
              <span>{risk.replace(' Risk', '')}</span>
            </div>
            {data.limiting_factor && (
              <div className="decision-limiting-factor">
                Limiting factor: <span>{data.limiting_factor}</span>
              </div>
            )}
          </div>
          {score != null && (
            <div className="decision-score-block">
              <div className="decision-score">{score.toFixed(0)}</div>
              <div className="decision-score-label">Safety Score</div>
            </div>
          )}
        </div>

        {/* Single row of label+value pairs separated by thin dividers — not four separate bordered tiles */}
        <div className="metrics-row-divided">
          <div className="divided-metric-col">
            <div className="metric-label"><Wind size={10} /> Wind</div>
            <div className="metric-data">
              {conditions?.wind_speed_knots != null
                ? `${conditions.wind_speed_knots.toFixed(1)}`
                : '—'}
              <span className="metric-unit"> kn</span>
            </div>
            <div className="metric-sub">
              {conditions?.wind_direction || 'Wind speed'}
            </div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label"><Waves size={10} /> Waves</div>
            <div className="metric-data">
              {conditions?.wave_height_meters != null
                ? `${conditions.wave_height_meters.toFixed(1)}`
                : '—'}
              <span className="metric-unit"> m</span>
            </div>
            <div className="metric-sub">
              {conditions?.wave_period_seconds
                ? `${conditions.wave_period_seconds.toFixed(0)}s period`
                : 'Significant wave'}
            </div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label"><Gauge size={10} /> Pressure</div>
            <div className="metric-data">
              {conditions?.surface_pressure_hpa != null
                ? `${conditions.surface_pressure_hpa.toFixed(0)}`
                : '—'}
              <span className="metric-unit"> hPa</span>
            </div>
            <div className="metric-sub">Barometric</div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label">Status</div>
            <div className="metric-data sm" style={{ color: isLowRisk ? 'var(--success)' : 'var(--warning)' }}>
              {isLowRisk ? 'Normal' : 'Advisory'}
            </div>
            <div className="metric-sub">Operational</div>
          </div>
        </div>

        {/* Source */}
        {data.source && (
          <div style={{ marginTop: 8 }}>
            <span className="source-pill">{data.source}</span>
            {data.confidence && <span className="source-pill" style={{ marginLeft: 5 }}>Confidence: {data.confidence}</span>}
          </div>
        )}

        {/* Narrative */}
        {(data.safety_narrative || data.safety_advice) && (
          <div className="card-narrative-section">
            {data.safety_narrative && (
              <div className="narrative-item scientific">{data.safety_narrative}</div>
            )}
            {data.safety_advice && (
              <div className="narrative-item advice">{data.safety_advice}</div>
            )}
          </div>
        )}

        <div className="disclaimer-text">
          {data.disclaimer || 'Prototype decision-support indicator. Does not represent official maritime safety standards.'}
        </div>
      </div>
    </div>
  );
};
