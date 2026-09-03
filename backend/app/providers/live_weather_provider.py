"""
live_weather_provider.py

Interim Live Weather Provider for Blue Orbit (ORCA) - Step 19.
Integrates verified external marine weather observation sources (Open-Meteo Marine API).

Constraints & Rules:
  - Retrieves real observed marine conditions (wind speed, direction, wave height, wave period).
  - Never fabricates or hallucinates weather parameters.
  - Never silently falls back to October 2025 historical data when live mode is requested.
  - Returns explicit INSUFFICIENT_DATA status on network failure or missing observations.
  - Designed with clean abstraction so IMD (India Meteorological Department) provider
    can be plugged in later without altering upstream consumers.
"""

import time
import logging
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .base_weather_provider import BaseWeatherProvider

logger = logging.getLogger(__name__)

# User-Agent for compliant API consumption
HTTP_USER_AGENT = "BlueOrbit-MarineIntelligence/1.0 (SIH 2026)"
DEFAULT_TIMEOUT_SECONDS = 6.0
CACHE_TTL_SECONDS = 300.0  # 5-minute in-memory cache for repeated sector queries


class InterimLiveWeatherProvider(BaseWeatherProvider):
    """
    Interim live marine weather provider using Open-Meteo Marine & Forecast APIs.
    Serves as the authoritative live weather provider until official IMD APIs are integrated.
    """

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        cache_ttl_seconds: float = CACHE_TTL_SECONDS,
    ):
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        # In-memory short-lived cache: (rounded_lat, rounded_lon) -> (timestamp, data_dict)
        self._cache: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}

    def _fetch_url_json(self, url: str) -> Optional[Dict[str, Any]]:
        req = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
        return None

    def get_weather(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves real-time marine weather observations for the specified coordinate.
        """
        # 1. Coordinate validation
        if not (-90.0 <= lat <= 90.0):
            return {
                "success": False,
                "error": f"Invalid latitude {lat}. Must be between -90.0 and 90.0.",
                "code": "INVALID_COORDINATES",
                "observation_type": "unavailable",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
            }
        if not (-180.0 <= lon <= 180.0):
            return {
                "success": False,
                "error": f"Invalid longitude {lon}. Must be between -180.0 and 180.0.",
                "code": "INVALID_COORDINATES",
                "observation_type": "unavailable",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
            }

        # 2. Check short-lived sector cache
        cache_key = (round(lat, 2), round(lon, 2))
        now = time.time()
        if cache_key in self._cache:
            ts, cached_val = self._cache[cache_key]
            if now - ts < self.cache_ttl_seconds:
                logger.debug(f"InterimLiveWeatherProvider: Cache hit for sector {cache_key}")
                result = dict(cached_val)
                result["date"] = date_str
                return result

        # 3. Build API URLs
        # Open-Meteo Marine API: wave_height (m), wave_direction (°), wave_period (s)
        marine_url = (
            f"https://marine-api.open-meteo.com/v1/marine?"
            f"latitude={lat}&longitude={lon}&current=wave_height,wave_direction,wave_period,wind_wave_height"
        )
        # Open-Meteo Forecast API: wind_speed_10m (knots), wind_direction_10m (°), surface_pressure (hPa)
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=wind_speed_10m,wind_direction_10m,surface_pressure&wind_speed_unit=kn"
        )

        marine_data: Optional[Dict[str, Any]] = None
        forecast_data: Optional[Dict[str, Any]] = None

        # 4. Fetch concurrently
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_marine = executor.submit(self._fetch_url_json, marine_url)
                future_forecast = executor.submit(self._fetch_url_json, forecast_url)
                marine_data = future_marine.result(timeout=self.timeout_seconds + 1.0)
                forecast_data = future_forecast.result(timeout=self.timeout_seconds + 1.0)
        except Exception as e:
            logger.error(f"InterimLiveWeatherProvider: Network retrieval failed: {e}")
            return {
                "success": False,
                "error": f"Live marine weather API unavailable or timed out: {e}",
                "code": "INSUFFICIENT_DATA",
                "observation_type": "unavailable",
                "source": "Interim Live Weather Provider (Open-Meteo Marine API)",
                "data_status": "unavailable",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
            }

        if not marine_data or not forecast_data:
            return {
                "success": False,
                "error": "Failed to receive live weather or marine observations from service provider.",
                "code": "INSUFFICIENT_DATA",
                "observation_type": "unavailable",
                "source": "Interim Live Weather Provider (Open-Meteo Marine API)",
                "data_status": "unavailable",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
            }

        marine_current = marine_data.get("current", {})
        forecast_current = forecast_data.get("current", {})

        wave_height = marine_current.get("wave_height")
        wave_direction = marine_current.get("wave_direction")
        wave_period = marine_current.get("wave_period")

        wind_speed = forecast_current.get("wind_speed_10m")
        wind_direction = forecast_current.get("wind_direction_10m")
        surface_pressure = forecast_current.get("surface_pressure")

        # If wave height is missing (e.g. coordinates inland), return explicit insufficient data
        if wave_height is None and wind_speed is None:
            return {
                "success": False,
                "error": "No marine weather observations available for this coordinate (inland or unmonitored waters).",
                "code": "INSUFFICIENT_DATA",
                "observation_type": "unavailable",
                "source": "Interim Live Weather Provider (Open-Meteo Marine API)",
                "data_status": "insufficient_data",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
            }

        matched_lat = float(marine_data.get("latitude", lat))
        matched_lon = float(marine_data.get("longitude", lon))

        # Spatial distance approx
        import math
        dlat = (matched_lat - lat) * 111.0
        dlon = (matched_lon - lon) * 111.0 * math.cos(math.radians(lat))
        dist_km = round(math.sqrt(dlat**2 + dlon**2), 2)

        wind_speed_knots = float(wind_speed) if wind_speed is not None else None
        wave_height_meters = float(wave_height) if wave_height is not None else None
        surface_pressure_hpa = float(surface_pressure) if surface_pressure is not None else None

        result = {
            "success": True,
            "latitude": lat,
            "longitude": lon,
            "date": date_str,
            "matched_latitude": matched_lat,
            "matched_longitude": matched_lon,
            "distance_km": dist_km,
            "wind_speed_knots": wind_speed_knots,
            "wave_height_meters": wave_height_meters,
            "surface_pressure_hpa": surface_pressure_hpa,
            "wind_direction": str(round(wind_direction)) + "°" if wind_direction is not None else None,
            "wave_direction": str(round(wave_direction)) + "°" if wave_direction is not None else None,
            "wave_period_seconds": float(wave_period) if wave_period is not None else None,
            "source": "Interim Live Weather Provider (Open-Meteo Marine API)",
            "data_status": "observed",
            "observation_type": "current_observation",
        }

        # Cache result
        self._cache[cache_key] = (now, result)
        return result


# Backwards compatibility alias
LiveWeatherProvider = InterimLiveWeatherProvider
