"""
resolver.py

Location Resolver for Blue Orbit (ORCA) - Step 18.
Resolves human-friendly place names, coastal sectors, and coordinate strings
into normalized LocationContext objects without LLM hallucinations.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from .schemas import LocationContext, LocationResolveResponse

logger = logging.getLogger(__name__)

# Curated reference coastal locations along the Indian West Coast
COASTAL_PLACES: Dict[str, Dict[str, Any]] = {
    "standard test sector": {
        "lat": 19.50,
        "lon": 70.50,
        "display_name": "Standard Test Sector (19.50° N, 70.50° E)",
        "aliases": ["test sector", "standard sector"]
    },
    "mumbai": {
        "lat": 18.94,
        "lon": 72.84,
        "display_name": "Mumbai Coast, Maharashtra",
        "aliases": ["mumbai coast", "bombay", "bombay coast", "mumbai port"]
    },
    "goa": {
        "lat": 15.41,
        "lon": 73.80,
        "display_name": "Goa Coastal Zone",
        "aliases": ["goa coast", "panaji", "panjim", "mormugao", "mormugao port", "south goa", "north goa"]
    },
    "veraval": {
        "lat": 20.90,
        "lon": 70.37,
        "display_name": "Veraval Port, Gujarat",
        "aliases": ["veraval port", "veraval coast", "somnath", "somnath coast"]
    },
    "porbandar": {
        "lat": 21.64,
        "lon": 69.60,
        "display_name": "Porbandar Coast, Gujarat",
        "aliases": ["porbandar coast", "porbandar port"]
    },
    "ratnagiri": {
        "lat": 16.99,
        "lon": 73.30,
        "display_name": "Ratnagiri Coast, Maharashtra",
        "aliases": ["ratnagiri coast", "ratnagiri port", "konkan coast"]
    },
    "kochi": {
        "lat": 9.96,
        "lon": 76.22,
        "display_name": "Kochi Offshore, Kerala",
        "aliases": ["kochi coast", "cochin", "cochin port", "cochin offshore", "kochi port"]
    },
    "mangalore": {
        "lat": 12.91,
        "lon": 74.85,
        "display_name": "Mangalore Coast, Karnataka",
        "aliases": ["mangalore coast", "mangaluru", "new mangalore", "panambur"]
    },
    "karwar": {
        "lat": 14.80,
        "lon": 74.13,
        "display_name": "Karwar Port, Karnataka",
        "aliases": ["karwar coast", "karwar port"]
    },
    "alibaug": {
        "lat": 18.64,
        "lon": 72.87,
        "display_name": "Alibaug Coast, Maharashtra",
        "aliases": ["alibaug coast", "alibag"]
    },
    "okha": {
        "lat": 22.47,
        "lon": 69.07,
        "display_name": "Okha Port, Gujarat",
        "aliases": ["okha port", "okha coast", "dwarka", "dwarka coast"]
    },
    "diu": {
        "lat": 20.71,
        "lon": 70.98,
        "display_name": "Diu Coastal Waters",
        "aliases": ["diu coast", "diu island"]
    },
    "gujarat coast": {
        "lat": 21.00,
        "lon": 70.00,
        "display_name": "Gujarat Coastal Waters (Saurashtra)",
        "aliases": ["gujarat", "gulf of kutch", "gulf of khambhat", "saurashtra coast"]
    },
    "maharashtra coast": {
        "lat": 18.50,
        "lon": 72.50,
        "display_name": "Maharashtra Coastal Waters",
        "aliases": ["maharashtra", "north konkan"]
    },
    "karnataka coast": {
        "lat": 13.50,
        "lon": 74.50,
        "display_name": "Karnataka Coastal Waters",
        "aliases": ["karnataka", "canara coast"]
    },
    "kerala coast": {
        "lat": 10.00,
        "lon": 75.80,
        "display_name": "Kerala Coastal Waters",
        "aliases": ["kerala", "malabar coast"]
    }
}

# Landlocked entities mapped to helpful maritime guidance and suggestions
LANDLOCKED_AREAS: Dict[str, Dict[str, Any]] = {
    "rajasthan": {
        "message": "Rajasthan has no coastline. Did you mean the Gujarat coast?",
        "suggestions": ["Gujarat Coast", "Porbandar Coast", "Veraval Port"]
    },
    "punjab": {
        "message": "Punjab is a landlocked inland state with no marine coastline.",
        "suggestions": ["Gujarat Coast"]
    },
    "haryana": {
        "message": "Haryana is a landlocked state with no maritime coastline.",
        "suggestions": ["Gujarat Coast", "Maharashtra Coast"]
    },
    "delhi": {
        "message": "Delhi is an inland territory with no oceanographic waters.",
        "suggestions": ["Mumbai Coast", "Gujarat Coast"]
    },
    "madhya pradesh": {
        "message": "Madhya Pradesh is in central India and has no maritime coastline.",
        "suggestions": ["Gujarat Coast", "Maharashtra Coast"]
    },
    "telangana": {
        "message": "Telangana is an inland state with no coastal waters.",
        "suggestions": ["Goa Coastal Zone", "Maharashtra Coast"]
    },
    "uttar pradesh": {
        "message": "Uttar Pradesh has no marine coastline.",
        "suggestions": ["Gujarat Coast"]
    },
    "bihar": {
        "message": "Bihar has no marine coastline.",
        "suggestions": ["Gujarat Coast"]
    }
}


class LocationResolver:
    """
    Deterministic resolver for coastal points, places, and coordinates.
    """

    @staticmethod
    def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
        """
        Attempts to parse latitude and longitude pairs from formatted text.
        e.g. "19.5, 70.5", "19.5 70.5", "19.5N, 70.5E", "19.5° N, 70.5° E"
        """
        clean = text.replace("°", "").replace("N", "").replace("n", "").replace("E", "").replace("e", "")
        # Match two float numbers separated by comma, slash, or whitespace
        m = re.search(r"([-+]?\d+(?:\.\d+)?)[,\s/]+([-+]?\d+(?:\.\d+)?)", clean.strip())
        if m:
            try:
                lat = float(m.group(1))
                lon = float(m.group(2))
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    return lat, lon
            except ValueError:
                pass
        return None

    @classmethod
    def resolve_location(cls, query: str) -> LocationResolveResponse:
        """
        Main entry point for resolving a query string into a LocationContext.
        """
        if not query or not query.strip():
            return LocationResolveResponse(
                success=False,
                message="Location query cannot be empty.",
                suggestions=cls.get_all_places()[:5]
            )

        q_clean = query.strip().lower()
        # Remove common punctuation for matching
        q_norm = re.sub(r"[^\w\s\.\,\-]", "", q_clean).strip()

        # 1. Check for explicit coordinate input
        coords = cls.parse_coordinates(q_norm)
        if coords:
            lat, lon = coords
            return LocationResolveResponse(
                success=True,
                location=LocationContext(
                    latitude=lat,
                    longitude=lon,
                    display_name=f"{lat:.2f}° N, {lon:.2f}° E",
                    source="manual"
                )
            )

        # 2. Check for landlocked inquiries (e.g. "Rajasthan coast")
        for landlocked_name, info in LANDLOCKED_AREAS.items():
            if landlocked_name in q_norm:
                return LocationResolveResponse(
                    success=False,
                    message=info["message"],
                    suggestions=info["suggestions"]
                )

        # 3. Check exact place names & aliases
        for canonical, place_data in COASTAL_PLACES.items():
            if q_norm == canonical or q_norm in place_data["aliases"]:
                return LocationResolveResponse(
                    success=True,
                    location=LocationContext(
                        latitude=place_data["lat"],
                        longitude=place_data["lon"],
                        display_name=place_data["display_name"],
                        source="search"
                    )
                )

        # 4. Check substring matching
        best_match = None
        for canonical, place_data in COASTAL_PLACES.items():
            all_names = [canonical] + place_data["aliases"]
            for name in all_names:
                if name in q_norm or q_norm in name:
                    best_match = place_data
                    break
            if best_match:
                break

        if best_match:
            return LocationResolveResponse(
                success=True,
                location=LocationContext(
                    latitude=best_match["lat"],
                    longitude=best_match["lon"],
                    display_name=best_match["display_name"],
                    source="search"
                )
            )

        # 5. Unresolved place
        suggestions = cls.get_suggestions(q_norm)
        return LocationResolveResponse(
            success=False,
            message=f"Could not resolve coastal location for '{query}'. Please select from supported Indian West Coast places or choose on the map.",
            suggestions=suggestions if suggestions else ["Mumbai Coast", "Goa Coastal Zone", "Veraval Port", "Kochi Offshore"]
        )

    @classmethod
    def extract_location_from_text(cls, text: str) -> Optional[LocationContext]:
        """
        Extracts a coastal location mentioned inside natural language query text.
        e.g. "What is the habitat near Goa today?" -> extracts Goa
        """
        clean = text.lower()
        
        # Check coordinates first
        coords = cls.parse_coordinates(clean)
        if coords:
            lat, lon = coords
            return LocationContext(
                latitude=lat,
                longitude=lon,
                display_name=f"{lat:.2f}° N, {lon:.2f}° E",
                source="manual"
            )

        # Check coastal places (longest alias first to avoid greedy substrings)
        sorted_places = sorted(
            COASTAL_PLACES.items(),
            key=lambda item: max(len(a) for a in [item[0]] + item[1]["aliases"]),
            reverse=True
        )

        for canonical, place_data in sorted_places:
            names = [canonical] + place_data["aliases"]
            for name in names:
                # Word boundary match
                pattern = r"\b" + re.escape(name) + r"\b"
                if re.search(pattern, clean):
                    return LocationContext(
                        latitude=place_data["lat"],
                        longitude=place_data["lon"],
                        display_name=place_data["display_name"],
                        source="search"
                    )
        return None

    @classmethod
    def check_landlocked_mention(cls, text: str) -> Optional[str]:
        """
        Checks if the text contains a reference to a landlocked state.
        """
        clean = text.lower()
        for name, info in LANDLOCKED_AREAS.items():
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, clean):
                return info["message"]
        return None

    @classmethod
    def get_suggestions(cls, query: str) -> List[str]:
        """Returns matching coastal place suggestions."""
        q = query.lower().strip()
        matches = []
        for canonical, place_data in COASTAL_PLACES.items():
            if q in canonical or any(q in alias for alias in place_data["aliases"]):
                matches.append(place_data["display_name"])
        return matches[:5]

    @classmethod
    def get_all_places(cls) -> List[str]:
        """Returns all canonical display names."""
        return [p["display_name"] for p in COASTAL_PLACES.values()]


_resolver_instance: Optional[LocationResolver] = None

def get_location_resolver() -> LocationResolver:
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = LocationResolver()
    return _resolver_instance
