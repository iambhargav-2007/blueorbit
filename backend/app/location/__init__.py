"""
backend/app/location/__init__.py
Location domain module for Blue Orbit (ORCA) - Step 18.
"""

from .schemas import LocationContext, LocationResolveRequest, LocationResolveResponse
from .resolver import LocationResolver, get_location_resolver

__all__ = [
    "LocationContext",
    "LocationResolveRequest",
    "LocationResolveResponse",
    "LocationResolver",
    "get_location_resolver",
]
