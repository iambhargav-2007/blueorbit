import os
from typing import Dict, Any, Optional

from .base_marine_provider import BaseMarineProvider
from ..services.marine_spatial_engine import MarineSpatialEngine
from ..config import MARINE_PARQUET_PATH

class CacheMarineProvider(BaseMarineProvider):
    """
    Cache provider for marine environmental observations.
    Reads from the local processed Parquet dataset (processed_marine_db.parquet)
    using the spatial indexing and query capabilities of MarineSpatialEngine.
    """

    def __init__(self, parquet_path: Optional[str] = None, max_distance_km: float = 50.0):
        self.parquet_path = parquet_path or MARINE_PARQUET_PATH
        if not os.path.exists(self.parquet_path):
            raise FileNotFoundError(f"Processed marine dataset not found at: {self.parquet_path}")

        self.engine = MarineSpatialEngine(
            parquet_path=self.parquet_path,
            max_distance_km=max_distance_km
        )

    def get_marine_data(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves marine observation from local cached Parquet via nearest-neighbor spatial index.
        """
        return self.engine.query(lat=lat, lon=lon, date_str=date_str)
