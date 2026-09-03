"""
test_step16_smart_routing.py

Dedicated test suite for Step 16: Smart Data Routing in Blue Orbit (ORCA).
Verifies:
  - TemporalContextResolver deterministic classification (LIVE, HISTORICAL, UNSUPPORTED_FUTURE, COMPARISON)
  - SmartMarineRouter provider routing (Live vs Historical vs Unsupported Future)
  - Strict absence of temporal mixing
  - Deterministic authority over LLM outputs
  - Multi-turn conversation state location preservation & temporal context switching
  - Comparison requests with dual independent paths
"""

import os
import sys
import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend directory is in path
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

os.environ.setdefault("GROQ_API_KEY", "mock-groq-key")
os.environ.setdefault("LLM_PROVIDER", "groq")

from app.services.temporal_resolver import (
    TemporalContextResolver,
    TemporalMode,
    TemporalResolution,
)
from app.providers.smart_marine_router import SmartMarineRouter
from app.providers.base_marine_provider import BaseMarineProvider
from app.tools.habitat_tool import HabitatTool
from app.agents.fishing_agent import FishingHabitatAgent
from app.conversation.conversation_coordinator import ConversationCoordinator
from app.conversation.state_manager import ConversationStateManager


# Fixed reference date for testing: 2026-09-03
FIXED_REF_DATE = date(2026, 9, 3)


def _make_mock_llm(capabilities=None, scientific_text="Mock scientific text"):
    """Helper to create a mock Groq client."""
    caps = capabilities or ["habitat"]
    def side_effect(*args, **kwargs):
        messages = kwargs.get("messages", [])
        sys_msg = messages[0]["content"] if messages else ""
        if "Intent Router" in sys_msg:
            content = json.dumps({"requested_capabilities": caps})
        else:
            content = json.dumps({
                "scientific_explanation": scientific_text,
                "fisherman_advice": "Mock advice for fishermen."
            })
        m_msg = MagicMock(content=content)
        m_choice = MagicMock(message=m_msg)
        m_comp = MagicMock(choices=[m_choice])
        return m_comp

    mock = MagicMock()
    mock.chat.completions.create.side_effect = side_effect
    return mock


# ---------------------------------------------------------------------------
# TEST 1 — Input: "habitat suitability today" -> Expected: LIVE
# ---------------------------------------------------------------------------
def test_1_route_today_resolves_live():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    res = resolver.resolve(query_text="habitat suitability today")
    assert res.mode == TemporalMode.LIVE
    assert res.date_str == "2026-09-03"


# ---------------------------------------------------------------------------
# TEST 2 — Input: "current habitat suitability" -> Expected: LIVE
# ---------------------------------------------------------------------------
def test_2_route_current_resolves_live():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    res = resolver.resolve(query_text="current habitat suitability")
    assert res.mode == TemporalMode.LIVE
    assert res.date_str == "2026-09-03"


# ---------------------------------------------------------------------------
# TEST 3 — Input: "habitat suitability right now" -> Expected: LIVE
# ---------------------------------------------------------------------------
def test_3_route_right_now_resolves_live():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    res = resolver.resolve(query_text="habitat suitability right now")
    assert res.mode == TemporalMode.LIVE
    assert res.date_str == "2026-09-03"


# ---------------------------------------------------------------------------
# TEST 4 — Input: "habitat suitability on 2025-10-15" -> Expected: HISTORICAL
# ---------------------------------------------------------------------------
def test_4_route_explicit_past_date_resolves_historical():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    res = resolver.resolve(query_text="habitat suitability on 2025-10-15")
    assert res.mode == TemporalMode.HISTORICAL
    assert res.date_str == "2025-10-15"


# ---------------------------------------------------------------------------
# TEST 5 — Explicit date overrides current context
# ---------------------------------------------------------------------------
def test_5_explicit_date_overrides_current_context():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    # Even if query might say "what is the habitat", explicit date parameter takes priority
    res = resolver.resolve(
        query_text="what is the habitat suitability?",
        explicit_date_str="2025-10-15"
    )
    assert res.mode == TemporalMode.HISTORICAL
    assert res.date_str == "2025-10-15"


# ---------------------------------------------------------------------------
# TEST 6 — Future date: "habitat suitability on 2027-01-01" -> UNSUPPORTED_FUTURE
# ---------------------------------------------------------------------------
def test_6_future_date_rejected_as_unsupported():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    res = resolver.resolve(query_text="habitat suitability on 2027-01-01")
    assert res.mode == TemporalMode.UNSUPPORTED_FUTURE
    assert res.date_str == "2027-01-01"

    # Verify router explicitly rejects without calling providers
    mock_live = MagicMock()
    mock_hist = MagicMock()
    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )
    output = router.get_marine_data(lat=19.5, lon=70.5, date_str="2027-01-01")
    assert output["success"] is False
    assert output["code"] == "UNSUPPORTED_FUTURE"
    assert "future" in output["error"].lower()
    mock_live.get_marine_data.assert_not_called()
    mock_hist.get_marine_data.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 7 — Historical date exists -> Historical provider called
# ---------------------------------------------------------------------------
def test_7_historical_date_exists_calls_historical_provider():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()
    mock_hist.get_marine_data.return_value = {
        "success": True,
        "temperature": 27.5,
        "chlorophyll": 0.5,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2025-10-15",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )

    result = router.get_marine_data(lat=19.5, lon=70.5, date_str="2025-10-15")
    assert result["success"] is True
    assert result["temperature"] == 27.5
    assert result["chlorophyll"] == 0.5
    assert result["temporal_mode"] == "HISTORICAL"
    mock_hist.get_marine_data.assert_called_once_with(lat=19.5, lon=70.5, date_str="2025-10-15")
    mock_live.get_marine_data.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 8 — Historical date does not exist -> INSUFFICIENT_DATA (No fabrication)
# ---------------------------------------------------------------------------
def test_8_historical_date_missing_returns_insufficient_data():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()
    # When date is outside cache range
    mock_hist.get_marine_data.return_value = {
        "success": False,
        "error": "Date 2024-01-01 is outside the available historical range.",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )

    result = router.get_marine_data(lat=19.5, lon=70.5, date_str="2024-01-01")
    assert result["success"] is False
    assert result["code"] == "INSUFFICIENT_DATA"
    assert "unavailable" in result["error"].lower() or "outside" in result["error"].lower()
    mock_live.get_marine_data.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 9 — Live provider unavailable -> Explicit error/insufficient data (No cache fallback)
# ---------------------------------------------------------------------------
def test_9_live_provider_unavailable_returns_error_no_fallback():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()
    mock_live.get_marine_data.return_value = {
        "success": False,
        "error": "Copernicus API network timeout",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )

    result = router.get_marine_data(
        lat=19.5,
        lon=70.5,
        date_str="2026-09-03",
        temporal_mode=TemporalMode.LIVE
    )
    assert result["success"] is False
    assert "timeout" in result["error"].lower() or "failed" in result["error"].lower()
    # CRITICAL: historical provider must NEVER be called as fallback for a live failure
    mock_hist.get_marine_data.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 10 — Verify live data is not mixed with historical chlorophyll
# ---------------------------------------------------------------------------
def test_10_live_partial_data_returns_insufficient_data_no_mixing():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()
    # Live temperature exists, live chlorophyll is None/masked
    mock_live.get_marine_data.return_value = {
        "success": True,
        "temperature": 28.5,
        "chlorophyll": None,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2026-09-03",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )
    tool = HabitatTool(router=router)

    result = tool.get_habitat_suitability(
        latitude=19.5,
        longitude=70.5,
        date_str="2026-09-03",
        temporal_mode=TemporalMode.LIVE
    )

    # Result must indicate Insufficient Data due to missing chlorophyll
    assert result["success"] is True
    assert result["fishing_potential"] == "Insufficient Data"
    assert result["chlorophyll_mg_m3"] is None
    # No historical chlorophyll was substituted
    mock_hist.get_marine_data.assert_not_called()


# ---------------------------------------------------------------------------
# TEST 11 — Comparison request: "Compare today with 2025-10-15."
# ---------------------------------------------------------------------------
def test_11_comparison_invokes_both_providers_independently():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()

    mock_live.get_marine_data.return_value = {
        "success": True,
        "temperature": 28.5,
        "chlorophyll": 0.8,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2026-09-03",
    }
    mock_hist.get_marine_data.return_value = {
        "success": True,
        "temperature": 26.5,
        "chlorophyll": 0.3,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2025-10-15",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )
    tool = HabitatTool(router=router)

    comp = tool.compare_habitat_suitability(
        latitude=19.5,
        longitude=70.5,
        historical_date="2025-10-15",
        current_date="2026-09-03"
    )

    assert comp["success"] is True
    assert comp["type"] == "comparison"
    mock_hist.get_marine_data.assert_called_once_with(
        lat=19.5, lon=70.5, date_str="2025-10-15"
    )
    mock_live.get_marine_data.assert_called_once_with(
        lat=19.5, lon=70.5, date_str="2026-09-03"
    )


# ---------------------------------------------------------------------------
# TEST 12 — Comparison must preserve independent results
# ---------------------------------------------------------------------------
def test_12_comparison_preserves_independent_results():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()

    mock_live.get_marine_data.return_value = {
        "success": True,
        "temperature": 28.8,
        "chlorophyll": 1.2,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2026-09-03",
    }
    mock_hist.get_marine_data.return_value = {
        "success": True,
        "temperature": 26.0,
        "chlorophyll": 0.2,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2025-10-15",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )
    tool = HabitatTool(router=router)

    agent = FishingHabitatAgent(llm_client=_make_mock_llm())
    agent._tool = tool

    temp_res = TemporalResolution(
        mode=TemporalMode.COMPARISON,
        historical_date="2025-10-15",
        current_date="2026-09-03",
        is_comparison=True,
    )

    response = agent.run(
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15 vs 2026-09-03",
        query_text="Compare today with 2025-10-15",
        temporal_resolution=temp_res
    )

    assert response.success is True
    assert response.comparison is not None
    assert response.comparison.type == "comparison"
    # Historical result is independent
    assert response.comparison.historical.date == "2025-10-15"
    assert response.comparison.historical.result["temperature_c"] == 26.0
    assert response.comparison.historical.result["chlorophyll_mg_m3"] == 0.2

    # Current result is independent
    assert response.comparison.current.date == "2026-09-03"
    assert response.comparison.current.result["temperature_c"] == 28.8
    assert response.comparison.current.result["chlorophyll_mg_m3"] == 1.2


# ---------------------------------------------------------------------------
# TEST 13 — LLM contradiction test
# ---------------------------------------------------------------------------
def test_13_llm_contradiction_deterministic_authority():
    resolver = TemporalContextResolver(reference_date=FIXED_REF_DATE)
    mock_live = MagicMock()
    mock_hist = MagicMock()

    mock_live.get_marine_data.return_value = {
        "success": True,
        "temperature": 28.5,
        "chlorophyll": 0.8,
        "matched_latitude": 19.5,
        "matched_longitude": 70.5,
        "requested_date": "2026-09-03",
    }

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        temporal_resolver=resolver,
    )
    tool = HabitatTool(router=router)

    # Mock the LLM to claim "Use historical data from October 2025"
    mock_llm = _make_mock_llm(scientific_text="Use historical data from October 2025.")
    agent = FishingHabitatAgent(llm_client=mock_llm)
    agent._tool = tool

    # User asks for today's conditions
    temp_res = resolver.resolve("What is the habitat suitability today?")
    assert temp_res.mode == TemporalMode.LIVE

    res = agent.run(
        latitude=19.5,
        longitude=70.5,
        date_str=temp_res.date_str,
        query_text="What is the habitat suitability today?",
        temporal_resolution=temp_res
    )

    # Deterministic router used LIVE provider
    mock_live.get_marine_data.assert_called_once()
    mock_hist.get_marine_data.assert_not_called()
    assert res.temporal_mode == "LIVE"
    assert res.environmental_summary.temperature_c == 28.5


# ---------------------------------------------------------------------------
# TEST 14 — Conversation follow-up: today -> what about 2025-10-15?
# ---------------------------------------------------------------------------
def test_14_follow_up_preserves_location_switches_to_historical():
    coord = ConversationCoordinator(llm_client=_make_mock_llm(["habitat"]))

    # Mock router in habitat tool to inspect provider calls
    mock_live = MagicMock()
    mock_hist = MagicMock()
    mock_live.get_marine_data.return_value = {
        "success": True, "temperature": 28.5, "chlorophyll": 0.8,
        "matched_latitude": 19.5, "matched_longitude": 70.5, "requested_date": FIXED_REF_DATE.strftime("%Y-%m-%d")
    }
    mock_hist.get_marine_data.return_value = {
        "success": True, "temperature": 27.0, "chlorophyll": 0.4,
        "matched_latitude": 19.5, "matched_longitude": 70.5, "requested_date": "2025-10-15"
    }

    smart_router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        reference_date=FIXED_REF_DATE
    )
    coord._coordinator._habitat_agent._tool._router = smart_router

    # Turn 1: "habitat suitability at 19.5,70.5 today"
    turn1 = coord.process_turn(
        session_id="test-follow-up-1",
        query_text="habitat suitability at 19.5, 70.5 today",
        latitude=19.5,
        longitude=70.5,
    )
    assert turn1.success is True
    assert turn1.request["latitude"] == 19.5
    assert turn1.request["longitude"] == 70.5
    mock_live.get_marine_data.assert_called_once()

    # Turn 2: "what about 2025-10-15?" (no location provided)
    turn2 = coord.process_turn(
        session_id="test-follow-up-1",
        query_text="what about 2025-10-15?",
    )
    assert turn2.success is True
    # Preserves coordinates from Turn 1!
    assert turn2.request["latitude"] == 19.5
    assert turn2.request["longitude"] == 70.5
    assert turn2.request["date_str"] == "2025-10-15"
    mock_hist.get_marine_data.assert_called_once()


# ---------------------------------------------------------------------------
# TEST 15 — Conversation follow-up: 2025-10-15 -> what about today?
# ---------------------------------------------------------------------------
def test_15_follow_up_preserves_location_switches_to_live():
    coord = ConversationCoordinator(llm_client=_make_mock_llm(["habitat"]))

    mock_live = MagicMock()
    mock_hist = MagicMock()
    mock_live.get_marine_data.return_value = {
        "success": True, "temperature": 28.5, "chlorophyll": 0.8,
        "matched_latitude": 19.5, "matched_longitude": 70.5, "requested_date": FIXED_REF_DATE.strftime("%Y-%m-%d")
    }
    mock_hist.get_marine_data.return_value = {
        "success": True, "temperature": 27.0, "chlorophyll": 0.4,
        "matched_latitude": 19.5, "matched_longitude": 70.5, "requested_date": "2025-10-15"
    }

    smart_router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
        reference_date=FIXED_REF_DATE
    )
    coord._coordinator._habitat_agent._tool._router = smart_router

    # Turn 1: "habitat suitability at 19.5,70.5 on 2025-10-15"
    turn1 = coord.process_turn(
        session_id="test-follow-up-2",
        query_text="habitat suitability at 19.5, 70.5 on 2025-10-15",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )
    assert turn1.success is True
    assert turn1.request["date_str"] == "2025-10-15"
    mock_hist.get_marine_data.assert_called_once()

    # Turn 2: "what about today?"
    turn2 = coord.process_turn(
        session_id="test-follow-up-2",
        query_text="what about today?",
    )
    assert turn2.success is True
    # Preserves coordinates from Turn 1!
    assert turn2.request["latitude"] == 19.5
    assert turn2.request["longitude"] == 70.5
    # Switches to today's live date
    assert turn2.request["date_str"] == FIXED_REF_DATE.strftime("%Y-%m-%d") or turn2.habitat.temporal_mode == "LIVE"
    mock_live.get_marine_data.assert_called_once()
