"""
test_conversation.py

Step 13 test suite — Agent State + Conversation Flow.

All 20 tests are designed to verify:
- Session creation and isolation
- Context carry-forward (lat/lon/date reuse across turns)
- Explicit override of stored context
- Clarification on missing required values
- Session reset clears context
- Deterministic engine results cannot be overridden by LLM text
- The existing coordinator dynamic routing still works through this layer

LLM calls are MOCKED — no real Groq API key required.
"""

import sys
import os
import json
import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.conversation.conversation_coordinator import ConversationCoordinator
from app.conversation.state_manager import ConversationStateManager
from app.conversation.context_resolver import resolve_context, ResolvedContext
from app.conversation.schemas import ClarificationRequired
from app.conversation.state import ConversationState
from app.coordinator.schemas import CoordinatorResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(capabilities: list) -> MagicMock:
    """Return a mock Groq client whose router and agents produce valid JSON."""
    def smart_side_effect(*args, **kwargs):
        messages = kwargs.get("messages", [])
        sys_msg = messages[0]["content"] if messages else ""
        if "Intent Router" in sys_msg:
            content = json.dumps({"requested_capabilities": capabilities})
        else:
            content = json.dumps({
                "scientific_explanation": "Mock explanation.",
                "fisherman_advice": "Mock advice.",
                "safety_narrative": "Mock safety narrative.",
                "safety_advice": "Mock safety advice.",
                "geofence_narrative": "Mock geofence narrative.",
                "geofence_advice": "Mock geofence advice.",
            })
        m_msg = MagicMock()
        m_msg.content = content
        m_choice = MagicMock()
        m_choice.message = m_msg
        m_comp = MagicMock()
        m_comp.choices = [m_choice]
        return m_comp

    mock_llm = MagicMock()
    mock_llm.chat.completions.create.side_effect = smart_side_effect
    return mock_llm


def _make_conv_coord(capabilities: list) -> ConversationCoordinator:
    """Create a ConversationCoordinator with mocked LLM, cache mode."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(capabilities),
            live_mode=False,
        )
    return cc


def _fresh_session_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# TEST 1 — Create a new session
# ---------------------------------------------------------------------------
def test_1_create_new_session():
    cc = _make_conv_coord(["habitat"])
    sid = _fresh_session_id()

    assert not cc._state_manager.session_exists(sid)
    cc.create_session(sid)
    assert cc._state_manager.session_exists(sid)

    state = cc.get_state(sid)
    assert state is not None
    assert state.session_id == sid
    assert state.latitude is None
    assert state.longitude is None


# ---------------------------------------------------------------------------
# TEST 2 — Store latitude/longitude in state
# ---------------------------------------------------------------------------
def test_2_store_lat_lon_in_state():
    manager = ConversationStateManager()
    sid = _fresh_session_id()
    manager.create_session(sid)
    manager.update_state(sid, latitude=19.5, longitude=70.5)

    state = manager.get_state(sid)
    assert state.latitude == 19.5
    assert state.longitude == 70.5


# ---------------------------------------------------------------------------
# TEST 3 — Retrieve stored state
# ---------------------------------------------------------------------------
def test_3_retrieve_stored_state():
    manager = ConversationStateManager()
    sid = _fresh_session_id()
    manager.create_session(sid)
    manager.update_state(sid, latitude=16.0, longitude=73.0, date_str="2025-11-01")

    state = manager.get_state(sid)
    assert state.latitude == 16.0
    assert state.longitude == 73.0
    assert state.date_str == "2025-11-01"


# ---------------------------------------------------------------------------
# TEST 4 — Habitat request stores location and structured result
# ---------------------------------------------------------------------------
def test_4_habitat_request_stores_location_and_result():
    cc = _make_conv_coord(["habitat"])
    sid = _fresh_session_id()

    cc.process_turn(
        session_id=sid,
        query_text="Habitat suitability?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    state = cc.get_state(sid)
    assert state.latitude == 19.5
    assert state.longitude == 70.5
    assert state.date_str == "2025-10-15"
    assert "habitat" in state.last_capabilities
    assert state.last_result is not None
    assert state.last_result.habitat is not None


# ---------------------------------------------------------------------------
# TEST 5 — Follow-up weather request reuses previous location
# ---------------------------------------------------------------------------
def test_5_followup_weather_reuses_stored_location():
    sid = _fresh_session_id()

    # Turn 1: habitat with explicit location
    cc1 = _make_conv_coord(["habitat"])
    cc1.process_turn(
        session_id=sid,
        query_text="How is the habitat?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    # Inject state into a second coordinator (shared state manager)
    # Simpler: use the SAME coordinator object for both turns
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat"]),
            live_mode=False,
        )

    sid2 = _fresh_session_id()

    # Turn 1: store location
    cc.process_turn(
        session_id=sid2,
        query_text="How is the habitat?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    # Now switch LLM to weather mode — mock only, cc object is the same
    cc._coordinator._router._llm.chat.completions.create.side_effect = \
        _make_mock_llm(["weather"]).chat.completions.create.side_effect

    # Turn 2: no lat/lon provided — should reuse stored
    result = cc.process_turn(
        session_id=sid2,
        query_text="What about the weather?",
        # latitude and longitude NOT provided
        date_str="2025-10-15",
    )

    assert isinstance(result, CoordinatorResponse)
    state = cc.get_state(sid2)
    assert state.latitude == 19.5
    assert state.longitude == 70.5


# ---------------------------------------------------------------------------
# TEST 6 — Follow-up geofencing request reuses previous location
# ---------------------------------------------------------------------------
def test_6_followup_geofencing_reuses_stored_location():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat"]),
            live_mode=False,
        )

    sid = _fresh_session_id()

    # Turn 1: habitat with explicit location
    cc.process_turn(
        session_id=sid,
        query_text="Habitat?",
        latitude=19.0,
        longitude=71.0,
        date_str="2025-10-15",
    )

    # Switch router to geofencing
    cc._coordinator._router._llm.chat.completions.create.side_effect = \
        _make_mock_llm(["geofencing"]).chat.completions.create.side_effect

    # Turn 2: no location provided
    result = cc.process_turn(
        session_id=sid,
        query_text="Is this inside the EEZ?",
    )

    assert isinstance(result, CoordinatorResponse)
    assert result.geofencing is not None
    assert result.geofencing.geofence_status == "SAFE"


# ---------------------------------------------------------------------------
# TEST 7 — Explicit new location overrides stored location
# ---------------------------------------------------------------------------
def test_7_explicit_new_location_overrides_stored():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()

    # Turn 1: store 19.0, 71.0
    cc.process_turn(
        session_id=sid,
        query_text="Inside EEZ?",
        latitude=19.0,
        longitude=71.0,
    )

    # Turn 2: provide completely different location
    cc.process_turn(
        session_id=sid,
        query_text="Inside EEZ?",
        latitude=18.0,
        longitude=65.0,
    )

    state = cc.get_state(sid)
    assert state.latitude == 18.0
    assert state.longitude == 65.0


# ---------------------------------------------------------------------------
# TEST 8 — Explicit new date overrides stored date
# ---------------------------------------------------------------------------
def test_8_explicit_new_date_overrides_stored():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat"]),
            live_mode=False,
        )

    sid = _fresh_session_id()

    cc.process_turn(
        session_id=sid,
        query_text="Habitat?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    cc.process_turn(
        session_id=sid,
        query_text="Habitat?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-11-01",
    )

    state = cc.get_state(sid)
    assert state.date_str == "2025-11-01"


# ---------------------------------------------------------------------------
# TEST 9 — Request without location and no prior state → clarification
# ---------------------------------------------------------------------------
def test_9_no_location_no_state_returns_clarification():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat"]),
            live_mode=False,
        )

    sid = _fresh_session_id()

    # No lat/lon in request, no prior state
    result = cc.process_turn(
        session_id=sid,
        query_text="How is the habitat?",
        # latitude and longitude are None
        date_str="2025-10-15",
    )

    assert isinstance(result, ClarificationRequired)
    assert result.needs_clarification is True
    assert "latitude" in result.missing or "longitude" in result.missing


# ---------------------------------------------------------------------------
# TEST 10 — Reset removes conversation context
# ---------------------------------------------------------------------------
def test_10_reset_removes_context():
    manager = ConversationStateManager()
    sid = _fresh_session_id()
    manager.create_session(sid)
    manager.update_state(sid, latitude=19.5, longitude=70.5, date_str="2025-10-15")

    manager.reset_session(sid)

    state = manager.get_state(sid)
    assert state.latitude is None
    assert state.longitude is None
    assert state.date_str is None
    assert state.last_result is None


# ---------------------------------------------------------------------------
# TEST 11 — After reset, old location is NOT reused
# ---------------------------------------------------------------------------
def test_11_after_reset_old_location_not_reused():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()

    # Store a location
    cc.process_turn(session_id=sid, query_text="EEZ?", latitude=19.0, longitude=71.0)

    # Reset the session
    cc.reset_session(sid)

    # Follow-up without coordinates — must NOT reuse old location
    result = cc.process_turn(session_id=sid, query_text="Inside EEZ?")

    assert isinstance(result, ClarificationRequired)
    assert "latitude" in result.missing or "longitude" in result.missing


# ---------------------------------------------------------------------------
# TEST 12 — Two sessions are completely isolated
# ---------------------------------------------------------------------------
def test_12_two_sessions_are_isolated():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid_a = _fresh_session_id()
    sid_b = _fresh_session_id()

    # Session A stores 19.5, 70.5
    cc.process_turn(session_id=sid_a, query_text="EEZ?", latitude=19.5, longitude=70.5)

    # Session B should have no stored coordinates
    state_b = cc.get_state(sid_b)  # auto-created inside process_turn below
    if state_b is None:
        cc.create_session(sid_b)
        state_b = cc.get_state(sid_b)

    assert state_b.latitude is None
    assert state_b.longitude is None

    # A request on B without coords must ask for clarification
    result_b = cc.process_turn(session_id=sid_b, query_text="Inside EEZ?")
    assert isinstance(result_b, ClarificationRequired)


# ---------------------------------------------------------------------------
# TEST 13 — Latest structured agent results are preserved in state
# ---------------------------------------------------------------------------
def test_13_latest_agent_results_preserved():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    cc.process_turn(session_id=sid, query_text="EEZ?", latitude=19.0, longitude=71.0)

    state = cc.get_state(sid)
    assert state.last_result is not None
    assert state.last_result.geofencing is not None
    # Verify the deterministic geofence status is preserved
    assert state.last_result.geofencing.geofence_status == "SAFE"


# ---------------------------------------------------------------------------
# TEST 14 — State does NOT store hallucinated LLM values
# ---------------------------------------------------------------------------
def test_14_state_does_not_store_llm_hallucinations():
    """
    The state only stores lat/lon/date/capabilities/structured results,
    all of which come from deterministic sources. The LLM's free-text
    narrative fields are in the CoordinatorResponse but are NOT used to
    make decisions, update coordinates, or override engine outputs.
    """
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    cc.process_turn(session_id=sid, query_text="EEZ?", latitude=19.0, longitude=71.0)

    state = cc.get_state(sid)
    # State only has numeric/structured values — no LLM text fields
    assert isinstance(state.latitude, float)
    assert isinstance(state.longitude, float)
    assert isinstance(state.last_capabilities, list)
    # No "fisherman_advice" or other narrative on the state object
    assert not hasattr(state, "fisherman_advice")
    assert not hasattr(state, "geofence_narrative")


# ---------------------------------------------------------------------------
# TEST 15 — Deterministic agent results cannot be overridden by LLM text
# ---------------------------------------------------------------------------
def test_15_deterministic_results_cannot_be_overridden_by_llm():
    """
    Even if the LLM narrative says 'SAFE', the engine result for OUTSIDE_EEZ
    coordinates must remain OUTSIDE_EEZ in the structured response.
    """
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    result = cc.process_turn(
        session_id=sid,
        query_text="Inside EEZ?",
        latitude=18.0,
        longitude=65.0,
    )

    # Engine says OUTSIDE_EEZ — LLM narrative cannot change this
    assert isinstance(result, CoordinatorResponse)
    assert result.geofencing.geofence_status == "OUTSIDE_EEZ"
    assert result.geofencing.inside_indian_eez is False


# ---------------------------------------------------------------------------
# TEST 16 — Coordinator dynamic routing still works through conversation layer
# ---------------------------------------------------------------------------
def test_16_coordinator_routing_still_works_through_conversation_layer():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat", "weather"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    result = cc.process_turn(
        session_id=sid,
        query_text="Is this a good and safe place?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    assert isinstance(result, CoordinatorResponse)
    assert result.habitat is not None
    assert result.weather is not None
    assert result.geofencing is None


# ---------------------------------------------------------------------------
# TEST 17 — Single-capability: Habitat only
# ---------------------------------------------------------------------------
def test_17_habitat_only_routing():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    result = cc.process_turn(
        session_id=sid,
        query_text="How is the habitat?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    assert isinstance(result, CoordinatorResponse)
    assert result.habitat is not None
    assert result.weather is None
    assert result.geofencing is None
    assert "fishing_habitat" in result.routing.agents_invoked


# ---------------------------------------------------------------------------
# TEST 18 — Single-capability: Weather only
# ---------------------------------------------------------------------------
def test_18_weather_only_routing():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["weather"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    result = cc.process_turn(
        session_id=sid,
        query_text="Is it safe to go out?",
        latitude=15.0,
        longitude=68.0,
        date_str="2025-10-01",
    )

    assert isinstance(result, CoordinatorResponse)
    assert result.weather is not None
    assert result.habitat is None
    assert result.geofencing is None
    assert result.weather.risk_level == "Very High Risk"


# ---------------------------------------------------------------------------
# TEST 19 — Single-capability: Geofencing only
# ---------------------------------------------------------------------------
def test_19_geofencing_only_routing():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    result = cc.process_turn(
        session_id=sid,
        query_text="Are we inside the Indian EEZ?",
        latitude=18.0,
        longitude=65.0,
    )

    assert isinstance(result, CoordinatorResponse)
    assert result.geofencing is not None
    assert result.geofencing.geofence_status == "OUTSIDE_EEZ"
    assert result.habitat is None
    assert result.weather is None


# ---------------------------------------------------------------------------
# TEST 20 — Combined routing works through the conversation layer
# ---------------------------------------------------------------------------
def test_20_combined_routing_still_works():
    with patch.dict(os.environ, {"GROQ_API_KEY": "mock-key", "LLM_PROVIDER": "groq"}):
        cc = ConversationCoordinator(
            llm_client=_make_mock_llm(["habitat", "weather", "geofencing"]),
            live_mode=False,
        )

    sid = _fresh_session_id()
    result = cc.process_turn(
        session_id=sid,
        query_text="Is this a good, safe place to fish inside the EEZ?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )

    assert isinstance(result, CoordinatorResponse)
    assert result.habitat is not None
    assert result.weather is not None
    assert result.geofencing is not None
    assert len(result.routing.agents_invoked) == 3


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
