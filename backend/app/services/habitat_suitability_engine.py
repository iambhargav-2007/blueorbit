import os
import json
from typing import Dict, Any, Optional

class HabitatSuitabilityEngine:
    def __init__(self, config_path: str = None):
        """
        Initializes the Habitat Suitability Engine with configurable thresholds.
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'suitability_config.json')
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Suitability config not found at: {config_path}")
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def _calculate_score(self, value: float, params: dict) -> float:
        """
        Calculates a 0-100 score based on optimal and absolute ranges.
        Uses a trapezoidal suitability function.
        """
        opt_min = params['optimal_min']
        opt_max = params['optimal_max']
        abs_min = params['absolute_min']
        abs_max = params['absolute_max']

        if value >= opt_min and value <= opt_max:
            return 100.0
        elif value <= abs_min or value >= abs_max:
            return 0.0
        elif value > abs_min and value < opt_min:
            # Linear ramp up
            return ((value - abs_min) / (opt_min - abs_min)) * 100.0
        elif value > opt_max and value < abs_max:
            # Linear ramp down
            return ((abs_max - value) / (abs_max - opt_max)) * 100.0
        return 0.0

    def _get_category(self, score: float) -> str:
        """
        Returns the categorical label for the overall score based on config.
        """
        categories = self.config.get("categories", [])
        for cat in categories:
            if score <= cat["max_score"]:
                return cat["label"]
        # Fallback to the highest category if it exceeds the max (e.g. 100.0 exactly)
        return categories[-1]["label"] if categories else "Unknown"

    def assess(self, marine_data: Dict[str, Any], strict_completeness: Optional[bool] = None) -> Dict[str, Any]:
        """
        Takes the output of the Marine Spatial Engine and converts it 
        into a deterministic habitat suitability assessment.
        """
        # If the marine spatial query failed, bubble up the failure
        if not marine_data.get("success", False):
            return {
                "success": False,
                "error": marine_data.get("error", "Marine data retrieval failed."),
                "requested": marine_data.get("requested")
            }

        temp_val = marine_data.get("temperature")
        chloro_val = marine_data.get("chlorophyll")

        temp_score = None
        chloro_score = None
        overall_score = None
        category = "Insufficient Data"
        explanation = []
        confidence = "Low"

        # Check data quality explicitly
        missing_temp = temp_val is None
        missing_chloro = chloro_val is None

        if missing_temp and missing_chloro:
            data_quality = "No environmental data"
            explanation.append("No environmental data available due to masking.")
        elif missing_temp:
            data_quality = "Missing Temperature"
            explanation.append("Temperature data is masked or missing.")
        elif missing_chloro:
            data_quality = "Missing Chlorophyll"
            explanation.append("Chlorophyll data is masked or missing.")
        else:
            data_quality = "Complete"

        # Determine if strict dual-variable completeness is enforced (e.g. for LIVE mode)
        is_strict = strict_completeness if strict_completeness is not None else (marine_data.get("temporal_mode") == "LIVE")

        # Process Temperature
        if not missing_temp:
            temp_score = self._calculate_score(temp_val, self.config["temperature"])
            if temp_score >= 70:
                explanation.append("Temperature conditions are highly suitable.")
            elif temp_score >= 40:
                explanation.append("Temperature conditions are moderately suitable.")
            else:
                explanation.append("Temperature conditions are less favorable.")

        # Process Chlorophyll
        if not missing_chloro:
            chloro_score = self._calculate_score(chloro_val, self.config["chlorophyll"])
            if chloro_score >= 70:
                explanation.append("Chlorophyll conditions are highly suitable.")
            elif chloro_score >= 40:
                explanation.append("Chlorophyll conditions are moderately suitable.")
            else:
                explanation.append("Chlorophyll conditions are less favorable.")

        # Calculate Overall Score
        weights = self.config["weights"]
        temp_weight = weights["temperature"]
        chloro_weight = weights["chlorophyll"]

        if not missing_temp and not missing_chloro:
            overall_score = (temp_score * temp_weight) + (chloro_score * chloro_weight)
            category = self._get_category(overall_score)
            explanation.append(f"Resulting in a {category.lower()} overall habitat suitability.")
            confidence = "High"
        elif is_strict:
            # Under strict completeness (e.g. live mode), missing either required variable
            # yields Insufficient Data to prevent biased partial calculations or mixing.
            overall_score = None
            category = "Insufficient Data"
            confidence = "Low"
            explanation.append("Insufficient data: Both temperature and chlorophyll are required without temporal mixing.")
        elif not missing_temp:
            # Configurable policy: If only one is present, calculate partial score but lower confidence
            # Here we just use the temp score directly as the overall proxy for partial data
            overall_score = temp_score
            category = self._get_category(overall_score)
            explanation.append(f"Resulting in a {category.lower()} suitability based on temperature alone (reduced confidence).")
            confidence = "Moderate"
        elif not missing_chloro:
            overall_score = chloro_score
            category = self._get_category(overall_score)
            explanation.append(f"Resulting in a {category.lower()} suitability based on chlorophyll alone (reduced confidence).")
            confidence = "Moderate"

        return {
            "latitude": marine_data.get("matched_latitude"),
            "longitude": marine_data.get("matched_longitude"),
            "date": marine_data.get("requested_date"),
            "temperature_c": temp_val,
            "chlorophyll_mg_m3": chloro_val,
            "temperature_score": round(temp_score, 2) if temp_score is not None else None,
            "chlorophyll_score": round(chloro_score, 2) if chloro_score is not None else None,
            "overall_suitability_score": round(overall_score, 2) if overall_score is not None else None,
            "fishing_potential": category,
            "data_quality": data_quality,
            "confidence": confidence,
            "explanation": " ".join(explanation),
            "success": True,
            "disclaimer": "This is a prototype heuristic habitat suitability model based on environmental indicators. It does not predict exact fish abundance or guarantee catch."
        }
