from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseWeatherProvider(ABC):
    """
    Abstract contract for marine weather data providers.
    All weather providers (Cache, InterimLive, SmartRouter, and future IMD)
    must implement this interface.
    """

    @abstractmethod
    def get_weather(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves weather observations for a specific coordinate and date.

        Args:
            lat (float): Requested latitude in WGS84 decimal degrees.
            lon (float): Requested longitude in WGS84 decimal degrees.
            date_str (str): Target date in 'YYYY-MM-DD' format.

        Returns:
            Dict[str, Any]: Standardized weather observation dictionary containing:
                - success (bool)
                - latitude (float)
                - longitude (float)
                - date (str)
                - matched_latitude (float)
                - matched_longitude (float)
                - distance_km (float)
                - wind_speed_knots (Optional[float])
                - wave_height_meters (Optional[float])
                - surface_pressure_hpa (Optional[float])
                - wind_direction (Optional[str | float])
                - wave_direction (Optional[str | float])
                - wave_period_seconds (Optional[float])
                - source (str)
                - data_status (str)
                - observation_type (str)
        """
        pass

    def get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Retrieves current real-time marine weather observation.
        Defaults to calling get_weather with current UTC date.
        """
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.get_weather(lat=lat, lon=lon, date_str=today_str)

    def get_weather_for_date(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves weather observations for a specific date.
        Alias to get_weather for explicit semantic clarity.
        """
        return self.get_weather(lat=lat, lon=lon, date_str=date_str)
