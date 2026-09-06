import json
import logging
import math
from typing import Dict, Any, Optional

from ..config import LLM_MODEL, GROQ_API_KEY, LLM_PROVIDER
from ..services.severe_weather_engine import SevereWeatherEngine, SevereWeatherClassification
from .schemas import CycloneAgentResponse, CycloneAlertSchema, SevereWeatherClassificationSchema, LocationInfo
from ..providers.factory import get_cyclone_provider, get_weather_provider
import groq

logger = logging.getLogger(__name__)

class CycloneAgent:
    """
    Cyclone & Severe Weather Intelligence Agent.
    Evaluates weather conditions and verified cyclone alerts (if any).
    The LLM provides safety explanations but DOES NOT alter risk classifications or invent forecasts.
    """

    def __init__(self, client: Optional[groq.Groq] = None, model_name: str = LLM_MODEL, live_mode: Optional[bool] = None):
        if client is not None:
            self._llm = client
        elif GROQ_API_KEY:
            try:
                self._llm = groq.Groq(api_key=GROQ_API_KEY)
            except Exception:
                self._llm = None
        else:
            self._llm = None
        self.model_name = model_name
        self.live_mode = live_mode
        self.engine = SevereWeatherEngine()

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points on the earth."""
        R = 6371.0 # Earth radius in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def run(
        self,
        latitude: float,
        longitude: float,
        date_str: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> CycloneAgentResponse:
        """
        Fetches necessary data from providers and evaluates severe weather synchronously.
        """
        import asyncio
        return asyncio.run(self._run_async(latitude, longitude, date_str, query_text))

    async def _run_async(
        self,
        latitude: float,
        longitude: float,
        date_str: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> CycloneAgentResponse:
        from datetime import datetime, timezone
        
        # Fetch verified cyclone data safely
        try:
            cyclone_provider = get_cyclone_provider()
            if date_str:
                cyclone_alert = await cyclone_provider.get_alerts_for_date(date_str)
            else:
                cyclone_alert = await cyclone_provider.get_alerts_for_location(latitude, longitude)
        except Exception as e:
            logger.warning(f"Cyclone provider error: {e}")
            cyclone_alert = {"status": "UNAVAILABLE"}
            
        # Fetch marine weather safely
        weather_conditions = {}
        temporal_mode = "HISTORICAL" if date_str else "LIVE"
        try:
            weather_provider = get_weather_provider(live_mode=self.live_mode)
            if date_str:
                if hasattr(weather_provider, "get_historical_marine_weather"):
                    weather_data = await weather_provider.get_historical_marine_weather(latitude, longitude, date_str)
                elif hasattr(weather_provider, "get_weather"):
                    weather_data = weather_provider.get_weather(latitude, longitude, date_str)
                else:
                    weather_data = {}
            else:
                if hasattr(weather_provider, "get_marine_weather"):
                    weather_data = await weather_provider.get_marine_weather(latitude, longitude)
                else:
                    weather_data = {}
            if weather_data and weather_data.get("success"):
                weather_conditions = weather_data.get("weather_conditions", {})
        except Exception as e:
            logger.warning(f"Weather provider error in cyclone agent: {e}")
            
        date_used = date_str if date_str else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        return await self.analyze(
            latitude=latitude,
            longitude=longitude,
            date_str=date_used,
            weather_conditions=weather_conditions,
            cyclone_alert=cyclone_alert,
            temporal_mode=temporal_mode
        )


    async def analyze(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
        weather_conditions: Dict[str, Any],
        cyclone_alert: Dict[str, Any],
        temporal_mode: str = "LIVE"
    ) -> CycloneAgentResponse:
        
        # Calculate distance to center if verified alert exists
        distance_to_center_km = None
        if cyclone_alert and cyclone_alert.get("status") != "UNAVAILABLE":
            c_lat = cyclone_alert.get("latitude")
            c_lon = cyclone_alert.get("longitude")
            if c_lat is not None and c_lon is not None:
                distance_to_center_km = self._haversine_distance(latitude, longitude, c_lat, c_lon)
                
        # Evaluate using deterministic engine
        classification: SevereWeatherClassification = self.engine.evaluate(
            wind_speed_knots=weather_conditions.get("wind_speed_knots"),
            wave_height_meters=weather_conditions.get("wave_height_meters"),
            surface_pressure_hpa=weather_conditions.get("surface_pressure_hpa"),
            cyclone_alert=cyclone_alert,
            distance_to_center_km=distance_to_center_km
        )
        
        # Prepare schemas
        alert_schema = None
        if cyclone_alert:
            alert_schema = CycloneAlertSchema(**cyclone_alert)
            
        severe_weather_schema = SevereWeatherClassificationSchema(
            risk_level=classification.risk_level,
            is_affected=classification.is_affected,
            affected_status=classification.affected_status,
            narrative=classification.narrative
        )
        
        # Build prompt for LLM
        prompt = (
            f"You are a maritime safety expert analyzing severe weather for coordinates {latitude}, {longitude}.\n"
            f"Date/Time context: {date_str} (Mode: {temporal_mode})\n\n"
            f"DETERMINISTIC ENGINE RESULTS (DO NOT ALTER):\n"
            f"- Severe Weather Risk: {classification.risk_level}\n"
            f"- Affected Status: {classification.affected_status}\n"
            f"- Engine Narrative: {classification.narrative}\n\n"
        )
        
        if distance_to_center_km is not None:
            prompt += f"- Distance to Cyclone Center: {distance_to_center_km:.1f} km\n"
            
        prompt += (
            "\nProvide a short, professional maritime narrative (under 4 sentences) summarizing the risk, "
            "and a short practical advice snippet for operations. Do not invent any cyclone name or forecast if none is provided. "
            "If the data status is UNAVAILABLE, clearly state that verified cyclone data is unavailable instead of saying there is no cyclone."
        )

        schema_props = {
            "type": "object",
            "properties": {
                "narrative": {"type": "string", "description": "Professional maritime narrative summarizing the risk."},
                "advice": {"type": "string", "description": "Practical advice for operations."}
            },
            "required": ["narrative", "advice"]
        }

        try:
            if LLM_PROVIDER != "groq":
                raise ValueError("Only groq is supported currently.")

            chat_completion = self._llm.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a maritime safety expert analyzing severe weather. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model_name,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result_text = chat_completion.choices[0].message.content
            if result_text:
                result_json = json.loads(result_text)
                
                return CycloneAgentResponse(
                    success=True,
                    location=LocationInfo(latitude=latitude, longitude=longitude),
                    date=date_str,
                    temporal_mode=temporal_mode,
                    cyclone_alert=alert_schema,
                    severe_weather=severe_weather_schema,
                    distance_to_center_km=distance_to_center_km,
                    narrative=result_json.get("narrative"),
                    advice=result_json.get("advice")
                )
        except Exception as e:
            logger.error(f"CycloneAgent LLM failure: {e}")

        # Fallback if LLM fails
        return CycloneAgentResponse(
            success=True,
            location=LocationInfo(latitude=latitude, longitude=longitude),
            date=date_str,
            temporal_mode=temporal_mode,
            cyclone_alert=alert_schema,
            severe_weather=severe_weather_schema,
            distance_to_center_km=distance_to_center_km,
            narrative=classification.narrative,
            advice="Exercise appropriate caution based on the stated risk level."
        )
