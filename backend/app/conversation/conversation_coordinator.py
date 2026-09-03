"""
conversation_coordinator.py

ConversationCoordinator — the stateful entry point for Blue Orbit (ORCA).

This is the NEW top-level class for Step 13. It wraps the existing
OrcaCoordinator with session-aware context management.

Flow for each turn:
  1.  Get or create the session state.
  2.  Ask the router which capabilities are needed (via the inner coordinator's
      router — we call coordinator.process_request which handles routing).
  3.  Use ContextResolver to determine effective lat/lon/date from:
        a) What the user just provided in this turn, OR
        b) Stored state from a previous turn.
  4.  If required values are still missing, return ClarificationRequired.
  5.  Call OrcaCoordinator.process_request with resolved values.
  6.  Update session state with new location/date/capabilities/result.
  7.  Return the unified CoordinatorResponse.

IMPORTANT:
  - The LLM is NOT involved in deciding locations, dates, or numeric values.
  - The OrcaCoordinator is reused exactly as-is — no logic is duplicated.
  - Deterministic engine results remain authoritative throughout.
"""

from __future__ import annotations

import logging
from typing import Optional, Any, Union

from .state_manager import ConversationStateManager
from .context_resolver import resolve_context, ResolvedContext
from .schemas import ClarificationRequired
from ..coordinator.coordinator import OrcaCoordinator
from ..coordinator.schemas import CoordinatorResponse, RoutingInfo
from ..location.schemas import LocationContext
from ..location.resolver import LocationResolver

logger = logging.getLogger(__name__)


import re

def _get_conversational_response(query_text: str) -> Optional[str]:
    """
    Fast deterministic detection of greetings, courtesies, and help requests.
    Prevents expensive LLM router and marine provider calls for simple conversational turns.
    """
    clean = query_text.strip().lower()
    # Strip punctuation
    clean = re.sub(r"[^\w\s]", "", clean).strip()

    # Greetings
    greetings = {
        "hey", "heyy", "heyyy", "heya", "hello", "hi", "hi there", "hello there",
        "good morning", "good afternoon", "good evening", "namaste", "greetings", "yo"
    }
    if clean in greetings:
        return (
            "Hello! I am Blue Orbit (ORCA), your marine decision-support assistant for the Indian West Coast. "
            "You can ask me about fishing habitat suitability, sea state weather safety, or Indian EEZ geofencing. "
            "Where are you planning to sail?"
        )

    # Gratitude
    thanks = {"thanks", "thank you", "thank you so much", "thx", "thanks a lot", "many thanks"}
    if clean in thanks:
        return (
            "You're welcome! Wishing you safe navigation. "
            "Feel free to ask if you need further habitat or weather safety checks."
        )

    # Identity / Capabilities
    help_queries = {
        "who are you", "what can you do", "help", "what is blue orbit", "what is orca", "commands"
    }
    if clean in help_queries:
        return (
            "I am Blue Orbit (ORCA), a multi-agent decision-support platform for fishermen and coast guards "
            "along the Indian West Coast. I provide:\n"
            "• Live & historical habitat suitability (Copernicus SST & chlorophyll-a)\n"
            "• Sea state weather safety (wind speed, wave height, risk scoring)\n"
            "• Indian EEZ spatial compliance (distance to boundary & zone validation)\n\n"
            "To begin, you can ask a question with coordinates (e.g. 'What is the habitat suitability at 19.5, 70.5 today?')."
        )

    return None


class ConversationCoordinator:
    """
    Stateful orchestrator that adds multi-turn context to OrcaCoordinator.

    One ConversationCoordinator instance manages ALL sessions via its
    shared ConversationStateManager. A single instance can be reused
    across the lifetime of the application.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        live_mode: Optional[bool] = None,
    ) -> None:
        """
        Args:
            llm_client: Optional mock LLM client (used for testing).
            live_mode:  Passed through to OrcaCoordinator → agents → providers.
        """
        self._coordinator = OrcaCoordinator(
            llm_client=llm_client,
            live_mode=live_mode,
        )
        self._state_manager = ConversationStateManager()

    # ------------------------------------------------------------------
    # Session management (thin pass-throughs to StateManager)
    # ------------------------------------------------------------------

    def create_session(self, session_id: str) -> None:
        """Explicitly create a session. Idempotent."""
        self._state_manager.create_session(session_id)

    def reset_session(self, session_id: str) -> None:
        """
        Clear all context for a session. The session itself is kept,
        but location, date, and last results are erased.

        A subsequent request will require the user to supply coordinates again.
        """
        self._state_manager.reset_session(session_id)

    def get_state(self, session_id: str):
        """Return the raw ConversationState for inspection (read-only use)."""
        return self._state_manager.get_state(session_id)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_turn(
        self,
        session_id: str,
        query_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        date_str: Optional[str] = None,
        location_context: Optional[LocationContext] = None,
    ) -> Union[CoordinatorResponse, ClarificationRequired]:
        """
        Process one turn in a multi-turn conversation.

        Args:
            session_id:        Unique session identifier. Auto-created if missing.
            query_text:        Natural language user input for this turn.
            latitude:          Latitude if the user provided one in this turn.
            longitude:         Longitude if the user provided one in this turn.
            date_str:          Date if the user provided one ('YYYY-MM-DD' or 'tomorrow').
            location_context:  Optional normalized LocationContext from GPS, Search, Map, or Manual.

        Returns:
            CoordinatorResponse on success (full multi-agent result), or
            ClarificationRequired if required information is missing.
        """
        # Step 1 — Ensure session exists (auto-create if needed)
        if not self._state_manager.session_exists(session_id):
            self._state_manager.create_session(session_id)

        state = self._state_manager.get_state(session_id)

        # Step 1.2 — Align coordinates from location_context if provided
        if location_context is not None:
            latitude = location_context.latitude
            longitude = location_context.longitude

        # Step 1.3 — Natural language place extraction if no explicit coordinates passed
        if latitude is None and longitude is None:
            extracted = LocationResolver.extract_location_from_text(query_text)
            if extracted is not None:
                latitude = extracted.latitude
                longitude = extracted.longitude
                location_context = extracted
                logger.info(f"Session '{session_id}': extracted location '{extracted.display_name}' ({latitude}, {longitude}) from text")

        # Step 1.4 — "Where am I?" handling
        clean_q = re.sub(r"[^\w\s]", "", query_text.strip().lower()).strip()
        if clean_q in {
            "where am i", "where am i currently", "where am i right now",
            "what is my location", "what is my current location", "my location", "current location",
            "tell me my location", "show my location"
        }:
            active_loc = location_context or (state.location_context if state else None)
            active_lat = latitude if latitude is not None else (state.latitude if state else None)
            active_lon = longitude if longitude is not None else (state.longitude if state else None)

            if active_loc is not None:
                if active_loc.source == "gps" and active_loc.accuracy_m:
                    msg = f"You are currently at: {active_loc.latitude:.2f}° N, {active_loc.longitude:.2f}° E (GPS accuracy: ~{active_loc.accuracy_m:.0f}m, near {active_loc.display_name})."
                else:
                    msg = f"You are currently at: {active_loc.latitude:.2f}° N, {active_loc.longitude:.2f}° E ({active_loc.display_name})."
            elif active_lat is not None and active_lon is not None:
                msg = f"You are currently at: {active_lat:.2f}° N, {active_lon:.2f}° E."
            else:
                msg = "I don't have your location yet. Use 'Use my location' (GPS) or select a place on the map."

            return CoordinatorResponse(
                success=True,
                request={
                    "query_text": query_text,
                    "latitude": active_lat,
                    "longitude": active_lon,
                    "date_str": state.date_str if state else date_str,
                },
                routing=RoutingInfo(requested_capabilities=[], agents_invoked=[]),
                conversation_response=msg,
                errors=[],
            )

        # Step 1.5 — Landlocked inquiry check (e.g. "Rajasthan coast")
        landlocked_msg = LocationResolver.check_landlocked_mention(query_text)
        if landlocked_msg:
            return CoordinatorResponse(
                success=True,
                request={
                    "query_text": query_text,
                    "latitude": state.latitude if state else latitude,
                    "longitude": state.longitude if state else longitude,
                    "date_str": state.date_str if state else date_str,
                },
                routing=RoutingInfo(requested_capabilities=[], agents_invoked=[]),
                conversation_response=landlocked_msg,
                errors=[],
            )

        # Step 1.6 — Fast conversational handling (greetings, courtesies, identity)
        conv_resp = _get_conversational_response(query_text)
        if conv_resp is not None:
            logger.info(f"Session '{session_id}': handled as conversational query ('{query_text}')")
            return CoordinatorResponse(
                success=True,
                request={
                    "query_text": query_text,
                    "latitude": state.latitude if state else latitude,
                    "longitude": state.longitude if state else longitude,
                    "date_str": state.date_str if state else date_str,
                },
                routing=RoutingInfo(requested_capabilities=[], agents_invoked=[]),
                conversation_response=conv_resp,
                errors=[],
            )

        # Step 2 — Determine which capabilities the query requires
        # We ask the router directly (same router the coordinator uses internally).
        requested_caps = self._coordinator._router.get_capabilities(query_text)

        needs_coords = any(c in requested_caps for c in ["habitat", "weather", "geofencing", "fishing_decision"])
        needs_date = any(c in requested_caps for c in ["habitat", "weather", "fishing_decision"])

        # Step 3 — Resolve effective lat/lon/date
        resolution = resolve_context(
            state=state,
            new_latitude=latitude,
            new_longitude=longitude,
            new_date_str=date_str,
            needs_coords=needs_coords,
            needs_date=needs_date,
            query_text=query_text,
        )

        # Step 4 — Return clarification if required values are missing
        if isinstance(resolution, ClarificationRequired):
            logger.info(
                f"Session '{session_id}': clarification needed — "
                f"missing {resolution.missing}"
            )
            return resolution

        # Step 5 — Call the existing coordinator with resolved inputs AND cached capabilities
        result: CoordinatorResponse = self._coordinator.process_request(
            query_text=query_text,
            latitude=resolution.latitude,
            longitude=resolution.longitude,
            date_str=resolution.date_str,
            temporal_resolution=resolution.temporal_resolution,
            requested_capabilities=requested_caps,
        )

        # Step 6 — Update session state from this turn's results
        # Only update fields that are now definitively known.
        # We never store None over an existing value.
        update_fields: dict = {}

        if resolution.latitude is not None:
            update_fields["latitude"] = resolution.latitude
        if resolution.longitude is not None:
            update_fields["longitude"] = resolution.longitude
        if resolution.date_str is not None:
            update_fields["date_str"] = resolution.date_str
        if requested_caps:
            update_fields["last_capabilities"] = requested_caps
        if result.success:
            update_fields["last_result"] = result

        # Store LocationContext in state
        if location_context is not None:
            update_fields["location_context"] = location_context
        elif resolution.latitude is not None and resolution.longitude is not None:
            # If no LocationContext existed yet, wrap resolved coords in manual LocationContext
            update_fields["location_context"] = LocationContext(
                latitude=resolution.latitude,
                longitude=resolution.longitude,
                display_name=f"{resolution.latitude:.2f}° N, {resolution.longitude:.2f}° E",
                source="manual"
            )

        if update_fields:
            self._state_manager.update_state(session_id, **update_fields)

        # Step 7 — Return the unified coordinator response
        return result
