/**
 * api.ts
 * TypeScript models matching Blue Orbit (ORCA) FastAPI backend schemas.
 */

export interface LocationInfo {
  latitude: number;
  longitude: number;
}

export interface EnvironmentalSummary {
  temperature_c?: number | null;
  chlorophyll_mg_m3?: number | null;
  temperature_score?: number | null;
  chlorophyll_score?: number | null;
}

export interface ComparisonData {
  date: string;
  result: Record<string, any>;
}

export interface ComparisonResult {
  type: string; // "comparison"
  historical: ComparisonData;
  current: ComparisonData;
}

export interface FishingAgentResponse {
  success: boolean;
  location?: LocationInfo | null;
  date?: string | null;
  habitat_score?: number | null;
  fishing_potential?: 'High' | 'Moderate' | 'Low' | 'Insufficient Data' | string | null;
  confidence?: 'High' | 'Moderate' | 'Low' | string | null;
  data_quality?: string | null;
  environmental_summary?: EnvironmentalSummary | null;
  scientific_explanation?: string | null;
  fisherman_advice?: string | null;
  disclaimer?: string | null;
  temporal_mode?: 'LIVE' | 'HISTORICAL' | 'UNSUPPORTED_FUTURE' | 'COMPARISON' | string | null;
  comparison?: ComparisonResult | null;
  error?: string | null;
}

export interface WeatherConditions {
  wind_speed_knots?: number | null;
  wave_height_meters?: number | null;
  surface_pressure_hpa?: number | null;
  wind_direction?: string | null;
  wave_direction?: string | null;
  wave_period_seconds?: number | null;
  overall_safety_score?: number | null;
  wind_safety_score?: number | null;
  wave_safety_score?: number | null;
  source?: string | null;
  data_status?: string | null;
  observation_type?: string | null;
}

export interface WeatherSafetyAgentResponse {
  success: boolean;
  location?: LocationInfo | null;
  date?: string | null;
  safety_score?: number | null;
  safety_status?: string | null;
  risk_level?: string | null;
  conditions?: WeatherConditions | null;
  weather_conditions?: WeatherConditions | null;
  safety_narrative?: string | null;
  safety_advice?: string | null;
  confidence?: string | null;
  data_quality?: string | null;
  source?: string | null;
  data_status?: string | null;
  observation_type?: string | null;
  temporal_mode?: string | null;
  limiting_factor?: string | null;
  disclaimer?: string | null;
  error?: string | null;
}

export interface GeofencingAgentResponse {
  success: boolean;
  location?: LocationInfo | null;
  is_inside_eez?: boolean | null;
  distance_to_boundary_km?: number | null;
  zone_name?: string | null;
  status?: 'SAFE' | 'WARNING' | 'OUTSIDE EEZ' | string | null;
  geofence_narrative?: string | null;
  geofence_advice?: string | null;
  disclaimer?: string | null;
  error?: string | null;
}

export interface RoutingInfo {
  requested_capabilities: string[];
  agents_invoked: string[];
}

export interface FishingDecision {
  decision: 'FAVORABLE' | 'CAUTION' | 'NOT_RECOMMENDED' | 'INSUFFICIENT_DATA' | string;
  overall_score?: number | null;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  habitat_score?: number | null;
  habitat_status?: string | null;
  weather_score?: number | null;
  weather_risk?: string | null;
  geofence_status?: string | null;
  limiting_factor?: string | null;
  reasons: string[];
  warnings: string[];
  location?: LocationInfo | null;
  timestamp?: string | null;
  data_sources?: string[];
  data_status?: string;
  temporal_mode?: string;
}

export interface FishingDecisionAgentResponse {
  success: boolean;
  decision?: FishingDecision | null;
  narrative?: string | null;
  advice?: string | null;
  disclaimer?: string | null;
  error?: string | null;
}

export interface CoordinatorResponse {
  success: boolean;
  request: {
    query_text?: string;
    latitude?: number | null;
    longitude?: number | null;
    date_str?: string | null;
  };
  routing: RoutingInfo;
  habitat?: FishingAgentResponse | null;
  weather?: WeatherSafetyAgentResponse | null;
  geofencing?: GeofencingAgentResponse | null;
  fishing_decision?: FishingDecisionAgentResponse | null;
  comparison?: ComparisonResult | null;
  conversation_response?: string | null;
  errors: string[];
}

export interface LocationContext {
  latitude: number;
  longitude: number;
  display_name: string;
  source: 'gps' | 'search' | 'map' | 'manual';
  accuracy_m?: number | null;
  timestamp?: string | null;
}

export interface LocationResolveRequest {
  query: string;
}

export interface LocationResolveResponse {
  success: boolean;
  location?: LocationContext | null;
  message?: string | null;
  suggestions: string[];
}

export interface ClarificationRequired {
  success: false;
  needs_clarification: true;
  missing: string[];
  message: string;
}

export type ApiResponse = CoordinatorResponse | ClarificationRequired;

export interface ChatRequest {
  session_id: string;
  message: string;
  latitude?: number | null;
  longitude?: number | null;
  date_str?: string | null;
  location_context?: LocationContext | null;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text?: string;
  data?: CoordinatorResponse | ClarificationRequired | null;
  isError?: boolean;
  errorMessage?: string;
}

export interface SessionRecord {
  id: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
  location?: { lat: number; lon: number } | null;
  locationContext?: LocationContext | null;
  dateStr?: string | null;
}
