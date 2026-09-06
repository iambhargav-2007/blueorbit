import pytest
from app.services.routing_engine import AStarRoutingEngine
from app.tools.routing_tool import RoutingTool

def test_astar_simple_route():
    engine = AStarRoutingEngine(resolution_degrees=0.05, max_nodes=1000)
    
    # Very simple deterministic data callback (all sea)
    def mock_node_data(lat, lon):
        return {
            "is_passable": True,
            "penalty": 0.0,
            "weather_state": "NORMAL",
            "wave_state": "NORMAL",
            "geofence_state": "SAFE",
            "hazard_state": "SAFE"
        }
        
    res = engine.compute_route(
        start_lat=18.0, start_lon=72.0,
        dest_lat=18.1, dest_lon=72.1,
        get_node_data=mock_node_data,
        mode="SAFEST"
    )
    
    assert res["status"] == "SUCCESS"
    assert len(res["route_points"]) > 2
    assert res["total_distance_km"] > 0

def test_astar_impassable_barrier():
    engine = AStarRoutingEngine(resolution_degrees=0.05, max_nodes=1000)
    
    # Create an impassable line between start and dest
    def mock_node_data(lat, lon):
        is_passable = True
        # Block latitude 18.05
        if 18.04 <= lat <= 18.06:
            is_passable = False
            
        return {
            "is_passable": is_passable,
            "penalty": 0.0,
            "weather_state": "NORMAL",
            "wave_state": "NORMAL",
            "geofence_state": "SAFE",
            "hazard_state": "SAFE"
        }
        
    res = engine.compute_route(
        start_lat=18.0, start_lon=72.0,
        dest_lat=18.1, dest_lon=72.0,
        get_node_data=mock_node_data,
        mode="SAFEST"
    )
    
    assert res["status"] == "NO_SAFE_ROUTE"

def test_routing_tool_success(mocker):
    # Mock geofencing to avoid loading big geojson in tests
    mocker.patch("app.services.geofencing_engine.GeofencingEngine.check_status", return_value={"geofence_status": "SAFE"})
    
    tool = RoutingTool()
    res = tool.plan_route(start_lat=18.0, start_lon=72.0, dest_lat=18.1, dest_lon=72.1)
    
    assert res.status == "SUCCESS"
    assert res.total_distance_km > 0
    assert len(res.route_points) > 0
