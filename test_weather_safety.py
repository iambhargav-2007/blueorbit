import sys
import json
import os

# Add backend to path to allow importing the services
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.weather.cache_weather_provider import CacheWeatherProvider
from app.services.weather_safety_engine import WeatherSafetyEngine

def main():
    parquet_path = "data/processed/weather_regional_grid.parquet"
    config_path = "backend/app/config/weather_safety_config.json"
    
    print("Initializing Cache Weather Provider and Safety Engine...")
    try:
        provider = CacheWeatherProvider(parquet_path=parquet_path, max_distance_km=100.0)
        safety_engine = WeatherSafetyEngine(config_path=config_path)
        print("Engines initialized successfully!\n")
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    def run_query(desc, lat, lon, date_str):
        print(f"==================================================")
        print(f"--- {desc} ---")
        print(f"Requested: Lat={lat}, Lon={lon}, Date={date_str}")
        
        # 1. Get raw weather data
        weather_data = provider.get_weather(lat=lat, lon=lon, date_str=date_str)
        
        # 2. Assess safety
        safety_result = safety_engine.assess(weather_data)
        
        if safety_result.get("success"):
            print(f"Matched: Lat={safety_result.get('matched_latitude')}, Lon={safety_result.get('matched_longitude')}, distance_km={safety_result.get('distance_km')}")
            
            print("Weather:")
            print(f"  wind speed (knots): {safety_result.get('wind_speed_knots')}")
            print(f"  wind direction: {safety_result.get('wind_direction')}")
            print(f"  pressure (hpa): {safety_result.get('surface_pressure_hpa')}")
            print(f"  wave height (meters): {safety_result.get('wave_height_meters')}")
            print(f"  wave direction: {safety_result.get('wave_direction')}")
            print(f"  wave period (seconds): {safety_result.get('wave_period_seconds')}")
            
            print("Scores:")
            print(f"  wind safety score: {safety_result.get('wind_safety_score')}")
            print(f"  wave safety score: {safety_result.get('wave_safety_score')}")
            print(f"  overall safety score: {safety_result.get('overall_safety_score')}")
            
            print("Result:")
            print(f"  risk level: {safety_result.get('risk_level')}")
            print(f"  data quality: {safety_result.get('data_quality')}")
            print(f"  confidence: {safety_result.get('confidence')}")
            print(f"  explanation: {safety_result.get('explanation')}")
        else:
            print("Error Result:")
            print(json.dumps(safety_result, indent=2))
            
        print("\n")

    # TEST 1: Valid coordinate/date with complete weather data
    run_query(
        "TEST 1: Valid Location/Date",
        lat=15.0, lon=68.0, date_str="2025-10-01"
    )

    # TEST 2: Different valid coordinate/date
    run_query(
        "TEST 2: Different Valid Location/Date",
        lat=19.5, lon=70.5, date_str="2025-10-15"
    )

    # TEST 3: Invalid latitude
    run_query(
        "TEST 3: Invalid latitude",
        lat=95.0, lon=70.5, date_str="2025-10-15"
    )

    # TEST 4: Invalid longitude
    run_query(
        "TEST 4: Invalid longitude",
        lat=19.5, lon=200.0, date_str="2025-10-15"
    )

    # TEST 5: Date outside the available historical range
    run_query(
        "TEST 5: Date outside historical range",
        lat=15.0, lon=68.0, date_str="2024-10-01"
    )
    
    # TEST 6: Explicitly missing values test (mocking provider response to demonstrate missing data behavior)
    print(f"==================================================")
    print(f"--- TEST 6: Missing Weather Data ---")
    mock_weather_data = {
        "success": True,
        "latitude": 15.0, "longitude": 68.0, "date": "2025-10-01",
        "matched_latitude": 15.0, "matched_longitude": 68.0, "distance_km": 0.0,
        "wind_speed_knots": None,
        "wind_direction": None,
        "surface_pressure_hpa": 1010.0,
        "wave_height_meters": None,
        "wave_direction": None,
        "wave_period_seconds": None
    }
    safety_result_missing = safety_engine.assess(mock_weather_data)
    print("Result:")
    print(f"  risk level: {safety_result_missing.get('risk_level')}")
    print(f"  data quality: {safety_result_missing.get('data_quality')}")
    print(f"  explanation: {safety_result_missing.get('explanation')}")
    print("\n")

if __name__ == "__main__":
    main()
