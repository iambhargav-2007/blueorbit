"""
schemas.py

Location Domain Models for Blue Orbit (ORCA) - Step 18.
Normalizes location representations across GPS, Search, Map, and Manual inputs.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


class LocationContext(BaseModel):
    """
    Normalized location context representing a geographical reference point.
    All upstream and downstream engines consume this standard structure.
    """
    latitude: float = Field(..., description="Latitude in decimal degrees [-90.0, 90.0]")
    longitude: float = Field(..., description="Longitude in decimal degrees [-180.0, 180.0]")
    display_name: str = Field(..., min_length=1, description="Human-friendly label (e.g. 'Goa Coastal Zone')")
    source: Literal["gps", "search", "map", "manual"] = Field(..., description="Input modality used")
    accuracy_m: Optional[float] = Field(None, ge=0.0, description="Estimated accuracy radius in meters if GPS")
    timestamp: Optional[str] = Field(None, description="ISO-8601 timestamp of coordinate acquisition")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude {v} is outside valid range [-90.0, 90.0].")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude {v} is outside valid range [-180.0, 180.0].")
        return v


class LocationResolveRequest(BaseModel):
    """Request payload for resolving a human-readable query into coordinates."""
    query: str = Field(..., min_length=1, description="Place name, coastal sector, or coordinate string")


class LocationResolveResponse(BaseModel):
    """Response payload returned by the Location Resolver."""
    success: bool = Field(..., description="True if a valid location was resolved")
    location: Optional[LocationContext] = Field(None, description="Normalized LocationContext if resolved")
    message: Optional[str] = Field(None, description="Explanation or landlocked advisory message")
    suggestions: List[str] = Field(default_factory=list, description="Alternative coastal suggestions if applicable")
