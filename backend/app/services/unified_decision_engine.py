"""
unified_decision_engine.py

Unified Fishing Decision Engine for Blue Orbit (ORCA) — Step 20.

Deterministic synthesis of:
  1. Marine habitat suitability (SST & Chlorophyll-a from Copernicus)
  2. Weather / Sea-State Safety (Wind & Waves from Open-Meteo or Parquet)
  3. Geofencing & EEZ compliance (Indian EEZ boundary buffer)

Rules & Invariants:
  - This is a DECISION-SUPPORT system based on environmental and meteorological observations.
  - NEVER claims guaranteed catch, fish abundance, or vessel safety.
  - The deterministic engine is the SOLE authority on the recommendation and score.
  - The LLM is strictly prohibited from altering the decision, scores, or risk values.
  - Zero cross-temporal mixing (never combine live marine data with historical weather).
  - Outside supported Indian EEZ -> NOT_RECOMMENDED (noted as dataset coverage, not legal determination).
"""

from typing import Dict, Any, Optional, List
from ..agents.schemas import FishingDecision, LocationInfo


class UnifiedFishingDecisionEngine:
    """
    Authoritative deterministic engine that aggregates habitat, weather, and geofencing
    into a unified fishing recommendation (FAVORABLE, CAUTION, NOT_RECOMMENDED, INSUFFICIENT_DATA).
    """

    def evaluate(
        self,
        habitat_data: Optional[Dict[str, Any]],
        weather_data: Optional[Dict[str, Any]],
        geofence_data: Optional[Dict[str, Any]],
        latitude: float,
        longitude: float,
        date_str: Optional[str] = None,
        temporal_mode: str = "LIVE",
    ) -> FishingDecision:
        """
        Synthesizes domain engine outputs into a normalized FishingDecision.
        """
        reasons: List[str] = []
        warnings: List[str] = []
        data_sources: List[str] = []

        # ------------------------------------------------------------------
        # 1. Coordinate Validation
        # ------------------------------------------------------------------
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            return FishingDecision(
                decision="NOT_RECOMMENDED",
                overall_score=0.0,
                confidence="LOW",
                limiting_factor="Invalid Coordinates",
                reasons=["Supplied coordinates are out of valid geographic range."],
                warnings=["Invalid latitude or longitude."],
                location=LocationInfo(latitude=latitude, longitude=longitude),
                timestamp=date_str,
                data_status="INSUFFICIENT_DATA",
                temporal_mode=temporal_mode,
            )

        location_info = LocationInfo(latitude=latitude, longitude=longitude)

        # ------------------------------------------------------------------
        # 2. Unsupported Future Rejection
        # ------------------------------------------------------------------
        if temporal_mode == "UNSUPPORTED_FUTURE":
            return FishingDecision(
                decision="INSUFFICIENT_DATA",
                overall_score=None,
                confidence="LOW",
                limiting_factor="Unsupported Future Date",
                reasons=[
                    f"Requested date {date_str} is in the future. Marine weather forecasts and oceanographic "
                    "projections are unsupported without verified forecast providers."
                ],
                warnings=["Official IMD marine forecasts are not yet integrated into the decision support system."],
                location=location_info,
                timestamp=date_str,
                data_status="INSUFFICIENT_DATA",
                temporal_mode=temporal_mode,
            )

        # ------------------------------------------------------------------
        # 3. Extract Domain Attributes
        # ------------------------------------------------------------------
        # Habitat
        hab_success = bool(habitat_data and habitat_data.get("success", False))
        hab_score: Optional[float] = (
            habitat_data.get("habitat_score") or habitat_data.get("overall_suitability_score")
        ) if hab_success else None
        hab_status: Optional[str] = habitat_data.get("fishing_potential") if hab_success else "Insufficient Data"
        hab_conf = habitat_data.get("confidence") if hab_success else "Low"
        hab_source = habitat_data.get("source") if hab_success else None
        if hab_source:
            data_sources.append(hab_source)

        # Weather
        weath_success = bool(weather_data and weather_data.get("success", False))
        weath_score: Optional[float] = None
        weath_risk: Optional[str] = "Insufficient Data"
        weath_conf = "Low"
        weath_source = None

        if weath_success and weather_data:
            conditions = weather_data.get("weather_conditions") or {}
            weath_score = (
                weather_data.get("safety_score")
                or weather_data.get("overall_safety_score")
                or conditions.get("overall_safety_score")
            )
            weath_risk = weather_data.get("risk_level") or "Insufficient Data"
            weath_conf = weather_data.get("confidence") or "Low"
            weath_source = weather_data.get("source") or conditions.get("source")
            if weath_source:
                data_sources.append(weath_source)

        # Geofence
        geo_success = bool(geofence_data and geofence_data.get("success", False))
        is_inside_eez: Optional[bool] = geofence_data.get("is_inside_eez") if geo_success else None
        geo_status: Optional[str] = geofence_data.get("status") if geo_success else "UNKNOWN"
        data_sources.append("Indian EEZ Spatial Layer (VLIZ)")

        # Check protected area coverage notice
        if geofence_data and not geofence_data.get("protected_area_coverage_available", False):
            warnings.append(
                "Marine protected area boundary coverage is currently unavailable in the spatial index. "
                "Consult local maritime sanctuary rules."
            )

        # ------------------------------------------------------------------
        # 4. Critical Data Completeness Checks
        # ------------------------------------------------------------------
        missing_domains = []
        if not hab_success or hab_status == "Insufficient Data" or hab_score is None:
            missing_domains.append("habitat")
        if not weath_success or weath_risk in ["Insufficient Data", None]:
            missing_domains.append("weather")

        if missing_domains:
            if len(missing_domains) > 1:
                lim_factor = "Multiple Factors"
            elif "weather" in missing_domains:
                lim_factor = "Insufficient Weather Data"
            else:
                lim_factor = "Insufficient Marine Data"

            if "weather" in missing_domains:
                reasons.append("Marine weather observations are unavailable or insufficient to evaluate sea-state safety.")
            if "habitat" in missing_domains:
                reasons.append("Oceanographic environmental observations (SST/Chlorophyll-a) are unavailable.")

            return FishingDecision(
                decision="INSUFFICIENT_DATA",
                overall_score=None,
                confidence="LOW",
                habitat_score=hab_score,
                habitat_status=hab_status,
                weather_score=weath_score,
                weather_risk=weath_risk,
                geofence_status=geo_status,
                limiting_factor=lim_factor,
                reasons=reasons,
                warnings=warnings,
                location=location_info,
                timestamp=date_str,
                data_sources=data_sources,
                data_status="INSUFFICIENT_DATA",
                temporal_mode=temporal_mode,
            )

        # ------------------------------------------------------------------
        # 5. Geofence Boundary Check (Hard Stop)
        # ------------------------------------------------------------------
        if is_inside_eez is False or geo_status == "OUTSIDE EEZ":
            warnings.append(
                "Location is outside the currently supported Indian EEZ data boundary. "
                "(Note: This refers to dataset boundary coverage, not a determination of legal fishing rights)."
            )
            reasons.append("Vessel position is outside supported Indian Exclusive Economic Zone coverage.")
            return FishingDecision(
                decision="NOT_RECOMMENDED",
                overall_score=round(min(hab_score or 0.0, weath_score or 0.0), 1),
                confidence="HIGH" if hab_conf == "High" and weath_conf == "High" else "MEDIUM",
                habitat_score=hab_score,
                habitat_status=hab_status,
                weather_score=weath_score,
                weather_risk=weath_risk,
                geofence_status="OUTSIDE EEZ",
                limiting_factor="EEZ Boundary",
                reasons=reasons,
                warnings=warnings,
                location=location_info,
                timestamp=date_str,
                data_sources=data_sources,
                data_status="COMPLETE",
                temporal_mode=temporal_mode,
            )

        if geo_status == "WARNING":
            dist_b = geofence_data.get("distance_to_boundary_km")
            dist_str = f" (~{dist_b:.1f} km)" if dist_b is not None else ""
            warnings.append(
                f"Vessel is close to the Indian EEZ boundary buffer zone{dist_str}. "
                "Maintain active navigational and radio awareness."
            )

        # ------------------------------------------------------------------
        # 6. Deterministic Safety & Habitat Combinations
        # ------------------------------------------------------------------
        is_weather_high_risk = weath_risk in ["High Risk", "Very High Risk"] or (weath_score is not None and weath_score <= 40.0)
        is_weather_moderate_risk = weath_risk == "Moderate Risk" or (weath_score is not None and 40.0 < weath_score < 75.0)
        is_weather_low_risk = weath_risk == "Low Risk" or (weath_score is not None and weath_score >= 75.0)

        is_habitat_high = hab_status == "High"
        is_habitat_moderate = hab_status == "Moderate"
        is_habitat_low = hab_status == "Low"

        decision: str = "CAUTION"
        limiting_factor: str = "Multiple Factors"

        # Case A: Hazardous Weather (Absolute Hard Stop)
        if is_weather_high_risk:
            decision = "NOT_RECOMMENDED"
            limiting_factor = "Weather Safety"
            reasons.append(f"Marine weather conditions present significant safety risks ({weath_risk}).")
            warnings.append("Small craft advisory: high winds or elevated waves exceed recommended navigational thresholds.")
            if is_habitat_high:
                reasons.append("Although ocean habitat suitability is high, fishing is NOT RECOMMENDED due to hazardous sea state.")

        # Case B: Low Habitat Potential
        elif is_habitat_low:
            decision = "NOT_RECOMMENDED"
            limiting_factor = "Habitat Suitability"
            reasons.append("Environmental parameters indicate low habitat suitability for fish aggregation (suboptimal SST or chlorophyll-a).")
            if is_weather_low_risk:
                reasons.append("Weather conditions are calm and safe, but environmental productivity is low.")

        # Case C: High Habitat + Low Weather Risk
        elif is_habitat_high and is_weather_low_risk:
            if geo_status == "WARNING":
                decision = "CAUTION"
                limiting_factor = "EEZ Boundary"
                reasons.append("Excellent habitat suitability and safe marine weather, but location is close to the EEZ boundary.")
            else:
                decision = "FAVORABLE"
                limiting_factor = "None"
                reasons.append("Favorable environmental ocean conditions (SST and chlorophyll-a favorable for fish aggregation).")
                reasons.append("Low maritime weather risk (calm sea state and favorable wind speeds).")
                reasons.append("Position confirmed inside supported Indian EEZ boundaries.")

        # Case D: High Habitat + Moderate Weather Risk
        elif is_habitat_high and is_weather_moderate_risk:
            decision = "CAUTION"
            limiting_factor = "Weather Safety"
            reasons.append("Oceanographic habitat suitability is favorable, but moderate sea-state requires maritime caution.")
            warnings.append("Moderate weather conditions: monitor wind gusts and wave chop closely.")

        # Case E: Moderate Habitat + Low Weather Risk
        elif is_habitat_moderate and is_weather_low_risk:
            decision = "CAUTION"
            limiting_factor = "Habitat Suitability"
            reasons.append("Sea state is safe for navigation, but oceanographic habitat suitability is moderate.")

        # Case F: Moderate Habitat + Moderate Weather Risk
        elif is_habitat_moderate and is_weather_moderate_risk:
            decision = "CAUTION"
            limiting_factor = "Multiple Factors"
            reasons.append("Both environmental habitat suitability and sea-state weather safety are moderate.")
            warnings.append("Exercise maritime caution; conditions are neither optimal nor hazardous.")

        else:
            decision = "CAUTION"
            limiting_factor = "Multiple Factors"
            reasons.append("Mixed environmental and weather indicators.")

        # ------------------------------------------------------------------
        # 7. Aggregate Decision-Support Score
        # ------------------------------------------------------------------
        overall_score: Optional[float] = None
        if hab_score is not None and weath_score is not None:
            if decision == "NOT_RECOMMENDED":
                overall_score = round(min(hab_score, weath_score), 1)
            else:
                overall_score = round(0.5 * hab_score + 0.5 * weath_score, 1)

        # ------------------------------------------------------------------
        # 8. Confidence Determination
        # ------------------------------------------------------------------
        if hab_conf == "High" and weath_conf == "High":
            confidence = "HIGH"
        elif hab_conf == "Low" or weath_conf == "Low":
            confidence = "LOW"
        else:
            confidence = "MEDIUM"

        return FishingDecision(
            decision=decision,
            overall_score=overall_score,
            confidence=confidence,
            habitat_score=hab_score,
            habitat_status=hab_status,
            weather_score=weath_score,
            weather_risk=weath_risk,
            geofence_status=geo_status,
            limiting_factor=limiting_factor,
            reasons=reasons,
            warnings=warnings,
            location=location_info,
            timestamp=date_str,
            data_sources=data_sources,
            data_status="COMPLETE",
            temporal_mode=temporal_mode,
        )
