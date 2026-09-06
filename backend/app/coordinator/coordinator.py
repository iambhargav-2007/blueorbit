"""
coordinator.py

The Multi-Agent Orchestration layer for Blue Orbit (ORCA) (Step 23).
Multi-Stakeholder Coastal Intelligence Platform supporting Fishermen,
Coast Guards, and Researchers.
"""

import logging
from typing import Optional, Any, List, Dict

from .schemas import (
    CoordinatorResponse,
    RoutingInfo,
    IntentEnum,
    IntelligenceDomainEnum,
    StructuredSummary,
)
from .router import OrcaRouter

from ..agents.fishing_agent import FishingHabitatAgent
from ..agents.weather_agent import WeatherSafetyAgent
from ..agents.geofencing_agent import GeofencingAgent
from ..agents.fishing_decision_agent import FishingDecisionAgent
from ..agents.cyclone_agent import CycloneAgent
from ..agents.research_agent import ResearchAgent

logger = logging.getLogger(__name__)


class OrcaCoordinator:
    """
    Main orchestration class. Coordinates between intent routing and domain agents.
    Enforces selective agent invocation to prevent over-calling and maintain failure isolation.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        live_mode: Optional[bool] = None,
        decision_agent: Optional[FishingDecisionAgent] = None,
    ):
        self._router = OrcaRouter(llm_client=llm_client)
        
        # Domain Agents
        self._habitat_agent = FishingHabitatAgent(live_mode=live_mode, llm_client=llm_client)
        self._weather_agent = WeatherSafetyAgent(live_mode=live_mode, llm_client=llm_client)
        self._geofencing_agent = GeofencingAgent(llm_client=llm_client)
        if decision_agent is not None:
            self._decision_agent = decision_agent
        else:
            from ..tools.fishing_decision_tool import FishingDecisionTool
            shared_tool = FishingDecisionTool(
                habitat_tool=self._habitat_agent._tool,
                weather_tool=self._weather_agent._tool,
                geofencing_tool=self._geofencing_agent._tool,
            )
            self._decision_agent = FishingDecisionAgent(llm_client=llm_client, tool=shared_tool)
        self._cyclone_agent = CycloneAgent(client=llm_client, live_mode=live_mode)
        self._research_agent = ResearchAgent()

    def process_request(
        self,
        query_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        date_str: Optional[str] = None,
        temporal_resolution: Optional[Any] = None,
        requested_capabilities: Optional[List[str]] = None,
        intent: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> CoordinatorResponse:
        """
        Processes a user request end-to-end with intent-driven selective execution.
        """
        request_dict = {
            "query_text": query_text,
            "latitude": latitude,
            "longitude": longitude,
            "date_str": date_str,
        }
        
        # 1. Routing & Intent Classification
        if intent is None or domain is None or requested_capabilities is None:
            classified_intent, classified_domain, classified_caps = self._router.classify_intent(query_text)
            intent = intent or classified_intent
            domain = domain or classified_domain
            requested_caps = requested_capabilities if requested_capabilities is not None else classified_caps
        else:
            requested_caps = requested_capabilities

        if not requested_caps and intent and intent != IntentEnum.UNKNOWN.value:
            intent_default_caps = {
                IntentEnum.FISHING_SUPPORT.value: ["fishing_decision"],
                IntentEnum.MARITIME_SAFETY.value: ["weather"],
                IntentEnum.SEVERE_WEATHER.value: ["cyclone"],
                IntentEnum.MARINE_ANALYSIS.value: ["research"],
                IntentEnum.ENVIRONMENTAL_ANALYSIS.value: ["research"],
                IntentEnum.SPATIAL_QUERY.value: ["geofencing"],
                IntentEnum.TEMPORAL_COMPARISON.value: ["research"],
                IntentEnum.GENERAL_COASTAL_QUERY.value: ["habitat", "weather", "geofencing"],
            }
            requested_caps = intent_default_caps.get(intent, [])

        if not requested_caps and intent == IntentEnum.UNKNOWN.value:
            # Unrelated or ambiguous query
            return CoordinatorResponse(
                success=False,
                request=request_dict,
                routing=RoutingInfo(
                    intent=IntentEnum.UNKNOWN.value,
                    domain=IntelligenceDomainEnum.COASTAL_OVERVIEW.value,
                    requested_capabilities=[],
                    agents_invoked=[]
                ),
                intent=IntentEnum.UNKNOWN.value,
                intelligence_domain=IntelligenceDomainEnum.COASTAL_OVERVIEW.value,
                errors=["Request is ambiguous or outside supported domain capabilities."]
            )

        # 2. Validation
        # Severe weather queries check basin-wide or regional alerts and do not strictly require coordinates
        if intent == IntentEnum.SEVERE_WEATHER.value or requested_caps == ["cyclone"]:
            needs_coords = False
            needs_date = False
        else:
            needs_coords = any(cap in requested_caps for cap in ["habitat", "weather", "geofencing", "fishing_decision"])
            needs_date = any(cap in requested_caps for cap in ["habitat", "weather", "fishing_decision"])
        
        errors = []
        if needs_coords and (latitude is None or longitude is None):
            errors.append("Latitude and longitude are required for this query.")
        if needs_date and date_str is None and not (temporal_resolution and temporal_resolution.is_comparison):
            errors.append("Date is required for this query.")
            
        if errors:
            return CoordinatorResponse(
                success=False,
                request=request_dict,
                routing=RoutingInfo(
                    intent=intent,
                    domain=domain,
                    requested_capabilities=requested_caps,
                    agents_invoked=[]
                ),
                intent=intent,
                intelligence_domain=domain,
                errors=errors
            )

        # 3. Selective Agent Invocation
        agents_invoked = []
        habitat_res = None
        weather_res = None
        geofencing_res = None
        decision_res = None
        cyclone_res = None

        # Execute ONLY capabilities designated by the intent
        if "fishing_decision" in requested_caps and intent == IntentEnum.FISHING_SUPPORT.value:
            agents_invoked.append("fishing_decision")
            try:
                decision_res = self._decision_agent.run(
                    latitude=latitude,
                    longitude=longitude,
                    date_str=date_str,
                    query_text=query_text,
                    temporal_resolution=temporal_resolution,
                )
                if not decision_res.success:
                    errors.append(f"Fishing Decision Agent failed: {decision_res.error}")
            except Exception as e:
                logger.error(f"Fishing Decision Agent execution error: {e}")
                errors.append(f"Fishing Decision Agent encountered an error: {e}")

        if "habitat" in requested_caps:
            agents_invoked.append("fishing_habitat")
            try:
                habitat_res = self._habitat_agent.run(
                    latitude=latitude,
                    longitude=longitude,
                    date_str=date_str or (temporal_resolution.historical_date if temporal_resolution else None),
                    query_text=query_text,
                    temporal_resolution=temporal_resolution,
                )
                if not habitat_res.success:
                    errors.append(f"Habitat Agent failed: {habitat_res.error}")
            except Exception as e:
                logger.error(f"Habitat Agent execution error: {e}")
                errors.append(f"Habitat Agent encountered an error: {e}")

        if "weather" in requested_caps:
            agents_invoked.append("weather_safety")
            try:
                weather_res = self._weather_agent.run(
                    latitude=latitude,
                    longitude=longitude,
                    date_str=date_str,
                    query_text=query_text,
                    temporal_resolution=temporal_resolution,
                )
                if not weather_res.success:
                    errors.append(f"Weather Agent failed: {weather_res.error}")
            except Exception as e:
                logger.error(f"Weather Agent execution error: {e}")
                errors.append(f"Weather Agent encountered an error: {e}")

        if "geofencing" in requested_caps:
            agents_invoked.append("geofencing")
            try:
                geofencing_res = self._geofencing_agent.run(
                    latitude=latitude,
                    longitude=longitude,
                    query_text=query_text
                )
                if not geofencing_res.success:
                    errors.append(f"Geofencing Agent failed: {geofencing_res.error}")
            except Exception as e:
                logger.error(f"Geofencing Agent execution error: {e}")
                errors.append(f"Geofencing Agent encountered an error: {e}")

        if "cyclone" in requested_caps or intent == IntentEnum.SEVERE_WEATHER.value:
            agents_invoked.append("cyclone")
            try:
                c_lat = latitude if latitude is not None else 19.0
                c_lon = longitude if longitude is not None else 70.0
                cyclone_res = self._cyclone_agent.run(
                    latitude=c_lat,
                    longitude=c_lon,
                    date_str=date_str,
                    query_text=query_text
                )
                if not cyclone_res.success:
                    errors.append(f"Cyclone Agent failed: {cyclone_res.error}")
            except Exception as e:
                logger.error(f"Cyclone Agent execution error: {e}")
                errors.append(f"Cyclone Agent encountered an error: {e}")

        research_res = None
        if "research" in requested_caps:
            agents_invoked.append("research")
            try:
                # We need to construct LocationInfo objects
                from ..agents.schemas import LocationInfo
                locs = []
                if latitude is not None and longitude is not None:
                    locs.append(LocationInfo(latitude=latitude, longitude=longitude))
                
                # If comparison, we might need a second location.
                # Currently location context resolver only yields primary lat/lon.
                # Assuming the temporal_resolution tells us if it's a comparison
                is_comp = (temporal_resolution and temporal_resolution.is_comparison)
                
                research_res = self._research_agent.analyze(
                    query=query_text,
                    locations=locs,
                    start_date=date_str or (temporal_resolution.historical_date if temporal_resolution else None) or "2025-10-01",
                    end_date=None,
                    is_comparison=is_comp
                )
                if not research_res.success:
                    errors.append(f"Research Agent failed: {research_res.error}")
            except Exception as e:
                logger.error(f"Research Agent execution error: {e}")
                errors.append(f"Research Agent encountered an error: {e}")

        # 4. Domain-Specific Synthesis (Maritime Safety, Sector Overview, Structured Summary)
        safety_assessment = None
        if intent == IntentEnum.MARITIME_SAFETY.value or "weather" in requested_caps:
            risk = weather_res.risk_level if weather_res else "UNKNOWN"
            wc = weather_res.weather_conditions if weather_res else None
            c_affected = "NO_VERIFIED_DATA"
            if cyclone_res and hasattr(cyclone_res, 'severe_weather') and cyclone_res.severe_weather:
                c_affected = getattr(cyclone_res.severe_weather, 'affected_status', 'NO_VERIFIED_DATA')
            
            eez_st = getattr(geofencing_res, 'geofence_status', getattr(geofencing_res, 'status', 'UNKNOWN')) if geofencing_res else 'UNKNOWN'
            dist_km = getattr(geofencing_res, 'distance_to_eez_boundary_km', getattr(geofencing_res, 'distance_to_boundary_km', None)) if geofencing_res else None
            safety_assessment = {
                "risk_level": risk,
                "sea_state_risk": risk,
                "limiting_factor": getattr(weather_res, 'limiting_factor', None) if weather_res else None,
                "wind_speed_kn": wc.wind_speed_knots if wc else None,
                "wave_height_m": wc.wave_height_meters if wc else None,
                "surface_pressure_hpa": wc.surface_pressure_hpa if wc else None,
                "severe_weather_status": c_affected,
                "eez_compliance": eez_st,
                "distance_to_boundary_km": dist_km,
                "disclaimer": "Deterministic assessment based on available Copernicus/Open-Meteo observations. Not an official marine warning."
            }

        sector_overview = None
        if intent == IntentEnum.GENERAL_COASTAL_QUERY.value or len(agents_invoked) >= 3:
            marine_data = None
            if habitat_res and habitat_res.environmental_summary:
                env = habitat_res.environmental_summary
                marine_data = {
                    "sst_c": env.temperature_c,
                    "chlorophyll_mg_m3": env.chlorophyll_mg_m3,
                    "environmental_suitability": habitat_res.fishing_potential,
                    "habitat_score": habitat_res.habitat_score,
                }
            sea_state_data = None
            if weather_res and weather_res.weather_conditions:
                wc = weather_res.weather_conditions
                sea_state_data = {
                    "wind_speed_kn": wc.wind_speed_knots,
                    "wave_height_m": wc.wave_height_meters,
                    "risk_level": weather_res.risk_level,
                }
            c_status = "NO_VERIFIED_DATA"
            if cyclone_res and hasattr(cyclone_res, 'severe_weather') and cyclone_res.severe_weather:
                c_status = getattr(cyclone_res.severe_weather, 'affected_status', 'NO_VERIFIED_DATA')
            
            sector_overview = {
                "marine": marine_data,
                "marine_environment": marine_data,
                "sea_state": sea_state_data,
                "severe_weather": {"status": c_status},
                "geospatial": {
                    "eez_status": getattr(geofencing_res, 'geofence_status', getattr(geofencing_res, 'status', None)) if geofencing_res else None,
                    "distance_to_boundary_km": getattr(geofencing_res, 'distance_to_eez_boundary_km', getattr(geofencing_res, 'distance_to_boundary_km', None)) if geofencing_res else None,
                },
            }

        # 5. Determine Overall Success
        any_success = any([
            decision_res and decision_res.success,
            habitat_res and habitat_res.success,
            weather_res and weather_res.success,
            geofencing_res and geofencing_res.success,
            cyclone_res and cyclone_res.success,
        ])
        
        overall_success = any_success or (intent == IntentEnum.GENERAL_COASTAL_QUERY.value)

        # 6. Build Standardized ORCA Summary (Section 13)
        structured_summary = None
        if overall_success:
            if intent == IntentEnum.MARITIME_SAFETY.value and weather_res:
                wc = weather_res.weather_conditions
                wind_val = f"{wc.wind_speed_knots:.1f} kn" if wc and wc.wind_speed_knots is not None else "—"
                wave_val = f"{wc.wave_height_meters:.1f} m" if wc and wc.wave_height_meters is not None else "—"
                structured_summary = StructuredSummary(
                    overview=f"Maritime safety assessment indicates {weather_res.risk_level or 'Normal'} operational conditions.",
                    key_findings=[
                        f"Wind Speed: {wind_val}",
                        f"Wave Height: {wave_val}",
                        f"Risk Level: {weather_res.risk_level or 'Unknown'}",
                    ],
                    operational_status=weather_res.risk_level or "Operational",
                    confidence=weather_res.confidence or "High",
                )
            elif intent == IntentEnum.SEVERE_WEATHER.value and cyclone_res:
                c_name = "No Active Cyclonic System"
                if hasattr(cyclone_res, 'cyclone_alert') and cyclone_res.cyclone_alert:
                    c_name = cyclone_res.cyclone_alert.name or "Active Storm Alert"
                structured_summary = StructuredSummary(
                    overview=f"Severe weather evaluation: {c_name}.",
                    key_findings=[
                        f"Status: {c_name}",
                        "Regional basin tracked via IMD / RSMC severe weather bulletins.",
                    ],
                    operational_status="ALERT" if (hasattr(cyclone_res, 'cyclone_alert') and cyclone_res.cyclone_alert) else "NORMAL",
                    confidence="High",
                )
            elif intent in [IntentEnum.MARINE_ANALYSIS.value, IntentEnum.ENVIRONMENTAL_ANALYSIS.value] and habitat_res:
                env = habitat_res.environmental_summary
                sst_val = f"{env.temperature_c:.1f}°C" if env and env.temperature_c is not None else "—"
                chl_val = f"{env.chlorophyll_mg_m3:.2f} mg/m³" if env and env.chlorophyll_mg_m3 is not None else "—"
                structured_summary = StructuredSummary(
                    overview=f"Marine ecological analysis: Habitat suitability score {habitat_res.habitat_score or '—'}/100.",
                    key_findings=[
                        f"Sea Surface Temperature: {sst_val}",
                        f"Chlorophyll-a Concentration: {chl_val}",
                        f"Environmental Rating: {habitat_res.fishing_potential or 'Baseline'}",
                    ],
                    operational_status="Scientific Research Observation",
                    confidence=habitat_res.confidence or "High",
                )
            else:
                findings = []
                if habitat_res and habitat_res.environmental_summary:
                    env = habitat_res.environmental_summary
                    if env.temperature_c is not None:
                        findings.append(f"SST: {env.temperature_c:.1f}°C")
                    if env.chlorophyll_mg_m3 is not None:
                        findings.append(f"Chlorophyll-a: {env.chlorophyll_mg_m3:.2f} mg/m³")
                if weather_res and weather_res.weather_conditions:
                    wc = weather_res.weather_conditions
                    if wc.wind_speed_knots is not None:
                        findings.append(f"Wind: {wc.wind_speed_knots:.1f} kn")
                    if wc.wave_height_meters is not None:
                        findings.append(f"Waves: {wc.wave_height_meters:.1f} m")
                if geofencing_res:
                    z_name = getattr(geofencing_res, 'geofence_status', 'EEZ')
                    b_dist = getattr(geofencing_res, 'distance_to_eez_boundary_km', 0.0) or 0.0
                    findings.append(f"Zone: {z_name} ({b_dist:.1f} km to boundary)")
                if not findings:
                    findings.append("Multi-domain coastal sector overview generated.")
                structured_summary = StructuredSummary(
                    overview=f"Coastal intelligence summary for sector ({request_dict.get('latitude')}, {request_dict.get('longitude')}).",
                    key_findings=findings,
                    operational_status="Active Monitoring",
                    confidence="High",
                )

        return CoordinatorResponse(
            success=overall_success,
            request=request_dict,
            routing=RoutingInfo(
                intent=intent,
                domain=domain,
                requested_capabilities=requested_caps,
                agents_invoked=agents_invoked
            ),
            intent=intent,
            intelligence_domain=domain,
            habitat=habitat_res,
            weather=weather_res,
            geofencing=geofencing_res,
            cyclone=cyclone_res,
            fishing_decision=decision_res,
            research=research_res,
            comparison=habitat_res.comparison if habitat_res and hasattr(habitat_res, "comparison") else None,
            safety_assessment=safety_assessment,
            sector_overview=sector_overview,
            structured_summary=structured_summary,
            errors=errors
        )
