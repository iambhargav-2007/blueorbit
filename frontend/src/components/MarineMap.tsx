import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LocationContext } from '../types/api';
import { fetchEezGeoJson, fetchGridLayer } from '../services/spatialApi';
import { SpatialLayerType } from './spatial/LayerControlPanel';

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
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const eezLayerRef = useRef<L.GeoJSON | null>(null);
  const gridLayerGroupRef = useRef<L.LayerGroup | null>(null);

  const [eezGeoJson, setEezGeoJson] = useState<any>(null);

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
    });

    // Dark sleek maritime basemap (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap | Blue Orbit Maritime',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    // Reposition zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(map);

    // Layer group for grid cells
    const gridGroup = L.layerGroup().addTo(map);
    gridLayerGroupRef.current = gridGroup;

    // Custom maritime pulsing marker icon
    const marineIcon = L.divIcon({
      className: 'custom-marine-marker',
      html: `
        <div class="marine-radar-marker">
          <div class="marker-pulse-ring"></div>
          <div class="marker-center-dot"></div>
        </div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
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
          style: {
            color: '#06B6D4',
            weight: 1.8,
            dashArray: '6, 6',
            fillColor: '#06B6D4',
            fillOpacity: 0.04,
            opacity: 0.85,
          },
          onEachFeature: (feature, layer) => {
            layer.bindTooltip('Indian Exclusive Economic Zone (EEZ)', {
              sticky: true,
              className: 'custom-marine-tooltip',
            });
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

  return (
    <div className="marine-map-wrapper">
      <div ref={mapContainerRef} className="marine-map-canvas" />
    </div>
  );
};
