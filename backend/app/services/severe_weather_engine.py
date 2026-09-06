from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class SevereWeatherClassification(BaseModel):
    risk_level: str = Field(description="NORMAL, ELEVATED, SEVERE, EXTREME, INSUFFICIENT_DATA")
    is_affected: bool = Field(description="True if currently affected by severe weather or a cyclone")
    affected_status: str = Field(description="NOT_AFFECTED, POTENTIALLY_AFFECTED, AFFECTED, NO_VERIFIED_DATA")
    narrative: str

class SevereWeatherEngine:
    """
    Deterministically evaluates severe weather classification based on available wind/wave/pressure
    and verified cyclone alerts (if any).
    """

    def evaluate(
        self,
        wind_speed_knots: Optional[float] = None,
        wave_height_meters: Optional[float] = None,
        surface_pressure_hpa: Optional[float] = None,
        cyclone_alert: Optional[Dict[str, Any]] = None,
        distance_to_center_km: Optional[float] = None
    ) -> SevereWeatherClassification:
        
        # 1. Check verified cyclone data if available
        if cyclone_alert and cyclone_alert.get("status") != "UNAVAILABLE":
            # If we have real verified data, use it
            severity = cyclone_alert.get("severity", "UNKNOWN")
            radius = cyclone_alert.get("affected_radius_km")
            
            if distance_to_center_km is not None and radius is not None:
                if distance_to_center_km <= radius:
                    return SevereWeatherClassification(
                        risk_level="EXTREME" if severity in ["SEVERE", "EXTREME"] else "SEVERE",
                        is_affected=True,
                        affected_status="AFFECTED",
                        narrative=f"Location is within the affected radius ({radius}km) of a verified tropical system."
                    )
                else:
                    return SevereWeatherClassification(
                        risk_level="NORMAL",
                        is_affected=False,
                        affected_status="NOT_AFFECTED",
                        narrative="Location is outside the affected radius of known tropical systems."
                    )
            
            return SevereWeatherClassification(
                risk_level="SEVERE",
                is_affected=True,
                affected_status="POTENTIALLY_AFFECTED",
                narrative="Verified tropical system exists, but explicit radius/distance is unavailable. Caution advised."
            )
        
        # 2. Check local severe weather based on raw marine conditions (Not inferring a cyclone)
        # We classify extreme local weather
        if wind_speed_knots is None and wave_height_meters is None:
            return SevereWeatherClassification(
                risk_level="INSUFFICIENT_DATA",
                is_affected=False,
                affected_status="NO_VERIFIED_DATA",
                narrative="Insufficient verified data to classify severe weather."
            )
            
        risk = "NORMAL"
        affected = "NOT_AFFECTED"
        
        if wind_speed_knots and wind_speed_knots >= 45: # Gale force or higher
            risk = "SEVERE"
            affected = "AFFECTED"
            if wind_speed_knots >= 60:
                risk = "EXTREME"
        
        if wave_height_meters and wave_height_meters >= 4.0:
            risk = "SEVERE" if risk != "EXTREME" else "EXTREME"
            affected = "AFFECTED"
            if wave_height_meters >= 6.0:
                risk = "EXTREME"
                
        if risk == "NORMAL" and (wind_speed_knots and wind_speed_knots >= 25 or wave_height_meters and wave_height_meters >= 2.5):
            risk = "ELEVATED"
            
        narratives = {
            "NORMAL": "No severe weather indicators present in available verified data.",
            "ELEVATED": "Elevated wind/wave conditions detected. Not severe but caution recommended.",
            "SEVERE": "Severe marine weather conditions detected (gale-force winds or high waves). No verified cyclone alert.",
            "EXTREME": "Extreme marine weather conditions detected. Operations highly dangerous. No verified cyclone alert."
        }
        
        return SevereWeatherClassification(
            risk_level=risk,
            is_affected=(affected == "AFFECTED"),
            affected_status=affected if cyclone_alert is None or cyclone_alert.get("status") == "UNAVAILABLE" else "NO_VERIFIED_DATA",
            narrative=narratives[risk]
        )
