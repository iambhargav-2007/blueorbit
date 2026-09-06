"""
schemas.py

Pydantic output models for the ORCA Multi-Stakeholder Coordinator (Step 23).
Supports Fishermen, Coast Guards, and Researchers with domain-aware intelligence.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..agents.schemas import (
    FishingAgentResponse,
    WeatherSafetyAgentResponse,
    GeofencingAgentResponse,
    FishingDecisionAgentResponse,
    ComparisonResult,
)


class IntentEnum(str, Enum):
    """
    Explicit internal intent taxonomy for Blue Orbit / ORCA.
    """
    FISHING_SUPPORT = "FISHING_SUPPORT"
    MARITIME_SAFETY = "MARITIME_SAFETY"
    SEVERE_WEATHER = "SEVERE_WEATHER"
    MARINE_ANALYSIS = "MARINE_ANALYSIS"
    ENVIRONMENTAL_ANALYSIS = "ENVIRONMENTAL_ANALYSIS"
    SPATIAL_QUERY = "SPATIAL_QUERY"
    TEMPORAL_COMPARISON = "TEMPORAL_COMPARISON"
    GENERAL_COASTAL_QUERY = "GENERAL_COASTAL_QUERY"
    UNKNOWN = "UNKNOWN"


class IntelligenceDomainEnum(str, Enum):
    """
    Primary intelligence domain classification.
    """
    MARINE = "MARINE"
    WEATHER = "WEATHER"
    GEOSPATIAL = "GEOSPATIAL"
    SEVERE_WEATHER = "SEVERE_WEATHER"
    TEMPORAL = "TEMPORAL"
    FISHING = "FISHING"
    MARITIME_SAFETY = "MARITIME_SAFETY"
    COASTAL_OVERVIEW = "COASTAL_OVERVIEW"


class RoutingInfo(BaseModel):
    """
    Structured output returned by the OrcaRouter.
    """
    intent: str = Field(
        default=IntentEnum.UNKNOWN.value,
        description="Identified user intent string."
    )
    domain: str = Field(
        default=IntelligenceDomainEnum.COASTAL_OVERVIEW.value,
        description="Primary intelligence domain."
    )
    requested_capabilities: List[str] = Field(
        default_factory=list,
        description="List of identified domain capabilities. e.g. ['habitat', 'weather', 'geofencing']"
    )
    agents_invoked: List[str] = Field(
        default_factory=list,
        description="List of agent identifiers actually invoked."
    )


class StructuredSummary(BaseModel):
    """
    Standardized ORCA structured summary.
    Supports both operational metrics (overview, key_findings, operational_status, confidence)
    and response guidance (answer, evidence, context, next_action).
    """
    overview: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    operational_status: Optional[str] = None
    confidence: Optional[str] = None
    answer: Optional[str] = None
    evidence: Optional[str] = None
    context: Optional[str] = None
    next_action: Optional[str] = None


class CoordinatorResponse(BaseModel):
    """
    Unified structured response returned by the OrcaCoordinator.
    Preserves exact deterministic structures while providing domain-aware intelligence.
    """
    success: bool = Field(
        description="True if the routing and multi-agent invocation completed successfully."
    )
    request: Dict[str, Any] = Field(
        default_factory=dict,
        description="Echoes the valid parsed request parameters (latitude, longitude, date_str, query_text)."
    )
    routing: RoutingInfo = Field(
        default_factory=RoutingInfo,
        description="Details about identified intent, domain, and invoked agents."
    )
    
    # --- Intent & Domain Context ---
    intent: Optional[str] = Field(
        default=None,
        description="High-level user intent (e.g. 'FISHING_SUPPORT', 'MARITIME_SAFETY', 'MARINE_ANALYSIS')."
    )
    intelligence_domain: Optional[str] = Field(
        default=None,
        description="Target intelligence domain (e.g. 'MARITIME_SAFETY', 'MARINE', 'FISHING')."
    )
    
    # --- Agent Results ---
    habitat: Optional[FishingAgentResponse] = Field(
        default=None,
        description="Result from the Marine/Habitat Agent if 'habitat' capability was required."
    )
    weather: Optional[WeatherSafetyAgentResponse] = Field(
        default=None,
        description="Result from the Weather/Safety Agent if 'weather' capability was required."
    )
    geofencing: Optional[GeofencingAgentResponse] = Field(
        default=None,
        description="Result from the Geofencing Agent if 'geofencing' capability was required."
    )
    cyclone: Optional[Any] = Field(
        default=None,
        description="Result from the Cyclone / Severe Weather Agent if 'cyclone' capability was required."
    )
    fishing_decision: Optional[FishingDecisionAgentResponse] = Field(
        default=None,
        description="Unified fishing recommendation ONLY if fishing intent was requested."
    )
    research: Optional[Any] = Field(
        default=None,
        description="Result from the Research Agent if historical analysis was requested."
    )
    comparison: Optional[ComparisonResult] = Field(
        default=None,
        description="Structured comparison result if request was a comparison."
    )
    
    # --- Specialized Domain Views ---
    safety_assessment: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Synthesized maritime safety assessment for coast guards and navigators."
    )
    sector_overview: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Multi-domain coastal overview for general queries without forced fishing scores."
    )
    structured_summary: Optional[StructuredSummary] = Field(
        default=None,
        description="Standardized ORCA response model: Answer, Evidence, Context, Next Action or operational overview."
    )

    conversation_response: Optional[str] = Field(
        default=None,
        description="Conversational narrative for general messages, greetings, or explanations."
    )
    
    # --- Error path ---
    errors: List[str] = Field(
        default_factory=list,
        description="List of coordinator-level or agent-level errors."
    )


# Generic Normalized Intelligence Envelope (Section 33)
IntelligenceResponse = CoordinatorResponse
