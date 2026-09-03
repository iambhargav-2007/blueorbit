import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.providers.live_marine_provider import LiveMarineProvider
from app.services.habitat_suitability_engine import HabitatSuitabilityEngine
from app.config import COPERNICUS_THETAO_DATASET, COPERNICUS_CHL_DATASET

def run_smoke_test():
    print("=== Configuration ===")
    print(f"Temperature Dataset ID: {COPERNICUS_THETAO_DATASET}")
    print(f"Chlorophyll Dataset ID: {COPERNICUS_CHL_DATASET}")
    
    lat = 19.5
    lon = 70.5
    date_str = "2026-09-01"
    print(f"Requested coordinates/date: Lat: {lat}, Lon: {lon}, Date: {date_str}")
    
    # 1. Test Provider
    provider = LiveMarineProvider()
    print("\n=== Fetching Live Data ===")
    result = provider.get_marine_data(lat, lon, date_str)
    
    if result["success"]:
        val_theta = result["temperature"]
        val_chl = result["chlorophyll"]
        print(f"Actual returned temperature: {val_theta}")
        print(f"Actual returned chlorophyll: {val_chl}")
        print(f"Match Validity: {result.get('data_validity')}")
        
        # 2. Test Engine
        print("\n=== Running Habitat Engine ===")
        # The habitat engine requires the actual values
        # Since it uses rule-based constraints on temperature and chlorophyll
        engine = HabitatSuitabilityEngine()
        
        # The habitat engine requires the result dict from the provider
        try:
            assessment = engine.assess(result)
            print(f"Habitat Result: Score: {assessment.get('overall_score')}, Classification: {assessment.get('category')}")
            print(f"Explanation: {assessment.get('explanation')}")
        except Exception as e:
            print(f"Could not run habitat engine directly: {e}")
            
    else:
        print(f"Fetch Failed: {result['error']}")

if __name__ == "__main__":
    run_smoke_test()
