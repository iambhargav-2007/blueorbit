"""
test_coordinator.py

Automated tests for the ORCA Coordinator (Step 12).
Verifies multi-agent routing, execution, and deterministic result preservation.
LLM calls are MOCKED.
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch
import pytest

# Make sure backend is importable from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.coordinator.coordinator import OrcaCoordinator
from app.coordinator.schemas import CoordinatorResponse
from app.agents.schemas import FishingAgentResponse, WeatherSafetyAgentResponse, GeofencingAgentResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_mock_llm(capabilities):
    """Creates a mock Groq client that returns specific capabilities."""
    mock_message = MagicMock()
    mock_message.content = json.dumps({"requested_capabilities": capabilities})
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_llm = MagicMock()
    mock_llm.chat.completions.create.return_value = mock_completion
    return mock_llm

def _make_coordinator(capabilities=None) -> OrcaCoordinator:
    """Creates a coordinator with mocked LLM intent router and cache-mode agents."""
    if capabilities is None:
        capabilities = []
    mock_llm = _make_mock_llm(capabilities)
    
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        # Pass live_mode=False so underlying tools use local cache providers
        coord = OrcaCoordinator(llm_client=mock_llm, live_mode=False)
        
        # We also want to mock the LLM calls INSIDE the agents so they don't fail,
        # but we want their deterministic engines to run normally.
        # The agents take the same llm_client passed to coordinator.
        # So we override the chat.completions.create mock to return different things
        # based on the prompt, or just a generic valid JSON that covers all agent responses.
        
        def side_effect(*args, **kwargs):
            # Generic valid JSON that covers Fishing, Weather, and Geofencing agents
            generic_resp = {
                "scientific_explanation": "Mock explanation.",
                "fisherman_advice": "Mock advice.",
                "safety_narrative": "Mock safety narrative.",
                "safety_advice": "Mock safety advice.",
                "geofence_narrative": "Mock geofence narrative.",
                "geofence_advice": "Mock geofence advice."
            }
            m_msg = MagicMock()
            m_msg.content = json.dumps(generic_resp)
            m_choice = MagicMock()
            m_choice.message = m_msg
            m_comp = MagicMock()
            m_comp.choices = [m_choice]
            return m_comp
            
        # Only apply the side_effect for agent calls (not the router call which we already handled)
        # But since the router also uses it, we should inspect messages.
        def smart_side_effect(*args, **kwargs):
            messages = kwargs.get("messages", [])
            sys_msg = messages[0]["content"] if messages else ""
            if "Intent Router" in sys_msg:
                # Router prompt
                m_msg = MagicMock()
                m_msg.content = json.dumps({"requested_capabilities": capabilities})
                m_choice = MagicMock()
                m_choice.message = m_msg
                m_comp = MagicMock()
                m_comp.choices = [m_choice]
                return m_comp
            else:
                # Agent prompt
                generic_resp = {
                    "scientific_explanation": "Mock explanation.",
                    "fisherman_advice": "Mock advice.",
                    "safety_narrative": "Mock safety narrative.",
                    "safety_advice": "Mock safety advice.",
                    "geofence_narrative": "Mock geofence narrative.",
                    "geofence_advice": "Mock geofence advice."
                }
                m_msg = MagicMock()
                m_msg.content = json.dumps(generic_resp)
                m_choice = MagicMock()
                m_choice.message = m_msg
                m_comp = MagicMock()
                m_comp.choices = [m_choice]
                return m_comp
                
        mock_llm.chat.completions.create.side_effect = smart_side_effect
        
    return coord


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

# TEST 1 — HABITAT ONLY ROUTING
def test_1_habitat_only_routing():
    coord = _make_coordinator(["habitat"])
    res = coord.process_request("Is the fish habitat good?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    
    assert res.success is True
    assert "habitat" in res.routing.requested_capabilities
    assert "fishing_habitat" in res.routing.agents_invoked
    assert "weather_safety" not in res.routing.agents_invoked
    assert "geofencing" not in res.routing.agents_invoked
    
    assert res.habitat is not None
    assert res.weather is None
    assert res.geofencing is None
    assert res.habitat.habitat_score is not None

# TEST 2 — WEATHER ONLY ROUTING
def test_2_weather_only_routing():
    coord = _make_coordinator(["weather"])
    res = coord.process_request("Is it safe?", latitude=15.0, longitude=68.0, date_str="2025-10-01")
    
    assert res.success is True
    assert "weather" in res.routing.requested_capabilities
    assert "weather_safety" in res.routing.agents_invoked
    assert res.weather is not None
    assert res.habitat is None
    assert res.weather.risk_level == "Very High Risk" # deterministic engine output

# TEST 3 — GEOFENCING ONLY ROUTING
def test_3_geofencing_only_routing():
    coord = _make_coordinator(["geofencing"])
    res = coord.process_request("Inside EEZ?", latitude=19.0, longitude=71.0)
    
    assert res.success is True
    assert "geofencing" in res.routing.agents_invoked
    assert res.geofencing is not None
    assert res.geofencing.geofence_status == "SAFE"

# TEST 4 — HABITAT + WEATHER
def test_4_habitat_weather():
    coord = _make_coordinator(["habitat", "weather"])
    res = coord.process_request("Good and safe?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    
    assert "fishing_habitat" in res.routing.agents_invoked
    assert "weather_safety" in res.routing.agents_invoked
    assert "geofencing" not in res.routing.agents_invoked
    assert res.habitat is not None
    assert res.weather is not None
    assert res.geofencing is None

# TEST 5 — HABITAT + GEOFENCING
def test_5_habitat_geofencing():
    coord = _make_coordinator(["habitat", "geofencing"])
    res = coord.process_request("Good and in EEZ?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    
    assert "fishing_habitat" in res.routing.agents_invoked
    assert "geofencing" in res.routing.agents_invoked
    assert res.weather is None
    assert res.habitat is not None
    assert res.geofencing is not None

# TEST 6 — WEATHER + GEOFENCING
def test_6_weather_geofencing():
    coord = _make_coordinator(["weather", "geofencing"])
    res = coord.process_request("Safe and in EEZ?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    
    assert "weather_safety" in res.routing.agents_invoked
    assert "geofencing" in res.routing.agents_invoked
    assert res.weather is not None
    assert res.geofencing is not None
    assert res.habitat is None

# TEST 7 — ALL THREE AGENTS
def test_7_all_three_agents():
    coord = _make_coordinator(["habitat", "weather", "geofencing"])
    res = coord.process_request("Good, safe, in EEZ?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    
    assert len(res.routing.agents_invoked) == 3
    assert res.habitat is not None
    assert res.weather is not None
    assert res.geofencing is not None

# TEST 8 — HABITAT RESULT PRESERVATION
def test_8_habitat_result_preservation():
    coord = _make_coordinator(["habitat"])
    res = coord.process_request("Habitat?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    assert abs(res.habitat.habitat_score - 93.64) < 0.5
    assert res.habitat.fishing_potential == "High"

# TEST 9 — WEATHER RESULT PRESERVATION
def test_9_weather_result_preservation():
    coord = _make_coordinator(["weather"])
    res = coord.process_request("Weather?", latitude=15.0, longitude=68.0, date_str="2025-10-01")
    assert res.weather.weather_conditions.wind_speed_knots is not None
    assert abs(res.weather.weather_conditions.overall_safety_score - 25.2) < 0.5
    assert res.weather.risk_level == "Very High Risk"

# TEST 10 — GEOFENCE RESULT PRESERVATION
def test_10_geofence_result_preservation():
    coord = _make_coordinator(["geofencing"])
    res = coord.process_request("Geofence?", latitude=19.0, longitude=71.0)
    assert res.geofencing.geofence_status == "SAFE"
    assert res.geofencing.inside_indian_eez is True
    assert res.geofencing.distance_to_eez_boundary_km is not None

# TEST 11 — HIGH WEATHER RISK CANNOT BE DOWNGRADED
def test_11_high_weather_risk_preserved():
    coord = _make_coordinator(["habitat", "weather"])
    # This location has High Habitat but Very High Risk
    res = coord.process_request("Status?", latitude=15.0, longitude=68.0, date_str="2025-10-01")
    assert res.weather.risk_level == "Very High Risk"
    # Coordinator does NOT calculate a combined score. The risk remains explicitly Very High Risk.

# TEST 12 — OUTSIDE EEZ CANNOT BECOME SAFE
def test_12_outside_eez_preserved():
    coord = _make_coordinator(["geofencing"])
    res = coord.process_request("EEZ?", latitude=18.0, longitude=65.0)
    assert res.geofencing.geofence_status == "OUTSIDE_EEZ"
    assert res.geofencing.inside_indian_eez is False

# TEST 13 — BOUNDARY WARNING PRESERVED
def test_13_boundary_warning_preserved():
    coord = _make_coordinator(["geofencing"])
    res = coord.process_request("EEZ?", latitude=19.0, longitude=68.08)
    assert res.geofencing.geofence_status == "WARNING"

# TEST 14 — MISSING DATA
def test_14_missing_data():
    coord = _make_coordinator(["habitat"])
    # Missing environmental data path
    with patch('app.providers.cache_marine_provider.CacheMarineProvider.get_marine_data') as mock_prov:
        mock_prov.return_value = {
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
        res = coord.process_request("Habitat?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
        assert res.habitat.fishing_potential == "Insufficient Data"
        assert res.habitat.habitat_score is None

# TEST 15 — AGENT FAILURE ISOLATION
def test_15_agent_failure_isolation():
    coord = _make_coordinator(["habitat", "geofencing"])
    # Force the habitat agent to raise an exception
    with patch.object(coord._habitat_agent, 'run', side_effect=Exception("Critical failure")):
        res = coord.process_request("Habitat + Geofence?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
        
        # Geofencing should still succeed
        assert res.geofencing is not None
        assert res.geofencing.success is True
        # Habitat should be None or marked failed
        assert res.habitat is None
        # Coordinator should flag the error
        assert len(res.errors) > 0
        assert "Habitat Agent encountered a critical error" in res.errors[0]
        # Overall success is True because at least Geofencing succeeded
        assert res.success is True

# TEST 16 — INVALID INPUT
def test_16_invalid_input():
    coord = _make_coordinator(["geofencing"])
    res = coord.process_request("Geofence?", latitude=95.0, longitude=71.0)
    assert res.success is False
    assert len(res.errors) > 0

# TEST 17 — MISSING REQUIRED LOCATION
def test_17_missing_required_location():
    coord = _make_coordinator(["habitat"])
    # Missing lat/lon
    res = coord.process_request("Good place?")
    assert res.success is False
    assert len(res.errors) > 0
    assert "Latitude and longitude are required" in res.errors[0]

# TEST 18 — UNRELATED REQUEST
def test_18_unrelated_request():
    coord = _make_coordinator([])
    res = coord.process_request("What is the capital of India?")
    assert res.success is False
    assert len(res.routing.agents_invoked) == 0
    assert len(res.errors) > 0
    assert "outside supported domain" in res.errors[0]

# TEST 19 — AMBIGUOUS REQUEST
def test_19_ambiguous_request():
    coord = _make_coordinator([])
    res = coord.process_request("Tell me about this place.")
    assert res.success is False
    assert len(res.routing.agents_invoked) == 0

# TEST 20 — NO INVENTED COMBINED SCORE
def test_20_no_invented_combined_score():
    coord = _make_coordinator(["habitat", "weather", "geofencing"])
    res = coord.process_request("Status?", latitude=19.5, longitude=70.5, date_str="2025-10-15")
    # CoordinatorResponse schema does not have a "combined_score" field
    assert not hasattr(res, "combined_score")
    assert not hasattr(res, "overall_score")
    # All agent responses are intact
    assert res.habitat.habitat_score is not None
    assert res.weather.weather_conditions.overall_safety_score is not None
    assert res.geofencing.geofence_status is not None

# TEST 21 — LLM CANNOT OVERRIDE RESULTS
def test_21_llm_cannot_override_results():
    coord = _make_coordinator(["geofencing"])
    # We already know the smart_side_effect mock LLM returns "Mock geofence narrative"
    # without altering the engine result
    res = coord.process_request("Status?", latitude=18.0, longitude=65.0)
    assert res.geofencing.geofence_status == "OUTSIDE_EEZ"
    assert res.geofencing.inside_indian_eez is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
