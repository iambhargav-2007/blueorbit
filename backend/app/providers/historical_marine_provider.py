import os
from typing import Dict, Any, Optional

from .base_marine_provider import BaseMarineProvider
from ..services.marine_spatial_engine import MarineSpatialEngine
from ..config import MARINE_PARQUET_PATH, MARINE_HISTORICAL_DIR

class HistoricalMarineProvider(BaseMarineProvider):
    """
    Historical provider for marine environmental observations.
    It acts as a clean abstraction to access date-partitioned ingested data.
    If the requested date exists in the new ingested historical Parquet partitions,
    it queries that partition.
    Otherwise, it can fall back to the existing baseline dataset (October 2025 cache).
    """

    def __init__(self, max_distance_km: float = 50.0):
        self.max_distance_km = max_distance_km
        self._baseline_engine = None
        self._date_engines = {}

    def _get_baseline_engine(self) -> MarineSpatialEngine:
        if self._baseline_engine is None:
            self._baseline_engine = MarineSpatialEngine(
                parquet_path=MARINE_PARQUET_PATH,
                max_distance_km=self.max_distance_km
            )
        return self._baseline_engine

    def _get_date_engine(self, date_str: str) -> Optional[MarineSpatialEngine]:
        if date_str in self._date_engines:
            return self._date_engines[date_str]

        # Check if the partition exists in the historical directory
        partition_dir = os.path.join(MARINE_HISTORICAL_DIR, f"date={date_str}")
        partition_file = os.path.join(partition_dir, "marine.parquet")
        
        if os.path.exists(partition_file):
            engine = MarineSpatialEngine(
                parquet_path=partition_file,
                max_distance_km=self.max_distance_km
            )
            self._date_engines[date_str] = engine
            return engine
            
        return None

    def get_marine_data(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves marine observation for the specified date and coordinate.
        First tries to read from the newly ingested daily partitions.
        If not found, delegates to the existing baseline cache.
        """
        # Try finding the specific daily ingestion file
        date_engine = self._get_date_engine(date_str)
        if date_engine:
            return date_engine.query(lat=lat, lon=lon, date_str=date_str)
            
        # Fall back to October 2025 baseline cache
        baseline_engine = self._get_baseline_engine()
        return baseline_engine.query(lat=lat, lon=lon, date_str=date_str)
