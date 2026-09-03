/**
 * chatApi.ts
 * Dedicated API service layer for communicating with Blue Orbit FastAPI backend.
 */

import { ChatRequest, CoordinatorResponse, ClarificationRequired, ApiResponse } from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Checks backend health endpoint GET /api/health
 */
export async function checkBackendHealth(): Promise<{ healthy: boolean; status: string }> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(`${API_BASE}/api/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      return { healthy: data.status === 'healthy', status: data.status || 'running' };
    }
    return { healthy: false, status: `HTTP ${res.status}` };
  } catch (err: any) {
    return { healthy: false, status: 'offline' };
  }
}

/**
 * Sends chat turn to POST /api/v1/chat
 */
export async function sendChatMessage(request: ChatRequest): Promise<ApiResponse> {
  const payload: Record<string, any> = {
    session_id: request.session_id,
    message: request.message.trim(),
  };

  if (request.latitude !== undefined && request.latitude !== null) {
    payload.latitude = request.latitude;
  }
  if (request.longitude !== undefined && request.longitude !== null) {
    payload.longitude = request.longitude;
  }
  if (request.date_str && request.date_str.trim()) {
    payload.date_str = request.date_str.trim();
  }
  if (request.location_context) {
    payload.location_context = request.location_context;
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let errorDetail = `Server returned status ${res.status}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' 
            ? errorJson.detail 
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // use fallback message
      }
      throw new ApiError(errorDetail, res.status);
    }

    const data: ApiResponse = await res.json();
    return data;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out while waiting for marine intelligence backend.');
    }
    if (err.message && err.message.includes('Failed to fetch')) {
      throw new ApiError('Unable to connect to Blue Orbit backend. Please ensure the backend is running at http://localhost:8000.');
    }
    throw new ApiError(err.message || 'An unexpected error occurred while communicating with the backend.');
  }
}

/**
 * Resolves location query via POST /api/v1/location/resolve
 */
export async function resolveLocation(query: string): Promise<import('../types/api').LocationResolveResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/location/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.trim() }),
    });
    if (!res.ok) {
      throw new Error(`Location resolution failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err: any) {
    return {
      success: false,
      message: err.message || 'Location resolution unavailable.',
      suggestions: ['Mumbai Coast', 'Goa Coastal Zone', 'Veraval Port', 'Kochi Offshore'],
    };
  }
}

/**
 * Fetches coastal place suggestions via GET /api/v1/location/suggestions
 */
export async function getLocationSuggestions(q: string = ''): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/location/suggestions?q=${encodeURIComponent(q)}`);
    if (res.ok) {
      return await res.json();
    }
    return [];
  } catch {
    return [];
  }
}
