"""
smart_marine_router.py

Intelligent Data Router for Marine Observations (Step 16).

Routes marine environmental data queries to:
  - LiveMarineProvider for LIVE requests (current / today / now)
  - HistoricalMarineProvider for HISTORICAL requests (past dates)
  - Explicit rejection for UNSUPPORTED_FUTURE requests (future dates)

Rules:
  - Zero silent data mixing across temporal boundaries.
  - No fallback from live to historical cache on live failure.
  - Return explicit INSUFFICIENT_DATA when data is missing.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Any, Optional

from .base_marine_provider import BaseMarineProvider
from .live_marine_provider import LiveMarineProvider
from .historical_marine_provider import HistoricalMarineProvider
from ..services.temporal_resolver import TemporalContextResolver, TemporalMode

logger = logging.getLogger(__name__)


class SmartMarineRouter(BaseMarineProvider):
    """
    Intelligent Marine Provider that delegates to LiveMarineProvider or
    HistoricalMarineProvider based on deterministic temporal resolution.
    """

    def __init__(
        self,
        live_provider: Optional[BaseMarineProvider] = None,
        historical_provider: Optional[BaseMarineProvider] = None,
        temporal_resolver: Optional[TemporalContextResolver] = None,
        reference_date: Optional[date] = None,
        max_distance_km: float = 50.0,
    ) -> None:
        """
        Args:
            live_provider: Injected or default LiveMarineProvider.
            historical_provider: Injected or default HistoricalMarineProvider.
            temporal_resolver: Injected or default TemporalContextResolver.
            reference_date: Optional reference date for testing.
            max_distance_km: Distance threshold.
        """
        self.max_distance_km = max_distance_km
        self._resolver = temporal_resolver or TemporalContextResolver(reference_date=reference_date)
        self._live_provider = live_provider or LiveMarineProvider(max_distance_km=max_distance_km)
        self._historical_provider = historical_provider or HistoricalMarineProvider(max_distance_km=max_distance_km)

    def get_marine_data(
        self,
        lat: float,
        lon: float,
        date_str: str,
        temporal_mode: Optional[TemporalMode] = None,
        query_text: str = "",
    ) -> Dict[str, Any]:
        """
        Retrieves marine observation by routing to the appropriate provider.

        Args:
            lat: Latitude.
            lon: Longitude.
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
        # Case 3: Future Date → Deterministic Rejection
        # ------------------------------------------------------------------
        if mode == TemporalMode.UNSUPPORTED_FUTURE:
            logger.info(f"Rejecting future date query for {effective_date}.")
            return {
                "success": False,
                "error": f"Date {effective_date} is in the future. Marine habitat forecasts are unsupported.",
                "code": "UNSUPPORTED_FUTURE",
                "temporal_mode": TemporalMode.UNSUPPORTED_FUTURE.value,
                "requested": {"lat": lat, "lon": lon, "date": effective_date},
            }

        # ------------------------------------------------------------------
        # Case 1: LIVE (Today / Current / Now)
        # ------------------------------------------------------------------
        if mode == TemporalMode.LIVE:
            logger.debug(f"Routing query for {effective_date} to LiveMarineProvider.")
            try:
                live_res = self._live_provider.get_marine_data(lat=lat, lon=lon, date_str=effective_date)
            except Exception as e:
                logger.error(f"LiveMarineProvider raised unexpected exception: {e}")
                return {
                    "success": False,
                    "error": f"Live marine data retrieval error: {e}",
                    "code": "INSUFFICIENT_DATA",
                    "temporal_mode": TemporalMode.LIVE.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            # Live provider must NOT fall back to historical cache on error
            if not live_res.get("success", False):
                return {
                    "success": False,
                    "error": live_res.get("error", "Live marine provider failed to return data."),
                    "code": "INSUFFICIENT_DATA",
                    "temporal_mode": TemporalMode.LIVE.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            # Tag temporal mode
            live_res["temporal_mode"] = TemporalMode.LIVE.value
            return live_res

        # ------------------------------------------------------------------
        # Case 2: HISTORICAL (Past Date)
        # ------------------------------------------------------------------
        if mode == TemporalMode.HISTORICAL:
            logger.debug(f"Routing query for {effective_date} to HistoricalMarineProvider.")
            try:
                hist_res = self._historical_provider.get_marine_data(lat=lat, lon=lon, date_str=effective_date)
            except Exception as e:
                logger.error(f"HistoricalMarineProvider raised unexpected exception: {e}")
                return {
                    "success": False,
                    "error": f"Insufficient data: Historical marine data for {effective_date} is unavailable ({e}).",
                    "code": "INSUFFICIENT_DATA",
                    "temporal_mode": TemporalMode.HISTORICAL.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            if not hist_res.get("success", False):
                return {
                    "success": False,
                    "error": f"Insufficient data: Historical marine data for {effective_date} is unavailable.",
                    "code": "INSUFFICIENT_DATA",
                    "temporal_mode": TemporalMode.HISTORICAL.value,
                    "requested": {"lat": lat, "lon": lon, "date": effective_date},
                }

            hist_res["temporal_mode"] = TemporalMode.HISTORICAL.value
            return hist_res

        # Default unexpected mode fallback
        return {
            "success": False,
            "error": f"Unrecognized temporal mode '{mode}' for date {effective_date}.",
            "code": "INVALID_TEMPORAL_MODE",
            "requested": {"lat": lat, "lon": lon, "date": effective_date},
        }
