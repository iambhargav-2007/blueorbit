import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation } from 'lucide-react';
import { LocationContext } from '../types/api';

interface MarineMapProps {
  initialLat?: number;
  initialLon?: number;
  onSelectLocation: (loc: LocationContext) => void;
}

export const MarineMap: React.FC<MarineMapProps> = ({
  initialLat = 18.5,
  initialLon = 71.5,
  onSelectLocation,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  const [selectedLat, setSelectedLat] = useState<number>(initialLat);
  const [selectedLon, setSelectedLon] = useState<number>(initialLon);

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Custom maritime pulsing icon
    const marineIcon = L.divIcon({
      className: 'custom-marine-marker',
      html: `
        <div style="
          width: 22px;
          height: 22px;
          background: #06B6D4;
          border: 2.5px solid #FFFFFF;
          border-radius: 50%;
          box-shadow: 0 0 16px rgba(6, 182, 212, 0.9), 0 0 0 6px rgba(6, 182, 212, 0.25);
          cursor: pointer;
        "></div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 6,
      minZoom: 4,
      maxZoom: 14,
      zoomControl: true,
    });

    // Dark sleek maritime tiles (CartoDB Dark Matter / Voyager)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> | Blue Orbit Maritime',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    // Initial marker
    const marker = L.marker([initialLat, initialLon], {
      icon: marineIcon,
      draggable: true,
    }).addTo(map);

    marker.on('dragend', (e: any) => {
      const position = e.target.getLatLng();
      const clampedLat = Math.round(position.lat * 1000) / 1000;
      const clampedLon = Math.round(position.lng * 1000) / 1000;
      setSelectedLat(clampedLat);
      setSelectedLon(clampedLon);
    });

    map.on('click', (e: L.LeafletMouseEvent) => {
      const clampedLat = Math.round(e.latlng.lat * 1000) / 1000;
      const clampedLon = Math.round(e.latlng.lng * 1000) / 1000;
      marker.setLatLng([clampedLat, clampedLon]);
      setSelectedLat(clampedLat);
      setSelectedLon(clampedLon);
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;

    // Trigger resize after render
    setTimeout(() => {
      map.invalidateSize();
    }, 200);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
    };
  }, []);

  const handleConfirm = () => {
    onSelectLocation({
      latitude: selectedLat,
      longitude: selectedLon,
      display_name: `${selectedLat.toFixed(2)}° N · ${selectedLon.toFixed(2)}° E (Map Selection)`,
      source: 'map',
      timestamp: new Date().toISOString(),
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '280px',
          borderRadius: '10px',
          overflow: 'hidden',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'inset 0 0 12px rgba(0,0,0,0.6)',
        }}
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: 'var(--bg-card)',
          borderRadius: '8px',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Navigation size={15} color="var(--cyan-primary)" />
          <span style={{ fontSize: '12px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-main)' }}>
            {selectedLat >= 0 ? `${selectedLat.toFixed(2)}° N` : `${Math.abs(selectedLat).toFixed(2)}° S`} ·{' '}
            {selectedLon >= 0 ? `${selectedLon.toFixed(2)}° E` : `${Math.abs(selectedLon).toFixed(2)}° W`}
          </span>
        </div>

        <button
          type="button"
          className="btn-primary"
          style={{ padding: '6px 14px', fontSize: '12px' }}
          onClick={handleConfirm}
        >
          Confirm Pin
        </button>
      </div>
    </div>
  );
};
