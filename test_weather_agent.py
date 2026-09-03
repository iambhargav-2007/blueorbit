"""
test_weather_agent.py

Automated tests for the Weather/Safety AI Agent (Step 10).

LLM calls are MOCKED so no real Groq API key is required to run this suite.

All expected numerical values are sourced from the deterministic WeatherSafetyEngine
outputs observed by running the existing test_weather_safety.py:

  lat=15.0, lon=68.0, date=2025-10-01:
    wind_speed_knots=21.22, wave_height_meters=2.42
    wind_safety_score=25.2, wave_safety_score=29.0, overall_safety_score=25.2
    risk_level="Very High Risk"

  lat=19.5, lon=70.5, date=2025-10-15:
    wind_speed_knots=11.23, wave_height_meters=0.88
    wind_safety_score=91.8, wave_safety_score=100.0, overall_safety_score=91.8
    risk_level="Low Risk"

Run:
    python -m pytest test_weather_agent.py -v
    # or directly:
    python test_weather_agent.py
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

# Make sure backend is importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.tools.weather_tool import WeatherSafetyTool
from app.agents.weather_agent import WeatherSafetyAgent
from app.agents.schemas import WeatherSafetyAgentResponse
from app.providers.cache_weather_provider import CacheWeatherProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_mock_llm(
    safety_narrative: str = "Mocked safety narrative.",
    safety_advice: str = "Mocked safety advice.",
):
    """Creates a mock Groq client that returns a pre-set JSON response."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "safety_narrative": safety_narrative,
        "safety_advice": safety_advice,
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_llm = MagicMock()
    mock_llm.chat.completions.create.return_value = mock_completion
    return mock_llm


def _make_agent(mock_llm=None) -> WeatherSafetyAgent:
    """Creates an agent with mocked LLM, using cache provider (live_mode=False)."""
    if mock_llm is None:
        mock_llm = _make_mock_llm()
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        agent = WeatherSafetyAgent(live_mode=False, llm_client=mock_llm)
    return agent


# ---------------------------------------------------------------------------
# TEST 1: Valid location/date — agent calls tool and returns engine result
# ---------------------------------------------------------------------------
def test_1_valid_location_calls_tool_and_returns_result():
    """
    lat=19.5, lon=70.5, date=2025-10-15 — deterministic engine outputs:
      wind_safety_score=91.8, wave_safety_score=100.0, overall_safety_score=91.8
      risk_level="Low Risk", data_quality="Complete", confidence="High"

    Verifies the agent successfully calls the weather safety tool and returns
    the engine's structured result.
    """
    print("\n--- TEST 1: Valid Location/Date (lat=19.5, lon=70.5, 2025-10-15) ---")

    agent = _make_agent()
    response: WeatherSafetyAgentResponse = agent.run(
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
        query_text="Is it safe to fish at 19.5, 70.5 on 2025-10-15?",
    )

    print(f"  success: {response.success}")
    print(f"  risk_level: {response.risk_level}")
    print(f"  overall_safety_score: {response.weather_conditions.overall_safety_score}")
    print(f"  confidence: {response.confidence}")
    print(f"  safety_narrative: {response.safety_narrative}")
    print(f"  safety_advice: {response.safety_advice}")

    assert response.success is True, f"Expected success=True, got error: {response.error}"
    assert response.risk_level == "Low Risk", f"Expected 'Low Risk', got '{response.risk_level}'"
    assert response.confidence == "High"
    assert response.data_quality == "Complete"
    assert response.weather_conditions is not None
    assert response.weather_conditions.overall_safety_score is not None
    assert response.safety_narrative  # some narrative returned
    assert response.safety_advice     # some advice returned
    assert response.disclaimer
    print("  TEST 1 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 2: Wind/wave safety information preserved from the engine
# ---------------------------------------------------------------------------
def test_2_wind_wave_scores_preserved_from_engine():
    """
    Verifies that wind_safety_score, wave_safety_score, and overall_safety_score
    in the response match the deterministic engine values exactly.

    lat=15.0, lon=68.0, date=2025-10-01 — deterministic engine outputs:
      wind_speed_knots≈21.22, wave_height_meters≈2.42
      wind_safety_score=25.2, wave_safety_score=29.0, overall_safety_score=25.2
    """
    print("\n--- TEST 2: Wind/Wave Scores Preserved from Engine (lat=15.0, lon=68.0, 2025-10-01) ---")

    agent = _make_agent()
    response = agent.run(
        latitude=15.0,
        longitude=68.0,
        date_str="2025-10-01",
        query_text="What are the wave conditions at 15N 68E today?",
    )

    print(f"  success: {response.success}")
    print(f"  wind_speed_knots: {response.weather_conditions.wind_speed_knots}")
    print(f"  wave_height_meters: {response.weather_conditions.wave_height_meters}")
    print(f"  wind_safety_score: {response.weather_conditions.wind_safety_score}")
    print(f"  wave_safety_score: {response.weather_conditions.wave_safety_score}")
    print(f"  overall_safety_score: {response.weather_conditions.overall_safety_score}")

    assert response.success is True, f"Expected success=True, got error: {response.error}"
    assert response.weather_conditions is not None

    wc = response.weather_conditions
    assert wc.wind_speed_knots is not None
    assert wc.wave_height_meters is not None
    # Values must match deterministic engine output (within float rounding tolerance)
    assert abs(wc.wind_safety_score - 25.2) < 0.5, (
        f"Expected wind_safety_score≈25.2, got {wc.wind_safety_score}"
    )
    assert abs(wc.wave_safety_score - 29.0) < 0.5, (
        f"Expected wave_safety_score≈29.0, got {wc.wave_safety_score}"
    )
    assert abs(wc.overall_safety_score - 25.2) < 0.5, (
        f"Expected overall_safety_score≈25.2, got {wc.overall_safety_score}"
    )
    print("  TEST 2 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 3: Overall safety/risk classification preserved exactly from the engine
# ---------------------------------------------------------------------------
def test_3_risk_classification_preserved_exactly():
    """
    Verifies that risk_level in the response is the exact string from the engine,
    not an LLM interpretation. Two locations are checked to cover both ends of the
    risk spectrum.
    """
    print("\n--- TEST 3: Risk Classification Preserved Exactly ---")

    # Location A: Very High Risk (lat=15.0, lon=68.0, 2025-10-01)
    agent = _make_agent()
    response_a = agent.run(latitude=15.0, longitude=68.0, date_str="2025-10-01")
    print(f"  Location A risk_level: {response_a.risk_level}")
    assert response_a.success is True
    assert response_a.risk_level == "Very High Risk", (
        f"Expected 'Very High Risk', got '{response_a.risk_level}'"
    )

    # Location B: Low Risk (lat=19.5, lon=70.5, 2025-10-15)
    response_b = agent.run(latitude=19.5, longitude=70.5, date_str="2025-10-15")
    print(f"  Location B risk_level: {response_b.risk_level}")
    assert response_b.success is True
    assert response_b.risk_level == "Low Risk", (
        f"Expected 'Low Risk', got '{response_b.risk_level}'"
    )
    print("  TEST 3 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 4: Missing weather data — no hallucination, returns insufficient-data response
# ---------------------------------------------------------------------------
def test_4_missing_weather_data_no_hallucination():
    """
    Simulate a location where the weather provider returns null wind and wave values.
    The agent must report 'Insufficient Data' without fabricating safety scores.
    """
    print("\n--- TEST 4: Missing Weather Data (No Hallucination) ---")

    # Mock weather data with both wind and wave missing
    missing_weather_data = {
        "success": True,
        "latitude": 15.0,
        "longitude": 68.0,
        "date": "2025-10-01",
        "matched_latitude": 15.0,
        "matched_longitude": 68.0,
        "distance_km": 0.0,
        "wind_speed_knots": None,
        "wind_direction": None,
        "surface_pressure_hpa": 1010.0,
        "wave_height_meters": None,
        "wave_direction": None,
        "wave_period_seconds": None,
    }

    agent = _make_agent()
    # Patch the provider's get_weather method to return missing data
    agent._tool._provider.get_weather = MagicMock(return_value=missing_weather_data)

    response = agent.run(latitude=15.0, longitude=68.0, date_str="2025-10-01")

    print(f"  success: {response.success}")
    print(f"  risk_level: {response.risk_level}")
    print(f"  data_quality: {response.data_quality}")
    print(f"  wind_safety_score: {response.weather_conditions.wind_safety_score if response.weather_conditions else None}")
    print(f"  overall_safety_score: {response.weather_conditions.overall_safety_score if response.weather_conditions else None}")

    # Agent must return a structured (success=True) response since provider succeeded,
    # but must NOT fabricate scores — the engine returns Insufficient Data for missing values
    assert response.success is True
    assert response.risk_level == "Insufficient Data", (
        f"Expected 'Insufficient Data', got '{response.risk_level}'"
    )
    assert response.data_quality == "Insufficient Data"
    # Scores must be None — not invented
    if response.weather_conditions:
        assert response.weather_conditions.wind_safety_score is None, (
            "Should not produce a wind score with missing data"
        )
        assert response.weather_conditions.wave_safety_score is None, (
            "Should not produce a wave score with missing data"
        )
        assert response.weather_conditions.overall_safety_score is None, (
            "Should not produce an overall score with missing data"
        )
    print("  TEST 4 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 5: Invalid coordinates — agent rejects input appropriately
# ---------------------------------------------------------------------------
def test_5a_invalid_latitude():
    """lat=95.0 is out of range. Agent must return success=False without fabricating."""
    print("\n--- TEST 5a: Invalid Latitude (lat=95.0) ---")

    agent = _make_agent()
    response = agent.run(latitude=95.0, longitude=70.5, date_str="2025-10-15")

    print(f"  success: {response.success}")
    print(f"  error: {response.error}")

    assert response.success is False, "Expected failure for invalid latitude"
    assert response.error is not None and len(response.error) > 0
    assert response.risk_level is None, "Should not fabricate a risk level"
    assert response.weather_conditions is None, "Should not fabricate weather conditions"
    print("  TEST 5a PASSED [OK]")


def test_5b_invalid_longitude():
    """lon=200.0 is out of range."""
    print("\n--- TEST 5b: Invalid Longitude (lon=200.0) ---")

    agent = _make_agent()
    response = agent.run(latitude=19.5, longitude=200.0, date_str="2025-10-15")

    assert response.success is False
    assert response.risk_level is None
    assert response.weather_conditions is None
    print("  TEST 5b PASSED [OK]")


def test_5c_date_outside_range():
    """Date 2024-10-01 is outside the cached historical range."""
    print("\n--- TEST 5c: Date Outside Historical Range (2024-10-01) ---")

    agent = _make_agent()
    response = agent.run(latitude=15.0, longitude=68.0, date_str="2024-10-01")

    print(f"  success: {response.success}")
    print(f"  error: {response.error}")

    assert response.success is False
    assert response.error is not None
    assert response.risk_level is None
    print("  TEST 5c PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 6: LLM cannot override the deterministic safety result
# ---------------------------------------------------------------------------
def test_6_llm_cannot_override_deterministic_result():
    """
    The LLM is given a contradicting instruction (claiming "Low Risk") but the
    structured risk_level field must still come verbatim from the engine.

    For lat=15.0, lon=68.0, 2025-10-01 the engine produces:
      overall_safety_score=25.2, risk_level="Very High Risk"

    Even if the LLM narrative says "Low Risk", the structured fields must not change.
    """
    print("\n--- TEST 6: LLM Cannot Override Deterministic Safety Result ---")

    # Inject a mock LLM that tries to say the opposite of the engine result
    contradicting_mock_llm = _make_mock_llm(
        safety_narrative=(
            "Conditions are perfectly safe. This is Low Risk. "
            "Overall safety score should be 100."
        ),
        safety_advice="You can go out to sea without any concern.",
    )

    agent = _make_agent(mock_llm=contradicting_mock_llm)
    response = agent.run(latitude=15.0, longitude=68.0, date_str="2025-10-01")

    print(f"  risk_level (engine): {response.risk_level}")
    print(f"  overall_safety_score (engine): {response.weather_conditions.overall_safety_score}")
    print(f"  safety_narrative (LLM — allowed to contradict in text): {response.safety_narrative}")

    assert response.success is True

    # CRITICAL: The structured risk_level field must be the engine's result, not the LLM's claim
    assert response.risk_level == "Very High Risk", (
        f"LLM overrode the engine's risk_level! "
        f"Expected 'Very High Risk', got '{response.risk_level}'"
    )

    # CRITICAL: The structured overall_safety_score must be the engine's result
    assert response.weather_conditions is not None
    assert abs(response.weather_conditions.overall_safety_score - 25.2) < 0.5, (
        f"LLM overrode the engine's overall_safety_score! "
        f"Expected ≈25.2, got {response.weather_conditions.overall_safety_score}"
    )

    # The LLM text fields are allowed to say whatever — only the structured fields are guarded
    print("  TEST 6 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 7: Cache provider is used in cache mode
# ---------------------------------------------------------------------------
def test_7_cache_mode_uses_cache_weather_provider():
    """
    Verify that the agent's WeatherSafetyTool uses CacheWeatherProvider when
    live_mode=False (the default for testing/cache mode).
    """
    print("\n--- TEST 7: live_mode=False Uses Cache Weather Provider ---")

    agent = _make_agent()
    provider_type = type(agent._tool._provider).__name__

    print(f"  Provider type: {provider_type}")
    assert provider_type == "CacheWeatherProvider", (
        f"Expected CacheWeatherProvider, got {provider_type}"
    )
    print("  TEST 7 PASSED [OK]")


# ---------------------------------------------------------------------------
# Manual runner (no pytest required)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        test_1_valid_location_calls_tool_and_returns_result,
        test_2_wind_wave_scores_preserved_from_engine,
        test_3_risk_classification_preserved_exactly,
        test_4_missing_weather_data_no_hallucination,
        test_5a_invalid_latitude,
        test_5b_invalid_longitude,
        test_5c_date_outside_range,
        test_6_llm_cannot_override_deterministic_result,
        test_7_cache_mode_uses_cache_weather_provider,
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERR] ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n==================================================")
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    if failed == 0:
        print("ALL STEP 10 WEATHER AGENT TESTS PASSED [OK]")
    print(f"==================================================")
