import pytest
from app.providers.factory import get_cyclone_provider
from app.providers.placeholder_cyclone_provider import PlaceholderCycloneProvider

@pytest.mark.asyncio
async def test_placeholder_provider():
    provider = get_cyclone_provider()
    assert isinstance(provider, PlaceholderCycloneProvider)
    
    current = await provider.get_current_alerts()
    assert current["status"] == "UNAVAILABLE"
    
    loc = await provider.get_alerts_for_location(15.0, 70.0)
    assert loc["status"] == "UNAVAILABLE"
    
    date_alerts = await provider.get_alerts_for_date("2026-09-04")
    assert date_alerts["status"] == "UNAVAILABLE"
