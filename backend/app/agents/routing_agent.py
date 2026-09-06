import logging
import json
from typing import Optional, Any, Dict

from ..tools.routing_tool import RoutingTool
from .schemas import RoutingAgentResponse, LocationInfo
from ..config import LLM_MODEL, GROQ_API_KEY
import groq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the ORCA Routing & Navigation XAI Agent.
Your job is to:
1. Extract start and destination coordinates from the user's query if possible.
2. Explain the generated deterministic route safely.

DO NOT invent safety guarantees.
DO NOT invent missing underwater data.
Always state that this is a decision-support route, not an official nautical chart.
"""

class RoutingAgent:
    def __init__(self, llm_client: Optional[Any] = None, tool: Optional[RoutingTool] = None):
        self._llm = None
        if llm_client is not None:
            self._llm = llm_client
        elif GROQ_API_KEY:
            try:
                self._llm = groq.Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client in RoutingAgent: {e}")
                
        self._model = LLM_MODEL
        self._tool = tool or RoutingTool()

    def _extract_locations(self, query: str, context_lat: float = None, context_lon: float = None) -> Dict[str, Any]:
        """
        Uses LLM to extract start and end coordinates. If unable, fall back to context coordinates or default.
        """
        if not self._llm:
            return {
                "start_lat": context_lat or 18.9, "start_lon": context_lon or 72.8,
                "dest_lat": 15.5, "dest_lon": 73.8
            }
            
        prompt = f"""
Extract the start and destination coordinates (latitude and longitude) from the following query.
If the query mentions a city (like Mumbai, Goa, Ratnagiri, Mangalore), provide approximate coastal coordinates.
Current context location: {context_lat}, {context_lon}.

Query: "{query}"

Output ONLY valid JSON:
{{
  "start_lat": float,
  "start_lon": float,
  "dest_lat": float,
  "dest_lon": float
}}
"""
        try:
            chat_completion = self._llm.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self._model,
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            raw = chat_completion.choices[0].message.content
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to extract locations: {e}")
            return {
                "start_lat": context_lat or 18.9, "start_lon": context_lon or 72.8,
                "dest_lat": 15.5, "dest_lon": 73.8
            }

    def _generate_narrative(self, routing_res, query_text: str) -> str:
        if not self._llm:
            return f"Generated a route with {len(routing_res.route_points)} points. Total distance: {routing_res.total_distance_km:.1f} km."
            
        prompt = f"""
You are the XAI Synthesizer for ORCA Routing.
Explain this deterministic route payload to the user in a safe, helpful manner.
Route Payload:
Status: {routing_res.status}
Distance: {routing_res.total_distance_km} km
Start: ({routing_res.start_location.latitude}, {routing_res.start_location.longitude})
End: ({routing_res.destination_location.latitude}, {routing_res.destination_location.longitude})
Warnings: {routing_res.warnings}

User Query: "{query_text}"

Keep it concise. Highlight hazards. Emphasize that it is a decision support tool, not official navigation.
"""
        try:
            chat_completion = self._llm.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                model=self._model,
                temperature=0.3,
                max_tokens=300
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate narrative: {e}")
            return "Successfully calculated a decision-support route."

    def run(
        self,
        query_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        date_str: Optional[str] = None
    ) -> RoutingAgentResponse:
        
        locs = self._extract_locations(query_text, latitude, longitude)
        
        routing_res = self._tool.plan_route(
            start_lat=locs.get("start_lat", 18.9),
            start_lon=locs.get("start_lon", 72.8),
            dest_lat=locs.get("dest_lat", 15.5),
            dest_lon=locs.get("dest_lon", 73.8),
            date_str=date_str
        )
        
        narrative = None
        if routing_res.status == "SUCCESS":
            narrative = self._generate_narrative(routing_res, query_text)
            
        return RoutingAgentResponse(
            success=(routing_res.status == "SUCCESS"),
            routing=routing_res,
            narrative=narrative,
            error=routing_res.warnings[0] if routing_res.warnings else None
        )
