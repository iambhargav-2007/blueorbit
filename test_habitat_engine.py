import sys
import json
import os

# Add backend to path to allow importing the service
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.marine_spatial_engine import MarineSpatialEngine
from app.services.habitat_suitability_engine import HabitatSuitabilityEngine

def main():
    parquet_path = "data/processed/processed_marine_db.parquet"
    config_path = "backend/app/config/suitability_config.json"
    
    print("Initializing Marine Spatial Engine... (This may take a few seconds to build the spatial index)")
    try:
        marine_engine = MarineSpatialEngine(parquet_path=parquet_path, max_distance_km=25.0)
        habitat_engine = HabitatSuitabilityEngine(config_path=config_path)
        print("Engines initialized successfully!\n")
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    def run_query(desc, lat, lon, date_str):
        print(f"==================================================")
        print(f"--- {desc} ---")
        print(f"Request: Lat={lat}, Lon={lon}, Date={date_str}")
        
        # 1. Get raw marine data
        marine_data = marine_engine.query(lat=lat, lon=lon, date_str=date_str)
        
        # 2. Assess habitat suitability
        suitability_result = habitat_engine.assess(marine_data)
        
        print("\nHabitat Suitability Result:")
        print(json.dumps(suitability_result, indent=2))
        print("\n")

    # TEST 1: Valid location/date with valid temperature and chlorophyll
    run_query(
        "TEST 1: Valid Location/Date",
        lat=19.5, lon=70.5, date_str="2025-10-15"
    )

    # TEST 2: A different valid location/date
    run_query(
        "TEST 2: Different Valid Location/Date",
        lat=16.5, lon=72.0, date_str="2025-10-20"
    )

    # TEST 3: Explicit test of missing environmental data
    # (Since finding an exact coordinate with missing data in the parquet depends on the coastal mask, 
    # we explicitly simulate a missing data return here to demonstrate the engine's behavior)
    print(f"==================================================")
    print(f"--- TEST 3: Missing Environmental Data (Masked) ---")
    mock_marine_data = {
        "success": True,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2025-10-15",
        "temperature": None,
        "chlorophyll": None,
    }
    suitability_result = habitat_engine.assess(mock_marine_data)
    print("\nHabitat Suitability Result:")
    print(json.dumps(suitability_result, indent=2))
    print("\n")

    # TEST 4: Invalid coordinates (outside max distance)
    run_query(
        "TEST 4: Invalid Coordinates",
        lat=0.0, lon=0.0, date_str="2025-10-15"
    )

if __name__ == "__main__":
    main()
