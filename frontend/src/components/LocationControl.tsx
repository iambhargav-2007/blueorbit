import React, { useState, useEffect } from 'react';
import {
  Compass,
  X,
  MapPin,
  Navigation,
  Search,
  Map as MapIcon,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  SlidersHorizontal
} from 'lucide-react';
import { LocationContext } from '../types/api';
import { resolveLocation, getLocationSuggestions } from '../services/chatApi';
import { MarineMap } from './MarineMap';

interface LocationControlProps {
  currentLocationContext: LocationContext | null;
  onSaveLocation: (loc: LocationContext | null) => void;
  onClose: () => void;
}

type TabType = 'gps' | 'search' | 'map' | 'manual';

const WEST_COAST_PRESETS = [
  { name: 'Mumbai Coast', lat: 18.94, lon: 72.84 },
  { name: 'Goa Coastal Zone', lat: 15.41, lon: 73.80 },
  { name: 'Veraval Port (Gujarat)', lat: 20.90, lon: 70.37 },
  { name: 'Porbandar Coast', lat: 21.64, lon: 69.60 },
  { name: 'Kochi Offshore (Kerala)', lat: 9.96, lon: 76.22 },
  { name: 'Ratnagiri Coast', lat: 16.99, lon: 73.30 },
  { name: 'Standard Test Sector', lat: 19.50, lon: 70.50 },
];

export const LocationControl: React.FC<LocationControlProps> = ({
  currentLocationContext,
  onSaveLocation,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>(
    currentLocationContext?.source === 'gps' ? 'gps' :
    currentLocationContext?.source === 'map' ? 'map' :
    currentLocationContext?.source === 'search' ? 'search' : 'gps'
  );

  // GPS State
  const [isLocating, setIsLocating] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  // Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<LocationContext | null>(null);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const [searchSuggestions, setSearchSuggestions] = useState<string[]>([]);

  // Manual Coordinates State
  const [lat, setLat] = useState<string>(
    currentLocationContext ? String(currentLocationContext.latitude) : '19.50'
  );
  const [lon, setLon] = useState<string>(
    currentLocationContext ? String(currentLocationContext.longitude) : '70.50'
  );
  const [manualError, setManualError] = useState<string | null>(null);

  // Initial suggestions on mount
  useEffect(() => {
    getLocationSuggestions('').then((items) => {
      if (items && items.length > 0) setSearchSuggestions(items);
    });
  }, []);

  // Handler: Browser Geolocation
  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGpsError('Browser geolocation is unavailable on this device. Please search for a place or select a location on the map.');
      return;
    }

    setIsLocating(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = pos.coords;
        const latClamped = Math.round(coords.latitude * 1000) / 1000;
        const lonClamped = Math.round(coords.longitude * 1000) / 1000;
        const acc = Math.round(coords.accuracy);

        const newLoc: LocationContext = {
          latitude: latClamped,
          longitude: lonClamped,
          display_name: `Current Location (~${acc}m accuracy)`,
          source: 'gps',
          accuracy_m: acc,
          timestamp: new Date().toISOString(),
        };

        setIsLocating(false);
        onSaveLocation(newLoc);
        onClose();
      },
      (err) => {
        setIsLocating(false);
        if (err.code === err.PERMISSION_DENIED) {
          setGpsError('Location permission denied. Please allow access in your browser or search for a coastal place.');
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          setGpsError('Position unavailable. Search for a coastal place or choose on the map.');
        } else {
          setGpsError('Location request timed out. Please try again or search for a place.');
        }
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 }
    );
  };

  // Handler: Location Search
  const handleSearch = async (textToSearch?: string) => {
    const q = (textToSearch !== undefined ? textToSearch : searchQuery).trim();
    if (!q) return;

    setIsSearching(true);
    setSearchResult(null);
    setSearchMessage(null);

    const res = await resolveLocation(q);
    setIsSearching(false);

    if (res.success && res.location) {
      setSearchResult(res.location);
      setSearchSuggestions(res.suggestions || []);
    } else {
      setSearchMessage(res.message || 'Could not resolve coastal location.');
      setSearchSuggestions(res.suggestions || []);
    }
  };

  const handleApplySearchResult = () => {
    if (searchResult) {
      onSaveLocation(searchResult);
      onClose();
    }
  };

  // Handler: Manual Coordinates Save
  const handleSaveManual = () => {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);

    if (isNaN(latNum) || latNum < -90 || latNum > 90) {
      setManualError('Latitude must be a valid number between -90.0 and +90.0.');
      return;
    }
    if (isNaN(lonNum) || lonNum < -180 || lonNum > 180) {
      setManualError('Longitude must be a valid number between -180.0 and +180.0.');
      return;
    }

    onSaveLocation({
      latitude: latNum,
      longitude: lonNum,
      display_name: `${latNum.toFixed(2)}° N · ${lonNum.toFixed(2)}° E (Manual)`,
      source: 'manual',
    });
    onClose();
  };

  const handleSelectPreset = (preset: { name: string; lat: number; lon: number }) => {
    onSaveLocation({
      latitude: preset.lat,
      longitude: preset.lon,
      display_name: preset.name,
      source: 'search',
    });
    onClose();
  };

  const handleClear = () => {
    onSaveLocation(null);
    onClose();
  };

  return (
    <div className="popover-backdrop" onClick={onClose}>
      <div
        className="popover-panel animate-fade-in"
        style={{ maxWidth: '520px', width: '92%' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="popover-header">
          <div className="popover-title">
            <Compass size={18} color="var(--cyan-primary)" />
            <span>Marine Location Intelligence</span>
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '6px',
            marginBottom: '16px',
            background: 'var(--bg-card)',
            padding: '4px',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <button
            type="button"
            className={`preset-chip ${activeTab === 'gps' ? 'active' : ''}`}
            style={{ justifyContent: 'center', margin: 0, padding: '8px 4px', fontSize: '12px' }}
            onClick={() => setActiveTab('gps')}
          >
            <Navigation size={13} style={{ marginRight: '4px' }} />
            GPS
          </button>
          <button
            type="button"
            className={`preset-chip ${activeTab === 'search' ? 'active' : ''}`}
            style={{ justifyContent: 'center', margin: 0, padding: '8px 4px', fontSize: '12px' }}
            onClick={() => setActiveTab('search')}
          >
            <Search size={13} style={{ marginRight: '4px' }} />
            Search
          </button>
          <button
            type="button"
            className={`preset-chip ${activeTab === 'map' ? 'active' : ''}`}
            style={{ justifyContent: 'center', margin: 0, padding: '8px 4px', fontSize: '12px' }}
            onClick={() => setActiveTab('map')}
          >
            <MapIcon size={13} style={{ marginRight: '4px' }} />
            Map
          </button>
          <button
            type="button"
            className={`preset-chip ${activeTab === 'manual' ? 'active' : ''}`}
            style={{ justifyContent: 'center', margin: 0, padding: '8px 4px', fontSize: '12px' }}
            onClick={() => setActiveTab('manual')}
          >
            <SlidersHorizontal size={13} style={{ marginRight: '4px' }} />
            Coords
          </button>
        </div>

        {/* TAB 1: GPS / Browser Location */}
        {activeTab === 'gps' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div
              style={{
                background: 'rgba(6, 182, 212, 0.05)',
                border: '1px solid rgba(6, 182, 212, 0.2)',
                borderRadius: '8px',
                padding: '14px',
                textAlign: 'center',
              }}
            >
              <Navigation size={28} color="var(--cyan-primary)" style={{ margin: '0 auto 8px' }} />
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                Detect Current Device Position
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px', lineHeight: 1.4 }}>
                Uses browser high-accuracy GPS coordinates for immediate habitat, weather safety, and EEZ compliance assessment.
              </div>

              <button
                type="button"
                className="btn-primary"
                style={{ width: '100%', justifyContent: 'center', padding: '10px' }}
                onClick={handleUseCurrentLocation}
                disabled={isLocating}
              >
                {isLocating ? (
                  <>
                    <Loader2 size={16} className="animate-spin" style={{ marginRight: '8px' }} />
                    Acquiring GPS Signal...
                  </>
                ) : (
                  <>
                    <Navigation size={16} style={{ marginRight: '8px' }} />
                    Use My Location
                  </>
                )}
              </button>
            </div>

            {gpsError && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px',
                  borderRadius: '6px',
                  background: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  color: 'var(--rose)',
                  fontSize: '12px',
                }}
              >
                <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                <span>{gpsError}</span>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Place & Coast Search */}
        {activeTab === 'search' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <input
                  type="text"
                  className="text-input"
                  style={{ width: '100%', paddingLeft: '32px' }}
                  placeholder="e.g. Goa coast, Mumbai, Veraval..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSearch();
                  }}
                />
                <Search
                  size={15}
                  color="var(--text-muted)"
                  style={{ position: 'absolute', left: '10px', top: '11px' }}
                />
              </div>
              <button
                type="button"
                className="btn-primary"
                style={{ padding: '0 16px' }}
                onClick={() => handleSearch()}
                disabled={isSearching || !searchQuery.trim()}
              >
                {isSearching ? <Loader2 size={16} className="animate-spin" /> : 'Search'}
              </button>
            </div>

            {/* Resolved Place Result */}
            {searchResult && (
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.08)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: '8px',
                  padding: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <CheckCircle2 size={16} color="var(--emerald)" />
                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--emerald)' }}>
                    {searchResult.display_name}
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)', marginBottom: '10px' }}>
                  {searchResult.latitude.toFixed(2)}° N · {searchResult.longitude.toFixed(2)}° E
                </div>
                <button
                  type="button"
                  className="btn-primary"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={handleApplySearchResult}
                >
                  Select This Location
                </button>
              </div>
            )}

            {/* Advisory / Landlocked explanation */}
            {searchMessage && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  color: 'var(--amber)',
                  fontSize: '12px',
                }}
              >
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>{searchMessage}</div>
              </div>
            )}

            {/* Suggestions / Presets */}
            {searchSuggestions.length > 0 && (
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Coastal Suggestions
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {searchSuggestions.map((place) => (
                    <button
                      key={place}
                      type="button"
                      className="preset-chip"
                      style={{ fontSize: '11px' }}
                      onClick={() => {
                        setSearchQuery(place);
                        handleSearch(place);
                      }}
                    >
                      <MapPin size={11} style={{ marginRight: '4px' }} />
                      {place}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Interactive Marine Map */}
        {activeTab === 'map' && (
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
              Click anywhere on the Arabian Sea or drag the pin to select target coordinates.
            </div>
            <MarineMap
              initialLat={currentLocationContext?.latitude || 18.5}
              initialLon={currentLocationContext?.longitude || 71.5}
              onSelectLocation={(loc) => {
                onSaveLocation(loc);
                onClose();
              }}
            />
          </div>
        )}

        {/* TAB 4: Manual Coordinates */}
        {activeTab === 'manual' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div className="coord-inputs-grid">
              <div className="input-group">
                <label className="input-label" htmlFor="lat-input">Latitude (°N)</label>
                <input
                  id="lat-input"
                  type="number"
                  step="0.01"
                  min="-90"
                  max="90"
                  className="text-input"
                  placeholder="e.g. 19.50"
                  value={lat}
                  onChange={(e) => {
                    setLat(e.target.value);
                    setManualError(null);
                  }}
                />
              </div>
              <div className="input-group">
                <label className="input-label" htmlFor="lon-input">Longitude (°E)</label>
                <input
                  id="lon-input"
                  type="number"
                  step="0.01"
                  min="-180"
                  max="180"
                  className="text-input"
                  placeholder="e.g. 70.50"
                  value={lon}
                  onChange={(e) => {
                    setLon(e.target.value);
                    setManualError(null);
                  }}
                />
              </div>
            </div>

            {manualError && (
              <div style={{ fontSize: '12px', color: 'var(--rose)' }}>{manualError}</div>
            )}

            <div className="presets-container">
              <div className="presets-label">Indian West Coast Presets</div>
              <div className="presets-pills">
                {WEST_COAST_PRESETS.map((p) => (
                  <button
                    key={p.name}
                    type="button"
                    className="preset-chip"
                    onClick={() => handleSelectPreset(p)}
                  >
                    <MapPin size={11} style={{ marginRight: '4px' }} />
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleSaveManual}
            >
              Apply Coordinates
            </button>
          </div>
        )}

        {/* Footer Actions */}
        <div className="popover-actions" style={{ marginTop: '16px' }}>
          {currentLocationContext && (
            <button type="button" className="btn-secondary" onClick={handleClear}>
              Clear Location
            </button>
          )}
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
