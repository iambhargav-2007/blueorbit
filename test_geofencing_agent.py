"""
test_geofencing_agent.py

Automated tests for the Geofencing AI Agent (Step 11).

LLM calls are MOCKED so no real Groq API key is required to run this suite.

All expected numerical values and geofence statuses are sourced from the
deterministic GeofencingEngine outputs (observed in test_geofencing.py).

Run:
    python -m pytest test_geofencing_agent.py -v
    # or directly:
    python test_geofencing_agent.py
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

# Make sure backend is importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.tools.geofencing_tool import GeofencingTool
from app.agents.geofencing_agent import GeofencingAgent
from app.agents.schemas import GeofencingAgentResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_mock_llm(
    geofence_narrative: str = "Mocked geofence narrative.",
    geofence_advice: str = "Mocked geofence advice.",
):
    """Creates a mock Groq client that returns a pre-set JSON response."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({
        "geofence_narrative": geofence_narrative,
        "geofence_advice": geofence_advice,
    })
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_llm = MagicMock()
    mock_llm.chat.completions.create.return_value = mock_completion
    return mock_llm


def _make_agent(mock_llm=None) -> GeofencingAgent:
    """Creates an agent with mocked LLM."""
    if mock_llm is None:
        mock_llm = _make_mock_llm()
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        agent = GeofencingAgent(llm_client=mock_llm)
    return agent


# ---------------------------------------------------------------------------
# TEST 1: Location inside EEZ
# ---------------------------------------------------------------------------
def test_1_location_inside_eez():
    """
    lat=19.0, lon=71.0 — expected from engine tests:
      inside_indian_eez=True, geofence_status="SAFE"
    """
    print("\n--- TEST 1: Location Inside EEZ (lat=19.0, lon=71.0) ---")

    agent = _make_agent()
    response: GeofencingAgentResponse = agent.run(
        latitude=19.0,
        longitude=71.0,
        query_text="Am I inside Indian waters?",
    )

    print(f"  success: {response.success}")
    print(f"  inside_indian_eez: {response.inside_indian_eez}")
    print(f"  geofence_status: {response.geofence_status}")
    print(f"  geofence_narrative: {response.geofence_narrative}")

    assert response.success is True, f"Expected success=True, got error: {response.error}"
    assert response.inside_indian_eez is True, "Expected to be inside EEZ"
    assert response.geofence_status == "SAFE", f"Expected 'SAFE', got '{response.geofence_status}'"
    print("  TEST 1 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 2: Location outside EEZ
# ---------------------------------------------------------------------------
def test_2_location_outside_eez():
    """
    lat=18.0, lon=65.0 — expected from engine tests:
      inside_indian_eez=False, geofence_status="OUTSIDE_EEZ"
    """
    print("\n--- TEST 2: Location Outside EEZ (lat=18.0, lon=65.0) ---")

    agent = _make_agent()
    response = agent.run(
        latitude=18.0,
        longitude=65.0,
        query_text="Are we in international waters?",
    )

    print(f"  success: {response.success}")
    print(f"  inside_indian_eez: {response.inside_indian_eez}")
    print(f"  geofence_status: {response.geofence_status}")

    assert response.success is True
    assert response.inside_indian_eez is False
    assert response.geofence_status == "OUTSIDE_EEZ"
    print("  TEST 2 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 3: Location near EEZ boundary (Warning)
# ---------------------------------------------------------------------------
def test_3_location_near_boundary():
    """
    lat=19.0, lon=68.08, warning_distance_km=15.0
    Expected: geofence_status="WARNING", inside_indian_eez=True
    """
    print("\n--- TEST 3: Near Boundary Warning Zone (lat=19.0, lon=68.08) ---")

    agent = _make_agent()
    response = agent.run(
        latitude=19.0,
        longitude=68.08,
        warning_distance_km=15.0,
    )

    print(f"  success: {response.success}")
    print(f"  inside_indian_eez: {response.inside_indian_eez}")
    print(f"  geofence_status: {response.geofence_status}")
    print(f"  distance_to_eez_boundary_km: {response.distance_to_eez_boundary_km}")

    assert response.success is True
    assert response.inside_indian_eez is True
    assert response.geofence_status == "WARNING"
    assert response.distance_to_eez_boundary_km is not None
    print("  TEST 3 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 4: Invalid latitude
# ---------------------------------------------------------------------------
def test_4_invalid_latitude():
    """lat=95.0 is out of range. Agent must reject."""
    print("\n--- TEST 4: Invalid Latitude (lat=95.0) ---")

    agent = _make_agent()
    response = agent.run(latitude=95.0, longitude=71.0)

    print(f"  success: {response.success}")
    print(f"  error: {response.error}")

    assert response.success is False
    assert response.error is not None
    assert response.geofence_status is None
    print("  TEST 4 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 5: Invalid longitude
# ---------------------------------------------------------------------------
def test_5_invalid_longitude():
    """lon=195.0 is out of range. Agent must reject."""
    print("\n--- TEST 5: Invalid Longitude (lon=195.0) ---")

    agent = _make_agent()
    response = agent.run(latitude=19.0, longitude=195.0)

    assert response.success is False
    assert response.geofence_status is None
    print("  TEST 5 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 6: Deterministic result cannot be overridden
# ---------------------------------------------------------------------------
def test_6_llm_cannot_override_engine():
    """
    Mock LLM claims status is SAFE when engine says OUTSIDE_EEZ.
    The structured geofence_status MUST remain the engine's result.
    """
    print("\n--- TEST 6: Deterministic Result Cannot Be Overridden ---")

    contradicting_llm = _make_mock_llm(
        geofence_narrative="You are safely inside the EEZ and can fish here.",
        geofence_advice="Go ahead and fish.",
    )
    agent = _make_agent(mock_llm=contradicting_llm)
    
    # Use OUTSIDE_EEZ coords
    response = agent.run(latitude=18.0, longitude=65.0)

    print(f"  Engine geofence_status: {response.geofence_status}")
    print(f"  LLM narrative: {response.geofence_narrative}")

    assert response.success is True
    # The structured field MUST be the engine's reality, ignoring the LLM text
    assert response.geofence_status == "OUTSIDE_EEZ"
    assert response.inside_indian_eez is False
    print("  TEST 6 PASSED [OK]")


# ---------------------------------------------------------------------------
# TEST 7: Protected-area limitation explicitly handled
# ---------------------------------------------------------------------------
def test_7_protected_area_limitation():
    """
    Verify that the agent correctly passes through the engine's statement
    that protected-area data is not available.
    """
    print("\n--- TEST 7: Protected Area Limitation ---")

    agent = _make_agent()
    response = agent.run(latitude=19.0, longitude=71.0)

    print(f"  protected_area_coverage_available: {response.protected_area_coverage_available}")
    print(f"  inside_protected_area: {response.inside_protected_area}")

    assert response.success is True
    assert response.protected_area_coverage_available is False
    assert response.inside_protected_area is None
    print("  TEST 7 PASSED [OK]")


# ---------------------------------------------------------------------------
# Manual runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        test_1_location_inside_eez,
        test_2_location_outside_eez,
        test_3_location_near_boundary,
        test_4_invalid_latitude,
        test_5_invalid_longitude,
        test_6_llm_cannot_override_engine,
        test_7_protected_area_limitation,
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
        print("ALL STEP 11 GEOFENCING AGENT TESTS PASSED [OK]")
    print(f"==================================================")
