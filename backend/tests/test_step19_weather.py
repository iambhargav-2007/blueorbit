"""
test_step19_weather.py

Comprehensive test suite for Step 19 — Live Weather / Safety Intelligence.
Covers:
1. Valid current weather request
2. Current provider success (InterimLiveWeatherProvider)
3. Current provider unavailable returns explicit INSUFFICIENT_DATA
4. Zero silent fallback from current/live -> historical October 2025 cache
5. Historical date (2025-10-15) uses CacheWeatherProvider
6. Invalid coordinates rejected without modification
7. Nearest observation lookup
8. Observation too far (>100km threshold) returns Insufficient Data
9. Missing wind/wave data handled safely by WeatherSafetyEngine
10. Deterministic safety score preserved (minimum bottleneck logic)
11. LLM contradiction cannot override deterministic safety
12. Existing location context is reused without asking for coordinates
13. Goa location request resolves and evaluates
14. Mumbai location request resolves and evaluates
15. Future forecast request does not fabricate forecast (returns UNSUPPORTED_FUTURE)
16. Data source and provenance preserved
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.providers.base_weather_provider import BaseWeatherProvider
from app.providers.cache_weather_provider import CacheWeatherProvider
from app.providers.live_weather_provider import InterimLiveWeatherProvider
from app.providers.smart_weather_router import SmartWeatherRouter
from app.services.temporal_resolver import TemporalContextResolver, TemporalMode, TemporalResolution
from app.services.weather_safety_engine import WeatherSafetyEngine
from app.agents.weather_agent import WeatherSafetyAgent
from app.conversation.conversation_coordinator import ConversationCoordinator
from app.location.schemas import LocationContext
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 & 2: Current Provider Success & Normalized Schema
# ---------------------------------------------------------------------------

def test_1_and_2_current_provider_success():
    """InterimLiveWeatherProvider returns normalized observation schema."""
    provider = InterimLiveWeatherProvider()
    mock_marine = {
        "latitude": 15.4,
        "longitude": 73.8,
        "current": {"wave_height": 1.5, "wave_direction": 260, "wave_period": 8.0}
    }
    mock_forecast = {
        "current": {"wind_speed_10m": 12.5, "wind_direction_10m": 250, "surface_pressure": 1012.0}
    }

    with patch.object(provider, "_fetch_url_json", side_effect=[mock_marine, mock_forecast]):
        res = provider.get_weather(lat=15.41, lon=73.80, date_str="2026-09-03")

    assert res["success"] is True
    assert res["wind_speed_knots"] == 12.5
    assert res["wave_height_meters"] == 1.5
    assert res["surface_pressure_hpa"] == 1012.0
    assert res["wave_period_seconds"] == 8.0
    assert "Open-Meteo" in res["source"]
    assert res["data_status"] == "observed"
    assert res["observation_type"] == "current_observation"


# ---------------------------------------------------------------------------
# Test 3: Current Provider Unavailable
# ---------------------------------------------------------------------------

def test_3_current_provider_unavailable():
    """When the live API fails or network times out, return explicit INSUFFICIENT_DATA."""
    provider = InterimLiveWeatherProvider()

    with patch.object(provider, "_fetch_url_json", side_effect=Exception("Connection timed out")):
        res = provider.get_weather(lat=15.41, lon=73.80, date_str="2026-09-03")

    assert res["success"] is False
    assert res["code"] == "INSUFFICIENT_DATA"
    assert res["observation_type"] == "unavailable"
    assert "unavailable or timed out" in res["error"]


# ---------------------------------------------------------------------------
# Test 4: No Fallback from Current -> Historical Cache
# ---------------------------------------------------------------------------

def test_4_no_fallback_from_current_to_historical_cache():
    """Live provider failure must NEVER silently fall back to October 2025 cache."""
    mock_live = MagicMock()
    mock_live.get_weather.return_value = {
        "success": False,
        "error": "Live network failure",
        "code": "INSUFFICIENT_DATA"
    }

    mock_hist = MagicMock()
    mock_hist.get_weather.return_value = {
        "success": True,
        "wind_speed_knots": 10.0,
        "wave_height_meters": 1.0,
        "source": "Historical Weather Cache (October 2025)"
    }

    router = SmartWeatherRouter(live_provider=mock_live, historical_provider=mock_hist)
    res = router.get_weather(lat=15.41, lon=73.80, date_str="2026-09-03", temporal_mode=TemporalMode.LIVE)

    assert res["success"] is False
    assert mock_live.get_weather.called
    assert not mock_hist.get_weather.called, "Historical provider must NOT be called on live failure!"


# ---------------------------------------------------------------------------
# Test 5: Historical Date Uses Cache Provider
# ---------------------------------------------------------------------------

def test_5_historical_date_uses_cache_provider():
    """Historical date queries route strictly to CacheWeatherProvider."""
    mock_live = MagicMock()
    mock_hist = MagicMock()
    mock_hist.get_weather.return_value = {
        "success": True,
        "wind_speed_knots": 14.2,
        "wave_height_meters": 1.8,
        "source": "Historical Weather Cache (October 2025)",
        "observation_type": "historical_observation",
        "data_status": "historical",
    }

    router = SmartWeatherRouter(live_provider=mock_live, historical_provider=mock_hist)
    res = router.get_weather(lat=19.50, lon=70.50, date_str="2025-10-15", temporal_mode=TemporalMode.HISTORICAL)

    assert res["success"] is True
    assert mock_hist.get_weather.called
    assert not mock_live.get_weather.called
    assert res["observation_type"] == "historical_observation"
    assert "Historical" in res["source"]


# ---------------------------------------------------------------------------
# Test 6: Invalid Coordinates Rejected
# ---------------------------------------------------------------------------

def test_6_invalid_coordinates_rejected():
    """Coordinates out of bounds (-90..90, -180..180) are rejected."""
    provider = InterimLiveWeatherProvider()

    res_lat = provider.get_weather(lat=95.0, lon=70.50, date_str="2026-09-03")
    assert res_lat["success"] is False
    assert res_lat["code"] == "INVALID_COORDINATES"

    res_lon = provider.get_weather(lat=19.5, lon=195.0, date_str="2026-09-03")
    assert res_lon["success"] is False
    assert res_lon["code"] == "INVALID_COORDINATES"


# ---------------------------------------------------------------------------
# Test 7 & 8: Nearest Observation Lookup & Distance Threshold
# ---------------------------------------------------------------------------

def test_7_and_8_nearest_observation_lookup_and_distance_threshold():
    """Cache provider matches nearest grid point and rejects points > max_distance_km."""
    cache = CacheWeatherProvider(max_distance_km=50.0)

    # Valid point in Arabian Sea
    res_near = cache.get_weather(lat=19.5, lon=70.5, date_str="2025-10-15")
    assert res_near["success"] is True
    assert res_near["distance_km"] <= 50.0

    # Point far out in deep Indian Ocean outside 50km threshold
    res_far = cache.get_weather(lat=-10.0, lon=60.0, date_str="2025-10-15")
    assert res_far["success"] is False
    assert "distance threshold" in res_far["error"]


# ---------------------------------------------------------------------------
# Test 9: Missing Wind/Wave Data Handled Safely
# ---------------------------------------------------------------------------

def test_9_missing_wind_or_wave_data_handled_safely():
    """WeatherSafetyEngine returns Insufficient Data when required parameters are missing."""
    engine = WeatherSafetyEngine()

    # Incomplete weather data (missing waves)
    incomplete_data = {
        "success": True,
        "wind_speed_knots": 15.0,
        "wave_height_meters": None,
        "date": "2026-09-03",
        "latitude": 19.5,
        "longitude": 70.5,
    }
    res = engine.assess(incomplete_data)
    assert res["success"] is True
    assert res["risk_level"] == "Insufficient Data"
    assert res["overall_safety_score"] is None
    assert "Cannot evaluate complete marine safety" in res["explanation"]


# ---------------------------------------------------------------------------
# Test 10: Deterministic Safety Score Preserved
# ---------------------------------------------------------------------------

def test_10_deterministic_safety_score_preserved():
    """Overall safety score is strictly the minimum (bottleneck) of wind and wave scores."""
    engine = WeatherSafetyEngine()

    data = {
        "success": True,
        "wind_speed_knots": 10.0,  # Favorable (100.0)
        "wave_height_meters": 2.2,  # Hazardous (score < 50)
        "date": "2026-09-03",
        "latitude": 19.5,
        "longitude": 70.5,
    }
    res = engine.assess(data)
    assert res["success"] is True
    assert res["wind_safety_score"] == 100.0
    assert res["wave_safety_score"] < 50.0
    assert res["overall_safety_score"] == res["wave_safety_score"], "Bottleneck rule must enforce min(wind, wave)"


# ---------------------------------------------------------------------------
# Test 11: LLM Contradiction Cannot Override Safety
# ---------------------------------------------------------------------------

def test_11_llm_contradiction_cannot_override_safety():
    """Even if an LLM outputs 'Conditions are totally safe', deterministic engine scores prevail."""
    # Mock LLM returning contradictory narrative
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"safety_narrative": "It is completely safe and calm!", "safety_advice": "Go fish freely"}'))
    ]
    mock_llm.chat.completions.create.return_value = mock_response

    # Mock provider returning hazardous conditions
    mock_provider = MagicMock()
    mock_provider.get_weather.return_value = {
        "success": True,
        "wind_speed_knots": 35.0,  # Extreme gale
        "wave_height_meters": 4.5,  # High waves
        "date": "2026-09-03",
        "latitude": 19.5,
        "longitude": 70.5,
    }

    agent = WeatherSafetyAgent(llm_client=mock_llm, provider=mock_provider)
    resp = agent.run(latitude=19.5, longitude=70.5, date_str="2026-09-03")

    assert resp.success is True
    assert resp.risk_level in ["High Risk", "Very High Risk"]
    assert resp.weather_conditions.overall_safety_score == 0.0
    assert resp.weather_conditions.wind_speed_knots == 35.0


# ---------------------------------------------------------------------------
# Test 12: Existing Location Context Reused
# ---------------------------------------------------------------------------

def test_12_existing_location_context_reused():
    """Follow-up weather question reuses location from LocationContext without prompting."""
    coord = ConversationCoordinator()
    session_id = "test-weather-loc-reuse"

    # Set location via GPS
    loc = LocationContext(
        latitude=18.94,
        longitude=72.84,
        display_name="Mumbai Coast, Maharashtra",
        source="gps"
    )

    # Mock tool result so test runs deterministically without network
    mock_weather = {
        "success": True,
        "wind_speed_knots": 8.0,
        "wave_height_meters": 0.8,
        "date": "2025-10-15",
        "latitude": 18.94,
        "longitude": 72.84,
        "wind_safety_score": 100.0,
        "wave_safety_score": 100.0,
        "overall_safety_score": 100.0,
        "risk_level": "Low Risk",
        "confidence": "High",
        "data_quality": "Complete",
    }
    with patch.object(coord._coordinator._weather_agent._tool, "get_weather_safety", return_value=mock_weather):
        resp = coord.process_turn(
            session_id=session_id,
            query_text="Is the weather safe here?",
            location_context=loc,
            date_str="2025-10-15",
        )

    assert resp.success is True
    assert resp.weather is not None
    assert abs(resp.request["latitude"] - 18.94) < 0.1
    assert abs(resp.request["longitude"] - 72.84) < 0.1


# ---------------------------------------------------------------------------
# Test 13 & 14: Goa and Mumbai Location Requests
# ---------------------------------------------------------------------------

def test_13_and_14_goa_and_mumbai_weather_requests():
    """Natural language queries specifying Goa or Mumbai resolve coordinates for weather assessment."""
    coord = ConversationCoordinator()

    # Mock weather tool
    mock_weather_res = {
        "success": True,
        "wind_speed_knots": 9.0,
        "wave_height_meters": 0.9,
        "date": "2025-10-15",
        "latitude": 15.41,
        "longitude": 73.80,
        "wind_safety_score": 100.0,
        "wave_safety_score": 100.0,
        "overall_safety_score": 100.0,
        "risk_level": "Low Risk",
        "confidence": "High",
        "data_quality": "Complete",
    }

    with patch.object(coord._coordinator._weather_agent._tool, "get_weather_safety", return_value=mock_weather_res):
        resp_goa = coord.process_turn(
            session_id="test-goa-weather",
            query_text="How is the weather near Goa?",
            date_str="2025-10-15",
        )
    assert resp_goa.success is True
    assert abs(resp_goa.request["latitude"] - 15.41) < 0.1

    mock_weather_res["latitude"] = 18.94
    mock_weather_res["longitude"] = 72.84
    with patch.object(coord._coordinator._weather_agent._tool, "get_weather_safety", return_value=mock_weather_res):
        resp_mumbai = coord.process_turn(
            session_id="test-mumbai-weather",
            query_text="How are weather conditions near Mumbai?",
            date_str="2025-10-15",
        )
    assert resp_mumbai.success is True
    assert abs(resp_mumbai.request["latitude"] - 18.94) < 0.1


# ---------------------------------------------------------------------------
# Test 15: Future Forecast Request Does Not Fabricate Forecast
# ---------------------------------------------------------------------------

def test_15_future_forecast_request_does_not_fabricate_forecast():
    """Queries for future forecast (e.g. tomorrow) return UNSUPPORTED_FUTURE with no fake forecast."""
    coord = ConversationCoordinator()

    resp = coord.process_turn(
        session_id="test-future-weather",
        query_text="How is the weather tomorrow at 19.5, 70.5?",
        latitude=19.5,
        longitude=70.5,
        date_str="tomorrow",
    )

    # Weather Agent should return success=False with unsupported future explanation
    assert resp.weather is not None
    assert resp.weather.success is False
    assert resp.weather.temporal_mode == "UNSUPPORTED_FUTURE"
    assert "forecasts are currently unsupported" in resp.weather.error


# ---------------------------------------------------------------------------
# Test 16: Source and Provenance Preserved
# ---------------------------------------------------------------------------

def test_16_source_and_provenance_preserved():
    """Observation provenance (live vs historical) is preserved across agent responses."""
    mock_tool = MagicMock()
    mock_tool.get_weather_safety.return_value = {
        "success": True,
        "wind_speed_knots": 11.0,
        "wave_height_meters": 1.2,
        "wind_safety_score": 90.0,
        "wave_safety_score": 80.0,
        "overall_safety_score": 80.0,
        "risk_level": "Low Risk",
        "confidence": "High",
        "data_quality": "Complete",
        "source": "Interim Live Weather Provider (Open-Meteo Marine API)",
        "data_status": "observed",
        "observation_type": "current_observation",
        "temporal_mode": "LIVE",
    }

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"safety_narrative": "Favorable conditions", "safety_advice": "Normal operations"}'))
    ]
    mock_llm.chat.completions.create.return_value = mock_response

    agent = WeatherSafetyAgent(llm_client=mock_llm, tool=mock_tool)
    res = agent.run(latitude=19.5, longitude=70.5, date_str="2026-09-03")

    assert res.success is True
    assert "Open-Meteo" in res.source
    assert res.data_status == "observed"
    assert res.observation_type == "current_observation"
    assert res.limiting_factor == "Significant Wave Height"
