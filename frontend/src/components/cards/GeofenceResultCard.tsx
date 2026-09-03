import React from 'react';
import { Shield, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { GeofencingAgentResponse } from '../../types/api';

interface GeofenceResultCardProps {
  data: GeofencingAgentResponse;
}

export const GeofenceResultCard: React.FC<GeofenceResultCardProps> = ({ data }) => {
  const isInside = data.is_inside_eez ?? true;
  const status = data.status || (isInside ? 'SAFE' : 'OUTSIDE EEZ');
  const distance = data.distance_to_boundary_km;

  const getStatusClass = (st: string) => {
    switch (st.toUpperCase()) {
      case 'SAFE':
        return 'status-high';
      case 'WARNING':
        return 'status-moderate';
      case 'OUTSIDE EEZ':
      case 'DANGER':
        return 'status-low';
      default:
        return 'status-insufficient';
    }
  };

  return (
    <div className="result-card animate-fade-in">
      <div className="result-card-header">
        <div className="result-card-title">
          <Shield size={16} color={isInside ? 'var(--emerald)' : 'var(--rose)'} />
          <span>Maritime Border & EEZ Spatial Compliance</span>
        </div>
        <span className="temporal-tag" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
          WGS84 Geometric Engine
        </span>
      </div>

      <div className="result-card-body">
        {/* Border Status Highlight */}
        <div className="metric-highlight-panel">
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Jurisdiction Zone
            </div>
            <div className="metric-highlight-value" style={{ fontSize: '20px', marginTop: '4px' }}>
              {data.zone_name || (isInside ? 'Indian Sovereign EEZ' : 'International / External Waters')}
            </div>
          </div>
          <div className={`metric-highlight-category ${getStatusClass(status)}`}>
            {status}
          </div>
        </div>

        {/* Spatial Metrics */}
        <div className="metrics-grid">
          <div className="metric-item">
            <div className="metric-label">EEZ Interior Status</div>
            <div className="metric-data" style={{ color: isInside ? 'var(--emerald)' : 'var(--rose)' }}>
              {isInside ? 'Inside Sovereign EEZ' : 'Outside Indian EEZ'}
            </div>
          </div>

          <div className="metric-item">
            <div className="metric-label">Distance to Boundary</div>
            <div className="metric-data">
              {distance !== null && distance !== undefined ? `${distance.toFixed(1)} km` : '—'}
            </div>
          </div>
        </div>

        {/* Narrative & Disclaimer */}
        <div className="card-narrative-section">
          {data.geofence_narrative && (
            <div className="narrative-item scientific">
              <strong>Spatial Analysis:</strong> {data.geofence_narrative}
            </div>
          )}

          {data.geofence_advice && (
            <div className="narrative-item advice">
              <strong>Navigation Advisory:</strong> {data.geofence_advice}
            </div>
          )}

          <div className="disclaimer-text">
            Notice: Position relative to the Indian EEZ boundary does not constitute legal fishing permission or bilateral maritime border clearance.
          </div>
        </div>
      </div>
    </div>
  );
};
