import React, { useState, useEffect, useRef } from 'react';
import { 
  MarineMap 
} from '../MarineMap';
import { 
  LayerControlPanel, 
  SpatialLayerType 
} from './LayerControlPanel';
import { 
  SelectedLocationPanel 
} from './SelectedLocationPanel';
import { 
  PointAnalysisResponse, 
  LocationContext 
} from '../../types/api';
import { 
  fetchPointAnalysis 
} from '../../services/spatialApi';
import { 
  Compass, 
  Calendar, 
  Navigation, 
  Layers, 
  MessageSquare,
  AlertCircle
} from 'lucide-react';

interface MarineSpatialViewProps {
  currentLocationContext: LocationContext | null;
  onUpdateLocationContext: (loc: LocationContext) => void;
  observationDate: string | null;
  onOpenDateModal: () => void;
  onSwitchToChatWithLocation: (locName: string, lat: number, lon: number) => void;
}

export const MarineSpatialView: React.FC<MarineSpatialViewProps> = ({
  currentLocationContext,
  onUpdateLocationContext,
  observationDate,
  onOpenDateModal,
  onSwitchToChatWithLocation,
}) => {
  // Layer states
  const [showEez, setShowEez] = useState(true);
  const [activeLayer, setActiveLayer] = useState<SpatialLayerType>('none');
  const [isLoadingLayer, setIsLoadingLayer] = useState(false);

  // Selected coordinate analysis
  const [selectedCoords, setSelectedCoords] = useState<{ lat: number; lon: number }>({
    lat: currentLocationContext?.latitude ?? 15.41,
    lon: currentLocationContext?.longitude ?? 73.80,
  });

  const [pointAnalysis, setPointAnalysis] = useState<PointAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPanelVisible, setIsPanelVisible] = useState(true);

  // Map control hooks
  const fitEezRef = useRef<(() => void) | null>(null);
  const resetViewRef = useRef<(() => void) | null>(null);

  // Click-to-analyze handler
  const handleSelectCoordinates = (lat: number, lon: number) => {
    setSelectedCoords({ lat, lon });
    setIsPanelVisible(true);
    setIsAnalyzing(true);

    fetchPointAnalysis(lat, lon, observationDate)
      .then((res) => {
        setPointAnalysis(res);
        if (res.success && res.location) {
          onUpdateLocationContext({
            latitude: res.location.latitude,
            longitude: res.location.longitude,
            display_name: res.location.display_name,
            source: 'map',
            timestamp: new Date().toISOString(),
          });
        }
      })
      .catch((err) => {
        console.error('Point analysis error:', err);
      })
      .finally(() => {
        setIsAnalyzing(false);
      });
  };

  // Initial load analysis on mount or coordinate change
  useEffect(() => {
    if (selectedCoords.lat && selectedCoords.lon && !pointAnalysis && !isAnalyzing) {
      handleSelectCoordinates(selectedCoords.lat, selectedCoords.lon);
    }
  }, []);

  return (
    <div className="spatial-view-container animate-fade-in">
      {/* Top Floating Mini-Nav for Spatial Context */}
      <div className="spatial-top-bar">
        <div className="spatial-top-pill">
          <Compass size={14} color="var(--cyan-primary)" />
          <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>
            {currentLocationContext?.display_name || 'Indian West Coast Maritime Grid'}
          </span>
          <span style={{ color: 'var(--text-muted)' }}>
            ({selectedCoords.lat.toFixed(2)}° N, {selectedCoords.lon.toFixed(2)}° E)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button className="spatial-top-btn" onClick={onOpenDateModal} title="Change observation date">
            <Calendar size={13} color="var(--cyan-primary)" />
            <span>{observationDate && observationDate !== 'today' ? `Historical: ${observationDate}` : 'Today (LIVE)'}</span>
          </button>

          <button 
            className="spatial-top-btn primary"
            onClick={() => onSwitchToChatWithLocation(
              currentLocationContext?.display_name || 'Selected Sector',
              selectedCoords.lat,
              selectedCoords.lon
            )}
            title="Switch to conversational decision support"
          >
            <MessageSquare size={13} />
            <span>Ask ORCA AI</span>
          </button>
        </div>
      </div>

      {/* Centerpiece Marine Map */}
      <MarineMap
        initialLat={selectedCoords.lat}
        initialLon={selectedCoords.lon}
        selectedLat={selectedCoords.lat}
        selectedLon={selectedCoords.lon}
        showEez={showEez}
        activeLayer={activeLayer}
        observationDate={observationDate}
        onSelectCoordinates={handleSelectCoordinates}
        onFitEezReady={(fitFn) => { fitEezRef.current = fitFn; }}
        onResetViewReady={(resetFn) => { resetViewRef.current = resetFn; }}
        onLayerLoadingChange={setIsLoadingLayer}
      />

      {/* Floating Layer Control Panel (Bottom-Left) */}
      <LayerControlPanel
        showEez={showEez}
        onToggleEez={setShowEez}
        activeLayer={activeLayer}
        onChangeLayer={setActiveLayer}
        onFitEez={() => fitEezRef.current?.()}
        onResetView={() => resetViewRef.current?.()}
        isLoadingLayer={isLoadingLayer}
      />

      {/* Floating Selected Location / Analysis Panel (Right Side) */}
      {isPanelVisible && (
        <SelectedLocationPanel
          analysis={pointAnalysis}
          isLoading={isAnalyzing}
          onClose={() => setIsPanelVisible(false)}
          onAskOrca={(name, lat, lon) => onSwitchToChatWithLocation(name, lat, lon)}
        />
      )}
    </div>
  );
};
