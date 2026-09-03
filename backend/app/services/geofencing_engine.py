import os
import json
from typing import Dict, Any, Optional, List
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer

class GeofencingEngine:
    def __init__(
        self,
        eez_geojson_path: Optional[str] = None,
        config_path: Optional[str] = None,
        protected_areas_geojson_path: Optional[str] = None
    ):
        """
        Initializes the Geofencing Engine by loading static boundary geometries once in memory.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'geofence_config.json')
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Geofence config not found at: {config_path}")
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        if eez_geojson_path is None:
            eez_geojson_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', 'data', 'boundaries', 'india_eez.geojson'
            )
            eez_geojson_path = os.path.normpath(eez_geojson_path)

        if not os.path.exists(eez_geojson_path):
            raise FileNotFoundError(f"EEZ boundary GeoJSON not found at: {eez_geojson_path}")

        # 1. Load EEZ GeoJSON
        self.eez_gdf = gpd.read_file(eez_geojson_path)
        if self.eez_gdf.crs is None:
            self.eez_gdf.set_crs(epsg=4326, inplace=True)
        elif self.eez_gdf.crs.to_epsg() != 4326:
            self.eez_gdf = self.eez_gdf.to_crs(epsg=4326)

        # Merge all features into single unified polygon for efficient spatial predicate checks
        self.eez_geometry_wgs84 = self.eez_gdf.unary_union

        # 2. Prepare Metric Projection for Distance Calculation
        self.metric_crs = self.config.get("metric_crs", "EPSG:32643")
        self.eez_gdf_metric = self.eez_gdf.to_crs(self.metric_crs)
        self.eez_geometry_metric = self.eez_gdf_metric.unary_union
        self.eez_boundary_metric = self.eez_geometry_metric.boundary

        # Transformer to convert incoming WGS84 (lon, lat) to metric (x, y)
        self.transformer = Transformer.from_crs("EPSG:4326", self.metric_crs, always_xy=True)

        # 3. Protected Areas Layer (Extensible Interface)
        self.protected_areas_available = False
        self.protected_areas_gdf = None
        if protected_areas_geojson_path and os.path.exists(protected_areas_geojson_path):
            self.protected_areas_gdf = gpd.read_file(protected_areas_geojson_path)
            self.protected_areas_available = True

    def check_status(
        self,
        lat: float,
        lon: float,
        warning_distance_km: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the spatial location of a vessel against loaded maritime boundaries.

        Args:
            lat: Latitude in WGS84 decimal degrees.
            lon: Longitude in WGS84 decimal degrees.
            warning_distance_km: Optional boundary proximity warning threshold in km.

        Returns:
            Structured geofence status dictionary.
        """
        # 1. Validate Coordinates
        if not (-90 <= lat <= 90):
            return {
                "success": False,
                "error": f"Invalid latitude: {lat}. Must be between -90 and 90.",
                "requested": {"lat": lat, "lon": lon}
            }
        if not (-180 <= lon <= 180):
            return {
                "success": False,
                "error": f"Invalid longitude: {lon}. Must be between -180 and 180.",
                "requested": {"lat": lat, "lon": lon}
            }

        # 2. Construct WGS84 Point (lon, lat)
        point_wgs84 = Point(lon, lat)

        # 3. EEZ Spatial Containment Check (Predicate)
        # Using contains or intersects on the boundary polygon
        inside_eez = bool(self.eez_geometry_wgs84.contains(point_wgs84) or self.eez_geometry_wgs84.touches(point_wgs84))

        # 4. Projected Distance to EEZ Boundary Calculation
        x_m, y_m = self.transformer.transform(lon, lat)
        point_metric = Point(x_m, y_m)
        
        # Distance in meters to the boundary line
        dist_meters = float(self.eez_boundary_metric.distance(point_metric))
        distance_to_eez_km = round(dist_meters / 1000.0, 2)

        # 5. Protected Area Checks (Extensible interface)
        inside_protected = None
        nearest_protected = None
        dist_to_protected_km = None
        if self.protected_areas_available and self.protected_areas_gdf is not None:
            # Future implementation for loaded protected area polygons
            pass

        # 6. Determine Geofence Status & Deterministic Alerts
        threshold_km = warning_distance_km if warning_distance_km is not None else self.config.get("warning_distance_km", 15.0)
        
        alerts: List[str] = []
        statuses = self.config.get("statuses", {})

        if not inside_eez:
            geofence_status = statuses.get("outside_eez", "OUTSIDE_EEZ")
            alerts.append(
                f"Vessel is OUTSIDE the Indian Exclusive Economic Zone (EEZ) coverage area ({distance_to_eez_km} km from boundary)."
            )
        else:
            if distance_to_eez_km <= threshold_km:
                geofence_status = statuses.get("warning", "WARNING")
                alerts.append(
                    f"Vessel is approaching the EEZ maritime boundary ({distance_to_eez_km} km remaining, warning threshold is {threshold_km} km). Exercise caution."
                )
            else:
                geofence_status = statuses.get("safe", "SAFE")

        return {
            "latitude": lat,
            "longitude": lon,
            "inside_indian_eez": inside_eez,
            "distance_to_eez_boundary_km": distance_to_eez_km,
            "protected_area_coverage_available": self.protected_areas_available,
            "inside_protected_area": inside_protected,
            "nearest_protected_area": nearest_protected,
            "distance_to_protected_area_km": dist_to_protected_km,
            "geofence_status": geofence_status,
            "alerts": alerts,
            "success": True,
            "disclaimer": "This is a prototype decision-support geofencing engine based on supplied spatial boundary layers. It does not establish legal maritime boundaries or bilateral IMBL treaties."
        }
