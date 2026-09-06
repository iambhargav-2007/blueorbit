import math
import heapq
from typing import List, Tuple, Dict, Any, Callable

# Haversine formula to calculate geographic distance
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class AStarRoutingEngine:
    def __init__(self, resolution_degrees: float = 0.05, max_nodes: int = 5000):
        self.resolution = resolution_degrees
        self.max_nodes = max_nodes

    def _get_neighbors(self, lat: float, lon: float) -> List[Tuple[float, float]]:
        # 8-connected grid
        res = self.resolution
        return [
            (lat + res, lon),
            (lat - res, lon),
            (lat, lon + res),
            (lat, lon - res),
            (lat + res, lon + res),
            (lat + res, lon - res),
            (lat - res, lon + res),
            (lat - res, lon - res)
        ]

    def _snap_to_grid(self, lat: float, lon: float) -> Tuple[float, float]:
        res = self.resolution
        return (round(lat / res) * res, round(lon / res) * res)

    def compute_route(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        get_node_data: Callable[[float, float], Dict[str, Any]],
        mode: str = "SAFEST"
    ) -> Dict[str, Any]:
        """
        Computes the A* route.
        get_node_data should return a dict with:
        - is_passable: bool
        - penalty: float (additional cost)
        - weather_state: str
        - wave_state: str
        - geofence_state: str
        - hazard_state: str
        """
        start_node = self._snap_to_grid(start_lat, start_lon)
        dest_node = self._snap_to_grid(dest_lat, dest_lon)

        # Priority queue for A* (f_score, lat, lon)
        open_set = []
        heapq.heappush(open_set, (0.0, start_node[0], start_node[1]))

        # Maps node to its parent (for path reconstruction)
        came_from = {}

        # Cost from start to a node
        g_score = {start_node: 0.0}

        explored_count = 0
        node_data_cache = {}

        while open_set:
            if explored_count > self.max_nodes:
                return {"status": "ERROR", "reason": "Max nodes exceeded. Try shorter distance."}
            
            _, current_lat, current_lon = heapq.heappop(open_set)
            current_node = (current_lat, current_lon)

            # If we reached destination
            if haversine_distance(current_lat, current_lon, dest_node[0], dest_node[1]) <= self.resolution:
                # Reconstruct path
                path = []
                curr = current_node
                while curr in came_from:
                    path.append(curr)
                    curr = came_from[curr]
                path.append(start_node)
                path.reverse()
                
                # We reached near the destination, let's append exact destination
                if path[-1] != (dest_lat, dest_lon):
                    path.append((dest_lat, dest_lon))
                
                # Build route points with data
                route_points = []
                total_dist = 0.0
                prev_pt = None
                
                for pt in path:
                    lat, lon = pt
                    data = node_data_cache.get(pt)
                    if data is None:
                        data = get_node_data(lat, lon)
                    
                    dist_from_prev = 0.0
                    if prev_pt:
                        dist_from_prev = haversine_distance(prev_pt[0], prev_pt[1], lat, lon)
                    total_dist += dist_from_prev
                    
                    route_points.append({
                        "latitude": lat,
                        "longitude": lon,
                        "distance_from_start_km": total_dist,
                        "weather_state": data.get("weather_state", "UNKNOWN"),
                        "wave_state": data.get("wave_state", "UNKNOWN"),
                        "geofence_state": data.get("geofence_state", "UNKNOWN"),
                        "hazard_state": data.get("hazard_state", "UNKNOWN"),
                        "traversal_cost": data.get("penalty", 0.0) + dist_from_prev
                    })
                    prev_pt = pt

                return {
                    "status": "SUCCESS",
                    "route_points": route_points,
                    "total_distance_km": total_dist,
                    "estimated_route_cost": g_score[current_node]
                }

            explored_count += 1

            for neighbor_lat, neighbor_lon in self._get_neighbors(current_lat, current_lon):
                neighbor = (round(neighbor_lat, 5), round(neighbor_lon, 5))
                
                if neighbor not in node_data_cache:
                    node_data_cache[neighbor] = get_node_data(neighbor[0], neighbor[1])
                
                data = node_data_cache[neighbor]
                if not data.get("is_passable", True):
                    continue
                
                dist = haversine_distance(current_lat, current_lon, neighbor[0], neighbor[1])
                
                # Apply mode weights
                penalty = data.get("penalty", 0.0)
                if mode == "SHORTEST":
                    penalty = penalty * 0.1
                elif mode == "SAFEST":
                    penalty = penalty * 2.0
                
                tentative_g_score = g_score[current_node] + dist + penalty

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current_node
                    g_score[neighbor] = tentative_g_score
                    h_score = haversine_distance(neighbor[0], neighbor[1], dest_node[0], dest_node[1])
                    f_score = tentative_g_score + h_score
                    heapq.heappush(open_set, (f_score, neighbor[0], neighbor[1]))

        return {"status": "NO_SAFE_ROUTE", "reason": "No valid path found."}
