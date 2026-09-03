"""
router.py

LLM-based Intent Classifier for the ORCA Coordinator (Step 12 & Step 20).

Responsibility:
  - Take a natural language user query.
  - Determine which domain capabilities are required:
      'habitat', 'weather', 'geofencing', 'fishing_decision'.
  - Output ONLY a structured JSON list of capabilities.
  - Return an empty list if the query is completely unrelated.
"""

import json
import logging
import re
from typing import List, Optional, Any

import groq

from ..config import GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER
from .schemas import RoutingInfo

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Intent Router for the Blue Orbit ORCA system, a multi-agent decision support tool for fishermen on the Indian West Coast.

The system supports four domain capabilities:
- 'habitat' : Assesses environmental conditions (temperature, chlorophyll) to determine fishing potential.
- 'weather' : Assesses marine weather (wind speed, wave height) to determine safety risk for going out to sea.
- 'geofencing' : Assesses geographic position relative to the Indian Exclusive Economic Zone (EEZ) boundary.
- 'fishing_decision' : Unified fishing recommendation synthesizing habitat suitability, weather safety, and EEZ boundary status (e.g. "Can I go fishing today?", "Is it a good day for fishing?", "Should I go fishing near Goa?", "Can I fish here?", "How are fishing conditions?").

Your job is to read the user's natural language request and determine which of these capabilities they need.

EXAMPLES:
1. User: "Can I go fishing today?" -> ['fishing_decision']
2. User: "Is it a good day for fishing?" -> ['fishing_decision']
3. User: "Should I go fishing near Goa?" -> ['fishing_decision']
4. User: "Can I fish from here?" -> ['fishing_decision']
5. User: "How are the fishing conditions today?" -> ['fishing_decision']
6. User: "Is the fish habitat good here?" -> ['habitat']
7. User: "How is the weather today?" -> ['weather']
8. User: "Are we in international waters?" -> ['geofencing']
9. User: "Tell me about this place." -> [] (Ambiguous/insufficient info)
10. User: "What is the capital of India?" -> [] (Unrelated)

RULES:
- You must output ONLY a JSON object containing a 'requested_capabilities' key mapped to a list of strings.
- Valid strings are exactly 'habitat', 'weather', 'geofencing', and 'fishing_decision'.
- If the query is ambiguous, unrelated, or you cannot determine intent, output an empty list [].
- DO NOT invent any other capabilities.
- DO NOT include explanations, markdown formatting outside the JSON, or conversational filler.
"""


class OrcaRouter:
    """
    LLM Intent Classifier to route user queries to the correct domain agents.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        if LLM_PROVIDER != "groq":
            raise ValueError(
                f"LLM_PROVIDER '{LLM_PROVIDER}' is not supported. Currently only 'groq' is implemented."
            )

        if llm_client is not None:
            self._llm = llm_client
        else:
            if not GROQ_API_KEY:
                raise EnvironmentError(
                    "GROQ_API_KEY is not set. Please add it to backend/.env."
                )
            self._llm = groq.Groq(api_key=GROQ_API_KEY)

        self._model = LLM_MODEL

    def get_capabilities(self, query_text: str) -> List[str]:
        """
        Determines the required capabilities based on the user's query.

        Args:
            query_text: The user's natural language request.

        Returns:
            A list of required capability strings (subset of 'habitat', 'weather', 'geofencing', 'fishing_decision').
        """
        if not query_text or not query_text.strip():
            return []

        clean = query_text.lower().strip()

        # Fast deterministic path for unambiguous unified fishing queries
        decision_patterns = [
            r"\bcan i go fishing\b",
            r"\bshould i go fishing\b",
            r"\bis it a good day for fishing\b",
            r"\bis today good for fishing\b",
            r"\bcan i fish\b",
            r"\bshould i fish\b",
            r"\bis fishing recommended\b",
            r"\bhow are (the )?fishing conditions\b",
            r"\bare conditions good for fishing\b",
            r"\bgood day to fish\b",
            r"\bfishing recommendation\b",
        ]
        if any(re.search(pat, clean) for pat in decision_patterns):
            # Check if it was purely a habitat query like "habitat for fishing"
            if not re.search(r"\b(habitat suitability|sea temperature|chlorophyll)\b", clean):
                return ["fishing_decision"]

        try:
            chat_completion = self._llm.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query_text},
                ],
                model=self._model,
                temperature=0.1,  # Low temperature for deterministic routing
                max_tokens=64,
                response_format={"type": "json_object"},
            )

            raw_response = chat_completion.choices[0].message.content
            parsed = json.loads(raw_response)
            capabilities = parsed.get("requested_capabilities", [])

            valid_caps = {"habitat", "weather", "geofencing", "fishing_decision"}
            return [c for c in capabilities if c in valid_caps]

        except Exception as e:
            logger.warning(f"Router LLM call failed or returned invalid JSON: {e}")
            return []
