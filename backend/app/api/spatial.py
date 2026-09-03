"""
spatial.py

FastAPI router for Step 21: Premium Marine Spatial Intelligence.
Provides dedicated spatial endpoints for map visualization and click-to-analyze:
- GET /api/v1/spatial/eez: Real Indian EEZ GeoJSON boundary
- GET /api/v1/spatial/point: High-performance point analysis (geofence, habitat, weather, unified decision)
- GET /api/v1/spatial/grid: Real gridded ocean observations (SST, Chlorophyll, Habitat Suitability, Weather)
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np

from app import config
from app.location.resolver import LocationResolver
from app.services.temporal_resolver import TemporalContextResolver, TemporalMode
from app.services.unified_decision_engine import UnifiedFishingDecisionEngine
from app.tools.fishing_decision_tool import FishingDecisionTool
from app.tools.geofencing_tool import GeofencingTool
from app.agents.schemas import FishingDecision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spatial", tags=["spatial"])

# In-memory caches for static datasets
_EEZ_GEOJSON_CACHE: Optional[Dict[str, Any]] = None
_MARINE_PARQUET_DF: Optional[pd.DataFrame] = None
_WEATHER_PARQUET_DF: Optional[pd.DataFrame] = None

_location_resolver = LocationResolver()
_decision_tool = FishingDecisionTool()
_geofence_tool = GeofencingTool()
_decision_engine = UnifiedFishingDecisionEngine()
_temporal_resolver = TemporalContextResolver()


def _get_eez_geojson() -> Dict[str, Any]:
    global _EEZ_GEOJSON_CACHE
    if _EEZ_GEOJSON_CACHE is None:
        eez_path = Path(config.EEZ_GEOJSON_PATH)
        if not eez_path.exists():
            raise HTTPException(status_code=404, detail="EEZ boundary GeoJSON not found on server")
        with open(eez_path, "r", encoding="utf-8") as f:
            _EEZ_GEOJSON_CACHE = json.load(f)
    return _EEZ_GEOJSON_CACHE


def _get_marine_df() -> pd.DataFrame:
    global _MARINE_PARQUET_DF
    if _MARINE_PARQUET_DF is None:
        path = Path(config.MARINE_PARQUET_PATH)
        if path.exists():
            _MARINE_PARQUET_DF = pd.read_parquet(path)
        else:
            _MARINE_PARQUET_DF = pd.DataFrame()
    return _MARINE_PARQUET_DF


def _get_weather_df() -> pd.DataFrame:
    global _WEATHER_PARQUET_DF
    if _WEATHER_PARQUET_DF is None:
        path = Path(config.WEATHER_PARQUET_PATH)
        if path.exists():
            _WEATHER_PARQUET_DF = pd.read_parquet(path)
        else:
            _WEATHER_PARQUET_DF = pd.DataFrame()
    return _WEATHER_PARQUET_DF


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PointAnalysisLocation(BaseModel):
    latitude: float
    longitude: float
    display_name: str
    is_inside_eez: bool
    distance_to_boundary_km: Optional[float] = None
    zone_name: Optional[str] = None


class PointAnalysisResponse(BaseModel):
    success: bool
    location: PointAnalysisLocation
    geofence: Dict[str, Any]
    marine: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    decision: Optional[FishingDecision] = None
    temporal_mode: str
    timestamp: str
    error: Optional[str] = None


class GridCell(BaseModel):
    lat: float
    lon: float
    val: float
    label: str
    category: str


class GridLayerResponse(BaseModel):
    success: bool
    layer: str
    unit: str
    date: str
    temporal_mode: str
    source: str
    min_val: float
    max_val: float
    cells: List[GridCell]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/eez")
def get_eez_boundary():
    """
    Returns the authoritative Indian EEZ boundary GeoJSON.
    """
    return _get_eez_geojson()


@router.get("/point", response_model=PointAnalysisResponse)
def analyze_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    date: Optional[str] = Query(None, description="Observation date (YYYY-MM-DD or 'today')"),
):
    """
    Click-to-analyze endpoint: Returns comprehensive deterministic spatial intelligence
    for a clicked point, including EEZ status, Marine conditions, Weather safety,
    and Unified Fishing Decision.
    """
    # 1. Resolve temporal mode & date
    temp_res = _temporal_resolver.resolve(
        query_text="",
        explicit_date_str=date,
        stored_date_str=None
    )
    resolved_date = temp_res.date_str
    temporal_mode_str = temp_res.mode.value

    # 2. Resolve place name
    from app.location.resolver import COASTAL_PLACES
    display_name = f"Sector {lat:.2f}° N · {lon:.2f}° E"
    closest_dist = float("inf")
    closest_name = None
    for k, v in COASTAL_PLACES.items():
        dist = ((lat - v["lat"]) ** 2 + (lon - v["lon"]) ** 2) ** 0.5
        if dist < closest_dist:
            closest_dist = dist
            closest_name = v["display_name"]
    if closest_dist < 0.7:  # Within ~75 km
        display_name = f"Near {closest_name}"

    # 3. Perform unified fishing decision tool query
    decision_result = _decision_tool.get_fishing_decision(
        latitude=lat,
        longitude=lon,
        date_str=resolved_date,
        temporal_resolution=temp_res,
        query_text=f"Coordinates {lat}, {lon}"
    )

    if not decision_result.get("success"):
        # Even if data is unavailable, return structured response
        geo_res = _geofence_tool.check_point(lat, lon)
        loc_obj = PointAnalysisLocation(
            latitude=lat,
            longitude=lon,
            display_name=display_name,
            is_inside_eez=bool(geo_res.get("is_inside_eez", False)),
            distance_to_boundary_km=geo_res.get("distance_to_boundary_km"),
            zone_name=geo_res.get("zone_name"),
        )
        return PointAnalysisResponse(
            success=False,
            location=loc_obj,
            geofence=geo_res,
            marine=None,
            weather=None,
            decision=None,
            temporal_mode=temporal_mode_str,
            timestamp=resolved_date or "",
            error=decision_result.get("error", "Unable to analyze point"),
        )

    # 4. Extract sub-domain items
    fishing_dec: FishingDecision = decision_result["decision"]
    hab_data = decision_result.get("habitat_data")
    weath_data = decision_result.get("weather_data")
    geo_data = decision_result.get("geofence_data") or {}

    loc_obj = PointAnalysisLocation(
        latitude=lat,
        longitude=lon,
        display_name=display_name,
        is_inside_eez=bool(geo_data.get("is_inside_eez", False)),
        distance_to_boundary_km=geo_data.get("distance_to_boundary_km"),
        zone_name=geo_data.get("zone_name"),
    )

    return PointAnalysisResponse(
        success=True,
        location=loc_obj,
        geofence=geo_data,
        marine=hab_data,
        weather=weath_data,
        decision=fishing_dec,
        temporal_mode=temporal_mode_str,
        timestamp=resolved_date or "",
        error=None,
    )


@router.get("/grid", response_model=GridLayerResponse)
def get_grid_layer(
    layer: str = Query(..., pattern="^(sst|chlorophyll|habitat|weather)$", description="Target spatial layer"),
    date: Optional[str] = Query(None, description="Observation date (YYYY-MM-DD or 'today')"),
    step: int = Query(2, ge=1, le=10, description="Spatial subsampling step to keep transfer lightweight"),
):
    """
    Returns real, gridded spatial observations across the West Coast maritime grid.
    Never fabricates points; queries real Copernicus and Open-Meteo processed parquet datasets.
    """
    # Resolve date
    temp_res = _temporal_resolver.resolve(query_text="", explicit_date_str=date)
    target_date = temp_res.date_str or "2025-10-01"
    temp_mode = temp_res.mode.value

    cells: List[GridCell] = []
    unit = ""
    source = "Copernicus Marine (CMEMS)"
    min_val = 0.0
    max_val = 100.0

    if layer in ("sst", "chlorophyll", "habitat"):
        df = _get_marine_df()
        if df.empty:
            return GridLayerResponse(
                success=False,
                layer=layer,
                unit=unit,
                date=target_date,
                temporal_mode=temp_mode,
                source=source,
                min_val=0.0,
                max_val=0.0,
                cells=[],
            )

        # Match date or fallback to first available date in dataset
        if target_date in df["time"].values:
            sub_df = df[df["time"] == target_date]
        else:
            first_date = str(df["time"].iloc[0])
            sub_df = df[df["time"] == first_date]
            target_date = first_date

        # Drop NaN values for marine variables
        sub_df = sub_df.dropna(subset=["temperature_c", "chlorophyll_mg_m3"])
        if sub_df.empty:
            return GridLayerResponse(
                success=False,
                layer=layer,
                unit=unit,
                date=target_date,
                temporal_mode=temp_mode,
                source=source,
                min_val=0.0,
                max_val=0.0,
                cells=[],
            )

        # Subsample to keep Leaflet fast and lightweight (under 250KB transfer)
        sub_df = sub_df.iloc[::step]

        if layer == "sst":
            unit = "°C"
            source = "Copernicus Global Ocean Physics (0.083°)"
            min_val = float(np.nanmin(sub_df["temperature_c"]))
            max_val = float(np.nanmax(sub_df["temperature_c"]))

            for _, row in sub_df.iterrows():
                val = float(row["temperature_c"])
                if np.isnan(val) or np.isinf(val):
                    continue
                # Color binning: 26-31C
                if val >= 29.5:
                    cat = "sst-warm"
                elif val >= 28.0:
                    cat = "sst-optimal"
                else:
                    cat = "sst-cool"

                cells.append(GridCell(
                    lat=round(float(row["latitude"]), 3),
                    lon=round(float(row["longitude"]), 3),
                    val=round(val, 2),
                    label=f"{val:.1f} °C",
                    category=cat
                ))

        elif layer == "chlorophyll":
            unit = "mg/m³"
            source = "Copernicus Global Ocean Biogeochemistry (0.25°)"
            min_val = float(np.nanmin(sub_df["chlorophyll_mg_m3"]))
            max_val = float(np.nanmax(sub_df["chlorophyll_mg_m3"]))

            for _, row in sub_df.iterrows():
                val = float(row["chlorophyll_mg_m3"])
                if np.isnan(val) or np.isinf(val):
                    continue
                if val >= 0.5:
                    cat = "chl-high"
                elif val >= 0.2:
                    cat = "chl-moderate"
                else:
                    cat = "chl-low"

                cells.append(GridCell(
                    lat=round(float(row["latitude"]), 3),
                    lon=round(float(row["longitude"]), 3),
                    val=round(val, 3),
                    label=f"{val:.2f} mg/m³",
                    category=cat
                ))

        elif layer == "habitat":
            from app.services.habitat_suitability_engine import HabitatSuitabilityEngine
            suit_engine = HabitatSuitabilityEngine()
            unit = "Suitability Index"
            source = "Deterministic Habitat Suitability Engine"
            min_val = 0.0
            max_val = 100.0

            # Evaluate suitability on the fly or compute scores
            for _, row in sub_df.iterrows():
                t = float(row["temperature_c"])
                c = float(row["chlorophyll_mg_m3"])
                if np.isnan(t) or np.isnan(c):
                    continue
                res = suit_engine.assess({"success": True, "temperature": t, "chlorophyll": c})
                if not res.get("success"):
                    continue
                score = round(float(res.get("overall_suitability_score", 0.0)), 1)
                pot = res.get("fishing_potential", "Moderate")

                if pot == "High":
                    cat = "habitat-high"
                    label = f"High ({score})"
                elif pot == "Moderate":
                    cat = "habitat-moderate"
                    label = f"Mod ({score})"
                else:
                    cat = "habitat-low"
                    label = f"Low ({score})"

                cells.append(GridCell(
                    lat=round(float(row["latitude"]), 3),
                    lon=round(float(row["longitude"]), 3),
                    val=score,
                    label=label,
                    category=cat
                ))

    elif layer == "weather":
        wdf = _get_weather_df()
        unit = "knots / m"
        source = "Open-Meteo West Coast Marine Grid"

        if not wdf.empty:
            wdf = wdf.dropna(subset=["mean_wind_speed_knots", "mean_wave_height_meters"])
            if target_date in wdf["date"].values:
                sub_wdf = wdf[wdf["date"] == target_date]
            else:
                first_date = str(wdf["date"].iloc[0])
                sub_wdf = wdf[wdf["date"] == first_date]
                target_date = first_date

            sub_wdf = sub_wdf.iloc[::step]
            min_val = float(np.nanmin(sub_wdf["mean_wind_speed_knots"]))
            max_val = float(np.nanmax(sub_wdf["max_wind_speed_knots"]))

            for _, row in sub_wdf.iterrows():
                w_speed = float(row["mean_wind_speed_knots"])
                w_wave = float(row["mean_wave_height_meters"])
                if np.isnan(w_speed) or np.isnan(w_wave):
                    continue
                
                # Safety classification
                if w_speed > 25.0 or w_wave > 2.5:
                    cat = "weather-high-risk"
                    lbl = f"{w_speed:.0f}kn · {w_wave:.1f}m (High Risk)"
                elif w_speed > 15.0 or w_wave > 1.5:
                    cat = "weather-moderate-risk"
                    lbl = f"{w_speed:.0f}kn · {w_wave:.1f}m (Caution)"
                else:
                    cat = "weather-low-risk"
                    lbl = f"{w_speed:.0f}kn · {w_wave:.1f}m (Low Risk)"

                cells.append(GridCell(
                    lat=round(float(row["latitude"]), 3),
                    lon=round(float(row["longitude"]), 3),
                    val=round(w_speed, 1),
                    label=lbl,
                    category=cat
                ))

    return GridLayerResponse(
        success=True,
        layer=layer,
        unit=unit,
        date=target_date,
        temporal_mode=temp_mode,
        source=source,
        min_val=round(min_val, 2),
        max_val=round(max_val, 2),
        cells=cells,
    )
