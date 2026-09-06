"""
router.py

Multi-Stakeholder Intent Classifier & Capability Router for Blue Orbit / ORCA (Step 23).
Routes queries across Fishermen, Coast Guards, and Researchers without forcing
a universal fishing decision.
"""

import json
import logging
import re
from typing import List, Optional, Any, Tuple

import groq

from ..config import GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER
from .schemas import IntentEnum, IntelligenceDomainEnum, RoutingInfo

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Multi-Stakeholder Intent Router for Blue Orbit / ORCA, a coastal and marine intelligence platform supporting Fishermen, Coast Guards, and Researchers along the Indian West Coast.

The user may ask questions in English, Telugu, Hindi, or Marathi. Mentally translate the query to English before classifying.
Determine both the user's INTENT and the minimal necessary CAPABILITIES.

Possible Intents:
- 'FISHING_SUPPORT': User wants fishing-specific guidance ("Can I fish?", "Is it a good day to fish?", "Fishing potential").
- 'MARITIME_SAFETY': User wants sea-state and navigational hazard assessment ("Is the sea dangerous?", "Wave risk", "Safe to sail?").
- 'SEVERE_WEATHER': User asks about verified cyclones, depressions, or official weather warnings ("Is there a cyclone?", "Storm alerts").
- 'MARINE_ANALYSIS': User asks for scientific/oceanographic variables ("What is the SST?", "Chlorophyll concentration").
- 'ENVIRONMENTAL_ANALYSIS': User asks for environmental/habitat suitability indicators without fishing claims.
- 'SPATIAL_QUERY': User asks about Indian EEZ, borders, or proximity ("Are we in international waters?", "Distance to EEZ").
- 'TEMPORAL_COMPARISON': User compares marine observations across dates or locations ("Compare SST between Oct 1 and Oct 15").
- 'ROUTING_NAVIGATION': User wants to find a route from start to destination ("Route me to Goa", "Find a safe route from Mumbai to Ratnagiri").
- 'GENERAL_COASTAL_QUERY': Broad sector overview inquiries ("What is happening in this area?", "Tell me about this sector").
- 'UNKNOWN': Ambiguous, greeting, or off-topic questions.

Possible Capabilities:
'habitat', 'weather', 'geofencing', 'fishing_decision', 'cyclone', 'routing'.

CRITICAL RULE: DO NOT over-call capabilities. Only include what the intent genuinely requires.
- Cyclone queries require ONLY 'cyclone'.
- Research queries require ONLY 'habitat' (or 'habitat' + comparison).
- Maritime safety requires 'weather', 'geofencing', and optionally 'cyclone'.

Output format (JSON only):
{
  "intent": "FISHING_SUPPORT",
  "requested_capabilities": ["fishing_decision"]
}
"""


class OrcaRouter:
    """
    Multi-Stakeholder Intent Router that classifies user queries into explicit
    intents and maps them to minimal required capabilities.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        self._llm = None
        if llm_client is not None:
            self._llm = llm_client
        elif GROQ_API_KEY and LLM_PROVIDER == "groq":
            try:
                self._llm = groq.Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

        self._model = LLM_MODEL

    def classify_intent(self, query_text: str) -> Tuple[str, str, List[str]]:
        """
        Determines the intent, intelligence domain, and minimal required capabilities.

        Returns:
            Tuple of (intent: str, domain: str, capabilities: List[str])
        """
        if not query_text or not query_text.strip():
            return IntentEnum.UNKNOWN.value, IntelligenceDomainEnum.COASTAL_OVERVIEW.value, []

        clean = query_text.lower().strip()

        # -------------------------------------------------------------
        # 1. Fast Deterministic Routing Engine (Zero API latency / offline resilient)
        # -------------------------------------------------------------

        # A. Severe Weather / Cyclone Intent
        cyclone_patterns = [
            r"\bcyclone\b",
            r"\bdepression\b",
            r"\btropical storm\b",
            r"\bsevere weather\b",
            r"\bstorm alert\b",
            r"\bcyclone alert\b",
            r"\bweather warning\b",
            r"\bstorm activity\b",
            r"\bcyclone effects\b",
        ]
        if any(re.search(pat, clean) for pat in cyclone_patterns):
            # Pure severe weather query -> invoke ONLY cyclone capability
            return (
                IntentEnum.SEVERE_WEATHER.value,
                IntelligenceDomainEnum.SEVERE_WEATHER.value,
                ["cyclone"],
            )

        # B. Temporal Comparison Intent
        comparison_patterns = [
            r"\bcompare\b",
            r"\bcomparison\b",
            r"\bversus\b",
            r"\bvs\b",
            r"\bdifference between\b",
        ]
        if any(re.search(pat, clean) for pat in comparison_patterns):
            return (
                IntentEnum.TEMPORAL_COMPARISON.value,
                IntelligenceDomainEnum.TEMPORAL.value,
                ["habitat"],
            )

        # C. Fishing Support Intent (Unambiguous fishing decisions)
        fishing_patterns = [
            r"\bcan i (go )?fish\b",
            r"\bshould i (go )?fish\b",
            r"\bgood (day )?to fish\b",
            r"\bgood for fishing\b",
            r"\bfishing recommendation\b",
            r"\bfishing conditions\b",
            r"\bare conditions good for fishing\b",
            r"\bcan i go fishing\b",
            r"\bfishing potential\b",
            r"\bfishing advice\b",
            r"\bgo out fishing\b",
        ]
        if any(re.search(pat, clean) for pat in fishing_patterns):
            # If not asking purely for scientific SST / Chlorophyll
            if not re.search(r"\b(sst|sea surface temperature|chlorophyll)\b", clean):
                return (
                    IntentEnum.FISHING_SUPPORT.value,
                    IntelligenceDomainEnum.FISHING.value,
                    ["fishing_decision"],
                )

        # D. Maritime Safety Intent
        safety_patterns = [
            r"\bis the sea dangerous\b",
            r"\bis (it|the sea) safe\b",
            r"\bsea conditions?\b",
            r"\bsea state (risk|safety|condition)\b",
            r"\brough sea\b",
            r"\bhigh waves?\b",
            r"\bmarine risk\b",
            r"\bnavigational risk\b",
            r"\bsafe to sail\b",
            r"\bsafe for navigation\b",
            r"\bdanger at sea\b",
            r"\bweather risk\b",
            r"\bweather safety\b",
        ]
        if any(re.search(pat, clean) for pat in safety_patterns):
            return (
                IntentEnum.MARITIME_SAFETY.value,
                IntelligenceDomainEnum.MARITIME_SAFETY.value,
                ["weather", "geofencing", "cyclone"],
            )

        # E. Marine Analysis Intent (SST, Chlorophyll, Oceanographic parameters)
        marine_patterns = [
            r"\bsst\b",
            r"\bsea surface temperature\b",
            r"\bchlorophyll\b",
            r"\bwater temperature\b",
            r"\bocean temperature\b",
            r"\bmarine observation\b",
        ]
        if any(re.search(pat, clean) for pat in marine_patterns):
            return (
                IntentEnum.MARINE_ANALYSIS.value,
                IntelligenceDomainEnum.MARINE.value,
                ["habitat"],
            )

        # F. Environmental Analysis Intent
        env_patterns = [
            r"\bhabitat suitability\b",
            r"\benvironmental suitability\b",
            r"\bhabitat score\b",
            r"\benvironmental condition\b",
            r"\bhabitat condition\b",
            r"\bhabitat potential\b",
            r"\bfish habitat\b",
        ]
        if any(re.search(pat, clean) for pat in env_patterns):
            return (
                IntentEnum.ENVIRONMENTAL_ANALYSIS.value,
                IntelligenceDomainEnum.MARINE.value,
                ["habitat"],
            )

        # G. Spatial / Geofencing Intent
        spatial_patterns = [
            r"\beez\b",
            r"\bindian eez\b",
            r"\bexclusive economic zone\b",
            r"\binternational waters\b",
            r"\bboundary\b",
            r"\bgeofence\b",
            r"\bdistance to line\b",
            r"\bdistance to boundary\b",
            r"\bboundary status\b",
        ]
        if any(re.search(pat, clean) for pat in spatial_patterns):
            return (
                IntentEnum.SPATIAL_QUERY.value,
                IntelligenceDomainEnum.GEOSPATIAL.value,
                ["geofencing"],
            )

        # H. Weather Intelligence Intent
        weather_patterns = [
            r"\bweather today\b",
            r"\bhow is the weather\b",
            r"\bwind speed\b",
            r"\bwave height\b",
            r"\bwind and waves\b",
            r"\bsurface pressure\b",
            r"\bweather forecast\b",
            r"\bmarine weather\b",
            r"\bవాతావరణం\b",       # Telugu: weather
            r"\bvathavaranam\b",
            r"\bmausam\b",          # Hindi: weather
            r"\bhavaman\b",         # Marathi: weather
            r"\bహవామాన్\b",
            r"\bమౌసమ్\b",
        ]
        if any(re.search(pat, clean) for pat in weather_patterns):
            return (
                IntentEnum.MARITIME_SAFETY.value,
                IntelligenceDomainEnum.WEATHER.value,
                ["weather"],
            )

        # H.5 Routing & Navigation Intent
        routing_patterns = [
            r"\broute me\b",
            r"\bfind a route\b",
            r"\bsafe route\b",
            r"\bnavigate to\b",
            r"\bhow can i safely travel\b",
            r"\bplan a (marine )?route\b",
            r"\bsafest route\b",
            r"\bshortest route\b",
            r"\broute from\b"
        ]
        if any(re.search(pat, clean) for pat in routing_patterns):
            return (
                IntentEnum.ROUTING_NAVIGATION.value,
                IntelligenceDomainEnum.NAVIGATION.value,
                ["routing"],
            )

        # I. General Coastal Query Intent (Sector Overview)
        general_patterns = [
            r"\bwhat is happening (in|at|near|along)\b",
            r"\btell me about this (area|sector|place|location)\b",
            r"\bsector overview\b",
            r"\bcoastal overview\b",
            r"\bwhat's happening\b",
            r"\barea overview\b",
            r"\boverview of this\b",
        ]
        if any(re.search(pat, clean) for pat in general_patterns):
            return (
                IntentEnum.GENERAL_COASTAL_QUERY.value,
                IntelligenceDomainEnum.COASTAL_OVERVIEW.value,
                ["habitat", "weather", "geofencing", "cyclone"],
            )

        # -------------------------------------------------------------
        # 2. LLM Intent Classifier Fallback (if Groq is available)
        # -------------------------------------------------------------
        if self._llm:
            try:
                chat_completion = self._llm.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query_text},
                    ],
                    model=self._model,
                    temperature=0.1,
                    max_tokens=64,
                    response_format={"type": "json_object"},
                )

                raw_response = chat_completion.choices[0].message.content
                parsed = json.loads(raw_response)
                intent = parsed.get("intent", IntentEnum.UNKNOWN.value)
                capabilities = parsed.get("requested_capabilities", [])

                valid_caps = {"habitat", "weather", "geofencing", "fishing_decision", "cyclone", "routing"}
                caps = [c for c in capabilities if c in valid_caps]

                # Map intent to domain
                domain_map = {
                    IntentEnum.FISHING_SUPPORT.value: IntelligenceDomainEnum.FISHING.value,
                    IntentEnum.MARITIME_SAFETY.value: IntelligenceDomainEnum.MARITIME_SAFETY.value,
                    IntentEnum.SEVERE_WEATHER.value: IntelligenceDomainEnum.SEVERE_WEATHER.value,
                    IntentEnum.MARINE_ANALYSIS.value: IntelligenceDomainEnum.MARINE.value,
                    IntentEnum.ENVIRONMENTAL_ANALYSIS.value: IntelligenceDomainEnum.MARINE.value,
                    IntentEnum.SPATIAL_QUERY.value: IntelligenceDomainEnum.GEOSPATIAL.value,
                    IntentEnum.TEMPORAL_COMPARISON.value: IntelligenceDomainEnum.TEMPORAL.value,
                    IntentEnum.ROUTING_NAVIGATION.value: IntelligenceDomainEnum.NAVIGATION.value,
                    IntentEnum.GENERAL_COASTAL_QUERY.value: IntelligenceDomainEnum.COASTAL_OVERVIEW.value,
                }
                domain = domain_map.get(intent, IntelligenceDomainEnum.COASTAL_OVERVIEW.value)
                return intent, domain, caps
            except Exception as e:
                logger.warning(f"Router LLM classification failed: {e}")

        # Fallback for unrecognized query
        return IntentEnum.UNKNOWN.value, IntelligenceDomainEnum.COASTAL_OVERVIEW.value, []

    def get_capabilities(self, query_text: str) -> List[str]:
        """
        Backwards-compatible interface.
        Returns the list of requested capabilities.
        """
        _, _, capabilities = self.classify_intent(query_text)
        return capabilities


# Alias for backward compatibility
OrcaQueryRouter = OrcaRouter
