import React from 'react';
import { Waves, Thermometer, Droplet, CheckCircle2, AlertCircle } from 'lucide-react';
import { FishingAgentResponse } from '../../types/api';

interface HabitatResultCardProps {
  data: FishingAgentResponse;
}

export const HabitatResultCard: React.FC<HabitatResultCardProps> = ({ data }) => {
  const potential = data.fishing_potential || 'Insufficient Data';
  const score = data.habitat_score;
  const temporalMode = data.temporal_mode || (data.date === 'today' ? 'LIVE' : 'HISTORICAL');
  const summary = data.environmental_summary;

  const getStatusClass = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'high':
        return 'status-high';
      case 'moderate':
        return 'status-moderate';
      case 'low':
        return 'status-low';
      default:
        return 'status-insufficient';
    }
  };

  const isLive = temporalMode === 'LIVE';

  return (
    <div className="result-card animate-fade-in">
      <div className="result-card-header">
        <div className="result-card-title">
          <Waves size={16} color="var(--cyan-primary)" />
          <span>Habitat Suitability Assessment</span>
        </div>
        <span className={`temporal-tag ${isLive ? 'live' : 'historical'}`}>
          {isLive ? '● Live Marine Data' : `Historical · ${data.date || 'Cache'}`}
        </span>
      </div>

      <div className="result-card-body">
        {/* Score Highlight */}
        <div className="metric-highlight-panel">
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Suitability Index
            </div>
            <div className="metric-highlight-value">
              {score !== null && score !== undefined ? `${score.toFixed(1)}/100` : '—'}
            </div>
          </div>
          <div className={`metric-highlight-category ${getStatusClass(potential)}`}>
            {potential} Potential
          </div>
        </div>

        {/* Environmental Indicators */}
        <div className="metrics-grid">
          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Thermometer size={12} />
              <span>Near-Surface SST</span>
            </div>
            <div className="metric-data">
              {summary?.temperature_c !== null && summary?.temperature_c !== undefined
                ? `${summary.temperature_c.toFixed(2)} °C`
                : 'Masked / Null'}
            </div>
          </div>

          <div className="metric-item">
            <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Droplet size={12} />
              <span>Chlorophyll-a</span>
            </div>
            <div className="metric-data">
              {summary?.chlorophyll_mg_m3 !== null && summary?.chlorophyll_mg_m3 !== undefined
                ? `${summary.chlorophyll_mg_m3.toFixed(3)} mg/m³`
                : 'Masked / Null'}
            </div>
          </div>

          <div className="metric-item">
            <div className="metric-label">Data Completeness</div>
            <div className="metric-data" style={{ fontSize: '13px' }}>
              {data.data_quality || 'Complete'}
            </div>
          </div>

          <div className="metric-item">
            <div className="metric-label">Confidence</div>
            <div className="metric-data" style={{ fontSize: '13px' }}>
              {data.confidence || 'Moderate'}
            </div>
          </div>
        </div>

        {/* Narratives */}
        <div className="card-narrative-section">
          {data.scientific_explanation && (
            <div className="narrative-item scientific">
              <strong>Scientific Assessment:</strong> {data.scientific_explanation}
            </div>
          )}

          {data.fisherman_advice && (
            <div className="narrative-item advice">
              <strong>Practical Guidance:</strong> {data.fisherman_advice}
            </div>
          )}

          <div className="disclaimer-text">
            {data.disclaimer || 'Prototype heuristic habitat suitability model based on environmental indicators.'}
          </div>
        </div>
      </div>
    </div>
  );
};
