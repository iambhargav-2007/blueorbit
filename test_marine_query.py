import sys
import json
import os

# Add backend to path to allow importing the service
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.marine_spatial_engine import MarineSpatialEngine

def main():
    parquet_path = "data/processed/processed_marine_db.parquet"
    
    print("Initializing Marine Spatial Engine... (This may take a few seconds to build the spatial index)")
    try:
        engine = MarineSpatialEngine(parquet_path=parquet_path, max_distance_km=25.0)
        print("Engine initialized successfully!\n")
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    # Helper function to print results clearly
    def run_query(desc, lat, lon, date_str):
        print(f"--- {desc} ---")
        print(f"Request: Lat={lat}, Lon={lon}, Date={date_str}")
        result = engine.query(lat=lat, lon=lon, date_str=date_str)
        print("Result:")
        print(json.dumps(result, indent=2))
        print("\n")

    # 1. One coordinate/date that should successfully return data
    # We pick coordinates within the dataset bounds (Lat: 15-23, Lon: 68-73.92)
    # Using 2025-10-15 as a safe date in the middle of October
    run_query(
        "TEST 1: Successful Data Retrieval (Valid Coordinate)",
        lat=19.5, lon=70.5, date_str="2025-10-15"
    )

    # 2. One different coordinate/date (another success)
    run_query(
        "TEST 2: Successful Data Retrieval (Different Coordinate)",
        lat=16.5, lon=72.0, date_str="2025-10-20"
    )

    # 3. One invalid coordinate (Out of geographic bounds or entirely outside the dataset bounding box)
    # The max distance is 25km. So setting lat=0, lon=0 will definitely exceed the max distance
    run_query(
        "TEST 3: Invalid Coordinate (Outside Max Distance Threshold)",
        lat=0.0, lon=0.0, date_str="2025-10-15"
    )
    
    # 3b. Formally invalid coordinate (>90 lat)
    run_query(
        "TEST 3b: Invalid Coordinate (Invalid Latitude format)",
        lat=95.0, lon=70.0, date_str="2025-10-15"
    )

    # 4. One date outside the available historical range
    run_query(
        "TEST 4: Date Outside Historical Range",
        lat=19.5, lon=70.5, date_str="2024-10-15" # dataset is for 2025-10
    )
    
if __name__ == "__main__":
    main()
