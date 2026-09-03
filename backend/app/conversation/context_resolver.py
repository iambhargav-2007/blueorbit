"""
context_resolver.py

Deterministic context resolution for the ORCA conversation layer (Step 13).

Purpose:
  Before the OrcaCoordinator is called, this module decides which latitude,
  longitude, and date to use — based on what the user just provided and what
  is stored in the session state from previous turns.

Resolution rules (applied in this order):
  1. An explicitly-provided value in the current request always takes priority
     and is used to update the session state.
  2. If a value is absent (None) in the current request, fall back to whatever
     is stored in the session state from a previous turn.
  3. If a required value is still missing after both steps, return a
     ClarificationRequired response — the value is NOT invented.

Date resolution:
  - "tomorrow" is resolved relative to today's date (datetime.utcnow), NOT by
    asking the LLM. The LLM is never involved in date arithmetic.
  - Any other natural-language date expression is treated as missing unless it
    can be parsed deterministically (currently: 'YYYY-MM-DD' and 'tomorrow').

IMPORTANT:
  The LLM must NEVER be the source of truth for resolved coordinates or dates.
  This module is entirely deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Union

from .schemas import ClarificationRequired
from .state import ConversationState


from ..services.temporal_resolver import TemporalContextResolver, TemporalResolution, TemporalMode

# ---------------------------------------------------------------------------
# Result type returned by the resolver
# ---------------------------------------------------------------------------

@dataclass
class ResolvedContext:
    """
    The successfully resolved inputs, ready to pass to OrcaCoordinator.

    All fields are guaranteed non-None when this object is returned
    (for the subset actually required by the selected capabilities).
    """
    latitude: Optional[float]
    longitude: Optional[float]
    date_str: Optional[str]
    temporal_resolution: Optional[TemporalResolution] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_context(
    state: ConversationState,
    new_latitude: Optional[float],
    new_longitude: Optional[float],
    new_date_str: Optional[str],
    needs_coords: bool,
    needs_date: bool,
    query_text: str = "",
) -> Union[ResolvedContext, ClarificationRequired]:
    """
    Resolve the effective latitude, longitude, and date for an incoming turn.

    Args:
        state:         Current conversation session state.
        new_latitude:  Latitude explicitly provided in this request (may be None).
        new_longitude: Longitude explicitly provided in this request (may be None).
        new_date_str:  Date string explicitly provided in this request (may be None).
        needs_coords:  Whether the identified capabilities require a location.
        needs_date:    Whether the identified capabilities require a date.
        query_text:    Natural language query for temporal context resolution.

    Returns:
        ResolvedContext if all required values could be resolved, or
        ClarificationRequired if any required value is still missing.
    """
    # --- Resolve latitude ---
    resolved_lat = _resolve_numeric(new_latitude, state.latitude)

    # --- Resolve longitude ---
    resolved_lon = _resolve_numeric(new_longitude, state.longitude)

    # --- Resolve date & temporal context ---
    temp_resolver = TemporalContextResolver()
    temp_resolution = temp_resolver.resolve(
        query_text=query_text,
        explicit_date_str=new_date_str,
        stored_date_str=state.date_str,
    )
    resolved_date = temp_resolution.date_str
    if temp_resolution.is_comparison and resolved_date is None:
        resolved_date = temp_resolution.historical_date or temp_resolution.current_date

    # --- Check for missing required values ---
    missing = []
    if needs_coords:
        if resolved_lat is None:
            missing.append("latitude")
        if resolved_lon is None:
            missing.append("longitude")
    if needs_date and resolved_date is None and not temp_resolution.is_comparison:
        missing.append("date")

    if missing:
        return ClarificationRequired(
            missing=missing,
            message=_missing_message(missing),
        )

    return ResolvedContext(
        latitude=resolved_lat,
        longitude=resolved_lon,
        date_str=resolved_date,
        temporal_resolution=temp_resolution,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_numeric(
    new_value: Optional[float],
    stored_value: Optional[float],
) -> Optional[float]:
    """
    Prefer the explicitly provided value; fall back to stored state.
    Returns None if both are absent.
    """
    if new_value is not None:
        return new_value
    return stored_value


def _resolve_date(
    new_date_str: Optional[str],
    stored_date_str: Optional[str],
) -> Optional[str]:
    """
    Resolve the date string:
    1. If 'tomorrow' is provided, resolve relative to today (UTC) deterministically.
    2. If a valid 'YYYY-MM-DD' string is provided, use it directly.
    3. If None, fall back to stored state.
    4. If stored state is also None, return None.
    """
    if new_date_str is not None:
        parsed = _parse_date_expression(new_date_str)
        if parsed is not None:
            return parsed
        # Unrecognised expression — treat as missing (do not fall back to stored)
        # so that an erroneous date doesn't silently use old data.
        return None

    return stored_date_str


def _parse_date_expression(expr: str) -> Optional[str]:
    """
    Convert a date expression to 'YYYY-MM-DD'.

    Supported:
      - 'YYYY-MM-DD'  — returned as-is after validation
      - 'tomorrow'    — resolved to today + 1 day (UTC)

    Returns None for anything else so the caller can treat it as missing.
    """
    expr = expr.strip().lower()

    if expr == "tomorrow":
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")

    if expr == "today":
        today = datetime.utcnow().date()
        return today.strftime("%Y-%m-%d")

    # Validate YYYY-MM-DD format
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", expr):
        try:
            datetime.strptime(expr, "%Y-%m-%d")
            return expr
        except ValueError:
            return None

    return None


def _missing_message(missing: list[str]) -> str:
    """Build a clear human-readable message about what is needed."""
    readable = {
        "latitude": "a latitude",
        "longitude": "a longitude",
        "date": "a date (YYYY-MM-DD)",
    }
    parts = [readable.get(f, f) for f in missing]
    joined = ", ".join(parts)
    return (
        f"I need {joined} to answer this question. "
        f"Please provide the missing information."
    )
