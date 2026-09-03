import React, { useState } from 'react';
import { 
  Layers, 
  Eye, 
  EyeOff, 
  Thermometer, 
  Leaf, 
  Fish, 
  Wind, 
  Compass, 
  Maximize2, 
  RotateCcw,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export type SpatialLayerType = 'none' | 'sst' | 'chlorophyll' | 'habitat' | 'weather';

interface LayerControlPanelProps {
  showEez: boolean;
  onToggleEez: (show: boolean) => void;
  activeLayer: SpatialLayerType;
  onChangeLayer: (layer: SpatialLayerType) => void;
  onFitEez: () => void;
  onResetView: () => void;
  isLoadingLayer: boolean;
}

export const LayerControlPanel: React.FC<LayerControlPanelProps> = ({
  showEez,
  onToggleEez,
  activeLayer,
  onChangeLayer,
  onFitEez,
  onResetView,
  isLoadingLayer,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="spatial-layers-panel animate-fade-in">
      {/* Header */}
      <div 
        className="spatial-layers-header"
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={{ cursor: 'pointer' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <Layers size={14} color="var(--cyan-primary)" />
          <span style={{ fontWeight: 600, fontSize: '12.5px' }}>Marine Spatial Layers</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isLoadingLayer && (
            <span style={{ fontSize: '10.5px', color: 'var(--cyan-primary)' }}>Loading...</span>
          )}
          {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </div>
      </div>

      {!isCollapsed && (
        <div className="spatial-layers-body">
          {/* Boundary Toggle */}
          <div className="spatial-layer-toggle-row">
            <label style={{ display: 'flex', alignItems: 'center', gap: '7px', cursor: 'pointer', fontSize: '12px', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={showEez}
                onChange={(e) => onToggleEez(e.target.checked)}
                style={{ accentColor: 'var(--cyan-primary)' }}
              />
              <span style={{ fontWeight: 500 }}>Indian EEZ Boundary</span>
            </label>
            <span className="source-pill" style={{ fontSize: '10px', padding: '1px 6px' }}>Official</span>
          </div>

          <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '6px 0' }} />

          {/* Layer Selector */}
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '5px' }}>
            Oceanographic Grid
          </div>

          <div className="spatial-layer-buttons">
            <button
              className={`spatial-layer-btn ${activeLayer === 'none' ? 'active' : ''}`}
              onClick={() => onChangeLayer('none')}
            >
              <span>Basemap</span>
            </button>

            <button
              className={`spatial-layer-btn ${activeLayer === 'sst' ? 'active' : ''}`}
              onClick={() => onChangeLayer('sst')}
            >
              <Thermometer size={12} color="var(--rose)" />
              <span>SST (°C)</span>
            </button>

            <button
              className={`spatial-layer-btn ${activeLayer === 'chlorophyll' ? 'active' : ''}`}
              onClick={() => onChangeLayer('chlorophyll')}
            >
              <Leaf size={12} color="var(--emerald)" />
              <span>Chlorophyll-a</span>
            </button>

            <button
              className={`spatial-layer-btn ${activeLayer === 'habitat' ? 'active' : ''}`}
              onClick={() => onChangeLayer('habitat')}
            >
              <Fish size={12} color="var(--cyan-primary)" />
              <span>Habitat Potential</span>
            </button>

            <button
              className={`spatial-layer-btn ${activeLayer === 'weather' ? 'active' : ''}`}
              onClick={() => onChangeLayer('weather')}
            >
              <Wind size={12} color="var(--amber)" />
              <span>Weather Risk</span>
            </button>
          </div>

          {/* Scientific Legend */}
          {activeLayer !== 'none' && (
            <div className="spatial-layer-legend animate-fade-in">
              {activeLayer === 'sst' && (
                <div>
                  <div className="legend-label">Sea Surface Temperature (Copernicus)</div>
                  <div className="legend-gradient-bar sst-gradient" />
                  <div className="legend-scale-labels">
                    <span>Cool &lt;28°C</span>
                    <span>Optimal 28–29.5°C</span>
                    <span>Warm &gt;29.5°C</span>
                  </div>
                </div>
              )}

              {activeLayer === 'chlorophyll' && (
                <div>
                  <div className="legend-label">Chlorophyll-a (Copernicus BGC)</div>
                  <div className="legend-gradient-bar chl-gradient" />
                  <div className="legend-scale-labels">
                    <span>&lt;0.2 mg/m³</span>
                    <span>0.2–0.5 mg/m³</span>
                    <span>&gt;0.5 mg/m³</span>
                  </div>
                </div>
              )}

              {activeLayer === 'habitat' && (
                <div>
                  <div className="legend-label">Habitat Suitability Index (ORCA Engine)</div>
                  <div className="legend-gradient-bar habitat-gradient" />
                  <div className="legend-scale-labels">
                    <span>Low (&lt;50)</span>
                    <span>Moderate (50–74)</span>
                    <span>High (75–100)</span>
                  </div>
                </div>
              )}

              {activeLayer === 'weather' && (
                <div>
                  <div className="legend-label">Marine Sea-State Risk (Open-Meteo)</div>
                  <div className="legend-gradient-bar weather-gradient" />
                  <div className="legend-scale-labels">
                    <span>Low Risk (&lt;15kn)</span>
                    <span>Caution (15–25kn)</span>
                    <span>High Risk (&gt;25kn)</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Map Utility Actions */}
          <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
            <button className="spatial-util-btn" onClick={onFitEez} title="Fit to Indian EEZ Boundary">
              <Maximize2 size={12} />
              <span>Fit EEZ</span>
            </button>
            <button className="spatial-util-btn" onClick={onResetView} title="Reset to West Coast Center">
              <RotateCcw size={12} />
              <span>Reset</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
