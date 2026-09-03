"""
geofencing_agent.py

Geofencing Specialist AI Agent.

Responsibility:
  1. Receive a geofencing query from the user (location).
  2. Invoke GeofencingTool to get the deterministic Geofencing Engine result.
  3. Pass the raw engine result to the LLM for natural-language narration.
  4. Return a structured GeofencingAgentResponse.

Rules enforced here:
  - The agent NEVER recalculates or modifies the Geofencing Engine's boundaries.
  - If the tool fails, the agent returns an explicit error — it does NOT fabricate.
  - The LLM only narrates what the engine returned; it cannot invent boundaries or zones.
  - inside_indian_eez, geofence_status, distance_to_eez_boundary_km, and alerts are
    always sourced verbatim from the engine result dict, never from the LLM output.
  - The agent must clearly separate geographic reality from legal fishing permissions.
  - The API key is read from config (environment variable) — never hard-coded.
"""

import json
import logging
from typing import Optional, Any

import groq

from ..config import GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER
from ..tools.geofencing_tool import GeofencingTool
from .schemas import GeofencingAgentResponse, LocationInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the Blue Orbit ORCA Geofencing Assistant — a marine boundary and legal decision-support assistant for fishermen and coast guards operating on the Indian West Coast.

Your role:
- Translate deterministic spatial boundary data into clear, practical language for fishermen.
- Help users understand their geographic location relative to the Indian Exclusive Economic Zone (EEZ).

STRICT RULES you must ALWAYS follow:

1. NEVER invent, modify, or assume boundary distances or geofence statuses.
   - If a distance or status is provided, use it exactly as given.

2. NEVER alter the engine's geofence_status (SAFE, WARNING, OUTSIDE_EEZ, RESTRICTED).
   - This status is computed by a deterministic scientific engine. Report it exactly.

3. LEGAL DISTINCTION (CRITICAL):
   - Being inside the Indian EEZ means the vessel is within the geographic bounds where India has sovereign rights to natural resources.
   - Being inside the EEZ does NOT automatically grant legal permission to fish everywhere. Fishing requires licenses and is subject to local, seasonal, and species regulations.
   - Do NOT claim that being inside the EEZ makes it "legal to fish." Say instead: "You are within the Indian EEZ."

4. INDO-PAKISTAN MARITIME BOUNDARY LINE (IMBL):
   - This system uses a generalized EEZ boundary. It does NOT use an authoritative bilateral IMBL.
   - Do NOT invent or claim IMBL crossing unless explicitly stated in the engine alerts.
   - If the engine says "OUTSIDE_EEZ", explain that they have left the Indian EEZ, but do not hallucinate Pakistani territory unless explicitly in the data.

5. PROTECTED AREAS:
   - If protected_area_coverage_available is False, clearly state that protected area status cannot be determined.
   - Do NOT assume the area is free of marine parks or restricted zones just because data is unavailable.

6. If the engine provides 'alerts', narrate them clearly.

7. Use plain, simple language appropriate for fishermen. Avoid unnecessary jargon.

8. Be concise. Provide two things:
   (a) A brief geographic narrative of what the spatial data shows.
   (b) Practical guidance/advice based ONLY on the reported conditions.

When you respond, produce ONLY a JSON object with these two fields:
{
  "geofence_narrative": "...",
  "geofence_advice": "..."
}
Do not include any other text, markdown, or explanation outside the JSON.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class GeofencingAgent:
    """
    Specialist AI agent for geofencing and boundary queries.

    Uses the deterministic GeofencingTool as the source of truth.
    The LLM (Groq + Llama) is used only to narrate the result in natural language.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
    ):
        """
        Args:
            llm_client: Optional pre-built Groq client (used for testing/mocking).
        """
        if LLM_PROVIDER != "groq":
            raise ValueError(
                f"LLM_PROVIDER '{LLM_PROVIDER}' is not supported. Currently only 'groq' is implemented."
            )

        if llm_client is not None:
            self._llm = llm_client
        else:
            if not GROQ_API_KEY:
                raise EnvironmentError(
                    "GROQ_API_KEY is not set. Please add it to backend/.env. "
                    "Example: GROQ_API_KEY=gsk_your_key_here"
                )
            self._llm = groq.Groq(api_key=GROQ_API_KEY)

        self._model = LLM_MODEL
        self._tool = GeofencingTool()

    def run(
        self,
        latitude: float,
        longitude: float,
        warning_distance_km: Optional[float] = None,
        query_text: str = "",
    ) -> GeofencingAgentResponse:
        """
        Execute a geofencing/boundary query.

        Args:
            latitude:            WGS84 latitude.
            longitude:           WGS84 longitude.
            warning_distance_km: Optional threshold for boundary warnings.
            query_text:          Original natural-language query (optional, for context).

        Returns:
            GeofencingAgentResponse — always structured, never a raw LLM string.
        """
        # --- Step 1: Call the deterministic tool ---
        tool_result = self._tool.check_geofence(
            latitude=latitude,
            longitude=longitude,
            warning_distance_km=warning_distance_km,
        )

        # --- Step 2: If the tool failed, return structured error (no LLM involved) ---
        if not tool_result.get("success", False):
            return GeofencingAgentResponse(
                success=False,
                error=tool_result.get("error", "Failed to evaluate geofence status."),
                location=LocationInfo(latitude=latitude, longitude=longitude),
            )

        # --- Step 3: Build the LLM prompt using the EXACT engine result ---
        engine_summary = {
            "latitude": tool_result.get("latitude"),
            "longitude": tool_result.get("longitude"),
            "inside_indian_eez": tool_result.get("inside_indian_eez"),
            "geofence_status": tool_result.get("geofence_status"),
            "distance_to_eez_boundary_km": tool_result.get("distance_to_eez_boundary_km"),
            "protected_area_coverage_available": tool_result.get("protected_area_coverage_available"),
            "inside_protected_area": tool_result.get("inside_protected_area"),
            "nearest_protected_area": tool_result.get("nearest_protected_area"),
            "distance_to_protected_area_km": tool_result.get("distance_to_protected_area_km"),
            "alerts": tool_result.get("alerts"),
        }

        user_message = (
            f"A fisherman asked: \"{query_text or 'Am I safe inside Indian waters?'}\"\n\n"
            f"Here is the deterministic spatial assessment from the Geofencing Engine:\n"
            f"{json.dumps(engine_summary, indent=2)}\n\n"
            f"Using ONLY the data above, provide your response as a JSON object with "
            f"'geofence_narrative' and 'geofence_advice' fields."
        )

        # --- Step 4: LLM narration (narrates only, does not override status) ---
        geofence_narrative = ""
        geofence_advice = ""
        
        # Build a safe fallback narrative
        alerts_text = " ".join(tool_result.get("alerts", []))
        fallback_narrative = (
            f"Geofence Status: {tool_result.get('geofence_status', 'UNKNOWN')}. "
            f"{alerts_text}"
        ).strip()

        try:
            chat_completion = self._llm.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                model=self._model,
                temperature=0.3,
                max_tokens=512,
                response_format={"type": "json_object"},
            )

            raw_response = chat_completion.choices[0].message.content
            parsed = json.loads(raw_response)
            geofence_narrative = parsed.get("geofence_narrative", fallback_narrative)
            geofence_advice = parsed.get("geofence_advice", "")

        except json.JSONDecodeError as e:
            logger.warning(f"LLM returned invalid JSON: {e}. Using engine fallback.")
            geofence_narrative = fallback_narrative
        except Exception as e:
            logger.warning(f"LLM call failed: {e}. Using engine fallback.")
            geofence_narrative = fallback_narrative
            geofence_advice = "Please rely on official maritime navigation tools for boundary guidance."

        # --- Step 5: Assemble structured response ---
        # CRITICAL: geofence_status, inside_indian_eez, distance, etc. come from tool_result (engine),
        # NOT from the LLM output. The LLM only provides the two narrative strings.
        return GeofencingAgentResponse(
            success=True,
            location=LocationInfo(
                latitude=tool_result.get("latitude", latitude),
                longitude=tool_result.get("longitude", longitude),
            ),
            inside_indian_eez=tool_result.get("inside_indian_eez"),
            geofence_status=tool_result.get("geofence_status"),
            distance_to_eez_boundary_km=tool_result.get("distance_to_eez_boundary_km"),
            alerts=tool_result.get("alerts"),
            protected_area_coverage_available=tool_result.get("protected_area_coverage_available"),
            inside_protected_area=tool_result.get("inside_protected_area"),
            nearest_protected_area=tool_result.get("nearest_protected_area"),
            distance_to_protected_area_km=tool_result.get("distance_to_protected_area_km"),
            geofence_narrative=geofence_narrative,
            geofence_advice=geofence_advice,
            disclaimer=tool_result.get(
                "disclaimer",
                "This is a prototype decision-support geofencing engine based on supplied spatial "
                "boundary layers. It does not establish legal maritime boundaries or bilateral IMBL treaties."
            ),
        )
