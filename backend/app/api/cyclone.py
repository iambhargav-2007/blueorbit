from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..providers.factory import get_cyclone_provider, get_weather_provider
from ..agents.cyclone_agent import CycloneAgent

router = APIRouter(prefix="/api/v1/cyclone", tags=["Cyclone & Severe Weather"])

@router.get("/location", response_model=Dict[str, Any])
async def get_cyclone_for_location(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    date: Optional[str] = Query(None, description="ISO date string (YYYY-MM-DD)")
):
    try:
        # Fetch verified cyclone data
        cyclone_provider = get_cyclone_provider()
        if date:
            cyclone_alert = await cyclone_provider.get_alerts_for_date(date)
        else:
            cyclone_alert = await cyclone_provider.get_alerts_for_location(lat, lon)
            
        # Fetch current marine weather to compute severe weather risk
        weather_provider = get_weather_provider()
        if date:
            weather_data = await weather_provider.get_historical_marine_weather(lat, lon, date)
            temporal_mode = "HISTORICAL"
        else:
            weather_data = await weather_provider.get_marine_weather(lat, lon)
            temporal_mode = "LIVE"
            
        if not weather_data or not weather_data.get("success"):
            weather_conditions = {}
        else:
            weather_conditions = weather_data.get("weather_conditions", {})
            
        date_str = date if date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Analyze using CycloneAgent
        agent = CycloneAgent()
        response = await agent.analyze(
            latitude=lat,
            longitude=lon,
            date_str=date_str,
            weather_conditions=weather_conditions,
            cyclone_alert=cyclone_alert,
            temporal_mode=temporal_mode
        )
        
        return response.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
