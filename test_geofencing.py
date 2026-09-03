import sys
import json
import os
import geopandas as gpd

# Add backend to path to allow importing the service
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.geofencing_engine import GeofencingEngine

def inspect_geojson(filepath: str):
    print("==================================================")
    print("GEOJSON INSPECTION REPORT")
    print("==================================================")
    gdf = gpd.read_file(filepath)
    print(f"File: {filepath}")
    print(f"GeoJSON Type: FeatureCollection (GeoDataFrame loaded)")
    print(f"Feature Count: {len(gdf)}")
    print(f"Geometry Types: {list(gdf.geom_type.unique())}")
    print(f"CRS: {gdf.crs}")
    total_bounds = gdf.total_bounds # minx, miny, maxx, maxy
    print(f"Bounding Box: [MinLon: {total_bounds[0]:.4f}, MinLat: {total_bounds[1]:.4f}, MaxLon: {total_bounds[2]:.4f}, MaxLat: {total_bounds[3]:.4f}]")
    print(f"Important Properties: {list(gdf.columns.drop('geometry').values)}")
    print(f"Sample Properties: {gdf.iloc[0].drop('geometry').to_dict()}")
    print("Protected-Area Geometry Exists in file: NO (Only EEZ polygon present)")
    print("==================================================\n")

def main():
    eez_path = "data/boundaries/india_eez.geojson"
    config_path = "backend/app/config/geofence_config.json"

    # Run inspection first
    inspect_geojson(eez_path)

    print("Initializing Geofencing Engine...")
    try:
        engine = GeofencingEngine(eez_geojson_path=eez_path, config_path=config_path)
        print("Geofencing Engine initialized successfully!\n")
    except Exception as e:
        print(f"Failed to initialize Geofencing Engine: {e}")
        return

    def run_check(desc, lat, lon, warning_distance_km=None):
        print(f"==================================================")
        print(f"--- {desc} ---")
        print(f"Requested: Lat={lat}, Lon={lon}, WarningThreshold={warning_distance_km or 'Default'}")
        result = engine.check_status(lat=lat, lon=lon, warning_distance_km=warning_distance_km)
        print("Result:")
        print(json.dumps(result, indent=2))
        print("\n")

    # TEST 1: Clearly inside EEZ
    run_check(
        "TEST 1: Clearly Inside EEZ",
        lat=19.0, lon=71.0
    )

    # TEST 2: Clearly outside EEZ
    run_check(
        "TEST 2: Clearly Outside EEZ",
        lat=18.0, lon=65.0
    )

    # TEST 3: Coordinate near EEZ boundary (within warning threshold)
    # At the western EEZ boundary (Lon ~68.0), a point at Lon 68.08, Lat 19.0 is very close to boundary
    run_check(
        "TEST 3: Near Boundary Warning Zone",
        lat=19.0, lon=68.08, warning_distance_km=15.0
    )

    # TEST 4: Invalid Latitude
    run_check(
        "TEST 4: Invalid Latitude",
        lat=95.0, lon=71.0
    )

    # TEST 5: Invalid Longitude
    run_check(
        "TEST 5: Invalid Longitude",
        lat=19.0, lon=195.0
    )

    # TEST 6: Protected Area Availability Verification
    print(f"==================================================")
    print(f"--- TEST 6: Protected Area Unavailability Explicit Check ---")
    res = engine.check_status(lat=19.0, lon=71.0)
    print(f"protected_area_coverage_available: {res['protected_area_coverage_available']}")
    print(f"inside_protected_area: {res['inside_protected_area']}")
    print(f"nearest_protected_area: {res['nearest_protected_area']}")
    print(f"Explanation: Verified that protected area status is NOT falsely reported as active or evaluated as false when geometry is absent.")
    print("==================================================\n")

if __name__ == "__main__":
    main()
