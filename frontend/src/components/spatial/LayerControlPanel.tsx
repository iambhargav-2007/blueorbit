import React, { useState } from 'react';
import {
  Layers, Thermometer, Leaf, Fish, Wind,
  Maximize2, RotateCcw, ChevronDown, ChevronUp
} from 'lucide-react';

export type SpatialLayerType = 'none' | 'sst' | 'chlorophyll' | 'habitat' | 'weather' | 'cyclone';

interface LayerControlPanelProps {
  showEez: boolean;
  onToggleEez: (show: boolean) => void;
  showLiveVessels: boolean;
  onToggleLiveVessels: (show: boolean) => void;
  activeLayer: SpatialLayerType;
  onChangeLayer: (layer: SpatialLayerType) => void;
  onFitEez: () => void;
  onResetView: () => void;
  isLoadingLayer: boolean;
}

const LAYERS: { id: SpatialLayerType; label: string; icon: React.ReactNode; sub?: string }[] = [
  { id: 'none',        label: 'Basemap',       icon: null },
  { id: 'sst',         label: 'SST',           icon: <Thermometer size={11} />, sub: 'LIVE' },
  { id: 'chlorophyll', label: 'Chlorophyll-a', icon: <Leaf size={11} />,        sub: 'LIVE' },
  { id: 'habitat',     label: 'Suitability',   icon: <Fish size={11} />,        sub: 'ORCA' },
  { id: 'weather',     label: 'Weather Risk',  icon: <Wind size={11} />,        sub: 'LIVE' },
  { id: 'cyclone',     label: 'Cyclone',       icon: <Wind size={11} />,        sub: 'IMD' },
];

const LEGEND: Record<string, { label: string; gradient: string; ticks: string[] }> = {
  sst: {
    label: 'Sea Surface Temperature',
    gradient: 'linear-gradient(to right, #0ea5e9, #06b6d4, #fbbf24, #ef4444)',
    ticks: ['<27°C', '28–29.5°C', '>30°C'],
  },
  chlorophyll: {
    label: 'Chlorophyll-a (mg/m³)',
    gradient: 'linear-gradient(to right, #1a3a1a, #16a34a, #86efac)',
    ticks: ['<0.2', '0.2–1.5', '>1.5'],
  },
  habitat: {
    label: 'Habitat Suitability Index',
    gradient: 'linear-gradient(to right, #ef4444, #fbbf24, #34d399)',
    ticks: ['Low', 'Moderate', 'High'],
  },
  weather: {
    label: 'Marine Sea-State Risk',
    gradient: 'linear-gradient(to right, #34d399, #fbbf24, #ef4444)',
    ticks: ['Low (<15kn)', 'Caution', 'High (>25kn)'],
  },
  cyclone: {
    label: 'Severe Weather Alerts',
    gradient: 'linear-gradient(to right, rgba(248,113,113,0.1), rgba(248,113,113,0.9))',
    ticks: ['Clear', 'Elevated', 'Severe'],
  },
};

export const LayerControlPanel: React.FC<LayerControlPanelProps> = ({
  showEez,
  onToggleEez,
  showLiveVessels,
  onToggleLiveVessels,
  activeLayer,
  onChangeLayer,
  onFitEez,
  onResetView,
  isLoadingLayer,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  const legend = activeLayer !== 'none' ? LEGEND[activeLayer] : null;

  return (
    <div className="spatial-layers-panel animate-fade-in" id="layer-control-panel">
      {/* Header */}
      <div className="spatial-layers-header" onClick={() => setCollapsed(!collapsed)} role="button" aria-expanded={!collapsed}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <Layers size={13} color="var(--accent)" />
          <span style={{ fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)' }}>
            Marine Layers
          </span>
          {isLoadingLayer && (
            <span style={{ fontSize: 10, color: 'var(--accent)' }}>Loading…</span>
          )}
        </div>
        {collapsed ? <ChevronDown size={13} color="var(--text-muted)" /> : <ChevronUp size={13} color="var(--text-muted)" />}
      </div>

      {!collapsed && (
        <div className="spatial-layers-body">
          {/* EEZ toggle */}
          <div className="spatial-layer-toggle-row">
            <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', fontSize: 12, userSelect: 'none', color: 'var(--text-secondary)' }}>
              <input
                id="toggle-eez"
                type="checkbox"
                checked={showEez}
                onChange={(e) => onToggleEez(e.target.checked)}
                style={{ accentColor: 'var(--accent)', width: 13, height: 13 }}
                aria-label="Toggle Indian EEZ Boundary"
              />
              <span style={{ fontWeight: 500 }}>Indian EEZ Boundary</span>
            </label>
            <span className="source-pill" style={{ fontSize: 9.5 }}>Official</span>
          </div>

          <div style={{ height: 1, background: 'var(--border-subtle)', margin: '7px 0' }} />

          {/* LIVE INTELLIGENCE */}
          <div style={{ fontSize: 9.5, fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>
            Live Intelligence
          </div>
          <div className="spatial-layer-toggle-row" style={{ marginBottom: '10px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', fontSize: 12, userSelect: 'none', color: 'var(--text-secondary)' }}>
              <input
                id="toggle-live-vessels"
                type="checkbox"
                checked={showLiveVessels}
                onChange={(e) => onToggleLiveVessels(e.target.checked)}
                style={{ accentColor: 'var(--accent)', width: 13, height: 13 }}
                aria-label="Toggle Live Vessels"
              />
              <span style={{ fontWeight: 500 }}>Live Vessels</span>
            </label>
            <span className="source-pill" style={{ fontSize: 9.5 }}>AISStream · Current</span>
          </div>

          <div style={{ height: 1, background: 'var(--border-subtle)', margin: '7px 0' }} />

          {/* Layer label */}
          <div style={{ fontSize: 9.5, fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>
            Oceanographic Grid
          </div>

          {/* Layer buttons */}
          <div className="spatial-layer-buttons">
            {LAYERS.map((l) => (
              <button
                key={l.id}
                id={`layer-btn-${l.id}`}
                className={`spatial-layer-btn ${activeLayer === l.id ? 'active' : ''}`}
                onClick={() => onChangeLayer(l.id)}
                aria-pressed={activeLayer === l.id}
                title={l.label}
              >
                {l.icon && <span style={{ opacity: 0.8 }}>{l.icon}</span>}
                <span>{l.label}</span>
                {l.sub && activeLayer === l.id && (
                  <span style={{ fontSize: 9, marginLeft: 'auto', opacity: 0.7 }}>{l.sub}</span>
                )}
              </button>
            ))}
          </div>

          {/* Legend */}
          {legend && (
            <div className="spatial-layer-legend animate-fade-in">
              <div className="legend-label">{legend.label}</div>
              <div
                className="legend-gradient-bar"
                style={{ background: legend.gradient }}
                aria-hidden="true"
              />
              <div className="legend-ticks">
                {legend.ticks.map((t) => <span key={t}>{t}</span>)}
              </div>
            </div>
          )}

          {/* Map actions */}
          <div className="spatial-map-controls">
            <button className="spatial-map-btn" onClick={onFitEez} title="Fit to Indian EEZ" id="btn-fit-eez">
              <Maximize2 size={11} />
              <span>Fit EEZ</span>
            </button>
            <button className="spatial-map-btn" onClick={onResetView} title="Reset map view" id="btn-reset-view">
              <RotateCcw size={11} />
              <span>Reset</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// [AIS_STUB] Live Vessels toggle added here
