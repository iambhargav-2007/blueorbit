"""
test_step17a_performance.py

Automated tests for Step 17A:
- Conversational message routing (e.g. 'Heyy', 'Hello', 'Thanks') without provider/agent overhead.
- Elimination of redundant LLM router calls.
- Concurrent extraction and in-memory observation caching in LiveMarineProvider.
- Anti-fallback preservation (live failures return explicit errors, never historical cache).
"""

import time
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from app.conversation.conversation_coordinator import ConversationCoordinator
from app.coordinator.schemas import CoordinatorResponse
from app.providers.live_marine_provider import LiveMarineProvider
from app.providers.smart_marine_router import SmartMarineRouter
from app.services.temporal_resolver import TemporalMode


# ---------------------------------------------------------------------------
# Test 1 & 2: Conversational Messages ("Heyy", "Thanks")
# ---------------------------------------------------------------------------

def test_1_simple_heyy_does_not_invoke_marine_providers():
    """
    Verifies that 'Heyy' returns instantly as a conversation response,
    without calling the LLM router, domain agents, or any marine data providers.
    """
    coord = ConversationCoordinator(live_mode=False)

    with patch.object(coord._coordinator._router, "get_capabilities") as mock_router, \
         patch.object(coord._coordinator._habitat_agent, "run") as mock_hab, \
         patch.object(coord._coordinator._weather_agent, "run") as mock_wea, \
         patch.object(coord._coordinator._geofencing_agent, "run") as mock_geo:

        t0 = time.time()
        res = coord.process_turn(session_id="test-conv-1", query_text="Heyy")
        elapsed = time.time() - t0

        # Assertions
        assert isinstance(res, CoordinatorResponse)
        assert res.success is True
        assert res.conversation_response is not None
        assert "Blue Orbit" in res.conversation_response or "Hello" in res.conversation_response
        assert len(res.routing.agents_invoked) == 0
        assert len(res.errors) == 0

        # Provider/agent zero-invocation verification
        mock_router.assert_not_called()
        mock_hab.assert_not_called()
        mock_wea.assert_not_called()
        mock_geo.assert_not_called()

        # Must be practically instantaneous (< 50ms)
        assert elapsed < 0.05, f"Expected < 50ms, took {elapsed * 1000:.1f}ms"


def test_2_simple_thanks_returns_friendly_acknowledgment():
    """Verifies that 'Thank you so much' returns an immediate friendly acknowledgment."""
    coord = ConversationCoordinator(live_mode=False)

    res = coord.process_turn(session_id="test-conv-2", query_text="Thank you so much")
    assert isinstance(res, CoordinatorResponse)
    assert res.success is True
    assert res.conversation_response is not None
    assert "welcome" in res.conversation_response.lower()


# ---------------------------------------------------------------------------
# Test 3: LLM Router Called At Most Once (No Redundant Second Call)
# ---------------------------------------------------------------------------

def test_3_router_called_at_most_once_for_domain_queries():
    """
    Verifies that domain queries invoke the LLM router exactly once,
    with capabilities forwarded to OrcaCoordinator rather than re-routed.
    """
    coord = ConversationCoordinator(live_mode=False)

    with patch.object(coord._coordinator._router, "get_capabilities", return_value=["habitat"]) as mock_router:
        res = coord.process_turn(
            session_id="test-router-single",
            query_text="What is the habitat suitability?",
            latitude=19.5,
            longitude=70.5,
            date_str="2025-10-15"
        )
        assert res.success is True
        # Router must be called exactly once
        assert mock_router.call_count == 1


# ---------------------------------------------------------------------------
# Test 4: Live Marine Provider Concurrent Extraction
# ---------------------------------------------------------------------------

class MockLiveDataset:
    def __init__(self, val_dict):
        self.val_dict = val_dict
        self.dims = ['time', 'depth', 'latitude', 'longitude']
        self.coords = ['depth']
        self.variables = list(val_dict.keys())

    def sel(self, **kwargs):
        return MockLivePoint(self.val_dict)


class MockLivePoint:
    def __init__(self, val_dict):
        self.val_dict = val_dict
        self.latitude = MagicMock(values=val_dict.get('latitude', 19.5))
        self.longitude = MagicMock(values=val_dict.get('longitude', 70.5))
        if 'thetao' in val_dict:
            self.thetao = MagicMock(values=val_dict['thetao'])
        if 'chl' in val_dict:
            self.chl = MagicMock(values=val_dict['chl'])
        self.variables = list(val_dict.keys())


def test_4_live_marine_provider_concurrent_extraction():
    """Verifies that LiveMarineProvider concurrent extraction produces correct values."""
    with patch('app.providers.live_marine_provider.COPERNICUS_AVAILABLE', True):
        provider = LiveMarineProvider()

        with patch('app.providers.live_marine_provider.copernicusmarine.open_dataset') as mock_open:
            mock_open.side_effect = [
                MockLiveDataset({'thetao': 28.36, 'latitude': 19.5, 'longitude': 70.5}),
                MockLiveDataset({'chl': 0.244, 'latitude': 19.5, 'longitude': 70.5})
            ]

            res = provider.get_marine_data(19.5, 70.5, "2026-09-01")

            assert res["success"] is True
            assert res["temperature"] == 28.36
            assert res["chlorophyll"] == 0.244
            assert res["matched_latitude"] == 19.5
            assert res["matched_longitude"] == 70.5


# ---------------------------------------------------------------------------
# Test 5: Live Marine Provider In-Memory Point Cache
# ---------------------------------------------------------------------------

def test_5_live_marine_provider_in_memory_cache():
    """Verifies that repeat queries for the same coordinate/date hit in-memory cache."""
    with patch('app.providers.live_marine_provider.COPERNICUS_AVAILABLE', True):
        provider = LiveMarineProvider()

        with patch('app.providers.live_marine_provider.copernicusmarine.open_dataset') as mock_open:
            mock_open.side_effect = [
                MockLiveDataset({'thetao': 28.36, 'latitude': 19.5, 'longitude': 70.5}),
                MockLiveDataset({'chl': 0.244, 'latitude': 19.5, 'longitude': 70.5})
            ]

            # Turn 1: initial fetch
            res1 = provider.get_marine_data(19.5, 70.5, "2026-09-01")
            assert res1["success"] is True
            assert mock_open.call_count == 2

            # Turn 2: repeat query in same session
            res2 = provider.get_marine_data(19.5, 70.5, "2026-09-01")
            assert res2["success"] is True
            assert res2["temperature"] == res1["temperature"]
            # open_dataset must NOT be called again
            assert mock_open.call_count == 2


# ---------------------------------------------------------------------------
# Test 6: Anti-Fallback Preservation (Strict Separation)
# ---------------------------------------------------------------------------

def test_6_live_failure_never_falls_back_to_historical_cache():
    """
    Verifies that when LiveMarineProvider fails or times out,
    SmartMarineRouter returns INSUFFICIENT_DATA and never touches historical cache.
    """
    mock_live = MagicMock()
    mock_live.get_marine_data.return_value = {
        "success": False,
        "error": "Copernicus server unavailable.",
        "requested": {"lat": 19.5, "lon": 70.5, "date": "2026-09-01"}
    }

    mock_hist = MagicMock()

    router = SmartMarineRouter(
        live_provider=mock_live,
        historical_provider=mock_hist,
    )

    res = router.get_marine_data(19.5, 70.5, "2026-09-01", temporal_mode=TemporalMode.LIVE)

    assert res["success"] is False
    assert res["code"] == "INSUFFICIENT_DATA"
    assert "Copernicus server unavailable" in res["error"]
    # Historical provider must NEVER have been called as fallback
    mock_hist.get_marine_data.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: Multi-Turn Conversation Preserves Location Across Greetings
# ---------------------------------------------------------------------------

def test_7_conversation_greeting_preserves_established_location():
    """
    Verifies that asking a location query, then greeting the assistant,
    preserves the session coordinate state.
    """
    coord = ConversationCoordinator(live_mode=False)
    session_id = "test-greeting-state"

    with patch.object(coord._coordinator._router, "get_capabilities", return_value=["habitat"]):
        # Turn 1: Establish location
        res1 = coord.process_turn(
            session_id=session_id,
            query_text="Habitat suitability?",
            latitude=19.5,
            longitude=70.5,
            date_str="2025-10-15"
        )
        assert res1.success is True

    # Turn 2: Greeting
    res2 = coord.process_turn(
        session_id=session_id,
        query_text="Heyy"
    )
    assert res2.success is True
    assert res2.conversation_response is not None

    # State still has coordinates
    state = coord.get_state(session_id)
    assert state.latitude == 19.5
    assert state.longitude == 70.5
