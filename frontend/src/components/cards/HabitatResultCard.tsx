import React from 'react';
import { Thermometer, Droplet, Activity } from 'lucide-react';
import { FishingAgentResponse } from '../../types/api';

interface HabitatResultCardProps {
  data: FishingAgentResponse;
}

export const HabitatResultCard: React.FC<HabitatResultCardProps> = ({ data }) => {
  const potential = data.fishing_potential || 'Insufficient Data';
  const score = data.habitat_score;
  const temporalMode = data.temporal_mode || (data.date === 'today' ? 'LIVE' : 'HISTORICAL');
  const summary = data.environmental_summary;
  const isLive = temporalMode === 'LIVE';

  const potLower = potential.toLowerCase();
  const heroClass = potLower === 'high' ? 'favorable' : potLower === 'moderate' ? 'caution' : potLower === 'low' ? 'danger' : 'neutral';
  const verdictClass = heroClass;

  return (
    <div className="result-card animate-fade-in" id="habitat-result-card">
      <div className="result-card-header">
        <div className="result-card-title">
          <Activity size={14} color="var(--accent)" />
          <span>Environmental Suitability</span>
        </div>
        <span className={`temporal-tag ${isLive ? 'live' : 'cache'}`}>
          {isLive ? 'Live' : `Historical · ${data.date || 'Cache'}`}
        </span>
      </div>

      <div className="result-card-body">
        {/* Suitability Hero with Left Border Accent */}
        <div className={`decision-accent-hero ${heroClass}`}>
          <div>
            <div className="decision-accent-label">
              Marine Habitat Suitability
            </div>
            <div className={`decision-verdict ${verdictClass}`}>
              {potential}
            </div>
          </div>
          {score != null && (
            <div className="decision-score-block">
              <div className="decision-score">{score.toFixed(0)}</div>
              <div className="decision-score-label">Suitability Score</div>
            </div>
          )}
        </div>

        {/* Ocean indicators — single divided row */}
        <div className="metrics-row-divided">
          <div className="divided-metric-col">
            <div className="metric-label"><Thermometer size={10} /> Sea Surface Temp</div>
            <div className="metric-data">
              {summary?.temperature_c != null
                ? `${summary.temperature_c.toFixed(1)}°C`
                : '—'}
            </div>
            <div className="metric-sub">{summary?.temperature_c != null ? 'Copernicus' : 'No data'}</div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label"><Droplet size={10} /> Chlorophyll-a</div>
            <div className="metric-data">
              {summary?.chlorophyll_mg_m3 != null
                ? `${summary.chlorophyll_mg_m3.toFixed(3)}`
                : '—'}
              <span className="metric-unit"> mg/m³</span>
            </div>
            <div className="metric-sub">Biological activity</div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label">Data Quality</div>
            <div className="metric-data sm">{data.data_quality || 'Complete'}</div>
            <div className="metric-sub">Copernicus Grid</div>
          </div>

          <div className="metric-divider-line" />

          <div className="divided-metric-col">
            <div className="metric-label">Confidence</div>
            <div className="metric-data sm">{data.confidence || 'Moderate'}</div>
            <div className="metric-sub">Model certainty</div>
          </div>
        </div>

        {/* Narratives */}
        {(data.scientific_explanation || data.fisherman_advice) && (
          <div className="card-narrative-section">
            {data.scientific_explanation && (
              <div className="narrative-item scientific">{data.scientific_explanation}</div>
            )}
            {data.fisherman_advice && (
              <div className="narrative-item advice">{data.fisherman_advice}</div>
            )}
          </div>
        )}

        <div className="disclaimer-text">
          {data.disclaimer || 'Environmental indicator based on available marine observations — not a direct fish-abundance prediction.'}
        </div>
      </div>
    </div>
  );
};
