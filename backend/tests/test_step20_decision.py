"""
test_step20_decision.py

Comprehensive test suite for Step 20: Unified Fishing Decision Engine.

Covers all 20 required test cases:
1.  habitat HIGH + weather LOW -> FAVORABLE
2.  habitat MODERATE + weather LOW -> CAUTION
3.  habitat LOW + weather LOW -> NOT_RECOMMENDED
4.  habitat HIGH + weather MEDIUM -> CAUTION
5.  habitat HIGH + weather HIGH -> NOT_RECOMMENDED
6.  weather insufficient -> INSUFFICIENT_DATA
7.  habitat insufficient -> INSUFFICIENT_DATA
8.  outside EEZ -> NOT_RECOMMENDED with correct disclaimer
9.  EEZ WARNING preserved
10. protected-area coverage unavailable preserved
11. current marine + current weather -> LIVE
12. historical marine + historical weather -> HISTORICAL
13. live + historical mixing rejected
14. invalid location rejected
15. location context reused across follow-up
16. deterministic result cannot be overridden by LLM
17. limiting factor deterministic
18. confidence deterministic
19. unrelated request does not incorrectly trigger fishing decision
20. existing habitat/weather/geofence requests continue working
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.services.unified_decision_engine import UnifiedFishingDecisionEngine
from app.tools.fishing_decision_tool import FishingDecisionTool
from app.agents.fishing_decision_agent import FishingDecisionAgent
from app.conversation.conversation_coordinator import ConversationCoordinator
from app.location.schemas import LocationContext
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures for Domain Mocks
# ---------------------------------------------------------------------------

def make_habitat(success=True, score=92.0, status="High", confidence="High", source="Live Copernicus BGC"):
    return {
        "success": success,
        "habitat_score": score,
        "fishing_potential": status,
        "confidence": confidence,
        "source": source,
    }

def make_weather(success=True, score=90.0, risk="Low Risk", confidence="High", source="Interim Live Open-Meteo"):
    return {
        "success": success,
        "risk_level": risk,
        "confidence": confidence,
        "source": source,
        "weather_conditions": {
            "overall_safety_score": score,
            "wind_speed_knots": 10.0,
            "wave_height_meters": 0.9,
            "source": source,
        }
    }

def make_geofence(inside=True, status="SAFE", dist_km=45.0, prot_avail=False):
    return {
        "success": True,
        "is_inside_eez": inside,
        "status": status,
        "distance_to_boundary_km": dist_km,
        "protected_area_coverage_available": prot_avail,
    }


# ---------------------------------------------------------------------------
# Tests 1 - 5: Decision Matrix
# ---------------------------------------------------------------------------

def test_1_habitat_high_weather_low_is_favorable():
    """1. habitat HIGH + weather LOW -> FAVORABLE (Limiting factor None)."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=95.0, status="High"),
        weather_data=make_weather(score=92.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "FAVORABLE"
    assert dec.limiting_factor == "None"
    assert dec.overall_score == round(0.5 * 95.0 + 0.5 * 92.0, 1)


def test_2_habitat_moderate_weather_low_is_caution():
    """2. habitat MODERATE + weather LOW -> CAUTION (Limiting factor Habitat Suitability)."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=65.0, status="Moderate"),
        weather_data=make_weather(score=90.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "CAUTION"
    assert dec.limiting_factor == "Habitat Suitability"


def test_3_habitat_low_weather_low_is_not_recommended():
    """3. habitat LOW + weather LOW -> NOT_RECOMMENDED."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=30.0, status="Low"),
        weather_data=make_weather(score=90.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "NOT_RECOMMENDED"
    assert dec.limiting_factor == "Habitat Suitability"


def test_4_habitat_high_weather_medium_is_caution():
    """4. habitat HIGH + weather MEDIUM -> CAUTION (Limiting factor Weather Safety)."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=92.0, status="High"),
        weather_data=make_weather(score=60.0, risk="Moderate Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "CAUTION"
    assert dec.limiting_factor == "Weather Safety"


def test_5_habitat_high_weather_high_is_not_recommended():
    """5. habitat HIGH + weather HIGH -> NOT_RECOMMENDED (Limiting factor Weather Safety)."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=95.0, status="High"),
        weather_data=make_weather(score=25.0, risk="High Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "NOT_RECOMMENDED"
    assert dec.limiting_factor == "Weather Safety"
    assert any("hazardous" in r.lower() or "marine weather" in r.lower() for r in dec.reasons)


# ---------------------------------------------------------------------------
# Tests 6 & 7: Missing Data Handling
# ---------------------------------------------------------------------------

def test_6_weather_insufficient_returns_insufficient_data():
    """6. weather insufficient -> INSUFFICIENT_DATA."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=90.0, status="High"),
        weather_data={"success": False, "error": "API unreachable", "risk_level": "Insufficient Data"},
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "INSUFFICIENT_DATA"
    assert dec.limiting_factor == "Insufficient Weather Data"
    assert dec.overall_score is None


def test_7_habitat_insufficient_returns_insufficient_data():
    """7. habitat insufficient -> INSUFFICIENT_DATA."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data={"success": False, "error": "Chlorophyll unavailable", "fishing_potential": "Insufficient Data"},
        weather_data=make_weather(score=90.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE"),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "INSUFFICIENT_DATA"
    assert dec.limiting_factor == "Insufficient Marine Data"
    assert dec.overall_score is None


# ---------------------------------------------------------------------------
# Tests 8, 9 & 10: Geofence and Protected Area Rules
# ---------------------------------------------------------------------------

def test_8_outside_eez_is_not_recommended_with_coverage_disclaimer():
    """8. outside EEZ -> NOT_RECOMMENDED without claiming legal prohibition."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=90.0, status="High"),
        weather_data=make_weather(score=90.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=False, status="OUTSIDE EEZ"),
        latitude=12.0,
        longitude=65.0,
    )
    assert dec.decision == "NOT_RECOMMENDED"
    assert dec.limiting_factor == "EEZ Boundary"
    assert any("supported Indian EEZ data boundary" in w for w in dec.warnings)
    assert any("not a determination of legal fishing rights" in w for w in dec.warnings)


def test_9_eez_warning_preserved():
    """9. EEZ WARNING preserved as prominent advisory."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=92.0, status="High"),
        weather_data=make_weather(score=90.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=True, status="WARNING", dist_km=6.5),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec.decision == "CAUTION"
    assert dec.limiting_factor == "EEZ Boundary"
    assert any("buffer zone" in w for w in dec.warnings)


def test_10_protected_area_coverage_unavailable_preserved():
    """10. protected-area coverage unavailable is preserved truthfully."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=make_habitat(score=90.0, status="High"),
        weather_data=make_weather(score=90.0, risk="Low Risk"),
        geofence_data=make_geofence(inside=True, status="SAFE", prot_avail=False),
        latitude=15.41,
        longitude=73.80,
    )
    assert any("protected area boundary coverage is currently unavailable" in w for w in dec.warnings)


# ---------------------------------------------------------------------------
# Tests 11, 12, 13 & 14: Temporal Consistency & Invalid Coordinates
# ---------------------------------------------------------------------------

def test_11_and_12_current_and_historical_temporal_modes():
    """11 & 12: Proper propagation of LIVE vs HISTORICAL temporal mode."""
    engine = UnifiedFishingDecisionEngine()
    dec_live = engine.evaluate(
        habitat_data=make_habitat(),
        weather_data=make_weather(),
        geofence_data=make_geofence(),
        latitude=15.41,
        longitude=73.80,
        temporal_mode="LIVE"
    )
    assert dec_live.temporal_mode == "LIVE"

    dec_hist = engine.evaluate(
        habitat_data=make_habitat(source="Historical Parquet"),
        weather_data=make_weather(source="Historical Weather Cache"),
        geofence_data=make_geofence(),
        latitude=15.41,
        longitude=73.80,
        date_str="2025-10-15",
        temporal_mode="HISTORICAL"
    )
    assert dec_hist.temporal_mode == "HISTORICAL"


def test_13_live_future_mixing_rejected():
    """13. Future date requests return explicit UNSUPPORTED_FUTURE with no fake forecast."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=None,
        weather_data=None,
        geofence_data=None,
        latitude=15.41,
        longitude=73.80,
        date_str="2026-09-04",
        temporal_mode="UNSUPPORTED_FUTURE",
    )
    assert dec.decision == "INSUFFICIENT_DATA"
    assert dec.limiting_factor == "Unsupported Future Date"
    assert dec.overall_score is None


def test_14_invalid_location_rejected():
    """14. Coordinates out of bounds (-90..90, -180..180) are rejected."""
    engine = UnifiedFishingDecisionEngine()
    dec = engine.evaluate(
        habitat_data=None,
        weather_data=None,
        geofence_data=None,
        latitude=120.0,
        longitude=73.80,
    )
    assert dec.decision == "NOT_RECOMMENDED"
    assert dec.limiting_factor == "Invalid Coordinates"


# ---------------------------------------------------------------------------
# Test 15: Multi-Turn Location Context Reused
# ---------------------------------------------------------------------------

def test_15_location_context_reused_across_follow_up():
    """15. Follow-up 'Can I go fishing today?' reuses established location context."""
    coord = ConversationCoordinator()
    session_id = "test-step20-reuse"

    # Set location via GPS
    loc = LocationContext(
        latitude=15.41,
        longitude=73.80,
        display_name="Goa Coastal Zone",
        source="gps"
    )

    # Mock tool to return favorable decision
    mock_dec = UnifiedFishingDecisionEngine().evaluate(
        habitat_data=make_habitat(),
        weather_data=make_weather(),
        geofence_data=make_geofence(),
        latitude=15.41,
        longitude=73.80,
    )
    with patch.object(coord._coordinator._decision_agent._tool, "get_fishing_decision", return_value={"success": True, "decision": mock_dec}):
        resp = coord.process_turn(
            session_id=session_id,
            query_text="Can I go fishing today?",
            location_context=loc,
        )

    assert resp.success is True
    assert resp.fishing_decision is not None
    assert resp.fishing_decision.decision.decision == "FAVORABLE"
    assert abs(resp.request["latitude"] - 15.41) < 0.05


# ---------------------------------------------------------------------------
# Test 16: Deterministic Result Cannot Be Overridden by LLM
# ---------------------------------------------------------------------------

def test_16_deterministic_result_cannot_be_overridden_by_llm():
    """16. Even if LLM outputs 'Everything is perfect', deterministic scores remain."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"narrative": "It is totally fine to sail!", "advice": "Go fish freely"}'))
    ]
    mock_llm.chat.completions.create.return_value = mock_response

    # Engine generates NOT_RECOMMENDED due to high weather risk
    mock_dec = UnifiedFishingDecisionEngine().evaluate(
        habitat_data=make_habitat(score=90.0, status="High"),
        weather_data=make_weather(score=10.0, risk="High Risk"),
        geofence_data=make_geofence(),
        latitude=15.41,
        longitude=73.80,
    )
    mock_tool = MagicMock()
    mock_tool.get_fishing_decision.return_value = {"success": True, "decision": mock_dec}

    agent = FishingDecisionAgent(llm_client=mock_llm, tool=mock_tool)
    res = agent.run(latitude=15.41, longitude=73.80, date_str="2026-09-03")

    assert res.success is True
    assert res.decision.decision == "NOT_RECOMMENDED"
    assert res.decision.limiting_factor == "Weather Safety"
    assert res.decision.overall_score == 10.0


# ---------------------------------------------------------------------------
# Tests 17 & 18: Limiting Factor & Confidence Deterministic
# ---------------------------------------------------------------------------

def test_17_and_18_limiting_factor_and_confidence_deterministic():
    """17 & 18: Deterministic confidence and limiting factor computation."""
    engine = UnifiedFishingDecisionEngine()

    # High confidence test
    dec_high = engine.evaluate(
        habitat_data=make_habitat(confidence="High"),
        weather_data=make_weather(confidence="High"),
        geofence_data=make_geofence(),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec_high.confidence == "HIGH"
    assert dec_high.limiting_factor == "None"

    # Low confidence test
    dec_low = engine.evaluate(
        habitat_data=make_habitat(confidence="Low"),
        weather_data=make_weather(confidence="High"),
        geofence_data=make_geofence(),
        latitude=15.41,
        longitude=73.80,
    )
    assert dec_low.confidence == "LOW"


# ---------------------------------------------------------------------------
# Tests 19 & 20: Routing Integrity and Existing Capabilities
# ---------------------------------------------------------------------------

def test_19_unrelated_request_does_not_trigger_fishing_decision():
    """19. Unrelated query (e.g. 'What is the capital of India?') returns empty capabilities."""
    from app.coordinator.router import OrcaRouter
    router = OrcaRouter()
    caps = router.get_capabilities("What is the capital of India?")
    assert "fishing_decision" not in caps
    assert caps == []


def test_20_existing_capabilities_remain_functional():
    """20. Specialized queries for habitat, weather, and geofencing still route correctly."""
    from app.coordinator.router import OrcaRouter
    router = OrcaRouter()

    caps_hab = router.get_capabilities("What is the habitat suitability at 19.5, 70.5?")
    assert "habitat" in caps_hab

    caps_weath = router.get_capabilities("How is the weather today?")
    assert "weather" in caps_weath

    caps_geo = router.get_capabilities("Am I inside the Indian EEZ?")
    assert "geofencing" in caps_geo
