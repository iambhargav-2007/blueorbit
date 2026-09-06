import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..services.routing_engine import AStarRoutingEngine
from ..services.geofencing_engine import GeofencingEngine
from ..services.weather_safety_engine import WeatherSafetyEngine
from ..agents.schemas import RoutingResult, RouteNode, LocationInfo

logger = logging.getLogger(__name__)

class RoutingTool:
    def __init__(
        self,
        weather_engine: Optional[WeatherSafetyEngine] = None,
        geofencing_engine: Optional[GeofencingEngine] = None
    ):
        self.routing_engine = AStarRoutingEngine(resolution_degrees=0.05, max_nodes=10000)
        self.weather_engine = weather_engine or WeatherSafetyEngine()
        self.geofencing_engine = geofencing_engine or GeofencingEngine()
        # In a real scenario, this cache would be populated by a bulk API call to WeatherProvider
        self.weather_cache = {}

    def _get_node_data(self, lat: float, lon: float, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluates a single grid node for weather and geofence hazards.
        """
        # Geofence check
        geo_status = self.geofencing_engine.check_status(lat, lon, warning_distance_km=10.0)
        geofence_state = geo_status.get("geofence_status", "UNKNOWN")
        
        penalty = 0.0
        is_passable = True
        hazard_state = "SAFE"
        
        if geofence_state == "OUTSIDE_EEZ":
            penalty += 10.0
            hazard_state = "CAUTION"
        elif geofence_state == "WARNING":
            penalty += 2.0
            hazard_state = "CAUTION"
            
        # Simplified simulated weather check to avoid massive API calls in A* loop
        # In a real system, use weather_engine with pre-fetched grid
        weather_state = "NORMAL"
        wave_state = "NORMAL"
        
        # Artificial bad weather zone for demonstration/testing (e.g., strong wind around 18.0N)
        if 17.5 <= lat <= 18.5 and 71.0 <= lon <= 72.0:
            weather_state = "HIGH_WIND"
            wave_state = "HIGH_WAVES"
            penalty += 50.0  # High penalty for bad weather
            hazard_state = "CAUTION"
            
        # If penalty is too high, mark as impassable (or let A* route around it)
        if penalty > 100.0:
            is_passable = False
            hazard_state = "BLOCKED"

        return {
            "is_passable": is_passable,
            "penalty": penalty,
            "weather_state": weather_state,
            "wave_state": wave_state,
            "geofence_state": geofence_state,
            "hazard_state": hazard_state
        }

    def plan_route(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        date_str: Optional[str] = None,
        mode: str = "SAFEST"
    ) -> RoutingResult:
        
        try:
            # Deterministic Routing
            engine_res = self.routing_engine.compute_route(
                start_lat=start_lat,
                start_lon=start_lon,
                dest_lat=dest_lat,
                dest_lon=dest_lon,
                get_node_data=lambda lat, lon: self._get_node_data(lat, lon, date_str),
                mode=mode
            )
            
            start_loc = LocationInfo(latitude=start_lat, longitude=start_lon)
            dest_loc = LocationInfo(latitude=dest_lat, longitude=dest_lon)
            
            if engine_res["status"] != "SUCCESS":
                return RoutingResult(
                    status=engine_res["status"],
                    start_location=start_loc,
                    destination_location=dest_loc,
                    warnings=[engine_res.get("reason", "Route generation failed.")]
                )
                
            nodes = []
            for pt in engine_res["route_points"]:
                nodes.append(RouteNode(**pt))
                
            result = RoutingResult(
                status="SUCCESS",
                start_location=start_loc,
                destination_location=dest_loc,
                route_points=nodes,
                total_distance_km=engine_res["total_distance_km"],
                estimated_route_cost=engine_res["estimated_route_cost"],
                weather_assessment="Evaluated using grid heuristic",
                geofence_assessment="Evaluated against EEZ boundary",
                hazard_summary="Completed",
                data_status="PARTIAL",
                temporal_mode="LIVE" if not date_str else "HISTORICAL",
                data_sources=["GeofencingEngine", "Heuristic Weather"],
                generated_at=datetime.utcnow().isoformat(),
                warnings=[]
            )
            return result
            
        except Exception as e:
            logger.error(f"RoutingTool error: {e}")
            return RoutingResult(
                status="ERROR",
                start_location=LocationInfo(latitude=start_lat, longitude=start_lon),
                destination_location=LocationInfo(latitude=dest_lat, longitude=dest_lon),
                warnings=[f"Engine error: {str(e)}"]
            )
