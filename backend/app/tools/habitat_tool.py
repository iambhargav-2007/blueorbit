"""
habitat_tool.py

Exposes the Habitat Suitability Engine as a structured tool callable by the
Fishing/Habitat Agent.

The tool's responsibility is DATA RETRIEVAL and ENGINE INVOCATION only.
It does NOT modify, recalculate, or interpret scores.
All mathematical logic stays inside HabitatSuitabilityEngine.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..providers.factory import get_smart_marine_router, get_marine_provider
from ..providers.smart_marine_router import SmartMarineRouter
from ..services.habitat_suitability_engine import HabitatSuitabilityEngine
from ..services.temporal_resolver import TemporalMode


class HabitatTool:
    """
    Structured tool that wraps the marine data provider + Habitat Suitability Engine.

    The Fishing/Habitat Agent calls this tool; it never computes scores itself.
    """

    def __init__(
        self,
        live_mode: Optional[bool] = None,
        router: Optional[SmartMarineRouter] = None,
        max_distance_km: float = 50.0,
    ):
        """
        Args:
            live_mode: Legacy flag. If provided and router is None, uses static provider.
            router: Optional SmartMarineRouter instance.
            max_distance_km: Maximum spatial search radius passed to the marine provider.
        """
        self.max_distance_km = max_distance_km
        if router is not None:
            self._router = router
            self._legacy_provider = None
        elif live_mode is not None:
            # If live_mode is explicitly forced, honor legacy single-provider mode
            self._legacy_provider = get_marine_provider(live_mode=live_mode, max_distance_km=max_distance_km)
            self._router = get_smart_marine_router(max_distance_km=max_distance_km)
        else:
            self._router = get_smart_marine_router(max_distance_km=max_distance_km)
            self._legacy_provider = None

        self._engine = HabitatSuitabilityEngine()

    def get_habitat_suitability(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
        temporal_mode: Optional[TemporalMode] = None,
        query_text: str = "",
    ) -> Dict[str, Any]:
        """
        Retrieves marine environmental observations for the given coordinate/date
        and returns the deterministic habitat suitability assessment.

        Args:
            latitude:  WGS84 latitude in decimal degrees.
            longitude: WGS84 longitude in decimal degrees.
            date_str:  Target date as 'YYYY-MM-DD'.
            temporal_mode: Optional pre-resolved TemporalMode.
            query_text: Optional original query text for context.

        Returns:
            Structured habitat assessment dict produced by HabitatSuitabilityEngine.
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

        # 3. Retrieve marine observation via the provider/router
        try:
            if self._legacy_provider is not None and temporal_mode is None:
                marine_data = self._legacy_provider.get_marine_data(
                    lat=latitude, lon=longitude, date_str=date_str
                )
            else:
                marine_data = self._router.get_marine_data(
                    lat=latitude,
                    lon=longitude,
                    date_str=date_str,
                    temporal_mode=temporal_mode,
                    query_text=query_text
                )
        except Exception as exc:
            return {
                "success": False,
                "error": f"Marine data provider error: {exc}",
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        # 4. If router returned a failure (e.g. UNSUPPORTED_FUTURE or INSUFFICIENT_DATA)
        if not marine_data.get("success", False):
            return {
                "success": False,
                "error": marine_data.get("error", "Marine data retrieval failed."),
                "code": marine_data.get("code"),
                "temporal_mode": marine_data.get("temporal_mode"),
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        # 5. Feed observation into the authoritative Habitat Suitability Engine
        try:
            result = self._engine.assess(marine_data)
            if "temporal_mode" in marine_data:
                result["temporal_mode"] = marine_data["temporal_mode"]
        except Exception as exc:
            return {
                "success": False,
                "error": f"Habitat engine error: {exc}",
                "requested": {"latitude": latitude, "longitude": longitude, "date": date_str},
            }

        return result

    def compare_habitat_suitability(
        self,
        latitude: float,
        longitude: float,
        historical_date: str,
        current_date: str,
    ) -> Dict[str, Any]:
        """
        Executes two independent data paths:
          1. Historical provider -> Historical habitat assessment
          2. Live provider -> Live habitat assessment
        Returns both in a structured comparison format without mixing.
        """
        # Validate coordinates
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return {
                "success": False,
                "error": "Latitude and longitude must be numeric values.",
                "requested": {"latitude": latitude, "longitude": longitude},
            }

        # 1. Historical Path
        hist_marine = self._router.get_marine_data(
            lat=latitude,
            lon=longitude,
            date_str=historical_date,
            temporal_mode=TemporalMode.HISTORICAL
        )
        hist_assessment = self._engine.assess(hist_marine)

        # 2. Live Path
        live_marine = self._router.get_marine_data(
            lat=latitude,
            lon=longitude,
            date_str=current_date,
            temporal_mode=TemporalMode.LIVE
        )
        live_assessment = self._engine.assess(live_marine, strict_completeness=True)

        return {
            "success": True,
            "type": "comparison",
            "historical": {
                "date": historical_date,
                "result": hist_assessment,
            },
            "current": {
                "date": current_date,
                "result": live_assessment,
            },
            "latitude": latitude,
            "longitude": longitude,
        }


# Alias for cross-module consistency
HabitatSuitabilityTool = HabitatTool
