"""
research_agent.py

Agent responsible for handling historical/research marine queries.
"""
import json
import logging
from typing import Optional, Any, Dict, List
import groq

from ..config import GROQ_API_KEY, LLM_MODEL, MARINE_PARQUET_PATH, WEATHER_PARQUET_PATH
from .schemas import ResearchAgentResponse, LocationInfo, ResearchProvenance
from ..services.historical_marine_engine import HistoricalMarineEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Blue Orbit ORCA Historical Research Assistant.

Your role:
- Explain historical marine and weather conditions based ONLY on the provided deterministic data.
- Compare locations or time periods if data is provided.
- Identify trends (e.g. warming, cooling, chlorophyll changes).
- NEVER invent, modify, or assume measurements.
- Use explicit scientific wording ("chlorophyll concentration increased") rather than speculative fishing claims ("fish catch will increase").
- Do NOT claim that these historical trends constitute an official PFZ advisory.
"""

class ResearchAgent:
    def __init__(self, marine_parquet_path: str = MARINE_PARQUET_PATH, 
                 weather_parquet_path: str = WEATHER_PARQUET_PATH):
        self.engine = HistoricalMarineEngine(marine_parquet_path, weather_parquet_path)
        self.llm_client = groq.Groq(api_key=GROQ_API_KEY)

    def _generate_explanation(self, data: Dict[str, Any], query: str) -> str:
        prompt = f"""
The deterministic Historical Marine Engine provided the following data:
{json.dumps(data, indent=2)}

User Query: "{query}"

Provide a natural language explanation of this data. Focus on the trends, minimums, maximums, and means.
Do NOT invent any numbers. Do NOT predict fish catch. If the data status is INSUFFICIENT_DATA, say so clearly.
"""
        try:
            res = self.llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate LLM explanation: {e}")
            return "Unable to generate a natural language explanation for this data."

    def analyze(self, 
                query: str,
                locations: List[LocationInfo],
                start_date: str,
                end_date: Optional[str] = None,
                is_comparison: bool = False) -> ResearchAgentResponse:
        
        try:
            if not locations:
                return ResearchAgentResponse(
                    success=False,
                    temporal_range=start_date,
                    data_status="UNAVAILABLE",
                    provenance=ResearchProvenance(source="Unknown", dataset="Unknown", coverage="Unknown"),
                    error="No location provided for historical analysis."
                )

            if is_comparison and len(locations) >= 2:
                # Spatial comparison
                loc1, loc2 = locations[0], locations[1]
                engine_res = self.engine.compare_locations(
                    loc1.latitude, loc1.longitude,
                    loc2.latitude, loc2.longitude,
                    start_date
                )
                explanation = self._generate_explanation(engine_res, query)
                
                return ResearchAgentResponse(
                    success=True,
                    analysis_type="SPATIAL_COMPARISON",
                    temporal_range=engine_res["temporal_range"],
                    locations=engine_res["locations"],
                    data_status="AVAILABLE",
                    provenance=ResearchProvenance(**engine_res["provenance"]),
                    summary_explanation=explanation
                )
            
            else:
                # Point or Temporal range analysis
                loc = locations[0]
                engine_res = self.engine.analyze_point_history(
                    loc.latitude, loc.longitude, start_date, end_date
                )
                
                # Check overall status
                data_status = "AVAILABLE"
                if engine_res["marine"]["data_status"] == "INSUFFICIENT_DATA" and engine_res["weather"]["data_status"] == "INSUFFICIENT_DATA":
                    data_status = "INSUFFICIENT_DATA"
                
                explanation = self._generate_explanation(engine_res, query)
                
                return ResearchAgentResponse(
                    success=True,
                    analysis_type="POINT_ANALYSIS" if start_date == end_date else "TEMPORAL_SUMMARY",
                    temporal_range=engine_res["temporal_range"],
                    location=loc,
                    marine=engine_res["marine"],
                    weather=engine_res["weather"],
                    data_status=data_status,
                    provenance=ResearchProvenance(**engine_res["provenance"]),
                    summary_explanation=explanation
                )
                
        except Exception as e:
            logger.error(f"Research Agent failed: {e}")
            return ResearchAgentResponse(
                success=False,
                temporal_range=start_date,
                data_status="ERROR",
                provenance=ResearchProvenance(source="System", dataset="System", coverage="Unknown"),
                error=str(e)
            )
