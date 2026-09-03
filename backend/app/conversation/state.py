"""
state.py

ConversationState — the in-memory record for a single ORCA conversation session.

Design rules:
- Only deterministic values are stored: coordinates, dates, engine results.
- LLM-narrated text fields (e.g., fisherman_advice) are carried as part of
  the full CoordinatorResponse but are NEVER used to make decisions.
- All fields are Optional so that a fresh session has no stale carry-forward.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    # Avoid circular imports; CoordinatorResponse is only referenced for type hints.
    from ..coordinator.schemas import CoordinatorResponse


@dataclass
class ConversationState:
    """
    Holds the context for one conversation session.

    Fields
    ------
    session_id
        Unique identifier for this conversation (e.g., UUID string).
    latitude
        Most recently known / confirmed latitude for this session.
        Set only from explicit user input or prior confirmed request.
    longitude
        Most recently known / confirmed longitude for this session.
    date_str
        Most recently known / confirmed date as 'YYYY-MM-DD'.
    last_capabilities
        Which domain capabilities were used in the last successful request.
        e.g. ['habitat', 'weather']
    last_result
        Full structured CoordinatorResponse from the last successful request.
        Stored so the UI layer can reference prior results without re-querying.
        The deterministic engine values inside are authoritative.
    created_at
        When this session was first created.
    updated_at
        When this session was last updated.
    """

    session_id: str

    # --- Resolved context ---
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    date_str: Optional[str] = None
    location_context: Optional[Any] = None

    # --- Last-turn metadata ---
    last_capabilities: List[str] = field(default_factory=list)
    last_result: Optional["CoordinatorResponse"] = None

    # --- Timestamps ---
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
