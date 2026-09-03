import os
import json
from typing import Dict, Any

class WeatherSafetyEngine:
    def __init__(self, config_path: str = None):
        """
        Initializes the Weather Safety Engine with configurable thresholds.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'weather_safety_config.json')
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Weather safety config not found at: {config_path}")
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def _calculate_score(self, value: float, params: dict) -> float:
        """
        Calculates a 0-100 safety score using linear decay for hazardous conditions.
        value: wind speed or wave height
        params: dict containing optimal_max and absolute_max
        """
        opt_max = params['optimal_max']
        abs_max = params['absolute_max']

        if value <= opt_max:
            return 100.0
        elif value >= abs_max:
            return 0.0
        else:
            # Linear decay as value increases from optimal to absolute max
            return ((abs_max - value) / (abs_max - opt_max)) * 100.0

    def _get_category(self, score: float) -> str:
        """
        Returns the categorical risk label based on config.
        Lower score = higher risk.
        """
        categories = self.config.get("categories", [])
        for cat in categories:
            if score <= cat["max_score"]:
                return cat["label"]
        return categories[-1]["label"] if categories else "Unknown"

    def assess(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes the output of a WeatherProvider and converts it 
        into a deterministic safety assessment.
        """
        if not weather_data.get("success", False):
            return {
                "success": False,
                "error": weather_data.get("error", "Weather data retrieval failed."),
                "requested": weather_data.get("requested")
            }

        wind_val = weather_data.get("wind_speed_knots")
        wave_val = weather_data.get("wave_height_meters")

        missing_wind = wind_val is None
        missing_wave = wave_val is None

        if missing_wind and missing_wave:
            data_quality = "Insufficient Data"
            confidence = "Low"
            risk_level = "Insufficient Data"
            explanation = "Missing critical weather factors (wind and waves). Cannot evaluate safety."
            return self._build_result(weather_data, None, None, None, risk_level, data_quality, confidence, explanation)

        if missing_wind or missing_wave:
            data_quality = "Partial"
            confidence = "Low"
            risk_level = "Insufficient Data"
            missing_vars = []
            if missing_wind: missing_vars.append("wind")
            if missing_wave: missing_vars.append("wave")
            explanation = f"Missing critical weather factors ({' and '.join(missing_vars)}). Cannot evaluate complete marine safety."
            return self._build_result(weather_data, None, None, None, risk_level, data_quality, confidence, explanation)

        # Complete data available
        data_quality = "Complete"
        
        # Calculate individual scores
        wind_score = self._calculate_score(wind_val, self.config["wind"])
        wave_score = self._calculate_score(wave_val, self.config["wave"])
        
        # Overall safety score is the minimum (bottleneck) for conservative risk evaluation
        overall_score = min(wind_score, wave_score)
        
        risk_level = self._get_category(overall_score)
        confidence = "High"

        # Generate deterministic explanation
        explanation_parts = []
        
        if wind_score >= 80:
            explanation_parts.append("Wind conditions are favorable")
        elif wind_score >= 50:
            explanation_parts.append("Wind conditions are moderate")
        else:
            explanation_parts.append("Wind conditions are hazardous")
            
        if wave_score >= 80:
            explanation_parts.append("wave conditions are favorable")
        elif wave_score >= 50:
            explanation_parts.append("wave conditions are moderate")
        else:
            explanation_parts.append("wave conditions are hazardous")

        explanation = f"{explanation_parts[0]}, and {explanation_parts[1]}, resulting in a {risk_level.lower()}."

        return self._build_result(weather_data, wind_score, wave_score, overall_score, risk_level, data_quality, confidence, explanation)

    def _build_result(self, weather_data: Dict[str, Any], wind_score, wave_score, overall_score, risk_level, data_quality, confidence, explanation) -> Dict[str, Any]:
        return {
            "latitude": weather_data.get("latitude"),
            "longitude": weather_data.get("longitude"),
            "date": weather_data.get("date"),
            "matched_latitude": weather_data.get("matched_latitude"),
            "matched_longitude": weather_data.get("matched_longitude"),
            "distance_km": weather_data.get("distance_km"),
            "wind_speed_knots": weather_data.get("wind_speed_knots"),
            "wind_direction": weather_data.get("wind_direction"),
            "surface_pressure_hpa": weather_data.get("surface_pressure_hpa"),
            "wave_height_meters": weather_data.get("wave_height_meters"),
            "wave_direction": weather_data.get("wave_direction"),
            "wave_period_seconds": weather_data.get("wave_period_seconds"),
            "source": weather_data.get("source"),
            "data_status": weather_data.get("data_status"),
            "observation_type": weather_data.get("observation_type"),
            "temporal_mode": weather_data.get("temporal_mode"),
            "wind_safety_score": round(wind_score, 2) if wind_score is not None else None,
            "wave_safety_score": round(wave_score, 2) if wave_score is not None else None,
            "overall_safety_score": round(overall_score, 2) if overall_score is not None else None,
            "risk_level": risk_level,
            "data_quality": data_quality,
            "confidence": confidence,
            "explanation": explanation,
            "success": True,
            "disclaimer": "This is a prototype decision-support/risk indicator. It does not guarantee vessel safety or represent official maritime safety standards."
        }
