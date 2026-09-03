import sys
import json
import os

# Add backend to path to allow importing app modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.config import LIVE_MODE, MARINE_PARQUET_PATH, WEATHER_PARQUET_PATH, EEZ_GEOJSON_PATH
from app.providers import (
    get_marine_provider,
    get_weather_provider,
    CacheMarineProvider,
    LiveMarineProvider,
    CacheWeatherProvider,
    LiveWeatherProvider,
)
from app.services.habitat_suitability_engine import HabitatSuitabilityEngine
from app.services.weather_safety_engine import WeatherSafetyEngine
from app.services.geofencing_engine import GeofencingEngine

def run_tests():
    print("==================================================")
    print("BLUE ORBIT — STEP 8 PROVIDER & MODE SELECTION TESTS")
    print("==================================================")

    # ----------------------------------------------------
    # TEST 1: Cache mode initializes successfully
    # ----------------------------------------------------
    print("\n--- TEST 1: Cache Mode Initialization ---")
    marine_provider = get_marine_provider(live_mode=False)
    weather_provider = get_weather_provider(live_mode=False)
    print(f"Marine Provider Type: {type(marine_provider).__name__}")
    print(f"Weather Provider Type: {type(weather_provider).__name__}")
    assert isinstance(marine_provider, CacheMarineProvider), "Failed: Expected CacheMarineProvider"
    assert isinstance(weather_provider, CacheWeatherProvider), "Failed: Expected CacheWeatherProvider"
    print("TEST 1 PASSED: Cache mode initialized successfully.")

    # ----------------------------------------------------
    # TEST 2: Marine data retrieval via CacheMarineProvider
    # ----------------------------------------------------
    print("\n--- TEST 2: Marine Data Retrieval (lat=19.5, lon=70.5, date=2025-10-15) ---")
    marine_data = marine_provider.get_marine_data(lat=19.5, lon=70.5, date_str="2025-10-15")
    print("Marine Data Result:")
    print(json.dumps(marine_data, indent=2))
    assert marine_data.get("success") is True, "Failed to retrieve marine data"
    assert marine_data.get("temperature") is not None, "Expected valid temperature"
    assert marine_data.get("chlorophyll") is not None, "Expected valid chlorophyll"
    print("TEST 2 PASSED: Marine observation retrieved with valid temperature and chlorophyll.")

    # ----------------------------------------------------
    # TEST 3: Habitat engine integration on provider output
    # ----------------------------------------------------
    print("\n--- TEST 3: Habitat Suitability Engine on Provider Output ---")
    habitat_engine = HabitatSuitabilityEngine()
    habitat_result = habitat_engine.assess(marine_data)
    print("Habitat Result:")
    print(json.dumps(habitat_result, indent=2))
    assert habitat_result.get("success") is True, "Habitat assessment failed"
    assert habitat_result.get("overall_suitability_score") is not None, "Overall score missing"
    assert habitat_result.get("fishing_potential") in ("Low", "Moderate", "High"), "Invalid potential category"
    print("TEST 3 PASSED: Habitat Suitability Engine successfully processed provider data.")

    # ----------------------------------------------------
    # TEST 4: Weather cache provider retrieval
    # ----------------------------------------------------
    print("\n--- TEST 4: Weather Data Retrieval (lat=19.5, lon=70.5, date=2025-10-15) ---")
    weather_data = weather_provider.get_weather(lat=19.5, lon=70.5, date_str="2025-10-15")
    print("Weather Data Result:")
    print(json.dumps(weather_data, indent=2))
    assert weather_data.get("success") is True, "Failed to retrieve weather data"
    assert weather_data.get("wind_speed_knots") is not None, "Wind speed missing"
    assert weather_data.get("wave_height_meters") is not None, "Wave height missing"
    print("TEST 4 PASSED: Weather cache provider retrieved weather data successfully.")

    # ----------------------------------------------------
    # TEST 5: Weather Safety Engine integration
    # ----------------------------------------------------
    print("\n--- TEST 5: Weather Safety Engine on Provider Output ---")
    weather_engine = WeatherSafetyEngine()
    safety_result = weather_engine.assess(weather_data)
    print("Weather Safety Result:")
    print(json.dumps(safety_result, indent=2))
    assert safety_result.get("success") is True, "Weather safety assessment failed"
    assert safety_result.get("overall_safety_score") is not None, "Overall safety score missing"
    print("TEST 5 PASSED: Weather Safety Engine produced valid safety assessment.")

    # ----------------------------------------------------
    # TEST 6: Geofencing engine with india_eez.geojson
    # ----------------------------------------------------
    print("\n--- TEST 6: Geofencing Engine Spatial Check ---")
    geofence_engine = GeofencingEngine()
    geofence_result = geofence_engine.check_status(lat=19.0, lon=71.0)
    print("Geofence Result:")
    print(json.dumps(geofence_result, indent=2))
    assert geofence_result.get("success") is True, "Geofencing check failed"
    assert geofence_result.get("inside_indian_eez") is True, "Expected coordinate to be inside EEZ"
    assert geofence_result.get("geofence_status") == "SAFE", "Expected SAFE geofence status"
    print("TEST 6 PASSED: Geofencing engine operates as expected.")

    # ----------------------------------------------------
    # TEST 7: LIVE_MODE=False selects cache providers
    # ----------------------------------------------------
    print("\n--- TEST 7: LIVE_MODE=False Resolution ---")
    mp_false = get_marine_provider(live_mode=False)
    wp_false = get_weather_provider(live_mode=False)
    assert isinstance(mp_false, CacheMarineProvider), "Expected CacheMarineProvider when live_mode=False"
    assert isinstance(wp_false, CacheWeatherProvider), "Expected CacheWeatherProvider when live_mode=False"
    print("TEST 7 PASSED: LIVE_MODE=False properly instantiates Cache providers.")

    # ----------------------------------------------------
    # TEST 8: LIVE_MODE=True does NOT silently use cache (raises NotImplementedError)
    # ----------------------------------------------------
    print("\n--- TEST 8: LIVE_MODE=True Explicit NotImplementedError Verification ---")
    mp_live = get_marine_provider(live_mode=True)
    wp_live = get_weather_provider(live_mode=True)
    assert isinstance(mp_live, LiveMarineProvider), "Expected LiveMarineProvider when live_mode=True"
    assert isinstance(wp_live, LiveWeatherProvider), "Expected LiveWeatherProvider when live_mode=True"

    # Verify Marine Live Provider raises intentional error
    marine_error_raised = False
    try:
        mp_live.get_marine_data(lat=19.5, lon=70.5, date_str="2025-10-15")
    except NotImplementedError as e:
        marine_error_raised = True
        print(f"Captured expected Marine Live error: {e}")

    assert marine_error_raised, "LiveMarineProvider failed to raise NotImplementedError"

    # Verify Weather Live Provider raises intentional error
    weather_error_raised = False
    try:
        wp_live.get_weather(lat=19.5, lon=70.5, date_str="2025-10-15")
    except NotImplementedError as e:
        weather_error_raised = True
        print(f"Captured expected Weather Live error: {e}")

    assert weather_error_raised, "LiveWeatherProvider failed to raise NotImplementedError"
    print("TEST 8 PASSED: LIVE_MODE=True raises explicit NotImplementedError without silent fallback.")

    print("\n==================================================")
    print("ALL 8 STEP 8 PROVIDER TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
