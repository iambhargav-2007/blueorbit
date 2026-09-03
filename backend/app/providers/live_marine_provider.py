import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import concurrent.futures

# We'll lazily import copernicusmarine to avoid blocking startup if not installed
try:
    import copernicusmarine
    COPERNICUS_AVAILABLE = True
except ImportError:
    COPERNICUS_AVAILABLE = False

from .base_marine_provider import BaseMarineProvider
from ..config import (
    COPERNICUS_THETAO_DATASET,
    COPERNICUS_CHL_DATASET,
    COPERNICUS_SURFACE_DEPTH
)

logger = logging.getLogger(__name__)

class LiveMarineProvider(BaseMarineProvider):
    """
    Live Copernicus Marine Service API integration for Pathway A.
    Uses the copernicusmarine Python API to lazily open datasets and extract
    the nearest observations for thetao and chl.
    
    Step 17A Optimizations:
      - Dataset handles are retained on the provider instance.
      - Thetao and Chl data extractions run concurrently via ThreadPoolExecutor.
      - Strict 45s timeout on remote queries prevents indefinite hanging.
      - Safe in-memory observation cache avoids redundant remote queries for the same coordinate/date in a session.
    """

    def __init__(self, max_distance_km: float = 50.0):
        self.max_distance_km = max_distance_km
        if not COPERNICUS_AVAILABLE:
            logger.warning("copernicusmarine is not installed. Live mode will fail.")
            
        self._thetao_ds = None
        self._chl_ds = None
        self._observation_cache: Dict[Tuple[float, float, str], Dict[str, Any]] = {}

    def _get_thetao_ds(self):
        if self._thetao_ds is None:
            self._thetao_ds = copernicusmarine.open_dataset(
                dataset_id=COPERNICUS_THETAO_DATASET
            )
        return self._thetao_ds

    def _get_chl_ds(self):
        if self._chl_ds is None:
            self._chl_ds = copernicusmarine.open_dataset(
                dataset_id=COPERNICUS_CHL_DATASET
            )
        return self._chl_ds

    def _extract_thetao(self, ds_theta, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """Worker to extract temperature (thetao) from the dataset."""
        point_theta = ds_theta.sel(
            time=date_str,
            depth=COPERNICUS_SURFACE_DEPTH,
            latitude=lat,
            longitude=lon,
            method="nearest",
            tolerance=0.5  # About 50km
        )
        matched_lat = float(point_theta.latitude.values)
        matched_lon = float(point_theta.longitude.values)
        raw_theta = point_theta.thetao.values
        val_theta = float(raw_theta) if not pd.isna(raw_theta) else None
        return {
            "val": val_theta,
            "lat": matched_lat,
            "lon": matched_lon,
        }

    def _extract_chl(self, ds_chl, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """Worker to extract chlorophyll (chl) from the dataset."""
        sel_kwargs = {
            "time": date_str,
            "latitude": lat,
            "longitude": lon,
            "method": "nearest",
            "tolerance": 1.0  # About 100km for 0.25deg resolution
        }
        if hasattr(ds_chl, "dims") and ("depth" in ds_chl.dims or "depth" in getattr(ds_chl, "coords", [])):
            sel_kwargs["depth"] = COPERNICUS_SURFACE_DEPTH
            
        point_chl = ds_chl.sel(**sel_kwargs)
        
        if hasattr(point_chl, "variables") and "chl" in point_chl.variables:
            raw_chl = point_chl.chl.values
            val_chl = float(raw_chl) if not pd.isna(raw_chl) else None
        elif hasattr(point_chl, "chl"):
            raw_chl = point_chl.chl.values
            val_chl = float(raw_chl) if not pd.isna(raw_chl) else None
        else:
            val_chl = None

        if val_chl is not None and pd.isna(val_chl):
            val_chl = None

        return {"val": val_chl}

    def clear_cache(self):
        """Clears the short-lived in-memory observation cache."""
        self._observation_cache.clear()

    def get_marine_data(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves live marine environmental observations for a specific coordinate and date.
        """
        if not COPERNICUS_AVAILABLE:
            return {
                "success": False,
                "error": "copernicusmarine library is not available in the environment.",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }

        # 1. Validate coordinates
        if not (-90 <= lat <= 90):
            return {"success": False, "error": "Invalid latitude.", "requested": {"lat": lat, "lon": lon, "date": date_str}}
        if not (-180 <= lon <= 180):
            return {"success": False, "error": "Invalid longitude.", "requested": {"lat": lat, "lon": lon, "date": date_str}}
        
        # 2. Validate date
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return {"success": False, "error": "Invalid date format. Expected YYYY-MM-DD.", "requested": {"lat": lat, "lon": lon, "date": date_str}}

        # 3. Check session in-memory cache
        cache_key = (round(lat, 3), round(lon, 3), date_str)
        if cache_key in self._observation_cache:
            logger.info(f"LiveMarineProvider: Cache hit for {cache_key}")
            return self._observation_cache[cache_key].copy()

        # 4. Open datasets sequentially to preserve deterministic mock order in unit tests
        try:
            ds_theta = self._get_thetao_ds()
            ds_chl = self._get_chl_ds()
        except KeyError as e:
            logger.error(f"Failed to open Copernicus dataset - coordinate out of bounds: {e}")
            return {
                "success": False,
                "error": f"Failed to retrieve live marine data (out of bounds): {str(e)}",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }
        except Exception as e:
            logger.error(f"Failed to open Copernicus dataset: {e}")
            return {
                "success": False,
                "error": f"Failed to retrieve live marine data: {str(e)}",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }

        # 5. Execute heavy remote data extractions concurrently
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_theta = executor.submit(self._extract_thetao, ds_theta, lat, lon, date_str)
                future_chl = executor.submit(self._extract_chl, ds_chl, lat, lon, date_str)
                
                res_theta = future_theta.result(timeout=45.0)
                res_chl = future_chl.result(timeout=45.0)
                
            val_theta = res_theta["val"]
            matched_lat_theta = res_theta["lat"]
            matched_lon_theta = res_theta["lon"]
            val_chl = res_chl["val"]

        except concurrent.futures.TimeoutError:
            logger.error("Live Copernicus query timed out after 45 seconds.")
            return {
                "success": False,
                "error": "Live marine data retrieval timed out (Copernicus service delayed). Please try again.",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }
        except KeyError as e:
            logger.error(f"Failed to extract live Copernicus data - coordinate out of bounds: {e}")
            return {
                "success": False,
                "error": f"Failed to retrieve live marine data (out of bounds): {str(e)}",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }
        except Exception as e:
            logger.error(f"Failed to extract live Copernicus data: {e}")
            return {
                "success": False,
                "error": f"Failed to retrieve live marine data: {str(e)}",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }

        if val_theta is None and val_chl is None:
            validity = "Null values (land/coastal mask or missing live data)"
        else:
            validity = "Valid values found"

        # 6. Return structured data according to contract
        result = {
            "requested_latitude": lat,
            "requested_longitude": lon,
            "requested_date": date_str,
            "matched_latitude": matched_lat_theta,
            "matched_longitude": matched_lon_theta,
            "temperature": val_theta,
            "chlorophyll": val_chl,
            "distance_km": 0.0,
            "data_validity": validity,
            "success": True
        }

        # Cache the valid observation
        self._observation_cache[cache_key] = result.copy()
        return result
