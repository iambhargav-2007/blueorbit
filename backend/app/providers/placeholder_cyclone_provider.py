from typing import Dict, Any, Optional
from .base_cyclone_provider import BaseCycloneProvider

class PlaceholderCycloneProvider(BaseCycloneProvider):
    """
    Placeholder provider for cyclone/severe weather.
    Since official IMD cyclone integration is pending, this provider explicitly 
    returns UNAVAILABLE instead of fabricating data.
    """

    async def get_current_alerts(self) -> Dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "message": "Official cyclone forecast data is not currently available through the configured provider.",
            "alerts": []
        }

    async def get_alerts_for_location(self, latitude: float, longitude: float) -> Dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "message": "Official cyclone forecast data is not currently available through the configured provider.",
            "alerts": []
        }

    async def get_alerts_for_date(self, date: str) -> Dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "message": "Official cyclone forecast data is not currently available through the configured provider.",
            "alerts": []
        }

    async def get_active_systems(self) -> Dict[str, Any]:
        return {
            "status": "UNAVAILABLE",
            "message": "Official cyclone forecast data is not currently available through the configured provider.",
            "systems": []
        }
