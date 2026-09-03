"""
state_manager.py

ConversationStateManager — manages in-memory session state for ORCA.

Design rules:
- Pure in-memory storage: a plain Python dict.
- No database, no Redis, no file I/O.
- Sessions are completely isolated: session A can never read session B's data.
- Thread-safety is NOT required for this prototype (single-process, single-thread).
  If multi-threading is added later, replace the dict with a threading.Lock.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Any

from .state import ConversationState

logger = logging.getLogger(__name__)


class ConversationStateManager:
    """
    Creates, retrieves, updates, and resets per-session conversation state.

    Usage
    -----
    manager = ConversationStateManager()
    manager.create_session("sess-001")
    state = manager.get_state("sess-001")
    manager.update_state("sess-001", latitude=19.5, longitude=70.5)
    manager.reset_session("sess-001")
    """

    def __init__(self) -> None:
        # Keyed by session_id string → ConversationState
        self._sessions: dict[str, ConversationState] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, session_id: str) -> ConversationState:
        """
        Create a new blank session.

        If a session with this ID already exists it is left untouched
        and the existing state is returned (idempotent).

        Args:
            session_id: A unique identifier for this conversation.

        Returns:
            The (new or existing) ConversationState.
        """
        if session_id in self._sessions:
            logger.debug(f"Session '{session_id}' already exists — returning existing state.")
            return self._sessions[session_id]

        state = ConversationState(session_id=session_id)
        self._sessions[session_id] = state
        logger.debug(f"Session '{session_id}' created.")
        return state

    def session_exists(self, session_id: str) -> bool:
        """Return True if a session with this ID exists."""
        return session_id in self._sessions

    def get_state(self, session_id: str) -> Optional[ConversationState]:
        """
        Retrieve the state for an existing session.

        Returns None if the session does not exist (not auto-created here
        so callers must explicitly create sessions before use).
        """
        return self._sessions.get(session_id)

    def update_state(self, session_id: str, **fields: Any) -> ConversationState:
        """
        Update one or more fields on the session state.

        Only explicitly provided (non-None) keyword arguments overwrite stored values.
        Passing None for a field does NOT clear it — use reset_session for a full clear.

        Allowed fields: latitude, longitude, date_str, last_capabilities, last_result.

        Args:
            session_id: ID of the session to update.
            **fields:   Key-value pairs to update.

        Returns:
            Updated ConversationState.

        Raises:
            KeyError: If the session does not exist.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' does not exist. Call create_session first.")

        state = self._sessions[session_id]
        allowed = {"latitude", "longitude", "date_str", "last_capabilities", "last_result", "location_context"}

        for key, value in fields.items():
            if key not in allowed:
                logger.warning(f"Ignoring unknown state field '{key}'.")
                continue
            # Only write if the new value is genuinely supplied (not None),
            # unless it's last_result/last_capabilities which may be set to None on reset.
            if value is not None:
                setattr(state, key, value)

        state.updated_at = datetime.utcnow()
        return state

    def reset_session(self, session_id: str) -> ConversationState:
        """
        Reset a session's context to a clean slate while keeping the session ID.

        After reset:
        - latitude, longitude, date_str are None
        - last_capabilities is empty
        - last_result is None

        The session itself is NOT deleted — only its stored context is cleared.

        Args:
            session_id: ID of the session to reset.

        Returns:
            Freshly cleared ConversationState.

        Raises:
            KeyError: If the session does not exist.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session '{session_id}' does not exist.")

        old = self._sessions[session_id]
        fresh = ConversationState(
            session_id=session_id,
            created_at=old.created_at,  # preserve original creation time
        )
        self._sessions[session_id] = fresh
        logger.debug(f"Session '{session_id}' reset.")
        return fresh
