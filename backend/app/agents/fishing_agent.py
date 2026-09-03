"""
fishing_agent.py

Fishing / Habitat Specialist AI Agent.

Responsibility:
  1. Receive a fishing/habitat query from the user.
  2. Invoke HabitatTool to get the deterministic Habitat Engine result.
  3. Pass the raw engine result to the LLM for natural-language narration.
  4. Return a structured FishingAgentResponse.

Rules enforced here:
  - The agent NEVER recalculates or modifies the Habitat Engine's scores.
  - If the tool fails, the agent returns an explicit error — it does NOT fabricate.
  - The LLM only narrates what the engine returned; it cannot invent measurements.
  - The API key is read from config (environment variable) — never hard-coded.
"""

import json
import logging
from typing import Optional, Dict, Any

import groq

from ..config import GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER
from ..tools.habitat_tool import HabitatTool
from ..services.temporal_resolver import TemporalResolution, TemporalMode
from .schemas import (
    FishingAgentResponse,
    LocationInfo,
    EnvironmentalSummary,
    ComparisonResult,
    ComparisonData,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the Blue Orbit ORCA Fishing Assistant — a marine environmental decision-support assistant for fishermen and coast guards operating on the Indian West Coast.

Your role:
- Translate scientific environmental assessments into clear, practical language for fishermen.
- Help users understand what the environmental conditions mean for fishing potential.

STRICT RULES you must ALWAYS follow:

1. NEVER invent, modify, or assume environmental measurements.
   - If a temperature or chlorophyll value is provided, use it exactly as given.
   - If a value is missing (null/None), say so clearly.

2. NEVER alter the numerical habitat suitability score (overall_suitability_score).
   - The score is computed by a deterministic scientific engine. Report it exactly.

3. NEVER claim that a high habitat suitability score guarantees fish presence or a successful catch.
   - Always make it clear: suitability is based on environmental indicators, not direct fish detection.

4. NEVER invent SST gradients, thermal fronts, upwelling zones, PFZ targets, or fish abundance data
   unless those values are explicitly provided to you by the engine result.

5. Clearly distinguish between:
   (a) Measured environmental conditions (temperature, chlorophyll)
   (b) Calculated suitability scores (derived from the conditions)
   (c) Practical interpretation (what this means for a fisherman)

6. If data quality is "No environmental data" or "Missing Temperature" or "Missing Chlorophyll",
   clearly communicate the uncertainty. Do not assume or fill in the gaps.

7. If the fishing potential is "Insufficient Data", do NOT give fishing advice.
   Instead, explain that reliable environmental data was not available for this location/date.

8. Always respect the engine disclaimer: this is a prototype model, not a scientific guarantee.

9. Use plain, simple language appropriate for fishermen. Avoid unnecessary jargon.

10. Be concise. Provide two things:
    (a) A brief scientific explanation of what the environmental data shows.
    (b) Practical fishing advice based ONLY on the reported conditions.

When you respond, produce ONLY a JSON object with these two fields:
{
  "scientific_explanation": "...",
  "fisherman_advice": "..."
}
Do not include any other text, markdown, or explanation outside the JSON.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class FishingHabitatAgent:
    """
    Specialist AI agent for fishing/habitat suitability queries.

    Uses the deterministic HabitatTool as the source of truth.
    The LLM (Groq + Llama) is used only to narrate the result in natural language.
    """

    def __init__(
        self,
        live_mode: Optional[bool] = None,
        llm_client: Optional[Any] = None,
    ):
        """
        Args:
            live_mode: Provider mode. None = read from config (default: cache mode).
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
        self._tool = HabitatTool(live_mode=live_mode)

    def run(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
        query_text: str = "",
        temporal_resolution: Optional[TemporalResolution] = None,
        temporal_mode: Optional[TemporalMode] = None,
    ) -> FishingAgentResponse:
        """
        Execute a fishing/habitat suitability query.

        Args:
            latitude:   WGS84 latitude.
            longitude:  WGS84 longitude.
            date_str:   Date as 'YYYY-MM-DD'.
            query_text: Original natural-language query (optional, for context).
            temporal_resolution: Optional full TemporalResolution from coordinator.
            temporal_mode: Optional explicit TemporalMode.

        Returns:
            FishingAgentResponse — always structured, never a raw LLM string.
        """
        # Determine mode from temporal_resolution if provided
        active_mode = temporal_mode
        if active_mode is None and temporal_resolution is not None:
            active_mode = temporal_resolution.mode

        # ------------------------------------------------------------------
        # Comparison Path
        # ------------------------------------------------------------------
        if temporal_resolution is not None and temporal_resolution.is_comparison:
            hist_date = temporal_resolution.historical_date or date_str
            curr_date = temporal_resolution.current_date or date_str

            comp_result = self._tool.compare_habitat_comparison(
                latitude=latitude,
                longitude=longitude,
                historical_date=hist_date,
                current_date=curr_date,
            ) if hasattr(self._tool, "compare_habitat_comparison") else self._tool.compare_habitat_suitability(
                latitude=latitude,
                longitude=longitude,
                historical_date=hist_date,
                current_date=curr_date,
            )

            if not comp_result.get("success", False):
                return FishingAgentResponse(
                    success=False,
                    error=comp_result.get("error", "Failed to execute habitat comparison."),
                    location=LocationInfo(latitude=latitude, longitude=longitude),
                    date=f"{hist_date} vs {curr_date}",
                    temporal_mode=TemporalMode.COMPARISON.value,
                )

            comparison_obj = ComparisonResult(
                type="comparison",
                historical=ComparisonData(
                    date=hist_date,
                    result=comp_result["historical"]["result"]
                ),
                current=ComparisonData(
                    date=curr_date,
                    result=comp_result["current"]["result"]
                ),
            )

            # LLM narration for comparison
            user_message = (
                f"A fisherman asked: \"{query_text or 'Compare conditions'}\"\n\n"
                f"Here are the two independent environmental assessments:\n"
                f"Historical ({hist_date}): {json.dumps(comp_result['historical']['result'], indent=2)}\n\n"
                f"Current ({curr_date}): {json.dumps(comp_result['current']['result'], indent=2)}\n\n"
                f"Using ONLY the data above, describe the differences in environmental conditions "
                f"and practical fishing advice as a JSON object with 'scientific_explanation' and 'fisherman_advice' fields."
            )

            scientific_explanation = "Historical and current habitat suitability comparison calculated."
            fisherman_advice = ""
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
                parsed = json.loads(chat_completion.choices[0].message.content)
                scientific_explanation = parsed.get("scientific_explanation", scientific_explanation)
                fisherman_advice = parsed.get("fisherman_advice", "")
            except Exception as e:
                logger.warning(f"Comparison LLM narration failed: {e}")
                fisherman_advice = "Comparison completed using deterministic engine data."

            return FishingAgentResponse(
                success=True,
                location=LocationInfo(latitude=latitude, longitude=longitude),
                date=f"{hist_date} vs {curr_date}",
                temporal_mode=TemporalMode.COMPARISON.value,
                comparison=comparison_obj,
                scientific_explanation=scientific_explanation,
                fisherman_advice=fisherman_advice,
                disclaimer="This is a prototype heuristic habitat suitability comparison based on environmental indicators.",
            )

        # ------------------------------------------------------------------
        # Standard Single-Date Path
        # ------------------------------------------------------------------
        # --- Step 1: Call the deterministic tool ---
        tool_result = self._tool.get_habitat_suitability(
            latitude=latitude,
            longitude=longitude,
            date_str=date_str,
            temporal_mode=active_mode,
            query_text=query_text,
        )

        # --- Step 2: If the tool failed, return structured error (no LLM involved) ---
        if not tool_result.get("success", False):
            return FishingAgentResponse(
                success=False,
                error=tool_result.get("error", "Failed to retrieve habitat suitability data."),
                location=LocationInfo(latitude=latitude, longitude=longitude),
                date=date_str,
                temporal_mode=tool_result.get("temporal_mode", active_mode.value if active_mode else None),
            )

        # --- Step 3: Build the LLM prompt using the EXACT engine result ---
        engine_summary = {
            "latitude": tool_result.get("latitude"),
            "longitude": tool_result.get("longitude"),
            "date": tool_result.get("date"),
            "temperature_c": tool_result.get("temperature_c"),
            "chlorophyll_mg_m3": tool_result.get("chlorophyll_mg_m3"),
            "temperature_score": tool_result.get("temperature_score"),
            "chlorophyll_score": tool_result.get("chlorophyll_score"),
            "overall_suitability_score": tool_result.get("overall_suitability_score"),
            "fishing_potential": tool_result.get("fishing_potential"),
            "data_quality": tool_result.get("data_quality"),
            "confidence": tool_result.get("confidence"),
            "engine_explanation": tool_result.get("explanation"),
        }

        user_message = (
            f"A fisherman asked: \"{query_text or 'What is the fishing potential at this location?'}\"\n\n"
            f"Here is the deterministic environmental assessment from the Habitat Engine:\n"
            f"{json.dumps(engine_summary, indent=2)}\n\n"
            f"Using ONLY the data above, provide your response as a JSON object with "
            f"'scientific_explanation' and 'fisherman_advice' fields."
        )

        # --- Step 4: LLM narration (narrates only, does not recalculate) ---
        scientific_explanation = tool_result.get("explanation", "")
        fisherman_advice = ""

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
            scientific_explanation = parsed.get("scientific_explanation", scientific_explanation)
            fisherman_advice = parsed.get("fisherman_advice", "")

        except json.JSONDecodeError as e:
            logger.warning(f"LLM returned invalid JSON: {e}. Using engine explanation fallback.")
        except Exception as e:
            logger.warning(f"LLM call failed: {e}. Using engine explanation fallback.")
            # Graceful degradation: return engine result without LLM narration
            fisherman_advice = (
                f"Based on available environmental data, fishing potential is rated as "
                f"{tool_result.get('fishing_potential', 'Unknown')}. "
                f"Please consult a local expert for fishing advice."
            )

        # --- Step 5: Assemble structured response ---
        return FishingAgentResponse(
            success=True,
            location=LocationInfo(
                latitude=tool_result.get("latitude", latitude),
                longitude=tool_result.get("longitude", longitude),
            ),
            date=tool_result.get("date", date_str),
            temporal_mode=tool_result.get("temporal_mode", active_mode.value if active_mode else None),
            habitat_score=tool_result.get("overall_suitability_score"),
            fishing_potential=tool_result.get("fishing_potential"),
            confidence=tool_result.get("confidence"),
            data_quality=tool_result.get("data_quality"),
            environmental_summary=EnvironmentalSummary(
                temperature_c=tool_result.get("temperature_c"),
                chlorophyll_mg_m3=tool_result.get("chlorophyll_mg_m3"),
                temperature_score=tool_result.get("temperature_score"),
                chlorophyll_score=tool_result.get("chlorophyll_score"),
            ),
            scientific_explanation=scientific_explanation,
            fisherman_advice=fisherman_advice,
            disclaimer=tool_result.get(
                "disclaimer",
                "This is a prototype heuristic habitat suitability model. It does not guarantee catch.",
            ),
        )
