"""
schemas.py

Pydantic output models for the ORCA Coordinator (Step 12).
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..agents.schemas import (
    FishingAgentResponse,
    WeatherSafetyAgentResponse,
    GeofencingAgentResponse,
    FishingDecisionAgentResponse,
    ComparisonResult,
)

class RoutingInfo(BaseModel):
    """
    Structured output returned by the OrcaRouter.
    """
    requested_capabilities: List[str] = Field(
        default_factory=list,
        description="List of identified domain capabilities. e.g. ['habitat', 'weather', 'geofencing']"
    )
    agents_invoked: List[str] = Field(
        default_factory=list,
        description="List of agent identifiers actually invoked. e.g. ['fishing_habitat', 'weather_safety', 'geofencing']"
    )

class CoordinatorResponse(BaseModel):
    """
    Unified structured response returned by the OrcaCoordinator.
    Preserves the exact deterministic structures of the domain agents.
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
        description="Details about which capabilities were identified and invoked."
    )
    
    # --- Agent Results ---
    
    habitat: Optional[FishingAgentResponse] = Field(
        default=None,
        description="Result from the Fishing/Habitat Agent if 'habitat' capability was required."
    )
    
    weather: Optional[WeatherSafetyAgentResponse] = Field(
        default=None,
        description="Result from the Weather/Safety Agent if 'weather' capability was required."
    )
    
    geofencing: Optional[GeofencingAgentResponse] = Field(
        default=None,
        description="Result from the Geofencing Agent if 'geofencing' capability was required."
    )

    fishing_decision: Optional[FishingDecisionAgentResponse] = Field(
        default=None,
        description="Unified fishing recommendation from the Unified Fishing Decision Engine/Agent."
    )

    comparison: Optional[ComparisonResult] = Field(
        default=None,
        description="Structured comparison result if request was a comparison."
    )

    conversation_response: Optional[str] = Field(
        default=None,
        description="Conversational narrative for general messages, greetings, or help."
    )
    
    # --- Error path ---
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of coordinator-level or agent-level errors."
    )
