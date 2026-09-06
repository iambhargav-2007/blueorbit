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
  intent?: string;
  domain?: string;
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

export interface CycloneAlertSchema {
  id?: string | null;
  name?: string | null;
  status: string;
  severity?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  movement_direction?: string | null;
  movement_speed?: number | null;
  pressure_hpa?: number | null;
  maximum_wind_knots?: number | null;
  affected_radius_km?: number | null;
  issued_at?: string | null;
  valid_until?: string | null;
  source?: string | null;
  confidence?: string | null;
  data_status: string;
}

export interface SevereWeatherClassificationSchema {
  risk_level: string;
  is_affected: boolean;
  affected_status: string;
  narrative: string;
}

export interface CycloneAgentResponse {
  success: boolean;
  location?: LocationInfo | null;
  date?: string | null;
  temporal_mode?: string;
  cyclone_alert?: CycloneAlertSchema | null;
  severe_weather?: SevereWeatherClassificationSchema | null;
  distance_to_center_km?: number | null;
  narrative?: string | null;
  advice?: string | null;
  disclaimer?: string;
  error?: string | null;
}

export interface ResearchMetric {
  mean?: number | null;
  min?: number | null;
  max?: number | null;
}

export interface ResearchData {
  data_status: string;
  valid_observations?: number | null;
  temperature_c?: ResearchMetric | null;
  chlorophyll_mg_m3?: ResearchMetric | null;
  mean_wind_speed_knots?: ResearchMetric | null;
  mean_wave_height_meters?: ResearchMetric | null;
}

export interface ResearchLocationData {
  id: string;
  latitude: number;
  longitude: number;
  data: Record<string, any>;
}

export interface ResearchProvenance {
  source: string;
  dataset: string;
  coverage: string;
}

export interface ResearchAgentResponse {
  success: boolean;
  analysis_type: string;
  temporal_range: string;
  location?: LocationInfo | null;
  locations?: ResearchLocationData[] | null;
  marine?: Record<string, any> | null;
  weather?: Record<string, any> | null;
  data_status: string;
  summary_explanation?: string | null;
  provenance: ResearchProvenance;
  error?: string | null;
}

export interface StructuredSummary {
  overview?: string | null;
  key_findings?: string[];
  operational_status?: string | null;
  confidence?: string | null;
  answer?: string | null;
  evidence?: string | null;
  context?: string | null;
  next_action?: string | null;
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
  intent?: string | null;
  intelligence_domain?: string | null;
  habitat?: FishingAgentResponse | null;
  weather?: WeatherSafetyAgentResponse | null;
  geofencing?: GeofencingAgentResponse | null;
  cyclone?: CycloneAgentResponse | null;
  fishing_decision?: FishingDecisionAgentResponse | null;
  research?: ResearchAgentResponse | null;
  comparison?: ComparisonResult | null;
  routing_navigation?: RoutingAgentResponse | null;
  safety_assessment?: Record<string, any> | null;
  sector_overview?: Record<string, any> | null;
  structured_summary?: StructuredSummary | null;
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

export interface PointAnalysisLocation {
  latitude: number;
  longitude: number;
  display_name: string;
  is_inside_eez: boolean;
  distance_to_boundary_km?: number | null;
  zone_name?: string | null;
}

export interface PointAnalysisResponse {
  success: boolean;
  location: PointAnalysisLocation;
  geofence: Record<string, any>;
  marine?: Record<string, any> | null;
  weather?: Record<string, any> | null;
  decision?: FishingDecision | null;
  temporal_mode: string;
  timestamp: string;
  error?: string | null;
}

export interface GridCell {
  lat: number;
  lon: number;
  val: number;
  label: string;
  category: string;
}

export interface GridLayerResponse {
  success: boolean;
  layer: string;
  unit: string;
  date: string;
  temporal_mode: string;
  source: string;
  min_val: number;
  max_val: number;
  cells: GridCell[];
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
  wasVoice?: boolean;
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

export interface RouteNode {
  latitude: number;
  longitude: number;
  distance_from_start_km: number;
  weather_state?: string | null;
  wave_state?: string | null;
  geofence_state?: string | null;
  hazard_state?: string | null;
  traversal_cost: number;
}

export interface RoutingResult {
  status: string;
  start_location: LocationInfo;
  destination_location: LocationInfo;
  route_points: RouteNode[];
  total_distance_km: number;
  estimated_route_cost: number;
  weather_assessment?: string | null;
  geofence_assessment?: string | null;
  hazard_summary?: string | null;
  data_status: string;
  temporal_mode: string;
  data_sources: string[];
  generated_at?: string | null;
  warnings: string[];
  explanation_metadata?: Record<string, any> | null;
}

export interface RoutingAgentResponse {
  success: boolean;
  routing?: RoutingResult | null;
  narrative?: string | null;
  disclaimer: string;
  error?: string | null;
}
