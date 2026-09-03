"""
geofencing_tool.py

Exposes the Geofencing Engine as a structured tool callable by the
Geofencing Agent.

The tool's responsibility is COORDINATE VALIDATION and ENGINE INVOCATION only.
It does NOT implement geospatial logic.
All boundary checks and distance calculations stay inside GeofencingEngine.
"""

from typing import Dict, Any, Optional

from ..services.geofencing_engine import GeofencingEngine
from ..config import EEZ_GEOJSON_PATH, GEOFENCE_CONFIG_PATH


class GeofencingTool:
    """
    Structured tool that wraps the GeofencingEngine.

    The Geofencing Agent calls this tool; it never performs geospatial
    calculations itself.

    Architecture:
        GeofencingTool
            └─ GeofencingEngine (deterministic, authoritative)
                └─ india_eez.geojson (boundary data)
                └─ geofence_config.json (thresholds and status labels)
    """

    def __init__(self):
        """
        Initialises the GeofencingEngine once using project-configured paths.
        The engine loads the EEZ GeoJSON and builds the spatial index at init time.
        """
        self._engine = GeofencingEngine(
            eez_geojson_path=EEZ_GEOJSON_PATH,
            config_path=GEOFENCE_CONFIG_PATH,
        )

    def check_geofence(
        self,
        latitude: float,
        longitude: float,
        warning_distance_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a vessel position against the loaded maritime boundaries.

        Args:
            latitude:            WGS84 latitude in decimal degrees.
            longitude:           WGS84 longitude in decimal degrees.
            warning_distance_km: Optional proximity warning threshold in km.
                                 If None, the engine uses the config default (15 km).

        Returns:
            Structured geofence status dict produced by GeofencingEngine.
            On validation failure the dict contains success=False and an error message.
        """
        # Basic type check — the engine also validates ranges and will return
        # a structured error dict, but give an early friendly message here.
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return {
                "success": False,
                "error": "Latitude and longitude must be numeric values.",
                "requested": {"lat": latitude, "lon": longitude},
            }

        # Delegate entirely to the engine — no spatial logic here.
        try:
            result = self._engine.check_status(
                lat=latitude,
                lon=longitude,
                warning_distance_km=warning_distance_km,
            )
        except Exception as exc:
            return {
                "success": False,
                "error": f"Geofencing engine error: {exc}",
                "requested": {"lat": latitude, "lon": longitude},
            }

        return result
