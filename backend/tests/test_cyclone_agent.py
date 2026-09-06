import pytest
from app.agents.cyclone_agent import CycloneAgent

@pytest.mark.asyncio
async def test_cyclone_agent_analyze():
    agent = CycloneAgent()
    
    # Use unavailable data to avoid external LLM calls or rely on fallback
    cyclone = {
        "status": "UNAVAILABLE"
    }
    weather = {
        "wind_speed_knots": 10,
        "wave_height_meters": 1.0
    }
    
    response = await agent.analyze(
        latitude=15.0, 
        longitude=70.0, 
        date_str="2026-09-04", 
        weather_conditions=weather, 
        cyclone_alert=cyclone
    )
    
    assert response.success is True
    assert response.severe_weather.risk_level == "NORMAL"
    assert response.severe_weather.is_affected is False
    assert response.severe_weather.affected_status == "NOT_AFFECTED"
    # Ensure fallback works
    assert response.narrative is not None
