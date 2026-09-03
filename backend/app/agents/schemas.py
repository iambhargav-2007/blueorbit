"""
schemas.py

Pydantic output models for the Fishing/Habitat Agent (Step 9),
the Weather/Safety Agent (Step 10), and the Geofencing Agent (Step 11).
All fields reflect the actual available data from the respective engines.
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class LocationInfo(BaseModel):
    latitude: float
    longitude: float


class EnvironmentalSummary(BaseModel):
    temperature_c: Optional[float] = Field(
        default=None,
        description="Near-surface ocean temperature in Celsius from Copernicus CMEMS dataset."
    )
    chlorophyll_mg_m3: Optional[float] = Field(
        default=None,
        description="Chlorophyll-a concentration in mg/m³ as a proxy for ocean productivity."
    )
    temperature_score: Optional[float] = Field(
        default=None,
        description="Heuristic temperature suitability score (0–100). Higher = more suitable."
    )
    chlorophyll_score: Optional[float] = Field(
        default=None,
        description="Heuristic chlorophyll suitability score (0–100). Higher = more suitable."
    )


class FishingAgentResponse(BaseModel):
    """
    Structured output returned by the Fishing/Habitat Agent.

    Note: This is a prototype decision-support response based on environmental indicators.
    It does not predict fish abundance or guarantee a successful catch.
    """
    success: bool
    location: Optional[LocationInfo] = None
    date: Optional[str] = None
    habitat_score: Optional[float] = Field(
        default=None,
        description="Overall habitat suitability score (0–100). Computed by the deterministic Habitat Engine."
    )
    fishing_potential: Optional[str] = Field(
        default=None,
        description="Categorical fishing potential: High, Moderate, Low, or Insufficient Data."
    )
    confidence: Optional[str] = Field(
        default=None,
        description="Confidence level based on data completeness: High, Moderate, or Low."
    )
    data_quality: Optional[str] = Field(
        default=None,
        description="Describes the completeness of the underlying environmental observation."
    )
    environmental_summary: Optional[EnvironmentalSummary] = None
    scientific_explanation: Optional[str] = Field(
        default=None,
        description="Deterministic engine explanation of the suitability assessment."
    )
    fisherman_advice: Optional[str] = Field(
        default=None,
        description="LLM-narrated practical interpretation for fishermen. Based solely on the engine result."
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message when success=False."
    )
    disclaimer: str = (
        "This is a prototype heuristic habitat suitability model based on environmental "
        "indicators. It does not predict exact fish abundance or guarantee catch."
    )
    temporal_mode: Optional[str] = Field(
        default=None,
        description="Resolved temporal routing mode: LIVE, HISTORICAL, UNSUPPORTED_FUTURE, or COMPARISON."
    )
    comparison: Optional["ComparisonResult"] = Field(
        default=None,
        description="Structured comparison result when user requests a comparison between historical and current conditions."
    )


class ComparisonData(BaseModel):
    date: str
    result: Dict[str, Any]


class ComparisonResult(BaseModel):
    type: str = "comparison"
    historical: ComparisonData
    current: ComparisonData


FishingAgentResponse.model_rebuild()



# ---------------------------------------------------------------------------
# Step 10: Weather/Safety Agent schemas
# ---------------------------------------------------------------------------

class WeatherConditions(BaseModel):
    """Raw weather measurements and engine-computed safety scores."""

    wind_speed_knots: Optional[float] = Field(
        default=None,
        description="Maximum wind speed in knots from the nearest grid point."
    )
    wave_height_meters: Optional[float] = Field(
        default=None,
        description="Maximum wave height in meters from the nearest grid point."
    )
    surface_pressure_hpa: Optional[float] = Field(
        default=None,
        description="Mean surface pressure in hPa."
    )
    wind_direction: Optional[str] = Field(
        default=None,
        description="Wind direction if available from the provider."
    )
    wave_direction: Optional[str] = Field(
        default=None,
        description="Wave direction if available from the provider."
    )
    wave_period_seconds: Optional[float] = Field(
        default=None,
        description="Wave period in seconds if available from the provider."
    )
    wind_safety_score: Optional[float] = Field(
        default=None,
        description="Engine-computed wind safety score (0–100). Computed by WeatherSafetyEngine."
    )
    wave_safety_score: Optional[float] = Field(
        default=None,
        description="Engine-computed wave safety score (0–100). Computed by WeatherSafetyEngine."
    )
    overall_safety_score: Optional[float] = Field(
        default=None,
        description="Overall safety score (0–100); minimum of wind and wave scores (conservative bottleneck)."
    )
    source: Optional[str] = Field(
        default=None,
        description="Provenance of the weather data (e.g. Open-Meteo Marine API, Historical Parquet)."
    )
    data_status: Optional[str] = Field(
        default=None,
        description="Observation status: observed, historical, unavailable, or insufficient_data."
    )
    observation_type: Optional[str] = Field(
        default=None,
        description="Observation modality: current_observation, historical_observation, forecast, or unavailable."
    )


class WeatherSafetyAgentResponse(BaseModel):
    """
    Structured output returned by the Weather/Safety Agent.

    Note: This is a prototype decision-support response.
    risk_level, wind_safety_score, wave_safety_score, and overall_safety_score
    are ALWAYS taken verbatim from the deterministic WeatherSafetyEngine.
    The LLM provides only safety_narrative and safety_advice plain-text fields.
    """

    success: bool
    location: Optional[LocationInfo] = None
    date: Optional[str] = None
    matched_location: Optional[LocationInfo] = Field(
        default=None,
        description="Nearest grid point matched by the spatial index."
    )
    distance_km: Optional[float] = Field(
        default=None,
        description="Distance in km between the requested location and the matched grid point."
    )
    risk_level: Optional[str] = Field(
        default=None,
        description="Categorical risk label from the engine: Low Risk, Moderate Risk, High Risk, Very High Risk, or Insufficient Data."
    )
    confidence: Optional[str] = Field(
        default=None,
        description="Confidence level based on data completeness: High or Low."
    )
    data_quality: Optional[str] = Field(
        default=None,
        description="Describes the completeness of the underlying weather observation: Complete, Partial, or Insufficient Data."
    )
    weather_conditions: Optional[WeatherConditions] = None
    safety_narrative: Optional[str] = Field(
        default=None,
        description="Deterministic engine explanation of the safety assessment (engine-generated, never LLM-invented)."
    )
    safety_advice: Optional[str] = Field(
        default=None,
        description="LLM-narrated practical safety advice for fishermen. Based solely on the engine result."
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message when success=False."
    )
    source: Optional[str] = Field(
        default=None,
        description="Data provenance source."
    )
    data_status: Optional[str] = Field(
        default=None,
        description="Data status (observed, historical, unavailable)."
    )
    observation_type: Optional[str] = Field(
        default=None,
        description="Observation classification (current_observation, historical_observation, forecast, unavailable)."
    )
    temporal_mode: Optional[str] = Field(
        default=None,
        description="Resolved temporal mode (LIVE, HISTORICAL, UNSUPPORTED_FUTURE)."
    )
    limiting_factor: Optional[str] = Field(
        default=None,
        description="The primary physical bottleneck limiting maritime safety (Wind Speed, Wave Height, or None)."
    )
    disclaimer: str = (
        "This is a prototype decision-support/risk indicator. "
        "It does not guarantee vessel safety or represent official maritime safety standards."
    )


# ---------------------------------------------------------------------------
# Step 11: Geofencing Agent schemas
# ---------------------------------------------------------------------------

class GeofencingAgentResponse(BaseModel):
    """
    Structured output returned by the Geofencing Agent.

    IMPORTANT — field provenance:
      - inside_indian_eez, geofence_status, distance_to_eez_boundary_km, alerts,
        protected_area_coverage_available, inside_protected_area,
        nearest_protected_area, distance_to_protected_area_km, and disclaimer
        are ALWAYS taken verbatim from the deterministic GeofencingEngine.
      - geofence_narrative and geofence_advice are LLM-narrated fields only.
        The LLM may NOT override any structured engine field.

    LEGAL NOTE:
      Being inside the Indian EEZ does NOT automatically constitute legal
      permission to fish. Fishing rights are subject to Indian maritime law,
      licensing, species regulations, and seasonal restrictions. This prototype
      provides geographic boundary information only.

    PROTECTED AREA NOTE:
      Protected-area boundary geometry is not currently loaded. The engine
      sets protected_area_coverage_available=False in all current responses.
      Do not interpret inside_protected_area=None as confirmation that a
      location is free of protected-area restrictions.
    """

    success: bool

    location: Optional[LocationInfo] = Field(
        default=None,
        description="Requested vessel position (WGS84)."
    )

    # --- Engine-sourced structured fields (verbatim, never LLM-modified) ---

    inside_indian_eez: Optional[bool] = Field(
        default=None,
        description=(
            "True if the vessel position is within the Indian EEZ boundary polygon. "
            "False if outside. Source: GeofencingEngine (deterministic spatial check)."
        )
    )

    geofence_status: Optional[str] = Field(
        default=None,
        description=(
            "Deterministic geofence status from the engine: "
            "'SAFE' (inside EEZ, not near boundary), "
            "'WARNING' (inside EEZ but within warning_distance_km of the boundary), "
            "'OUTSIDE_EEZ' (outside the Indian EEZ). "
            "This field is ALWAYS the engine result — the LLM cannot change it."
        )
    )

    distance_to_eez_boundary_km: Optional[float] = Field(
        default=None,
        description=(
            "Distance in km from the vessel position to the nearest point on the "
            "EEZ boundary line. Computed by GeofencingEngine using EPSG:32643 projection."
        )
    )

    alerts: Optional[List[str]] = Field(
        default=None,
        description=(
            "List of deterministic alert messages from the engine. "
            "Empty list when geofence_status is SAFE."
        )
    )

    protected_area_coverage_available: Optional[bool] = Field(
        default=None,
        description=(
            "True only if protected-area boundary geometry was loaded at engine init. "
            "Currently always False — no protected-area GeoJSON is loaded in this project."
        )
    )

    inside_protected_area: Optional[bool] = Field(
        default=None,
        description=(
            "True if the position is inside a loaded protected-area polygon. "
            "Always None when protected_area_coverage_available=False."
        )
    )

    nearest_protected_area: Optional[str] = Field(
        default=None,
        description=(
            "Name/identifier of the nearest protected area. "
            "Always None when protected_area_coverage_available=False."
        )
    )

    distance_to_protected_area_km: Optional[float] = Field(
        default=None,
        description=(
            "Distance in km to the nearest protected area boundary. "
            "Always None when protected_area_coverage_available=False."
        )
    )

    # --- LLM-narrated fields (text only, cannot override structured fields) ---

    geofence_narrative: Optional[str] = Field(
        default=None,
        description=(
            "LLM-narrated explanation of the geographic boundary status. "
            "Based solely on the engine result. Never overrides structured fields."
        )
    )

    geofence_advice: Optional[str] = Field(
        default=None,
        description=(
            "LLM-narrated practical guidance for fishermen or coast guards "
            "based on the geofence status. Does not constitute legal advice."
        )
    )

    # --- Error path ---

    error: Optional[str] = Field(
        default=None,
        description="Error message when success=False."
    )

    disclaimer: str = (
        "This is a prototype decision-support geofencing engine based on supplied spatial "
        "boundary layers. It does not establish legal maritime boundaries or bilateral IMBL "
        "treaties. Being inside the Indian EEZ does not automatically confer legal fishing "
        "permission. Protected-area status cannot currently be determined — no protected-area "
        "geometry is loaded."
    )


# ---------------------------------------------------------------------------
# Step 20: Unified Fishing Decision Engine Models
# ---------------------------------------------------------------------------

class FishingDecision(BaseModel):
    """
    Unified deterministic fishing recommendation synthesized from habitat suitability,
    weather sea-state safety, and EEZ boundary compliance.
    """
    decision: str = Field(
        ...,
        description="Categorical decision recommendation: FAVORABLE, CAUTION, NOT_RECOMMENDED, or INSUFFICIENT_DATA."
    )
    overall_score: Optional[float] = Field(
        default=None,
        description="Aggregate decision-support indicator (0–100). Not a catch probability or safety guarantee."
    )
    confidence: str = Field(
        default="LOW",
        description="Confidence level based strictly on underlying data completeness: HIGH, MEDIUM, or LOW."
    )
    habitat_score: Optional[float] = Field(
        default=None,
        description="Deterministic habitat suitability score (0–100) from Habitat Suitability Engine."
    )
    habitat_status: Optional[str] = Field(
        default=None,
        description="Categorical habitat potential: High, Moderate, Low, or Insufficient Data."
    )
    weather_score: Optional[float] = Field(
        default=None,
        description="Deterministic weather safety score (0–100) from Weather Safety Engine."
    )
    weather_risk: Optional[str] = Field(
        default=None,
        description="Categorical weather risk: Low Risk, Moderate Risk, High Risk, Very High Risk, or Insufficient Data."
    )
    geofence_status: Optional[str] = Field(
        default=None,
        description="Categorical geofence compliance: SAFE, WARNING, OUTSIDE EEZ, or Insufficient Data."
    )
    limiting_factor: Optional[str] = Field(
        default=None,
        description="Primary factor dictating the recommendation: Weather Safety, Habitat Suitability, EEZ Boundary, Insufficient Data, or None."
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Deterministic justifications explaining the recommendation."
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Deterministic safety, environmental, or regulatory notices."
    )
    location: Optional[LocationInfo] = Field(
        default=None,
        description="Evaluated coordinates."
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="Assessment timestamp or date."
    )
    data_sources: List[str] = Field(
        default_factory=list,
        description="Observation sources used (e.g. Copernicus Marine, Open-Meteo, Historical Parquet)."
    )
    data_status: str = Field(
        default="INSUFFICIENT_DATA",
        description="Observation completeness: COMPLETE, PARTIAL, or INSUFFICIENT_DATA."
    )
    temporal_mode: str = Field(
        default="LIVE",
        description="Resolved temporal mode: LIVE, HISTORICAL, UNSUPPORTED_FUTURE, or INSUFFICIENT_DATA."
    )


class FishingDecisionAgentResponse(BaseModel):
    """
    Structured output returned by the Fishing Decision Agent.
    """
    success: bool
    decision: Optional[FishingDecision] = None
    narrative: Optional[str] = Field(
        default=None,
        description="LLM-narrated natural language synthesis strictly reflecting deterministic engine scores."
    )
    advice: Optional[str] = Field(
        default=None,
        description="LLM-narrated practical advice for fishermen based on the deterministic recommendation."
    )
    disclaimer: str = (
        "Decision support indicator based on available environmental and marine observations. "
        "Does not guarantee fish abundance, catch success, legal fishing rights, or vessel safety."
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message when success=False."
    )

