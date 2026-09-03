/**
 * spatialApi.ts
 * Service for fetching spatial intelligence data from FastAPI:
 * - Real Indian EEZ GeoJSON
 * - Click-to-analyze single point intelligence
 * - Real Copernicus and Open-Meteo gridded layers
 */

import { PointAnalysisResponse, GridLayerResponse } from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

let _cachedEez: any = null;

export async function fetchEezGeoJson(): Promise<any> {
  if (_cachedEez) return _cachedEez;
  const res = await fetch(`${API_BASE}/api/v1/spatial/eez`);
  if (!res.ok) {
    throw new Error(`Failed to load EEZ boundary: ${res.statusText}`);
  }
  const data = await res.json();
  _cachedEez = data;
  return data;
}

export async function fetchPointAnalysis(
  lat: number,
  lon: number,
  date?: string | null
): Promise<PointAnalysisResponse> {
  const params = new URLSearchParams({
    lat: lat.toFixed(4),
    lon: lon.toFixed(4),
  });
  if (date && date !== 'today') {
    params.append('date', date);
  }

  const res = await fetch(`${API_BASE}/api/v1/spatial/point?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Spatial point analysis failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchGridLayer(
  layer: 'sst' | 'chlorophyll' | 'habitat' | 'weather',
  date?: string | null,
  step: number = 3
): Promise<GridLayerResponse> {
  const params = new URLSearchParams({
    layer,
    step: String(step),
  });
  if (date && date !== 'today') {
    params.append('date', date);
  }

  const res = await fetch(`${API_BASE}/api/v1/spatial/grid?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Spatial grid layer '${layer}' retrieval failed: ${res.statusText}`);
  }
  return res.json();
}
