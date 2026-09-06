import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocationContext } from '../types/api';
import { fetchEezGeoJson, fetchGridLayer } from '../services/spatialApi';
import { SpatialLayerType } from './spatial/LayerControlPanel';
import { useTheme } from '../contexts/ThemeContext';

interface MarineMapProps {
  initialLat?: number;
  initialLon?: number;
  selectedLat?: number | null;
  selectedLon?: number | null;
  showEez?: boolean;
  activeLayer?: SpatialLayerType;
  observationDate?: string | null;
  onSelectCoordinates: (lat: number, lon: number) => void;
  onFitEezReady?: (fitFn: () => void) => void;
  onResetViewReady?: (resetFn: () => void) => void;
  onLayerLoadingChange?: (loading: boolean) => void;
  showLiveVessels?: boolean;
  routePoints?: {latitude: number, longitude: number, hazard_state?: string | null}[] | null;
}

export const MarineMap: React.FC<MarineMapProps> = ({
  initialLat = 17.5,
  initialLon = 71.5,
  selectedLat,
  selectedLon,
  showEez = true,
  activeLayer = 'none',
  observationDate,
  onSelectCoordinates,
  onFitEezReady,
  onResetViewReady,
  onLayerLoadingChange,
  showLiveVessels = false,
  routePoints,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const eezLayerRef = useRef<L.GeoJSON | null>(null);
  const gridLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const vesselLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const routeLayerGroupRef = useRef<L.LayerGroup | null>(null);
  
  const baseLayerRef = useRef<L.TileLayer | null>(null);
  const labelLayerRef = useRef<L.TileLayer | null>(null);
  const { theme } = useTheme();

  const [eezGeoJson, setEezGeoJson] = useState<any>(null);
  const [vessels, setVessels] = useState<any[]>([]);

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const startLat = selectedLat ?? initialLat;
    const startLon = selectedLon ?? initialLon;

    const map = L.map(mapContainerRef.current, {
      center: [startLat, startLon],
      zoom: 6,
      minZoom: 4,
      maxZoom: 13,
      zoomControl: false, // We'll add custom positioned controls
      dragging: true,
      touchZoom: true,
      scrollWheelZoom: true,
    });

    // Base Layer
    const baseLayerUrl = theme === 'dark'
      ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
      : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}';
      
    baseLayerRef.current = L.tileLayer(baseLayerUrl, {
      attribution: '&copy; Esri &mdash; Blue Orbit Maritime Intelligence',
      maxZoom: 16,
    }).addTo(map);

    // Reference Labels
    const labelLayerUrl = theme === 'dark'
      ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}'
      : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}';
      
    labelLayerRef.current = L.tileLayer(labelLayerUrl, {
      maxZoom: 16,
      pane: 'shadowPane',
    }).addTo(map);

    // Reposition zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(map);

    // Layer group for grid cells
    const gridGroup = L.layerGroup().addTo(map);
    gridLayerGroupRef.current = gridGroup;

    // Layer group for live vessels
    const vesselGroup = L.layerGroup().addTo(map);
    vesselLayerGroupRef.current = vesselGroup;

    // Layer group for route
    const routeGroup = L.layerGroup().addTo(map);
    routeLayerGroupRef.current = routeGroup;

    // Custom maritime marker icon — clean dot with subtle ring
    const marineIcon = L.divIcon({
      className: 'custom-marine-marker',
      html: `
        <div class="marine-radar-marker">
          <div class="marker-pulse-ring"></div>
          <div class="marker-center-dot"></div>
        </div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });

    // Marker
    const marker = L.marker([startLat, startLon], {
      icon: marineIcon,
      draggable: true,
      zIndexOffset: 1000,
    }).addTo(map);

    marker.on('dragend', (e: any) => {
      const pos = e.target.getLatLng();
      const clampedLat = Math.round(pos.lat * 1000) / 1000;
      const clampedLon = Math.round(pos.lng * 1000) / 1000;
      onSelectCoordinates(clampedLat, clampedLon);
    });

    // Click to analyze
    map.on('click', (e: L.LeafletMouseEvent) => {
      const clampedLat = Math.round(e.latlng.lat * 1000) / 1000;
      const clampedLon = Math.round(e.latlng.lng * 1000) / 1000;
      marker.setLatLng([clampedLat, clampedLon]);
      onSelectCoordinates(clampedLat, clampedLon);
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;

    // Expose View Functions
    if (onResetViewReady) {
      onResetViewReady(() => {
        map.setView([17.5, 71.5], 6, { animate: true });
      });
    }

    // Invalidate size
    setTimeout(() => {
      map.invalidateSize();
    }, 250);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
      eezLayerRef.current = null;
      gridLayerGroupRef.current = null;
    };
  }, []);

  // 1.5 Dynamic Theme Swap for Map Tiles
  useEffect(() => {
    if (baseLayerRef.current) {
      baseLayerRef.current.setUrl(
        theme === 'dark'
          ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
          : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
      );
    }
    if (labelLayerRef.current) {
      labelLayerRef.current.setUrl(
        theme === 'dark'
          ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}'
          : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}'
      );
    }
  }, [theme]);

  // 2. Fetch & Render Real EEZ GeoJSON
  useEffect(() => {
    let isMounted = true;
    fetchEezGeoJson()
      .then((data) => {
        if (!isMounted) return;
        setEezGeoJson(data);

        const map = mapInstanceRef.current;
        if (!map) return;

        if (eezLayerRef.current) {
          map.removeLayer(eezLayerRef.current);
        }

        const eezLayer = L.geoJSON(data, {
          interactive: false,
          style: {
            color: '#9C6B3E', // --accent
            weight: 2,
            dashArray: '5, 5',
            fillColor: 'transparent',
            fillOpacity: 0,
            opacity: 1,
            interactive: false,
          },
        });

        if (showEez) {
          eezLayer.addTo(map);
        }
        eezLayerRef.current = eezLayer;

        if (onFitEezReady) {
          onFitEezReady(() => {
            if (eezLayerRef.current && mapInstanceRef.current) {
              mapInstanceRef.current.fitBounds(eezLayerRef.current.getBounds(), {
                padding: [30, 30],
                animate: true,
              });
            }
          });
        }
      })
      .catch((err) => {
        console.warn('EEZ GeoJSON load notice:', err);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // 3. Toggle EEZ Visibility
  useEffect(() => {
    const map = mapInstanceRef.current;
    const eezLayer = eezLayerRef.current;
    if (!map || !eezLayer) return;

    if (showEez) {
      if (!map.hasLayer(eezLayer)) {
        eezLayer.addTo(map);
      }
    } else {
      if (map.hasLayer(eezLayer)) {
        map.removeLayer(eezLayer);
      }
    }
  }, [showEez]);

  // 4. Update Marker Position when selected coordinates change externally
  useEffect(() => {
    if (selectedLat !== undefined && selectedLat !== null && selectedLon !== undefined && selectedLon !== null) {
      if (markerRef.current) {
        markerRef.current.setLatLng([selectedLat, selectedLon]);
      }
      if (mapInstanceRef.current) {
        mapInstanceRef.current.panTo([selectedLat, selectedLon], { animate: true });
      }
    }
  }, [selectedLat, selectedLon]);

  // 5. Fetch & Render Real Gridded Data Layers
  useEffect(() => {
    const group = gridLayerGroupRef.current;
    if (!group) return;

    group.clearLayers();

    if (activeLayer === 'none') {
      if (onLayerLoadingChange) onLayerLoadingChange(false);
      return;
    }

    let isMounted = true;
    if (onLayerLoadingChange) onLayerLoadingChange(true);

    // Cyclone layer not rendered via grid tiles
    if (activeLayer === 'cyclone') {
      if (onLayerLoadingChange) onLayerLoadingChange(false);
      return;
    }

    fetchGridLayer(activeLayer, observationDate, 3)
      .then((gridData) => {
        if (!isMounted || !mapInstanceRef.current || !gridLayerGroupRef.current) return;

        const cells = gridData.cells || [];
        const getColor = (cat: string) => {
          switch (cat) {
            case 'sst-warm': return '#F43F5E';
            case 'sst-optimal': return '#06B6D4';
            case 'sst-cool': return '#3B82F6';
            case 'chl-high': return '#10B981';
            case 'chl-moderate': return '#14B8A6';
            case 'chl-low': return '#64748B';
            case 'habitat-high': return '#10B981';
            case 'habitat-moderate': return '#F59E0B';
            case 'habitat-low': return '#F43F5E';
            case 'weather-high-risk': return '#F43F5E';
            case 'weather-moderate-risk': return '#F59E0B';
            case 'weather-low-risk': return '#10B981';
            default: return '#06B6D4';
          }
        };

        cells.forEach((cell) => {
          const color = getColor(cell.category);
          const circle = L.circleMarker([cell.lat, cell.lon], {
            radius: activeLayer === 'weather' ? 6 : 4.5,
            fillColor: color,
            fillOpacity: activeLayer === 'weather' ? 0.75 : 0.6,
            color: color,
            weight: 1,
            opacity: 0.9,
          });

          circle.bindTooltip(
            `
            <div style="font-family: inherit; font-size: 11px;">
              <strong>${cell.label}</strong>
              <div style="color: #94A3B8; font-size: 10px;">${cell.lat.toFixed(2)}° N, ${cell.lon.toFixed(2)}° E</div>
            </div>
            `,
            { className: 'custom-marine-tooltip', sticky: true }
          );

          circle.on('click', (e: L.LeafletMouseEvent) => {
            L.DomEvent.stopPropagation(e);
            if (markerRef.current) {
              markerRef.current.setLatLng([cell.lat, cell.lon]);
            }
            onSelectCoordinates(cell.lat, cell.lon);
          });

          gridLayerGroupRef.current?.addLayer(circle);
        });

        if (onLayerLoadingChange) onLayerLoadingChange(false);
      })
      .catch((err) => {
        console.warn(`Layer ${activeLayer} fetch notice:`, err);
        if (onLayerLoadingChange) onLayerLoadingChange(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeLayer, observationDate, onSelectCoordinates]);

  // 6. Live Vessel Polling and Rendering
  useEffect(() => {
    let intervalId: any;
    
    const fetchVessels = async () => {
      try {
        const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE}/api/v1/vessels/`);
        let data = await response.json();
        
        if (Array.isArray(data)) {
          // Prevent React/Leaflet crash by limiting to 500 markers max globally
          data = data.slice(0, 500);
          const vesselCount = data.length;
          console.log(`[AIS DEBUG]\nAPI COUNT: ${vesselCount}\nSTATE COUNT: ${vessels.length}`);
          
          if (vesselCount > 0) {
            const first = data[0];
            console.log(`[AIS DEBUG] FIRST VESSEL:\n  MMSI: ${first.mmsi}\n  LAT: ${first.latitude}\n  LON: ${first.longitude}`);
          }
          setVessels(data);
        } else {
          console.error('[AIS DEBUG] API returned non-array payload:', data);
          setVessels([]);
        }
      } catch (err) {
        console.error('Failed to fetch live vessels:', err);
      }
    };

    if (showLiveVessels) {
      fetchVessels();
      intervalId = setInterval(fetchVessels, 15000);
    } else {
      setVessels([]);
      if (vesselLayerGroupRef.current) {
        vesselLayerGroupRef.current.clearLayers();
      }
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [showLiveVessels]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const vesselGroup = vesselLayerGroupRef.current;
    if (!map || !vesselGroup) return;

    vesselGroup.clearLayers();
    
    if (vessels.length === 0) return;

    // Basic vessel icon for debugging/rendering
    const vesselIcon = L.divIcon({
      className: 'custom-vessel-marker',
      html: `
        <div style="background-color: #9C6B3E; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; z-index: 1000;"></div>
      `,
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });

    let validCount = 0;

    vessels.forEach((v) => {
      if (typeof v.latitude === 'number' && typeof v.longitude === 'number') {
        validCount++;
        console.log(`[AIS MARKER DEBUG]\nMMSI: ${v.mmsi}\nLAT: ${v.latitude}\nLON: ${v.longitude}`);
        
        const marker = L.marker([v.latitude, v.longitude], {
          icon: vesselIcon,
          zIndexOffset: 2000, // Ensure it floats above
        });
        
        marker.bindPopup(`
          <div style="font-family: inherit; font-size: 11px;">
            <strong>MMSI:</strong> ${v.mmsi}<br/>
            <strong>Name:</strong> ${v.vessel_name || 'N/A'}<br/>
            <strong>Speed:</strong> ${v.speed_over_ground || 'N/A'}<br/>
            <strong>Status:</strong> ${v.data_status}<br/>
          </div>
        `);
        
        vesselGroup.addLayer(marker);
      }
    });
    
    console.log(`[AIS DEBUG] VALID COUNT: ${validCount}`);

  }, [vessels]);

  // 7. Route Rendering
  useEffect(() => {
    const map = mapInstanceRef.current;
    const routeGroup = routeLayerGroupRef.current;
    if (!map || !routeGroup) return;

    routeGroup.clearLayers();

    if (!routePoints || routePoints.length < 2) return;

    const latlngs = routePoints.map((pt) => [pt.latitude, pt.longitude] as [number, number]);

    // Draw main polyline
    const polyline = L.polyline(latlngs, {
      color: '#3B82F6', // Blue route
      weight: 4,
      opacity: 0.8,
      dashArray: '10, 10',
      lineJoin: 'round',
    });
    
    routeGroup.addLayer(polyline);

    // Draw hazard points if any
    routePoints.forEach((pt) => {
      if (pt.hazard_state && pt.hazard_state !== 'SAFE') {
        const circle = L.circleMarker([pt.latitude, pt.longitude], {
          radius: 4,
          fillColor: pt.hazard_state === 'BLOCKED' ? '#EF4444' : '#F59E0B',
          color: pt.hazard_state === 'BLOCKED' ? '#EF4444' : '#F59E0B',
          weight: 1,
          opacity: 0.9,
          fillOpacity: 1
        });
        routeGroup.addLayer(circle);
      }
    });

    // Fit bounds to route
    map.fitBounds(polyline.getBounds(), { padding: [40, 40], animate: true });

  }, [routePoints]);

  return (
    <div className="marine-map-wrapper">
      <div ref={mapContainerRef} className="marine-map-canvas" />
    </div>
  );
};
