"""
test_fishing_agent.py

Automated tests for the Fishing/Habitat AI Agent (Step 9).

LLM calls are MOCKED so no real Groq API key is required to run this suite.
Use the integration test at the bottom (requires GROQ_API_KEY) for real LLM validation.

Run:
    python -m pytest test_fishing_agent.py -v
    # or from the project root:
    python test_fishing_agent.py
"""

import sys
import os
import json
import types
from unittest.mock import MagicMock, patch

# Make sure backend is importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.tools.habitat_tool import HabitatTool
from app.agents.fishing_agent import FishingHabitatAgent
from app.agents.schemas import FishingAgentResponse
from app.providers.cache_marine_provider import CacheMarineProvider
from app.providers.live_marine_provider import LiveMarineProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_mock_llm(scientific_explanation: str = "Mocked explanation.", fisherman_advice: str = "Mocked advice."):
    """Creates a mock Groq client that returns a pre-set JSON response."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "scientific_explanation": scientific_explanation,
        "fisherman_advice": fisherman_advice,
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_llm = MagicMock()
    mock_llm.chat.completions.create.return_value = mock_completion
    return mock_llm


def _make_agent(mock_llm=None) -> FishingHabitatAgent:
    """Creates an agent with mocked LLM."""
    if mock_llm is None:
        mock_llm = _make_mock_llm()
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        agent = FishingHabitatAgent(live_mode=False, llm_client=mock_llm)
    return agent


# ---------------------------------------------------------------------------
# TEST 1: Valid location/date — baseline working test
# ---------------------------------------------------------------------------
def test_1_valid_location_known_result():
    """
    lat=19.5, lon=70.5, date=2025-10-15
    Expected from Step 5 baseline:
      temperature ≈ 28.40°C, chlorophyll ≈ 0.176 mg/m³
      overall_suitability_score ≈ 93.64
      fishing_potential = High
      confidence = High
    """
    print("\n--- TEST 1: Valid Location/Date (lat=19.5, lon=70.5, 2025-10-15) ---")

    agent = _make_agent()
    response: FishingAgentResponse = agent.run(
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
        query_text="Is fishing good at 19.5, 70.5 on 2025-10-15?",
    )

    print(f"  success: {response.success}")
    print(f"  habitat_score: {response.habitat_score}")
    print(f"  fishing_potential: {response.fishing_potential}")
    print(f"  confidence: {response.confidence}")
    print(f"  temperature_c: {response.environmental_summary.temperature_c}")
    print(f"  chlorophyll_mg_m3: {response.environmental_summary.chlorophyll_mg_m3}")
    print(f"  scientific_explanation: {response.scientific_explanation}")
    print(f"  fisherman_advice: {response.fisherman_advice}")

    assert response.success is True, f"Expected success=True, got error: {response.error}"
    assert response.fishing_potential == "High", f"Expected 'High', got '{response.fishing_potential}'"
    assert response.habitat_score is not None
    assert abs(response.habitat_score - 93.64) < 0.5, f"Expected ~93.64, got {response.habitat_score}"
    assert response.confidence == "High"
    assert response.environmental_summary.temperature_c is not None
    assert response.environmental_summary.chlorophyll_mg_m3 is not None
    assert response.scientific_explanation
    assert response.fisherman_advice
    assert response.disclaimer
    print("  TEST 1 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 2: Second valid location
# ---------------------------------------------------------------------------
def test_2_second_valid_location():
    """lat=16.5, lon=72.0, date=2025-10-20"""
    print("\n--- TEST 2: Second Valid Location (lat=16.5, lon=72.0, 2025-10-20) ---")

    agent = _make_agent()
    response = agent.run(
        latitude=16.5,
        longitude=72.0,
        date_str="2025-10-20",
        query_text="What is the fishing potential here?",
    )

    print(f"  success: {response.success}")
    print(f"  habitat_score: {response.habitat_score}")
    print(f"  fishing_potential: {response.fishing_potential}")
    print(f"  temperature_c: {response.environmental_summary.temperature_c}")
    print(f"  chlorophyll_mg_m3: {response.environmental_summary.chlorophyll_mg_m3}")

    assert response.success is True, f"Expected success=True, got error: {response.error}"
    assert response.fishing_potential in ("High", "Moderate", "Low"), f"Unexpected: {response.fishing_potential}"
    assert response.habitat_score is not None
    assert response.environmental_summary.temperature_c is not None
    print("  TEST 2 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 3: Invalid coordinates — agent must NOT fabricate
# ---------------------------------------------------------------------------
def test_3_invalid_latitude():
    """lat=95.0 is out of range. Agent must return success=False without fabricating."""
    print("\n--- TEST 3: Invalid Latitude (lat=95.0) ---")

    agent = _make_agent()
    response = agent.run(latitude=95.0, longitude=70.5, date_str="2025-10-15")

    print(f"  success: {response.success}")
    print(f"  error: {response.error}")

    assert response.success is False, "Expected failure for invalid latitude"
    assert response.error is not None and len(response.error) > 0
    assert response.habitat_score is None, "Should not fabricate a score"
    assert response.fishing_potential is None, "Should not fabricate a category"
    print("  TEST 3 PASSED [OK]")


def test_3b_invalid_longitude():
    """lon=200.0 is out of range."""
    print("\n--- TEST 3b: Invalid Longitude (lon=200.0) ---")

    agent = _make_agent()
    response = agent.run(latitude=19.5, longitude=200.0, date_str="2025-10-15")

    assert response.success is False
    assert response.habitat_score is None
    print("  TEST 3b PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 4: Missing / masked environmental data
# ---------------------------------------------------------------------------
def test_4_missing_environmental_data():
    """
    Simulate a location where the marine provider returns null temperature+chlorophyll.
    The agent must report 'Insufficient Data' without fabricating a score.
    """
    print("\n--- TEST 4: Missing Environmental Data ---")

    # Patch the provider to return masked data
    masked_marine_result = {
        "success": True,
        "requested_latitude": 19.5,
        "requested_longitude": 70.5,
        "requested_date": "2025-10-15",
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "temperature": None,
        "chlorophyll": None,
        "distance_km": 0.0,
        "data_validity": "Null values (land/coastal mask)",
    }

    agent = _make_agent()
    # Directly patch the provider on the tool
    agent._tool._provider.get_marine_data = MagicMock(return_value=masked_marine_result)

    response = agent.run(latitude=19.5, longitude=70.5, date_str="2025-10-15")

    print(f"  success: {response.success}")
    print(f"  fishing_potential: {response.fishing_potential}")
    print(f"  data_quality: {response.data_quality}")
    print(f"  habitat_score: {response.habitat_score}")
    print(f"  temperature_c: {response.environmental_summary.temperature_c if response.environmental_summary else None}")

    assert response.success is True
    assert response.habitat_score is None, f"Should not produce a score with no data; got {response.habitat_score}"
    assert response.fishing_potential == "Insufficient Data"
    assert response.data_quality in ("No environmental data", "Missing Temperature", "Missing Chlorophyll")
    # Confirm scores are null
    if response.environmental_summary:
        assert response.environmental_summary.temperature_c is None
        assert response.environmental_summary.chlorophyll_mg_m3 is None
    print("  TEST 4 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 5: Agent does NOT calculate or alter the numerical HSI
# ---------------------------------------------------------------------------
def test_5_agent_does_not_recalculate_score():
    """
    The agent must report the EXACT score returned by the tool/engine.
    It must not produce an independently computed score.
    """
    print("\n--- TEST 5: Agent Does Not Modify/Recalculate HSI ---")

    # Use a custom mock LLM that tries to inject a different score in its text
    mock_llm = _make_mock_llm(
        scientific_explanation="Conditions are great. Score should be 99.",  # LLM attempts a different score
        fisherman_advice="Go fishing everywhere!",
    )
    agent = _make_agent(mock_llm=mock_llm)
    response = agent.run(latitude=19.5, longitude=70.5, date_str="2025-10-15")

    print(f"  habitat_score from engine: {response.habitat_score}")
    print(f"  scientific_explanation (from LLM): {response.scientific_explanation}")

    # The structured score field must come from the engine, NOT the LLM's text
    assert response.success is True
    assert abs(response.habitat_score - 93.64) < 0.5, (
        f"Agent altered the habitat score! Expected ~93.64, got {response.habitat_score}"
    )
    # The LLM text is allowed to contain whatever — but the STRUCTURED score field must be from the engine
    print("  TEST 5 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 6: LIVE_MODE=False uses cache providers
# ---------------------------------------------------------------------------
def test_6_live_mode_false_uses_cache_provider():
    """
    Verify that the agent's HabitatTool uses CacheMarineProvider when LIVE_MODE=False.
    """
    print("\n--- TEST 6: LIVE_MODE=False Uses Cache Provider ---")

    agent = _make_agent()
    provider_type = type(agent._tool._provider).__name__

    print(f"  Provider type: {provider_type}")
    assert provider_type == "CacheMarineProvider", (
        f"Expected CacheMarineProvider, got {provider_type}"
    )
    print("  TEST 6 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 7: Date outside historical range
# ---------------------------------------------------------------------------
def test_7_date_outside_range():
    """Date 2024-10-15 is outside Oct 2025 dataset. Must return a clear failure."""
    print("\n--- TEST 7: Date Outside Historical Range (2024-10-15) ---")

    agent = _make_agent()
    response = agent.run(latitude=19.5, longitude=70.5, date_str="2024-10-15")

    print(f"  success: {response.success}")
    print(f"  error: {response.error}")

    assert response.success is False
    assert response.error is not None
    assert response.habitat_score is None
    print("  TEST 7 PASSED [OK]")


# ---------------------------------------------------------------------------
# Manual runner (no pytest required)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        test_1_valid_location_known_result,
        test_2_second_valid_location,
        test_3_invalid_latitude,
        test_3b_invalid_longitude,
        test_4_missing_environmental_data,
        test_5_agent_does_not_recalculate_score,
        test_6_live_mode_false_uses_cache_provider,
        test_7_date_outside_range,
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
        print("ALL STEP 9 AGENT TESTS PASSED [OK]")
    print(f"==================================================")
