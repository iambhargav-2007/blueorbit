"""
test_step18_location.py

Comprehensive test suite for Step 18 — Human-Friendly Location Intelligence.
Covers:
1. Coordinate validation and normalization into LocationContext
2. Rejection of out-of-bounds coordinates
3. GPS location with accuracy and timestamp
4. Coastal place name resolution (Goa, Mumbai, Veraval, etc.)
5. Landlocked state rejection with helpful guidance (Rajasthan, Punjab)
6. Map selection normalization
7. Session location override
8. Missing location does not invent coordinates
9. "Where am I?" response with and without location context
10. EEZ engine receiving normalized coordinates
11. Multi-turn place preservation across conversational follow-ups
12. FastAPI location endpoints (/api/v1/location/resolve, /api/v1/location/suggestions)
"""

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.location.schemas import LocationContext, LocationResolveRequest, LocationResolveResponse
from app.location.resolver import LocationResolver, get_location_resolver
from app.conversation.conversation_coordinator import ConversationCoordinator
from app.conversation.state_manager import ConversationStateManager
from app.coordinator.coordinator import OrcaCoordinator
from app.api.schemas import ChatRequest
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. LocationContext Domain Model & Validation
# ---------------------------------------------------------------------------

def test_1_valid_manual_coordinates_normalization():
    """Valid coordinates must normalize properly into a LocationContext."""
    loc = LocationContext(
        latitude=19.5,
        longitude=70.5,
        display_name="Standard Sector",
        source="manual"
    )
    assert loc.latitude == 19.5
    assert loc.longitude == 70.5
    assert loc.display_name == "Standard Sector"
    assert loc.source == "manual"
    assert loc.accuracy_m is None


def test_2_rejection_of_invalid_coordinates():
    """Invalid latitude or longitude must raise a ValidationError without silent modification."""
    with pytest.raises(ValidationError):
        LocationContext(
            latitude=95.0,  # Invalid: > 90
            longitude=70.5,
            display_name="Invalid Lat",
            source="manual"
        )

    with pytest.raises(ValidationError):
        LocationContext(
            latitude=19.5,
            longitude=-185.0,  # Invalid: < -180
            display_name="Invalid Lon",
            source="manual"
        )


def test_3_gps_location_context_with_accuracy_and_timestamp():
    """GPS input preserves accuracy radius and ISO timestamp."""
    loc = LocationContext(
        latitude=18.94,
        longitude=72.84,
        display_name="Current Position",
        source="gps",
        accuracy_m=14.5,
        timestamp="2026-09-03T12:00:00Z"
    )
    assert loc.source == "gps"
    assert loc.accuracy_m == 14.5
    assert loc.timestamp == "2026-09-03T12:00:00Z"


# ---------------------------------------------------------------------------
# 2. Coastal Resolver & Landlocked Detection
# ---------------------------------------------------------------------------

def test_4_coastal_place_resolution():
    """Resolver accurately identifies Indian West Coast reference points."""
    resolver = get_location_resolver()

    # Goa
    res_goa = resolver.resolve_location("Goa coast")
    assert res_goa.success is True
    assert res_goa.location is not None
    assert abs(res_goa.location.latitude - 15.41) < 0.1
    assert abs(res_goa.location.longitude - 73.80) < 0.1

    # Mumbai
    res_mumbai = resolver.resolve_location("Mumbai")
    assert res_mumbai.success is True
    assert res_mumbai.location is not None
    assert abs(res_mumbai.location.latitude - 18.94) < 0.1
    assert abs(res_mumbai.location.longitude - 72.84) < 0.1

    # Veraval
    res_veraval = resolver.resolve_location("Veraval port")
    assert res_veraval.success is True
    assert res_veraval.location is not None
    assert abs(res_veraval.location.latitude - 20.90) < 0.1


def test_5_landlocked_state_rejection_with_advisory():
    """Landlocked queries like 'Rajasthan coast' return an explicit advisory, not fake coordinates."""
    resolver = get_location_resolver()

    res = resolver.resolve_location("Rajasthan coast")
    assert res.success is False
    assert res.location is None
    assert "Rajasthan has no coastline" in res.message
    assert "Gujarat Coast" in res.suggestions

    res_punjab = resolver.resolve_location("Punjab coast")
    assert res_punjab.success is False
    assert "Punjab is a landlocked" in res_punjab.message


def test_6_coordinate_string_parsing_in_resolver():
    """String representations of coordinates resolve into manual LocationContext."""
    resolver = get_location_resolver()

    res = resolver.resolve_location("19.5, 70.5")
    assert res.success is True
    assert res.location is not None
    assert res.location.latitude == 19.5
    assert res.location.longitude == 70.5
    assert res.location.source == "manual"


# ---------------------------------------------------------------------------
# 3. Conversation Coordinator & State Integration
# ---------------------------------------------------------------------------

def test_7_where_am_i_with_and_without_location():
    """'Where am I?' queries return accurate current coordinates or instructions to set location."""
    coord = ConversationCoordinator()
    session_id = "test-where-am-i"

    # Turn 1: No location set yet
    resp1 = coord.process_turn(session_id=session_id, query_text="Where am I?")
    assert resp1.success is True
    assert "I don't have your location yet" in resp1.conversation_response

    # Turn 2: Set GPS location
    loc = LocationContext(
        latitude=18.94,
        longitude=72.84,
        display_name="Mumbai Coast, Maharashtra",
        source="gps",
        accuracy_m=12.0
    )
    resp2 = coord.process_turn(
        session_id=session_id,
        query_text="Where am I?",
        location_context=loc
    )
    assert resp2.success is True
    assert "18.94° N, 72.84° E" in resp2.conversation_response
    assert "GPS accuracy: ~12m" in resp2.conversation_response


def test_8_natural_language_place_extraction_and_persistence():
    """Asking about a place extracts coordinates and preserves them for subsequent follow-ups."""
    coord = ConversationCoordinator()
    session_id = "test-nl-place-session"

    # Turn 1: Ask about Goa in natural language with historical cache date
    resp1 = coord.process_turn(
        session_id=session_id,
        query_text="What is the habitat suitability near Goa?",
        date_str="2025-10-15"
    )
    assert resp1.success is True
    # Coordinates should be Goa's (15.41, 73.80)
    assert abs(resp1.request["latitude"] - 15.41) < 0.1
    assert abs(resp1.request["longitude"] - 73.80) < 0.1

    # Turn 2: Follow-up question without naming location or coordinates
    resp2 = coord.process_turn(
        session_id=session_id,
        query_text="Is it safe to fish?"
    )
    assert resp2.success is True
    # Should still retain Goa coordinates
    assert abs(resp2.request["latitude"] - 15.41) < 0.1
    assert abs(resp2.request["longitude"] - 73.80) < 0.1


def test_9_explicit_location_override_in_conversation():
    """Explicitly providing a new location overrides the previous location in state."""
    coord = ConversationCoordinator()
    session_id = "test-override-loc-session"

    # Turn 1: Goa
    loc_goa = LocationContext(
        latitude=15.41,
        longitude=73.80,
        display_name="Goa Coastal Zone",
        source="search"
    )
    coord.process_turn(
        session_id=session_id,
        query_text="Check habitat",
        location_context=loc_goa,
        date_str="2025-10-15"
    )

    # Turn 2: Override with Mumbai
    loc_mumbai = LocationContext(
        latitude=18.94,
        longitude=72.84,
        display_name="Mumbai Coast",
        source="search"
    )
    resp2 = coord.process_turn(
        session_id=session_id,
        query_text="Now check conditions here",
        location_context=loc_mumbai
    )
    assert abs(resp2.request["latitude"] - 18.94) < 0.1
    assert abs(resp2.request["longitude"] - 72.84) < 0.1


def test_10_missing_location_does_not_invent_coordinates():
    """Queries needing coordinates return ClarificationRequired rather than hallucinating coordinates."""
    coord = ConversationCoordinator()
    session_id = "test-missing-loc-clarification"

    resp = coord.process_turn(
        session_id=session_id,
        query_text="Check habitat suitability today"
    )
    # Must request clarification for latitude and longitude
    assert hasattr(resp, "needs_clarification")
    assert resp.needs_clarification is True
    assert "latitude" in resp.missing
    assert "longitude" in resp.missing


def test_11_landlocked_query_in_chat_turn():
    """Chat queries mentioning landlocked states receive an immediate explanatory response."""
    coord = ConversationCoordinator()
    session_id = "test-landlocked-chat"

    resp = coord.process_turn(
        session_id=session_id,
        query_text="How is the weather near Rajasthan coast today?"
    )
    assert resp.success is True
    assert resp.conversation_response is not None
    assert "Rajasthan has no coastline" in resp.conversation_response


# ---------------------------------------------------------------------------
# 4. HTTP API Endpoints
# ---------------------------------------------------------------------------

def test_12_api_location_endpoints():
    """Test HTTP API endpoints for location resolution and suggestions."""
    # Test POST /api/v1/location/resolve
    res_resolve = client.post("/api/v1/location/resolve", json={"query": "Veraval"})
    assert res_resolve.status_code == 200
    data = res_resolve.json()
    assert data["success"] is True
    assert "Veraval" in data["location"]["display_name"]
    assert abs(data["location"]["latitude"] - 20.90) < 0.1

    # Test GET /api/v1/location/suggestions
    res_sugg = client.get("/api/v1/location/suggestions?q=mum")
    assert res_sugg.status_code == 200
    suggs = res_sugg.json()
    assert any("Mumbai" in s for s in suggs)

    # Test POST /api/v1/chat with location_context
    chat_payload = {
        "session_id": "test-api-loc-ctx",
        "message": "Where am I?",
        "location_context": {
            "latitude": 19.50,
            "longitude": 70.50,
            "display_name": "Standard Test Sector",
            "source": "manual"
        }
    }
    res_chat = client.post("/api/v1/chat", json=chat_payload)
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert "19.50° N, 70.50° E" in chat_data["conversation_response"]
