"""
weather_tool.py

Exposes the Weather Safety Engine as a structured tool callable by the
Weather/Safety Agent.

The tool's responsibility is DATA RETRIEVAL and ENGINE INVOCATION only.
It does NOT modify, recalculate, or interpret scores.
All mathematical logic stays inside WeatherSafetyEngine.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..providers.factory import get_smart_weather_router, get_weather_provider
from ..providers.base_weather_provider import BaseWeatherProvider
from ..services.weather_safety_engine import WeatherSafetyEngine
from ..services.temporal_resolver import TemporalResolution, TemporalMode
from ..config import WEATHER_SAFETY_CONFIG_PATH


class WeatherSafetyTool:
    """
    Structured tool that wraps the weather data provider + Weather Safety Engine.

    The Weather/Safety Agent calls this tool; it never computes scores itself.

    Architecture:
        WeatherSafetyTool
            └─ SmartWeatherRouter (or injected WeatherProvider)
                ├─ InterimLiveWeatherProvider (live Open-Meteo)
                ├─ CacheWeatherProvider (weather_regional_grid.parquet)
                └─ Future IMDWeatherProvider
            └─ WeatherSafetyEngine (deterministic, authoritative)
    """

    def __init__(
        self,
        live_mode: Optional[bool] = None,
        max_distance_km: float = 100.0,
        provider: Optional[BaseWeatherProvider] = None,
    ):
        """
        Args:
            live_mode: If None, uses SmartWeatherRouter for smart temporal dispatch.
            max_distance_km: Maximum spatial search radius passed to the weather provider.
            provider: Explicitly injected weather provider (useful for unit tests/mocking).
        """
        if provider is not None:
            self._provider = provider
        elif live_mode is False:
            self._provider = get_weather_provider(live_mode=False, max_distance_km=max_distance_km)
        else:
            self._provider = get_smart_weather_router(max_distance_km=max_distance_km)

        self._engine = WeatherSafetyEngine(config_path=WEATHER_SAFETY_CONFIG_PATH)

    def get_weather_safety(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
        temporal_resolution: Optional[TemporalResolution] = None,
        query_text: str = "",
    ) -> Dict[str, Any]:
        """
        Retrieves weather observations for the given coordinate/date and returns
        the deterministic safety assessment from the Weather Safety Engine.

        Args:
            latitude:  WGS84 latitude in decimal degrees.
            longitude: WGS84 longitude in decimal degrees.
            date_str:  Target date as 'YYYY-MM-DD'.
            temporal_resolution: Optional resolved TemporalResolution.
            query_text: Optional original query text.

        Returns:
            Structured safety assessment dict produced by WeatherSafetyEngine.
            On any failure the dict contains success=False and an error message.
        """
        # 1. Basic coordinate validation
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return {
                "success": False,
                "error": "Latitude and longitude must be numeric values.",
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        # 2. Basic date format validation
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.",
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        # 3. Retrieve weather observation via the provider (never reads Parquet directly)
        try:
            temporal_mode = temporal_resolution.mode if temporal_resolution else None
            # Check if provider accepts temporal_mode and query_text (e.g. SmartWeatherRouter)
            import inspect
            sig = inspect.signature(self._provider.get_weather)
            if "temporal_mode" in sig.parameters:
                weather_data = self._provider.get_weather(
                    lat=latitude,
                    lon=longitude,
                    date_str=date_str,
                    temporal_mode=temporal_mode,
                    query_text=query_text,
                )
            else:
                weather_data = self._provider.get_weather(
                    lat=latitude, lon=longitude, date_str=date_str
                )
        except Exception as exc:
            return {
                "success": False,
                "error": f"Weather data provider error: {exc}",
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        if not weather_data.get("success", False):
            return weather_data

        # 4. Feed observation into the authoritative Weather Safety Engine
        try:
            result = self._engine.assess(weather_data)
        except Exception as exc:
            return {
                "success": False,
                "error": f"Weather safety engine error: {exc}",
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        return result
