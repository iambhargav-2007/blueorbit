"""
temporal_resolver.py

Deterministic Temporal Context Resolver for Blue Orbit (ORCA) - Step 16.

Responsibility:
  - Parse natural language query and explicit request parameters for temporal intent.
  - Classify temporal context into:
      * LIVE (current date / today / now / latest)
      * HISTORICAL (dates strictly before current date)
      * UNSUPPORTED_FUTURE (dates strictly after current date)
      * COMPARISON (requests comparing current conditions with a historical date)
  - Dynamically evaluate relative to system clock (or injected reference date).
  - Deterministic authority: LLM hallucinations cannot override resolved dates or modes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Optional, Tuple


class TemporalMode(str, Enum):
    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"
    UNSUPPORTED_FUTURE = "UNSUPPORTED_FUTURE"
    COMPARISON = "COMPARISON"


@dataclass
class TemporalResolution:
    """Structured resolution result from the TemporalContextResolver."""
    mode: TemporalMode
    date_str: Optional[str] = None
    historical_date: Optional[str] = None
    current_date: Optional[str] = None
    is_comparison: bool = False
    reason: Optional[str] = None


MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


class TemporalContextResolver:
    """
    Deterministic resolver that maps incoming requests to temporal modes and dates.
    """

    def __init__(self, reference_date: Optional[date] = None):
        """
        Args:
            reference_date: Optional fixed reference date (used for deterministic testing).
                           If None, uses the current UTC system clock.
        """
        self._reference_date = reference_date

    def get_reference_date(self) -> date:
        """Returns the active reference date (system clock or injected)."""
        if self._reference_date is not None:
            return self._reference_date
        return datetime.now(timezone.utc).date()

    def resolve(
        self,
        query_text: str = "",
        explicit_date_str: Optional[str] = None,
        stored_date_str: Optional[str] = None,
        reference_date: Optional[date] = None,
    ) -> TemporalResolution:
        """
        Deterministically resolve the temporal mode and target date(s).

        Args:
            query_text: Natural language user query.
            explicit_date_str: Explicit date string from API payload (e.g. 'YYYY-MM-DD', 'today').
            stored_date_str: Stored date string from conversation state.
            reference_date: Optional override for reference date for this call.

        Returns:
            TemporalResolution dataclass.
        """
        ref_date = reference_date or self.get_reference_date()
        ref_date_str = ref_date.strftime("%Y-%m-%d")
        query_lower = (query_text or "").strip().lower()

        # ------------------------------------------------------------------
        # 1. Check for Comparison Request
        # ------------------------------------------------------------------
        comp_res = self._check_comparison(query_lower, ref_date)
        if comp_res is not None:
            return comp_res

        # ------------------------------------------------------------------
        # 2. Priority: Explicit date provided in API request payload
        # ------------------------------------------------------------------
        if explicit_date_str is not None and explicit_date_str.strip():
            cleaned_explicit = explicit_date_str.strip()
            parsed_date = self._parse_date_expression(cleaned_explicit, ref_date)
            if parsed_date is not None:
                return self._classify_single_date(parsed_date, ref_date, reason="Explicit request date parameter")
            else:
                return TemporalResolution(
                    mode=TemporalMode.HISTORICAL,
                    date_str=cleaned_explicit,
                    reason=f"Explicit date provided in unparseable or custom format: {cleaned_explicit}"
                )

        # ------------------------------------------------------------------
        # 3. Check for keywords in query_text indicating LIVE (today/current/now/latest)
        # ------------------------------------------------------------------
        if self._has_live_keywords(query_lower):
            # If query specifically says "today", "current", "now", "latest", "right now"
            # It takes precedence over past conversation state!
            return TemporalResolution(
                mode=TemporalMode.LIVE,
                date_str=ref_date_str,
                reason="Query contains live temporal keyword (today/now/current)"
            )

        # ------------------------------------------------------------------
        # 4. Check for explicit date embedded in query_text
        # ------------------------------------------------------------------
        parsed_from_query = self._extract_date_from_text(query_lower, ref_date)
        if parsed_from_query is not None:
            return self._classify_single_date(parsed_from_query, ref_date, reason="Extracted date from query text")

        # ------------------------------------------------------------------
        # 5. Fall back to conversation state stored date
        # ------------------------------------------------------------------
        if stored_date_str is not None and stored_date_str.strip():
            parsed_stored = self._parse_date_expression(stored_date_str.strip(), ref_date)
            if parsed_stored is not None:
                return self._classify_single_date(parsed_stored, ref_date, reason="Inherited date from conversation state")

        # ------------------------------------------------------------------
        # 6. Default fallback when no date or indicator is found: default to TODAY (LIVE)
        # ------------------------------------------------------------------
        return TemporalResolution(
            mode=TemporalMode.LIVE,
            date_str=ref_date_str,
            reason="Defaulting to today/current date since no specific date was specified"
        )

    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------

    def _has_live_keywords(self, text: str) -> bool:
        """Checks if text contains current/today/now temporal indicators."""
        patterns = [
            r"\btoday\b",
            r"\bcurrent\b",
            r"\bnow\b",
            r"\bright now\b",
            r"\blatest\b",
            r"\bpresent\b",
        ]
        return any(re.search(pat, text) for pat in patterns)

    def _check_comparison(self, text: str, ref_date: date) -> Optional[TemporalResolution]:
        """Detects if query asks for a comparison between today and a past date."""
        if not ("compare" in text or "difference" in text or "what changed" in text):
            return None

        # Try to extract the historical date from the comparison query
        # Look for YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        hist_date_obj: Optional[date] = None

        if iso_match:
            try:
                hist_date_obj = datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
            except ValueError:
                pass
        else:
            # Look for natural date e.g. "october 15 2025" or "october 15, 2025" or "15 october 2025"
            hist_date_obj = self._extract_natural_date(text)

        if hist_date_obj is not None:
            hist_date_str = hist_date_obj.strftime("%Y-%m-%d")
            ref_date_str = ref_date.strftime("%Y-%m-%d")
            return TemporalResolution(
                mode=TemporalMode.COMPARISON,
                historical_date=hist_date_str,
                current_date=ref_date_str,
                is_comparison=True,
                reason=f"Comparison requested between historical {hist_date_str} and current {ref_date_str}"
            )

        return None

    def _classify_single_date(self, target_date: date, ref_date: date, reason: str) -> TemporalResolution:
        """Classifies a validated single date relative to reference date."""
        date_str = target_date.strftime("%Y-%m-%d")
        if target_date == ref_date:
            return TemporalResolution(
                mode=TemporalMode.LIVE,
                date_str=date_str,
                reason=f"{reason}: Matches reference date (LIVE)"
            )
        elif target_date < ref_date:
            return TemporalResolution(
                mode=TemporalMode.HISTORICAL,
                date_str=date_str,
                reason=f"{reason}: Before reference date (HISTORICAL)"
            )
        else:
            return TemporalResolution(
                mode=TemporalMode.UNSUPPORTED_FUTURE,
                date_str=date_str,
                reason=f"{reason}: After reference date (UNSUPPORTED_FUTURE)"
            )

    def _parse_date_expression(self, expr: str, ref_date: date) -> Optional[date]:
        """Parses a date expression string into a date object."""
        expr_clean = expr.strip().lower()
        if expr_clean in ("today", "now", "current"):
            return ref_date
        if expr_clean == "tomorrow":
            return ref_date + timedelta(days=1)
        if expr_clean == "yesterday":
            return ref_date - timedelta(days=1)

        # Try ISO format
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", expr_clean):
            try:
                return datetime.strptime(expr_clean, "%Y-%m-%d").date()
            except ValueError:
                return None

        # Try natural date
        return self._extract_natural_date(expr_clean)

    def _extract_date_from_text(self, text: str, ref_date: date) -> Optional[date]:
        """Finds any date mentioned in arbitrary text."""
        # Tomorrow
        if re.search(r"\btomorrow\b", text):
            return ref_date + timedelta(days=1)
        # Yesterday
        if re.search(r"\byesterday\b", text):
            return ref_date - timedelta(days=1)

        # ISO format YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if iso_match:
            try:
                return datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
            except ValueError:
                pass

        # Natural date e.g. October 15, 2025
        return self._extract_natural_date(text)

    def _extract_natural_date(self, text: str) -> Optional[date]:
        """Matches patterns like 'October 15 2025', 'October 15, 2025', '15 October 2025'."""
        months_regex = "|".join(MONTH_NAMES.keys())

        # Pattern: Month Day Year (e.g., 'October 15, 2025' or 'oct 15 2025')
        m_d_y = re.search(rf"\b({months_regex})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", text)
        if m_d_y:
            m_str, d_str, y_str = m_d_y.group(1), m_d_y.group(2), m_d_y.group(3)
            month = MONTH_NAMES.get(m_str)
            try:
                return date(int(y_str), month, int(d_str))
            except ValueError:
                pass

        # Pattern: Day Month Year (e.g., '15 October 2025')
        d_m_y = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({months_regex}),?\s+(\d{{4}})\b", text)
        if d_m_y:
            d_str, m_str, y_str = d_m_y.group(1), d_m_y.group(2), d_m_y.group(3)
            month = MONTH_NAMES.get(m_str)
            try:
                return date(int(y_str), month, int(d_str))
            except ValueError:
                pass

        return None
