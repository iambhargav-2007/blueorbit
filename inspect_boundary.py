"""
inspect_boundary.py
Inspection and validation script for data/boundaries/india_eez.geojson
"""

import sys
import os
import json

def audit_eez_geojson(filepath="data/boundaries/india_eez.geojson"):
    print("========================================")
    print("BLUE ORBIT — EEZ GEOJSON AUDIT")
    print("========================================")
    
    if not os.path.exists(filepath):
        print(f"File: {filepath} (NOT FOUND)")
        print("\nVALIDATION:\nFAIL")
        print("Reason: File does not exist.")
        return

    # 1. Check if file is valid JSON / GeoJSON
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"File: {filepath}")
        print(f"Error parsing JSON: {e}")
        print("\nVALIDATION:\nFAIL")
        return

    geojson_type = raw_data.get("type", "Unknown")
    crs_info = raw_data.get("crs", None)
    
    # Try importing shapely and geopandas
    try:
        import geopandas as gpd
        from shapely.geometry import shape
        from shapely.validation import explain_validity
        has_geo_libs = True
    except ImportError:
        has_geo_libs = False

    # Inspect features
    if geojson_type == "FeatureCollection":
        features = raw_data.get("features", [])
    elif geojson_type == "Feature":
        features = [raw_data]
    else:
        features = []

    feature_count = len(features)
    geometry_types = set()
    invalid_geoms = 0
    empty_geoms = 0
    property_keys = set()
    
    min_lon, min_lat = float('inf'), float('inf')
    max_lon, max_lat = float('-inf'), float('-inf')

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        if props:
            property_keys.update(props.keys())

        geom = feat.get("geometry")
        if geom is None:
            empty_geoms += 1
            continue

        g_type = geom.get("type")
        if g_type:
            geometry_types.add(g_type)

        if has_geo_libs:
            try:
                s_geom = shape(geom)
                if s_geom.is_empty:
                    empty_geoms += 1
                if not s_geom.is_valid:
                    invalid_geoms += 1
                    # print(f"Feature {idx} validity issue: {explain_validity(s_geom)}")
                
                bounds = s_geom.bounds # (minx, miny, maxx, maxy)
                min_lon = min(min_lon, bounds[0])
                min_lat = min(min_lat, bounds[1])
                max_lon = max(max_lon, bounds[2])
                max_lat = max(max_lat, bounds[3])
            except Exception as ex:
                invalid_geoms += 1
        else:
            # Fallback coordinate parsing if geo libs are not loaded
            coords = geom.get("coordinates", [])
            def extract_coords(c):
                if isinstance(c, (list, tuple)):
                    if len(c) >= 2 and isinstance(c[0], (int, float)) and isinstance(c[1], (int, float)):
                        yield c[0], c[1]
                    else:
                        for sub in c:
                            yield from extract_coords(sub)
            all_pts = list(extract_coords(coords))
            if not all_pts:
                empty_geoms += 1
            else:
                for lon, lat in all_pts:
                    min_lon = min(min_lon, lon)
                    max_lon = max(max_lon, lon)
                    min_lat = min(min_lat, lat)
                    max_lat = max(max_lat, lat)

    # CRS details
    crs_str = "CRS84 (WGS 84 - EPSG:4326)"
    if crs_info and isinstance(crs_info, dict):
        crs_name = crs_info.get("properties", {}).get("name", "")
        if crs_name:
            crs_str = crs_name

    # Geopandas reading validation if available
    gdf = None
    if has_geo_libs:
        try:
            gdf = gpd.read_file(filepath)
            if gdf.crs:
                crs_str = str(gdf.crs)
            total_bounds = gdf.total_bounds # minx, miny, maxx, maxy
            min_lon, min_lat, max_lon, max_lat = total_bounds[0], total_bounds[1], total_bounds[2], total_bounds[3]
            invalid_geoms = sum(~gdf.is_valid)
            empty_geoms = sum(gdf.is_empty)
            geometry_types = set(gdf.geom_type.unique())
        except Exception as e:
            pass

    bbox_str = f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}] (Lon: {min_lon:.4f} to {max_lon:.4f}, Lat: {min_lat:.4f} to {max_lat:.4f})"
    
    # Regional coverage check
    # The bounding box covers the Indian West Coast / Gujarat-Maharashtra Arabian Sea EEZ:
    # Lon: 68.00°E to 74.07°E, Lat: 15.00°N to 23.50°N
    covers_indian_eez = (min_lon <= 69.0 and max_lon >= 73.0 and min_lat <= 16.0 and max_lat >= 22.0)

    # Pass / Fail criteria
    is_valid_geojson = (geojson_type in ["FeatureCollection", "Feature"]) and (feature_count > 0)
    no_corruptions = (invalid_geoms == 0) and (empty_geoms == 0)
    passed = is_valid_geojson and no_corruptions and covers_indian_eez

    print(f"File: {filepath}")
    print(f"GeoJSON type: {geojson_type}")
    print(f"Feature count: {feature_count}")
    print(f"Geometry types: {', '.join(sorted(geometry_types))}")
    print(f"CRS: {crs_str}")
    print(f"Bounding box: {bbox_str}")
    print(f"Invalid geometries: {invalid_geoms}")
    print(f"Empty geometries: {empty_geoms}")
    print(f"Property fields: {', '.join(sorted(property_keys)) if property_keys else 'None'}")
    print()
    print("VALIDATION:")
    print("PASS" if passed else "FAIL")
    print()
    print("----------------------------------------")
    print("GEOGRAPHIC & REGIONAL ASSESSMENT:")
    print("----------------------------------------")
    print(f"- Coverage of Indian EEZ / West Coast: {'YES' if covers_indian_eez else 'NO'} (BBox span Lon: {min_lon:.2f} to {max_lon:.2f}, Lat: {min_lat:.2f} to {max_lat:.2f})")
    
    if features:
        sample_props = features[0].get("properties", {})
        print(f"- Feature Identification: {sample_props.get('geoname', 'N/A')} ({sample_props.get('pol_type', 'N/A')}, Territory: {sample_props.get('territory1', 'N/A')})")
        print(f"- Reported Area: {sample_props.get('area_km2', 'N/A')} km2")

    print("\n----------------------------------------")
    print("INTENDED USE & BOUNDARY LIMITATIONS:")
    print("----------------------------------------")
    print("What this geometry CAN be used for:")
    print("  1. General spatial geofencing to check if a vessel position is inside or outside the Indian Exclusive Economic Zone (EEZ).")
    print("  2. Distance-to-EEZ-boundary calculations for vessels operating along the Indian coastline.")
    print("  3. Regional zone filtering and spatial indexing for maritime AIS / GPS track datasets.")
    print()
    print("What this geometry CANNOT be used for:")
    print("  1. India-Pakistan International Maritime Boundary Line (IMBL) enforcement / alerting:")
    print("     - The file contains macro-level 200NM Exclusive Economic Zone polygons from standard global databases (e.g. Marineregions EEZ v11).")
    print("     - It does NOT explicitly establish, label, or delineate the bilateral India-Pakistan IMBL coordinates or treaty-specific maritime boundary lines.")
    print("  2. Marine Protected Area (MPA) / Sanctuary zone violation checks:")
    print("     - It does not contain Marine National Park, Marine Sanctuary, or no-fishing marine reserve polygons.")
    print("  3. High-precision coastal navigation or territorial sea boundary (12 NM baseline) navigation.")

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/boundaries/india_eez.geojson"
    audit_eez_geojson(filepath)
