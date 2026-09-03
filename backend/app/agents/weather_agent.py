"""
weather_agent.py

Weather / Safety Specialist AI Agent.

Responsibility:
  1. Receive a weather/safety query from the user (location + date).
  2. Invoke WeatherSafetyTool to get the deterministic Weather Safety Engine result.
  3. Pass the raw engine result to the LLM for natural-language narration.
  4. Return a structured WeatherSafetyAgentResponse.

Rules enforced here:
  - The agent NEVER recalculates or modifies the Weather Safety Engine's scores.
  - The agent NEVER invents wind speeds, wave heights, or safety thresholds.
  - If the tool fails, the agent returns an explicit error — it does NOT fabricate.
  - The LLM only narrates what the engine returned; it cannot invent measurements.
  - risk_level, wind_safety_score, wave_safety_score, and overall_safety_score are
    always sourced verbatim from the engine result dict, never from the LLM output.
  - The API key is read from config (environment variable) — never hard-coded.
"""

import json
import logging
from typing import Optional, Any

import groq

from ..config import GROQ_API_KEY, LLM_MODEL, LLM_PROVIDER
from ..tools.weather_tool import WeatherSafetyTool
from .schemas import (
    WeatherSafetyAgentResponse,
    LocationInfo,
    WeatherConditions,
)

from ..services.temporal_resolver import TemporalResolution, TemporalMode
from ..providers.base_weather_provider import BaseWeatherProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the Blue Orbit ORCA Weather Safety Assistant — a marine weather decision-support assistant for fishermen and coast guards operating on the Indian West Coast.

Your role:
- Translate scientific weather safety assessments into clear, practical language for fishermen.
- Help users understand what the weather and sea conditions mean for safe navigation and fishing operations.

STRICT RULES you must ALWAYS follow:

1. NEVER invent, modify, or assume weather measurements.
   - If a wind speed or wave height is provided, use it exactly as given.
   - If a value is missing (null/None), say so clearly.

2. NEVER alter the numerical safety scores (wind_safety_score, wave_safety_score, overall_safety_score).
   - These scores are computed by a deterministic scientific engine. Report them exactly.

3. NEVER change or reinterpret the risk_level label.
   - The label (e.g. "Low Risk", "Very High Risk") comes from the engine. Report it exactly.

4. NEVER claim conditions are safe when the engine reports High Risk or Very High Risk.
   - If the engine says Very High Risk, you must communicate danger clearly.

5. NEVER invent wind directions, wave periods, or any other measurement
   unless those values are explicitly provided to you by the engine result.

6. Clearly distinguish between:
   (a) Measured weather conditions (wind speed, wave height)
   (b) Calculated safety scores (derived from the conditions)
   (c) Practical interpretation (what this means for a fisherman's safety)

7. If data_quality is "Insufficient Data" or "Partial", clearly communicate the uncertainty.
   Do NOT assume or fill in the gaps with invented values.

8. If the risk_level is "Insufficient Data", do NOT give a safety recommendation.
   Instead, explain that reliable weather data was not available for this location/date.

9. Always respect the engine disclaimer: this is a prototype model, not an official maritime safety standard.

10. Use plain, simple language appropriate for fishermen. Avoid unnecessary jargon.

11. Be concise. Provide two things:
    (a) A brief scientific explanation of what the weather data shows.
    (b) Practical safety advice based ONLY on the reported conditions.

When you respond, produce ONLY a JSON object with these two fields:
{
  "safety_narrative": "...",
  "safety_advice": "..."
}
Do not include any other text, markdown, or explanation outside the JSON.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class WeatherSafetyAgent:
    """
    Specialist AI agent for weather safety queries.

    Uses the deterministic WeatherSafetyTool as the source of truth.
    The LLM (Groq + Llama) is used only to narrate the result in natural language.
    """

    def __init__(
        self,
        live_mode: Optional[bool] = None,
        llm_client: Optional[Any] = None,
        tool: Optional[WeatherSafetyTool] = None,
        provider: Optional[BaseWeatherProvider] = None,
    ):
        """
        Args:
            live_mode: Provider mode. None = smart routing mode.
            llm_client: Optional pre-built Groq client (used for testing/mocking).
            tool: Optional injected WeatherSafetyTool.
            provider: Optional injected BaseWeatherProvider.
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
        self._tool = tool or WeatherSafetyTool(live_mode=live_mode, provider=provider)

    def run(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
        query_text: str = "",
        temporal_resolution: Optional[TemporalResolution] = None,
    ) -> WeatherSafetyAgentResponse:
        """
        Execute a weather safety query.

        Args:
            latitude:            WGS84 latitude.
            longitude:           WGS84 longitude.
            date_str:            Date as 'YYYY-MM-DD'.
            query_text:          Original natural-language query (optional, for context).
            temporal_resolution: Resolved TemporalResolution (LIVE, HISTORICAL, UNSUPPORTED_FUTURE).

        Returns:
            WeatherSafetyAgentResponse — always structured, never a raw LLM string.
        """
        # --- Step 0: Check for unsupported future date requests ---
        if temporal_resolution and temporal_resolution.mode == TemporalMode.UNSUPPORTED_FUTURE:
            return WeatherSafetyAgentResponse(
                success=False,
                error=(
                    f"Date {date_str} is in the future. Marine weather forecasts are "
                    f"currently unsupported without verified forecast providers. "
                    f"Official IMD marine forecasts are not yet integrated."
                ),
                location=LocationInfo(latitude=latitude, longitude=longitude),
                date=date_str,
                temporal_mode=TemporalMode.UNSUPPORTED_FUTURE.value,
                observation_type="unavailable",
                data_status="unavailable",
            )

        # --- Step 1: Call the deterministic tool ---
        tool_result = self._tool.get_weather_safety(
            latitude=latitude,
            longitude=longitude,
            date_str=date_str,
            temporal_resolution=temporal_resolution,
            query_text=query_text,
        )

        # --- Step 2: If the tool/provider failed, return structured error (no LLM) ---
        if not tool_result.get("success", False):
            return WeatherSafetyAgentResponse(
                success=False,
                error=tool_result.get("error", "Failed to retrieve weather safety data."),
                location=LocationInfo(latitude=latitude, longitude=longitude),
                date=date_str,
                temporal_mode=tool_result.get("temporal_mode"),
                observation_type=tool_result.get("observation_type", "unavailable"),
                source=tool_result.get("source"),
                data_status=tool_result.get("data_status", "unavailable"),
            )

        # --- Step 3: Build the LLM prompt using the EXACT engine result ---
        # NOTE: Only engine-provided values are included. Nothing is invented here.
        engine_summary = {
            "latitude": tool_result.get("latitude"),
            "longitude": tool_result.get("longitude"),
            "date": tool_result.get("date"),
            "matched_latitude": tool_result.get("matched_latitude"),
            "matched_longitude": tool_result.get("matched_longitude"),
            "distance_km": tool_result.get("distance_km"),
            "wind_speed_knots": tool_result.get("wind_speed_knots"),
            "wind_direction": tool_result.get("wind_direction"),
            "surface_pressure_hpa": tool_result.get("surface_pressure_hpa"),
            "wave_height_meters": tool_result.get("wave_height_meters"),
            "wave_direction": tool_result.get("wave_direction"),
            "wave_period_seconds": tool_result.get("wave_period_seconds"),
            "wind_safety_score": tool_result.get("wind_safety_score"),
            "wave_safety_score": tool_result.get("wave_safety_score"),
            "overall_safety_score": tool_result.get("overall_safety_score"),
            "risk_level": tool_result.get("risk_level"),
            "data_quality": tool_result.get("data_quality"),
            "confidence": tool_result.get("confidence"),
            "engine_explanation": tool_result.get("explanation"),
        }

        user_message = (
            f"A fisherman asked: \"{query_text or 'Is it safe to go out to sea at this location?'}\"\n\n"
            f"Here is the deterministic weather safety assessment from the Weather Safety Engine:\n"
            f"{json.dumps(engine_summary, indent=2)}\n\n"
            f"Using ONLY the data above, provide your response as a JSON object with "
            f"'safety_narrative' and 'safety_advice' fields."
        )

        # --- Step 4: LLM narration (narrates only, does not recalculate) ---
        # Fallback values use the engine's own explanation so the response is always useful
        safety_narrative = tool_result.get("explanation", "")
        safety_advice = ""

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
            safety_narrative = parsed.get("safety_narrative", safety_narrative)
            safety_advice = parsed.get("safety_advice", "")

        except json.JSONDecodeError as e:
            logger.warning(f"LLM returned invalid JSON: {e}. Using engine explanation fallback.")
        except Exception as e:
            logger.warning(f"LLM call failed: {e}. Using engine explanation fallback.")
            # Graceful degradation: return engine result without LLM narration
            safety_advice = (
                f"Based on available weather data, the marine safety risk level is "
                f"{tool_result.get('risk_level', 'Unknown')}. "
                f"Please consult local authorities for official safety guidance."
            )

        # --- Step 5: Assemble structured response ---
        # CRITICAL: risk_level and all scores come from tool_result (engine),
        # NOT from the LLM output. The LLM only provides the two narrative strings.

        matched_lat = tool_result.get("matched_latitude")
        matched_lon = tool_result.get("matched_longitude")

        return WeatherSafetyAgentResponse(
            success=True,
            location=LocationInfo(
                latitude=tool_result.get("latitude", latitude),
                longitude=tool_result.get("longitude", longitude),
            ),
            date=tool_result.get("date", date_str),
            matched_location=(
                LocationInfo(latitude=matched_lat, longitude=matched_lon)
                if matched_lat is not None and matched_lon is not None
                else None
            ),
            distance_km=tool_result.get("distance_km"),
            risk_level=tool_result.get("risk_level"),          # from engine, verbatim
            confidence=tool_result.get("confidence"),
            data_quality=tool_result.get("data_quality"),
            weather_conditions=WeatherConditions(
                wind_speed_knots=tool_result.get("wind_speed_knots"),
                wave_height_meters=tool_result.get("wave_height_meters"),
                surface_pressure_hpa=tool_result.get("surface_pressure_hpa"),
                wind_direction=tool_result.get("wind_direction"),
                wave_direction=tool_result.get("wave_direction"),
                wave_period_seconds=tool_result.get("wave_period_seconds"),
                wind_safety_score=tool_result.get("wind_safety_score"),    # from engine, verbatim
                wave_safety_score=tool_result.get("wave_safety_score"),    # from engine, verbatim
                overall_safety_score=tool_result.get("overall_safety_score"),  # from engine, verbatim
                source=tool_result.get("source"),
                data_status=tool_result.get("data_status"),
                observation_type=tool_result.get("observation_type"),
            ),
            safety_narrative=safety_narrative,
            safety_advice=safety_advice,
            source=tool_result.get("source"),
            data_status=tool_result.get("data_status"),
            observation_type=tool_result.get("observation_type"),
            temporal_mode=tool_result.get("temporal_mode") or (temporal_resolution.mode.value if temporal_resolution else None),
            limiting_factor=(
                "Wind Speed" if (tool_result.get("wind_safety_score") is not None and tool_result.get("wave_safety_score") is not None and tool_result.get("wind_safety_score") < tool_result.get("wave_safety_score"))
                else "Significant Wave Height" if (tool_result.get("wind_safety_score") is not None and tool_result.get("wave_safety_score") is not None and tool_result.get("wave_safety_score") < tool_result.get("wind_safety_score"))
                else "Co-equal" if (tool_result.get("wind_safety_score") is not None and tool_result.get("wave_safety_score") is not None and tool_result.get("wind_safety_score") == tool_result.get("wave_safety_score"))
                else None
            ),
            disclaimer=tool_result.get(
                "disclaimer",
                "This is a prototype decision-support/risk indicator. "
                "It does not guarantee vessel safety or represent official maritime safety standards.",
            ),
        )
