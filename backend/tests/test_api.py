"""
test_api.py

Step 14 API tests — FastAPI integration.

This module uses pytest fixtures to set up the mock coordinator before
any coordinator instantiation occurs. The GROQ_API_KEY environment variable
is set before any imports that trigger the key check.
"""

import os
import sys
import json
from unittest.mock import MagicMock, patch

# Ensure backend/ is on the path regardless of where pytest is invoked from
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Set env var BEFORE any app import so the GROQ check doesn't fail at module level
os.environ.setdefault('GROQ_API_KEY', 'mock-key')
os.environ.setdefault('LLM_PROVIDER', 'groq')

import pytest
from fastapi.testclient import TestClient


def _make_mock_llm(capabilities: list) -> MagicMock:
    """Return a mock Groq client that produces valid JSON for router and agents."""
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


@pytest.fixture(scope="module")
def api_client():
    """
    Module-scoped fixture that:
    1. Creates a ConversationCoordinator with a mock LLM.
    2. Overrides the FastAPI dependency so no real API key is needed.
    3. Returns a TestClient reused for the whole module (preserving session state).
    """
    from app.main import app
    from app.api.chat import get_coordinator
    from app.conversation.conversation_coordinator import ConversationCoordinator

    coordinator = ConversationCoordinator(
        llm_client=_make_mock_llm(["habitat", "weather", "geofencing"]),
        live_mode=False,
    )

    def override():
        return coordinator

    app.dependency_overrides[get_coordinator] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TEST 1 — Health endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ---------------------------------------------------------------------------
# TEST 2 — Valid chat request with explicit location
# ---------------------------------------------------------------------------

def test_chat_valid_request_with_location(api_client):
    payload = {
        "session_id": "test-session-1",
        "message": "Is it safe to fish here?",
        "latitude": 19.5,
        "longitude": 70.5,
        "date_str": "2025-10-15",
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


# ---------------------------------------------------------------------------
# TEST 3 — Follow-up request reuses session location (same session)
# ---------------------------------------------------------------------------

def test_chat_follow_up_request_same_session(api_client):
    # Session test-session-1 already has 19.5, 70.5 from test 2
    payload = {
        "session_id": "test-session-1",
        "message": "What about the habitat?",
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("needs_clarification") is not True
    assert data.get("success") is True
    assert data.get("request", {}).get("latitude") == 19.5
    assert data.get("request", {}).get("longitude") == 70.5


# ---------------------------------------------------------------------------
# TEST 4 — Different session isolation
# ---------------------------------------------------------------------------

def test_chat_different_session_isolation(api_client):
    # test-session-2 is brand new — no stored coordinates
    payload = {
        "session_id": "test-session-2",
        "message": "What is the weather?",
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("needs_clarification") is True
    assert "latitude" in data.get("missing", []) or "longitude" in data.get("missing", [])


# ---------------------------------------------------------------------------
# TEST 5 — Explicit location override
# ---------------------------------------------------------------------------

def test_chat_explicit_location_override(api_client):
    payload = {
        "session_id": "test-session-1",
        "message": "Check another place",
        "latitude": 16.5,
        "longitude": 72.0,
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("request", {}).get("latitude") == 16.5
    assert data.get("request", {}).get("longitude") == 72.0


# ---------------------------------------------------------------------------
# TEST 6 — Invalid latitude rejected (HTTP 422)
# ---------------------------------------------------------------------------

def test_chat_invalid_latitude(api_client):
    payload = {
        "session_id": "test-session-err",
        "message": "Hello",
        "latitude": 190.5,
        "longitude": 70.5,
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# TEST 7 — Invalid longitude rejected (HTTP 422)
# ---------------------------------------------------------------------------

def test_chat_invalid_longitude(api_client):
    payload = {
        "session_id": "test-session-err",
        "message": "Hello",
        "latitude": 19.5,
        "longitude": 270.5,
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# TEST 8 — Missing location with brand-new session → clarification
# ---------------------------------------------------------------------------

def test_chat_missing_location_new_session(api_client):
    payload = {
        "session_id": "test-session-3",
        "message": "How's the weather?",
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("needs_clarification") is True


# ---------------------------------------------------------------------------
# TEST 9 — Deterministic result preservation
# ---------------------------------------------------------------------------

def test_chat_deterministic_result_preservation(api_client):
    """
    Verify the API returns the real deterministic habitat_score from the engine.
    The mock LLM provides narrative text only; the engine calculates the score.
    The API must not replace the engine-computed score with any LLM-invented value.
    """
    payload = {
        "session_id": "test-session-determ",
        "message": "How is the habitat suitability?",
        "latitude": 19.5,
        "longitude": 70.5,
        "date_str": "2025-10-15",
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["habitat"] is not None
    # habitat_score is populated by the deterministic Habitat Engine, not the LLM
    assert data["habitat"]["habitat_score"] is not None
    # Confirm it is a numeric value (engine output)
    assert isinstance(data["habitat"]["habitat_score"], (int, float))


# ---------------------------------------------------------------------------
# TEST 10 — Agent failure isolation
# ---------------------------------------------------------------------------

def test_chat_agent_failure_isolation(api_client, mocker):
    """
    Mock FishingHabitatAgent.run to return a failed response.
    The coordinator must isolate the failure and still return success=True
    if other agents succeed (or handle gracefully).
    """
    from app.agents.schemas import FishingAgentResponse

    failed_resp = FishingAgentResponse(
        success=False,
        error="Mock habitat agent failure",
        disclaimer="mock",
    )
    mocker.patch(
        "app.agents.fishing_agent.FishingHabitatAgent.run",
        return_value=failed_resp,
    )

    payload = {
        "session_id": "test-session-fail",
        "message": "Check habitat and weather",
        "latitude": 19.5,
        "longitude": 70.5,
        "date_str": "2025-10-15",
    }
    response = api_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Coordinator isolates the habitat failure; overall success depends on other agents
    assert data["success"] is True or len(data["errors"]) > 0
    # Habitat result is the failed mock or error is recorded
    habitat = data.get("habitat")
    errors = data.get("errors", [])
    assert (habitat is not None and habitat.get("success") is False) or any(
        "Mock habitat agent failure" in e or "Habitat" in e for e in errors
    )
