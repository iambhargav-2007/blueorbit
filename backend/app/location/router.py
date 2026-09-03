"""
router.py

FastAPI router for Location Intelligence (Step 18).
Endpoints:
  - POST /api/v1/location/resolve
  - GET  /api/v1/location/suggestions
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List
from .schemas import LocationResolveRequest, LocationResolveResponse
from .resolver import LocationResolver, get_location_resolver

router = APIRouter(prefix="/api/v1/location", tags=["location"])


@router.post("/resolve", response_model=LocationResolveResponse)
def resolve_location(
    request: LocationResolveRequest,
) -> LocationResolveResponse:
    """
    Resolves a human-readable coastal place, sector, or coordinate string
    into a standardized LocationContext.
    """
    resolver = get_location_resolver()
    return resolver.resolve_location(request.query)


@router.get("/suggestions", response_model=List[str])
def get_suggestions(
    q: str = Query("", description="Query prefix to auto-complete")
) -> List[str]:
    """
    Returns coastal place auto-complete suggestions for the Indian West Coast.
    """
    resolver = get_location_resolver()
    if not q.strip():
        return resolver.get_all_places()[:8]
    return resolver.get_suggestions(q)
