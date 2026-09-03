"""
smart_weather_router.py

Intelligent Data Router for Marine Weather & Sea State Observations (Step 19).

Routes marine weather queries to:
  - InterimLiveWeatherProvider for LIVE requests (current / today / now)
  - CacheWeatherProvider for HISTORICAL requests (October 2025 cache / past dates)
  - Explicit rejection for UNSUPPORTED_FUTURE requests (future dates / forecasts)

Rules:
  - Zero silent data mixing across temporal boundaries.
  - No fallback from live to historical cache on live failure.
  - Return explicit INSUFFICIENT_DATA when data is missing or out of threshold.
  - Extensible design allowing future IMDWeatherProvider integration without
    modifying downstream engines or agents.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Any, Optional

from .base_weather_provider import BaseWeatherProvider
from .live_weather_provider import InterimLiveWeatherProvider
from .cache_weather_provider import CacheWeatherProvider
from ..services.temporal_resolver import TemporalContextResolver, TemporalMode

logger = logging.getLogger(__name__)


class SmartWeatherRouter(BaseWeatherProvider):
    """
    Intelligent Weather Provider that delegates to InterimLiveWeatherProvider or
    CacheWeatherProvider based on deterministic temporal resolution.
    """

    def __init__(
        self,
        live_provider: Optional[BaseWeatherProvider] = None,
        historical_provider: Optional[BaseWeatherProvider] = None,
        imd_provider: Optional[BaseWeatherProvider] = None,
        temporal_resolver: Optional[TemporalContextResolver] = None,
        reference_date: Optional[date] = None,
        max_distance_km: float = 100.0,
    ) -> None:
        """
        Args:
            live_provider: Injected or default InterimLiveWeatherProvider.
            historical_provider: Injected or default CacheWeatherProvider.
            imd_provider: Optional future India Meteorological Department provider.
            temporal_resolver: Injected or default TemporalContextResolver.
            reference_date: Optional reference date for testing.
            max_distance_km: Distance threshold.
        """
        self.max_distance_km = max_distance_km
        self._resolver = temporal_resolver or TemporalContextResolver(reference_date=reference_date)
        self._live_provider = live_provider or InterimLiveWeatherProvider()
        self._historical_provider = historical_provider or CacheWeatherProvider(max_distance_km=max_distance_km)
        self._imd_provider = imd_provider  # Ready for future official IMD integration

    def get_weather(
        self,
        lat: float,
        lon: float,
        date_str: str,
        temporal_mode: Optional[TemporalMode] = None,
        query_text: str = "",
    ) -> Dict[str, Any]:
        """
        Retrieves weather observation by routing to the appropriate provider.

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.
            date_str: Target date string 'YYYY-MM-DD'.
            temporal_mode: Explicit mode override if already resolved.
            query_text: Optional original query text to help resolution.

        Returns:
            Structured observation dict or explicit failure dict.
        """
        # 1. Resolve temporal mode if not explicitly supplied
        if temporal_mode is None:
            resolution = self._resolver.resolve(
                query_text=query_text,
                explicit_date_str=date_str
            )
            mode = resolution.mode
            effective_date = resolution.date_str or date_str
        else:
            mode = temporal_mode
            effective_date = date_str

        # ------------------------------------------------------------------
        # Case 1: Future Date → Deterministic Rejection
        # ------------------------------------------------------------------
        if mode == TemporalMode.UNSUPPORTED_FUTURE:
            logger.info(f"Rejecting future date query for weather on {effective_date}.")
            return {
                "success": False,
                "error": (
                    f"Date {effective_date} is in the future. Marine weather forecasts are "
                    f"currently unsupported without verified forecast providers. "
                    f"Authoritative IMD marine forecasts are not yet integrated."
                ),
                "code": "UNSUPPORTED_FUTURE",
                "observation_type": "unavailable",
                "source": "None",
                "data_status": "unavailable",
                "temporal_mode": TemporalMode.UNSUPPORTED_FUTURE.value,
                "requested": {"lat": lat, "lon": lon, "date": effective_date},
            }

        # ------------------------------------------------------------------
        # Case 2: LIVE (Today / Current / Now)
        # ------------------------------------------------------------------
        if mode == TemporalMode.LIVE:
            logger.debug(f"Routing weather query for {effective_date} to InterimLiveWeatherProvider.")
            # Prefer IMD provider if configured and available
            active_live = self._imd_provider or self._live_provider
            try:
                live_res = active_live.get_weather(lat=lat, lon=lon, date_str=effective_date)
            except Exception as e:
                logger.error(f"Live weather provider raised unexpected exception: {e}")
                return {
                    "success": False,
                    "error": f"Live marine weather data retrieval error: {e}",
                    "code": "INSUFFICIENT_DATA",
                    "observation_type": "unavailable",
                    "source": "Live Provider Failure",
                    "data_status": "unavailable",
                    "temporal_mode": TemporalMode.LIVE.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            # Live provider must NEVER fall back to historical cache on error
            if not live_res.get("success", False):
                return {
                    "success": False,
                    "error": live_res.get("error", "Live weather provider failed to return valid observations."),
                    "code": live_res.get("code", "INSUFFICIENT_DATA"),
                    "observation_type": "unavailable",
                    "source": live_res.get("source", "Interim Live Weather Provider"),
                    "data_status": "unavailable",
                    "temporal_mode": TemporalMode.LIVE.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            # Tag temporal mode
            live_res["temporal_mode"] = TemporalMode.LIVE.value
            return live_res

        # ------------------------------------------------------------------
        # Case 3: HISTORICAL (Past Date)
        # ------------------------------------------------------------------
        if mode == TemporalMode.HISTORICAL:
            logger.debug(f"Routing weather query for {effective_date} to CacheWeatherProvider.")
            try:
                hist_res = self._historical_provider.get_weather(lat=lat, lon=lon, date_str=effective_date)
            except Exception as e:
                logger.error(f"CacheWeatherProvider raised unexpected exception: {e}")
                return {
                    "success": False,
                    "error": f"Historical weather cache retrieval error: {e}",
                    "code": "INSUFFICIENT_DATA",
                    "observation_type": "unavailable",
                    "source": "Historical Weather Cache",
                    "data_status": "unavailable",
                    "temporal_mode": TemporalMode.HISTORICAL.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            hist_res["temporal_mode"] = TemporalMode.HISTORICAL.value
            return hist_res

        # Default fallback (unhandled temporal mode)
        return {
            "success": False,
            "error": f"Unsupported temporal mode '{mode}'.",
            "code": "INSUFFICIENT_DATA",
            "observation_type": "unavailable",
            "temporal_mode": str(mode),
            "requested": {"lat": lat, "lon": lon, "date": effective_date},
        }
