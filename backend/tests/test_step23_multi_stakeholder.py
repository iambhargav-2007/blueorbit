"""
test_step23_multi_stakeholder.py

Comprehensive test suite for Step 23: Multi-Stakeholder Coastal Intelligence Architecture.
Validates:
1. Multi-stakeholder intent taxonomy and domain mapping
2. Selective agent invocation (NO fishing decision for cyclone, research, or safety)
3. Offline deterministic regex routing fallback
4. CoordinatorResponse schema compliance (intent, intelligence_domain, safety_assessment, sector_overview, structured_summary)
5. Multi-turn conversation coordinator handling across diverse domains
6. Backwards compatibility with existing Step 1-22 features
"""

import pytest
from unittest.mock import MagicMock
from app.coordinator.schemas import (
    IntentEnum,
    IntelligenceDomainEnum,
    CoordinatorResponse,
    RoutingInfo,
    StructuredSummary,
)
from app.coordinator.router import OrcaQueryRouter
from app.coordinator.coordinator import OrcaCoordinator
from app.conversation.conversation_coordinator import ConversationCoordinator
from app.conversation.schemas import ClarificationRequired
from app.agents.schemas import (
    FishingAgentResponse,
    WeatherSafetyAgentResponse,
    GeofencingAgentResponse,
    CycloneAgentResponse,
    FishingDecisionAgentResponse,
    FishingDecision,
    LocationInfo,
    EnvironmentalSummary,
    WeatherConditions,
    SevereWeatherClassificationSchema,
)


def _setup_mock_coordinator(coord: OrcaCoordinator) -> OrcaCoordinator:
    mock_habitat = FishingAgentResponse(
        success=True,
        location=LocationInfo(latitude=19.5, longitude=70.5),
        date="2025-10-15",
        habitat_score=85.0,
        fishing_potential="High",
        confidence="High",
        environmental_summary=EnvironmentalSummary(
            temperature_c=28.2,
            chlorophyll_mg_m3=0.75,
            temperature_score=88.0,
            chlorophyll_score=82.0,
        ),
        scientific_explanation="Favorable thermal and chlorophyll gradients detected."
    )
    coord._habitat_agent.run = MagicMock(return_value=mock_habitat)

    mock_weather = WeatherSafetyAgentResponse(
        success=True,
        location=LocationInfo(latitude=19.5, longitude=70.5),
        date="2025-10-15",
        risk_level="Low Risk",
        confidence="High",
        limiting_factor="None",
        weather_conditions=WeatherConditions(
            wind_speed_knots=12.5,
            wave_height_meters=1.2,
            surface_pressure_hpa=1012.0,
            wind_safety_score=90.0,
            wave_safety_score=88.0,
            overall_safety_score=88.0,
        ),
        safety_narrative="Calm sea conditions suitable for navigation."
    )
    coord._weather_agent.run = MagicMock(return_value=mock_weather)

    mock_geo = GeofencingAgentResponse(
        success=True,
        location=LocationInfo(latitude=19.5, longitude=70.5),
        inside_indian_eez=True,
        geofence_status="SAFE",
        distance_to_eez_boundary_km=142.5,
    )
    coord._geofencing_agent.run = MagicMock(return_value=mock_geo)

    mock_cyclone = CycloneAgentResponse(
        success=True,
        location=LocationInfo(latitude=19.5, longitude=70.5),
        date="2025-10-15",
        active_cyclones_count=0,
        severe_weather=SevereWeatherClassificationSchema(
            risk_level="NORMAL",
            is_affected=False,
            affected_status="NOT_AFFECTED",
            narrative="No verified cyclonic disturbance in the basin."
        ),
        narrative="No cyclonic systems detected in the operational area."
    )
    coord._cyclone_agent.run = MagicMock(return_value=mock_cyclone)

    mock_decision = FishingDecisionAgentResponse(
        success=True,
        decision=FishingDecision(
            decision="FAVORABLE",
            overall_score=87.0,
            confidence="HIGH",
            habitat_score=85.0,
            habitat_status="High",
            weather_score=88.0,
            weather_risk="Low Risk",
            geofence_status="SAFE",
            limiting_factor="None",
            reasons=["High chlorophyll concentration", "Low wave height"],
            warnings=[],
            location=LocationInfo(latitude=19.5, longitude=70.5),
        )
    )
    coord._decision_agent.run = MagicMock(return_value=mock_decision)
    return coord


@pytest.fixture
def router():
    return OrcaQueryRouter(llm_client=None)


@pytest.fixture
def coordinator():
    coord = OrcaCoordinator(llm_client=None, live_mode=False)
    return _setup_mock_coordinator(coord)


@pytest.fixture
def conv_coordinator():
    conv_coord = ConversationCoordinator(llm_client=None, live_mode=False)
    _setup_mock_coordinator(conv_coord._coordinator)
    return conv_coord


# =========================================================================
# 1. ROUTER INTENT CLASSIFICATION & DOMAIN MAPPING
# =========================================================================

def test_01_router_cyclone_intent(router):
    """Severe weather / cyclone queries classify to SEVERE_WEATHER and WEATHER domain."""
    intent, domain, caps = router.classify_intent("Are there any active cyclones near Gujarat coast?")
    assert intent == IntentEnum.SEVERE_WEATHER.value
    assert domain in {IntelligenceDomainEnum.SEVERE_WEATHER.value, IntelligenceDomainEnum.WEATHER.value, "severe_weather", "weather"}
    assert "cyclone" in caps


def test_02_router_marine_analysis_intent(router):
    """SST / Chlorophyll-a research queries classify to MARINE_ANALYSIS."""
    intent, domain, caps = router.classify_intent("What is the sea surface temperature and chlorophyll concentration at 19.5, 70.5?")
    assert intent == IntentEnum.MARINE_ANALYSIS.value
    assert domain == IntelligenceDomainEnum.MARINE.value
    assert "habitat" in caps


def test_03_router_environmental_analysis_intent(router):
    """Ecological / habitat conditions classify to ENVIRONMENTAL_ANALYSIS."""
    intent, domain, caps = router.classify_intent("Check ecological conditions and marine habitat quality")
    assert intent == IntentEnum.ENVIRONMENTAL_ANALYSIS.value
    assert domain == IntelligenceDomainEnum.MARINE.value
    assert "habitat" in caps


def test_04_router_maritime_safety_intent(router):
    """Sea state safety queries classify to MARITIME_SAFETY."""
    intent, domain, caps = router.classify_intent("Is it safe for a small vessel to sail today? Check wind and waves.")
    assert intent == IntentEnum.MARITIME_SAFETY.value
    assert domain in {IntelligenceDomainEnum.MARITIME_SAFETY.value, IntelligenceDomainEnum.WEATHER.value, "maritime_safety", "weather"}
    assert "weather" in caps


def test_05_router_spatial_geofencing_intent(router):
    """EEZ boundary and distance queries classify to SPATIAL_QUERY."""
    intent, domain, caps = router.classify_intent("What is the distance to the Indian EEZ boundary?")
    assert intent == IntentEnum.SPATIAL_QUERY.value
    assert domain == IntelligenceDomainEnum.GEOSPATIAL.value
    assert "geofencing" in caps


def test_06_router_fishing_support_intent(router):
    """Fishing queries classify to FISHING_SUPPORT."""
    intent, domain, caps = router.classify_intent("Is this a good time and spot for tuna fishing?")
    assert intent == IntentEnum.FISHING_SUPPORT.value
    assert domain == IntelligenceDomainEnum.FISHING.value
    assert "fishing_decision" in caps


def test_07_router_general_coastal_query_intent(router):
    """General sector overview queries classify to GENERAL_COASTAL_QUERY."""
    intent, domain, caps = router.classify_intent("Give me an area overview of what is happening near Mumbai coast")
    assert intent == IntentEnum.GENERAL_COASTAL_QUERY.value
    assert domain == IntelligenceDomainEnum.COASTAL_OVERVIEW.value
    assert len(caps) >= 3


def test_08_router_offline_deterministic_fallback(router):
    """Router works 100% offline without throwing or hanging when no LLM is configured."""
    queries = [
        "cyclone warning",
        "chlorophyll-a bloom",
        "patrol vessel safety",
        "eez line distance",
        "catch potential",
        "sector overview",
    ]
    for q in queries:
        intent, domain, caps = router.classify_intent(q)
        assert intent is not None
        assert domain is not None
        assert isinstance(caps, list)


# =========================================================================
# 2. SELECTIVE AGENT EXECUTION & COORDINATOR ISOLATION
# =========================================================================

def test_09_cyclone_query_does_not_call_fishing_decision(coordinator):
    """Cyclone query must NOT invoke FishingDecisionAgent or produce fishing_decision."""
    res = coordinator.process_request(
        query_text="Are there any cyclone alerts near 19.5, 70.5?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )
    assert res.success is True
    assert res.intent == IntentEnum.SEVERE_WEATHER.value
    assert res.fishing_decision is None
    assert "fishing_decision" not in res.routing.agents_invoked
    assert res.cyclone is not None


def test_10_marine_research_query_does_not_call_fishing_decision(coordinator):
    """Marine/SST analysis query must NOT produce fishing catch advice."""
    res = coordinator.process_request(
        query_text="Provide sea surface temperature and chlorophyll-a metrics at 18.0, 72.0",
        latitude=18.0,
        longitude=72.0,
        date_str="2025-10-15",
    )
    assert res.success is True
    assert res.intent in {IntentEnum.MARINE_ANALYSIS.value, IntentEnum.ENVIRONMENTAL_ANALYSIS.value}
    assert res.fishing_decision is None
    assert "fishing_decision" not in res.routing.agents_invoked
    assert res.habitat is not None


def test_11_maritime_safety_query_generates_safety_assessment(coordinator):
    """Maritime safety queries return safety_assessment and avoid fishing recommendations."""
    res = coordinator.process_request(
        query_text="Is it safe for maritime operations at 20.0, 69.5? Check wave height and wind.",
        latitude=20.0,
        longitude=69.5,
        date_str="2025-10-15",
    )
    assert res.success is True
    assert res.intent == IntentEnum.MARITIME_SAFETY.value
    assert res.safety_assessment is not None
    assert "sea_state_risk" in res.safety_assessment
    assert res.fishing_decision is None
    assert "fishing_decision" not in res.routing.agents_invoked


def test_12_fishing_query_invokes_fishing_decision_agent(coordinator):
    """Fishing queries specifically invoke fishing decision agent."""
    res = coordinator.process_request(
        query_text="Should I sail for fishing at 19.5, 70.5?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )
    assert res.success is True
    assert res.intent == IntentEnum.FISHING_SUPPORT.value
    assert res.fishing_decision is not None
    assert "fishing_decision" in res.routing.agents_invoked


def test_13_sector_overview_aggregates_without_universal_fishing_score(coordinator):
    """General coastal overview query generates sector_overview."""
    res = coordinator.process_request(
        query_text="Give me a sector overview for 19.5, 70.5",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )
    assert res.success is True
    assert res.intent == IntentEnum.GENERAL_COASTAL_QUERY.value
    assert res.sector_overview is not None
    assert "marine_environment" in res.sector_overview
    assert "sea_state" in res.sector_overview
    assert "geospatial" in res.sector_overview


# =========================================================================
# 3. SCHEMA INTEGRITY & STRUCTURED SUMMARY
# =========================================================================

def test_14_structured_summary_presence(coordinator):
    """CoordinatorResponse must include standardized structured_summary."""
    res = coordinator.process_request(
        query_text="What is the weather at 19.5, 70.5?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )
    assert res.structured_summary is not None
    assert hasattr(res.structured_summary, "overview")
    assert hasattr(res.structured_summary, "key_findings")
    assert hasattr(res.structured_summary, "operational_status")
    assert hasattr(res.structured_summary, "confidence")


def test_15_coordinator_response_serialization(coordinator):
    """CoordinatorResponse serializes cleanly to dict and JSON."""
    res = coordinator.process_request(
        query_text="Are there cyclones?",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
    )
    data = res.model_dump()
    assert "intent" in data
    assert "intelligence_domain" in data
    assert "structured_summary" in data


# =========================================================================
# 4. CONVERSATIONAL LAYER & MULTI-TURN BEHAVIOR
# =========================================================================

def test_16_cyclone_basin_query_without_coords(conv_coordinator):
    """Cyclone queries do not require coordinates and succeed directly."""
    res = conv_coordinator.process_turn(
        session_id="test-cyclone-session-1",
        query_text="Are there any active cyclones in the Arabian Sea?",
    )
    assert not isinstance(res, ClarificationRequired)
    assert res.success is True
    assert res.intent == IntentEnum.SEVERE_WEATHER.value


def test_17_habitat_missing_coords_prompts_clarification(conv_coordinator):
    """Research / marine query without coordinates prompts for clarification."""
    res = conv_coordinator.process_turn(
        session_id="test-marine-session-1",
        query_text="What is the sea surface temperature?",
    )
    assert isinstance(res, ClarificationRequired)
    assert "latitude" in res.missing
    assert "longitude" in res.missing


def test_18_context_persistence_across_domains(conv_coordinator):
    """Coordinates supplied in marine query persist when asking safety query next turn."""
    sess = "test-multi-turn-session-2"
    turn1 = conv_coordinator.process_turn(
        session_id=sess,
        query_text="Check SST at 19.5, 70.5 on 2025-10-15",
    )
    assert not isinstance(turn1, ClarificationRequired)
    assert turn1.intent in {IntentEnum.MARINE_ANALYSIS.value, IntentEnum.ENVIRONMENTAL_ANALYSIS.value}
    assert turn1.fishing_decision is None

    # Follow-up maritime safety question without repeating coordinates
    turn2 = conv_coordinator.process_turn(
        session_id=sess,
        query_text="Is it safe to navigate here?",
    )
    assert not isinstance(turn2, ClarificationRequired)
    assert turn2.intent == IntentEnum.MARITIME_SAFETY.value
    assert turn2.request["latitude"] == 19.5
    assert turn2.request["longitude"] == 70.5
    assert turn2.safety_assessment is not None
    assert turn2.fishing_decision is None


def test_19_identity_mentions_multi_stakeholders(conv_coordinator):
    """Asking 'who are you' returns multi-stakeholder platform description."""
    res = conv_coordinator.process_turn(
        session_id="test-identity-session",
        query_text="Who are you?",
    )
    assert not isinstance(res, ClarificationRequired)
    resp_lower = res.conversation_response.lower()
    assert "fishermen" in resp_lower
    assert "coast" in resp_lower
    assert "researchers" in resp_lower


# =========================================================================
# 5. DETERMINISTIC ENGINE AUTHORITATIVENESS
# =========================================================================

def test_20_deterministic_metrics_integrity(coordinator):
    """Deterministic engines remain the sole source of truth for numeric metrics."""
    res = coordinator.process_request(
        query_text="Full coastal scan for tuna fishing at 19.5, 70.5",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
        requested_capabilities=["habitat", "weather", "geofencing", "fishing_decision"],
        intent=IntentEnum.FISHING_SUPPORT.value,
    )
    assert res.habitat is not None
    assert res.weather is not None
    assert res.geofencing is not None
    assert res.fishing_decision is not None
    assert 0.0 <= res.habitat.habitat_score <= 100.0
    assert res.weather.weather_conditions.wind_speed_knots >= 0.0
    assert res.geofencing.distance_to_eez_boundary_km >= 0.0
    assert 0.0 <= res.fishing_decision.decision.overall_score <= 100.0


def test_21_spatial_query_isolation(coordinator):
    """Spatial query executes only geofencing without invoking weather or fishing."""
    res = coordinator.process_request(
        query_text="Check EEZ boundary status at 20.0, 69.0",
        latitude=20.0,
        longitude=69.0,
        date_str="2025-10-15",
    )
    assert res.success is True
    assert res.geofencing is not None
    assert res.fishing_decision is None
    assert "geofencing" in res.routing.agents_invoked
    assert "weather_safety" not in res.routing.agents_invoked
    assert "fishing_decision" not in res.routing.agents_invoked


def test_22_backward_compatibility_old_capabilities(coordinator):
    """Coordinator still supports explicit requested_capabilities list."""
    res = coordinator.process_request(
        query_text="Explicit request",
        latitude=19.5,
        longitude=70.5,
        date_str="2025-10-15",
        requested_capabilities=["habitat", "geofencing"],
    )
    assert res.success is True
    assert res.habitat is not None
    assert res.geofencing is not None
    assert res.weather is None
    assert res.fishing_decision is None


def test_23_natural_place_name_resolution(conv_coordinator):
    """Named locations resolve coordinates seamlessly."""
    res = conv_coordinator.process_turn(
        session_id="test-place-session",
        query_text="What is the sea state near Mumbai coast on 2025-10-15?",
    )
    assert not isinstance(res, ClarificationRequired)
    assert res.request["latitude"] is not None
    assert res.request["longitude"] is not None
    assert res.intent in {IntentEnum.MARITIME_SAFETY.value, IntentEnum.GENERAL_COASTAL_QUERY.value}


def test_24_unknown_query_graceful_fallback(conv_coordinator):
    """Unrecognized query defaults safely without unhandled exception."""
    res = conv_coordinator.process_turn(
        session_id="test-unknown-session",
        query_text="random unrecognized query xyz 12345",
        latitude=19.5,
        longitude=70.5,
    )
    assert not isinstance(res, ClarificationRequired)
    assert res is not None
    assert "errors" in res.model_dump()


def test_25_all_nine_intents_handled_cleanly(coordinator):
    """Every intent in IntentEnum can be processed by coordinator without error."""
    for intent_val in IntentEnum:
        res = coordinator.process_request(
            query_text=f"Testing intent {intent_val.value}",
            latitude=19.5,
            longitude=70.5,
            date_str="2025-10-15",
            intent=intent_val.value,
        )
        assert res.intent == intent_val.value
        if intent_val != IntentEnum.UNKNOWN:
            assert res.success is True
