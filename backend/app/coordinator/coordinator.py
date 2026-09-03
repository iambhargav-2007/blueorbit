"""
coordinator.py

The Multi-Agent Orchestration layer for Blue Orbit (ORCA).

Responsibility:
  1. Receive user requests (query, lat, lon, date).
  2. Route the request via OrcaRouter to identify required capabilities.
  3. Validate inputs required for the chosen agents.
  4. Invoke the required agents sequentially.
  5. Aggregate results into a unified CoordinatorResponse.
  6. Handle partial failures safely (Failure Isolation).
"""

import logging
from typing import Optional, Any, List

from .schemas import CoordinatorResponse, RoutingInfo
from .router import OrcaRouter

from ..agents.fishing_agent import FishingHabitatAgent
from ..agents.weather_agent import WeatherSafetyAgent
from ..agents.geofencing_agent import GeofencingAgent
from ..agents.fishing_decision_agent import FishingDecisionAgent

logger = logging.getLogger(__name__)

class OrcaCoordinator:
    """
    Main orchestration class. Coordinates between intent routing and domain agents.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        live_mode: Optional[bool] = None,
        decision_agent: Optional[FishingDecisionAgent] = None,
    ):
        """
        Args:
            llm_client: Shared optional mocked LLM client for testing.
            live_mode: Shared live_mode flag passed to agents.
            decision_agent: Optional injected FishingDecisionAgent for testing.
        """
        self._router = OrcaRouter(llm_client=llm_client)
        
        # Instantiate agents using existing interfaces
        self._habitat_agent = FishingHabitatAgent(live_mode=live_mode, llm_client=llm_client)
        self._weather_agent = WeatherSafetyAgent(live_mode=live_mode, llm_client=llm_client)
        self._geofencing_agent = GeofencingAgent(llm_client=llm_client)
        self._decision_agent = decision_agent or FishingDecisionAgent(llm_client=llm_client)

    def process_request(
        self,
        query_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        date_str: Optional[str] = None,
        temporal_resolution: Optional[Any] = None,
        requested_capabilities: Optional[List[str]] = None,
    ) -> CoordinatorResponse:
        """
        Processes a user request end-to-end.

        Args:
            query_text: Natural language user query.
            latitude: Optional latitude.
            longitude: Optional longitude.
            date_str: Optional date string 'YYYY-MM-DD'.
            temporal_resolution: Optional TemporalResolution dataclass from resolver.
            requested_capabilities: Optional pre-computed capabilities list from router.

        Returns:
            Unified CoordinatorResponse.
        """
        request_dict = {
            "query_text": query_text,
            "latitude": latitude,
            "longitude": longitude,
            "date_str": date_str,
        }
        
        # 1. Routing
        if requested_capabilities is not None:
            requested_caps = requested_capabilities
        else:
            requested_caps = self._router.get_capabilities(query_text)
        
        if not requested_caps:
            # Unrelated or ambiguous query
            return CoordinatorResponse(
                success=False,
                request=request_dict,
                routing=RoutingInfo(requested_capabilities=[], agents_invoked=[]),
                errors=["Request is ambiguous or outside supported domain capabilities."]
            )

        # 2. Validation
        # Check if coordinates are required for the identified capabilities
        # 2. Validation
        # Check if coordinates are required for the identified capabilities
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
                routing=RoutingInfo(requested_capabilities=requested_caps, agents_invoked=[]),
                errors=errors
            )

        # 3. Execution & Aggregation
        agents_invoked = []
        habitat_res = None
        weather_res = None
        geofencing_res = None
        decision_res = None

        # Execute domain capabilities
        if "fishing_decision" in requested_caps:
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
                errors.append(f"Fishing Decision Agent encountered a critical error: {e}")
        
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
                errors.append(f"Habitat Agent encountered a critical error: {e}")

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
                errors.append(f"Weather Agent encountered a critical error: {e}")

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
                errors.append(f"Geofencing Agent encountered a critical error: {e}")

        # 4. Determine overall success
        any_success = False
        if decision_res and decision_res.success: any_success = True
        if habitat_res and habitat_res.success: any_success = True
        if weather_res and weather_res.success: any_success = True
        if geofencing_res and geofencing_res.success: any_success = True
        
        overall_success = any_success

        return CoordinatorResponse(
            success=overall_success,
            request=request_dict,
            routing=RoutingInfo(
                requested_capabilities=requested_caps,
                agents_invoked=agents_invoked
            ),
            habitat=habitat_res,
            weather=weather_res,
            geofencing=geofencing_res,
            fishing_decision=decision_res,
            comparison=habitat_res.comparison if (habitat_res and habitat_res.comparison) else None,
            errors=errors
        )
