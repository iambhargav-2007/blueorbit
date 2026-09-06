import React from 'react';
import { GitCompare, Calendar, Radio, Thermometer, Droplet } from 'lucide-react';
import { ComparisonResult } from '../../types/api';

interface ComparisonResultCardProps {
  comparison: ComparisonResult;
  scientificExplanation?: string | null;
  fishermanAdvice?: string | null;
}

export const ComparisonResultCard: React.FC<ComparisonResultCardProps> = ({
  comparison,
  scientificExplanation,
  fishermanAdvice,
}) => {
  const hist = comparison.historical;
  const curr = comparison.current;

  const histRes = hist.result || {};
  const currRes = curr.result || {};

  return (
    <div className="result-card animate-fade-in">
      <div className="result-card-header">
        <div className="result-card-title">
          <GitCompare size={16} color="var(--accent)" />
          <span>Multi-Temporal Comparative Analysis</span>
        </div>
        <span className="temporal-tag">
          Step 16 Smart Dual Routing
        </span>
      </div>

      <div className="result-card-body">
        {/* Dual Panels */}
        <div className="comparison-grid">
          {/* Historical Column */}
          <div className="comparison-column">
            <div className="comparison-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11.5px', fontWeight: 500, color: 'var(--text-secondary)' }}>
                <Calendar size={13} />
                <span>HISTORICAL BASELINE</span>
              </div>
              <span className="temporal-tag">{hist.date}</span>
            </div>

            <div style={{ padding: '8px 0' }}>
              <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Suitability Rating</div>
              <div style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text-primary)' }}>
                {histRes.overall_suitability_score !== null && histRes.overall_suitability_score !== undefined
                  ? `${histRes.overall_suitability_score}/100 (${histRes.fishing_potential})`
                  : histRes.fishing_potential || '—'}
              </div>
            </div>

            <div className="metrics-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <div className="metric-item">
                <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <Thermometer size={11} />
                  <span>SST</span>
                </div>
                <div className="metric-data sm">
                  {histRes.temperature_c !== null && histRes.temperature_c !== undefined
                    ? `${histRes.temperature_c.toFixed(2)} °C`
                    : '—'}
                </div>
              </div>

              <div className="metric-item">
                <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <Droplet size={11} />
                  <span>Chlorophyll</span>
                </div>
                <div className="metric-data sm">
                  {histRes.chlorophyll_mg_m3 !== null && histRes.chlorophyll_mg_m3 !== undefined
                    ? `${histRes.chlorophyll_mg_m3.toFixed(3)} mg/m³`
                    : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Current Column */}
          <div className="comparison-column current">
            <div className="comparison-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11.5px', fontWeight: 500, color: 'var(--text-primary)' }}>
                <Radio size={13} color="var(--accent)" />
                <span>CURRENT CONDITIONS</span>
              </div>
              <span className="temporal-tag">LIVE · {curr.date}</span>
            </div>

            <div style={{ padding: '8px 0' }}>
              <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Suitability Rating</div>
              <div style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text-primary)' }}>
                {currRes.overall_suitability_score !== null && currRes.overall_suitability_score !== undefined
                  ? `${currRes.overall_suitability_score}/100 (${currRes.fishing_potential})`
                  : currRes.fishing_potential || '—'}
              </div>
            </div>

            <div className="metrics-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <div className="metric-item">
                <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <Thermometer size={11} />
                  <span>SST</span>
                </div>
                <div className="metric-data" style={{ fontSize: '13px' }}>
                  {currRes.temperature_c !== null && currRes.temperature_c !== undefined
                    ? `${currRes.temperature_c.toFixed(2)} °C`
                    : '—'}
                </div>
              </div>

              <div className="metric-item">
                <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <Droplet size={11} />
                  <span>Chlorophyll</span>
                </div>
                <div className="metric-data" style={{ fontSize: '13px' }}>
                  {currRes.chlorophyll_mg_m3 !== null && currRes.chlorophyll_mg_m3 !== undefined
                    ? `${currRes.chlorophyll_mg_m3.toFixed(3)} mg/m³`
                    : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Comparison Narratives */}
        <div className="card-narrative-section">
          {scientificExplanation && (
            <div className="narrative-item scientific">
              <strong>Comparative Synthesis:</strong> {scientificExplanation}
            </div>
          )}

          {fishermanAdvice && (
            <div className="narrative-item advice">
              <strong>Tactical Guidance:</strong> {fishermanAdvice}
            </div>
          )}

          <div className="disclaimer-text">
            Zero mixing policy: Historical and live observations are evaluated independently through their respective deterministic engines.
          </div>
        </div>
      </div>
    </div>
  );
};
