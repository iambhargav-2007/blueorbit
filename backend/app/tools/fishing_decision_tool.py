"""
fishing_decision_tool.py

Structured tool that orchestrates HabitatSuitabilityTool, WeatherSafetyTool,
and GeofencingTool, passing their deterministic outputs into the
UnifiedFishingDecisionEngine.

Architecture:
    FishingDecisionTool
        ├─ HabitatSuitabilityTool (Copernicus Marine SST/Chlorophyll)
        ├─ WeatherSafetyTool (Open-Meteo or Historical Parquet)
        ├─ GeofencingTool (Indian EEZ boundary buffer)
        └─ UnifiedFishingDecisionEngine (authoritative deterministic logic)
"""

from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

from .habitat_tool import HabitatSuitabilityTool
from .weather_tool import WeatherSafetyTool
from .geofencing_tool import GeofencingTool
from ..services.unified_decision_engine import UnifiedFishingDecisionEngine
from ..services.temporal_resolver import TemporalResolution, TemporalMode
from ..agents.schemas import FishingDecision

logger = logging.getLogger(__name__)


class FishingDecisionTool:
    """
    Orchestration tool for unified fishing decisions.
    Fetches marine, weather, and geofencing observations and evaluates them
    via the deterministic UnifiedFishingDecisionEngine.
    """

    def __init__(
        self,
        habitat_tool: Optional[HabitatSuitabilityTool] = None,
        weather_tool: Optional[WeatherSafetyTool] = None,
        geofencing_tool: Optional[GeofencingTool] = None,
        decision_engine: Optional[UnifiedFishingDecisionEngine] = None,
    ):
        self._habitat_tool = habitat_tool or HabitatSuitabilityTool()
        self._weather_tool = weather_tool or WeatherSafetyTool()
        self._geofencing_tool = geofencing_tool or GeofencingTool()
        self._engine = decision_engine or UnifiedFishingDecisionEngine()

    def get_fishing_decision(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
        temporal_resolution: Optional[TemporalResolution] = None,
        query_text: str = "",
    ) -> Dict[str, Any]:
        """
        Executes domain checks and generates a unified fishing recommendation.
        """
        # Resolve temporal mode
        temporal_mode_str = "LIVE"
        if temporal_resolution:
            temporal_mode_str = temporal_resolution.mode.value
        elif date_str:
            # Fallback simple check
            from datetime import datetime
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                today = datetime.utcnow().date()
                if dt > today:
                    temporal_mode_str = "UNSUPPORTED_FUTURE"
                elif dt < today:
                    temporal_mode_str = "HISTORICAL"
                else:
                    temporal_mode_str = "LIVE"
            except Exception:
                temporal_mode_str = "LIVE"

        # If unsupported future, return immediate rejection without expensive network calls
        if temporal_mode_str == "UNSUPPORTED_FUTURE":
            decision = self._engine.evaluate(
                habitat_data=None,
                weather_data=None,
                geofence_data=None,
                latitude=latitude,
                longitude=longitude,
                date_str=date_str,
                temporal_mode=temporal_mode_str,
            )
            return {
                "success": True,
                "decision": decision,
                "habitat": None,
                "weather": None,
                "geofencing": None,
            }

        # Concurrently retrieve Habitat and Weather data to maximize performance
        habitat_res: Optional[Dict[str, Any]] = None
        weather_res: Optional[Dict[str, Any]] = None

        def fetch_habitat():
            try:
                temp_mode = temporal_resolution.mode if temporal_resolution else None
                return self._habitat_tool.get_habitat_suitability(
                    latitude=latitude,
                    longitude=longitude,
                    date_str=date_str,
                    temporal_mode=temp_mode,
                    query_text=query_text,
                )
            except Exception as e:
                logger.error(f"FishingDecisionTool: Habitat fetch error: {e}")
                return {"success": False, "error": str(e), "fishing_potential": "Insufficient Data"}

        def fetch_weather():
            try:
                return self._weather_tool.get_weather_safety(
                    latitude=latitude,
                    longitude=longitude,
                    date_str=date_str,
                    temporal_resolution=temporal_resolution,
                    query_text=query_text,
                )
            except Exception as e:
                logger.error(f"FishingDecisionTool: Weather fetch error: {e}")
                return {"success": False, "error": str(e), "risk_level": "Insufficient Data"}

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_hab = executor.submit(fetch_habitat)
            fut_weath = executor.submit(fetch_weather)
            habitat_res = fut_hab.result()
            weather_res = fut_weath.result()

        # Geofence check (in-memory, <1ms)
        try:
            geofence_res = self._geofencing_tool.check_geofence(latitude=latitude, longitude=longitude)
        except Exception as e:
            logger.error(f"FishingDecisionTool: Geofence check error: {e}")
            geofence_res = {"success": False, "error": str(e), "status": "UNKNOWN"}

        # Feed all three into deterministic decision engine
        decision = self._engine.evaluate(
            habitat_data=habitat_res,
            weather_data=weather_res,
            geofence_data=geofence_res,
            latitude=latitude,
            longitude=longitude,
            date_str=date_str,
            temporal_mode=temporal_mode_str,
        )

        return {
            "success": True,
            "decision": decision,
            "habitat": habitat_res,
            "weather": weather_res,
            "geofencing": geofence_res,
        }
