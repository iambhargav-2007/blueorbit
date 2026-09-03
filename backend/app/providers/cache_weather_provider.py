import os
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
from datetime import datetime
from typing import Dict, Any, Optional

from .base_weather_provider import BaseWeatherProvider
from ..config import WEATHER_PARQUET_PATH

class CacheWeatherProvider(BaseWeatherProvider):
    """
    Cache provider for regional marine weather data.
    Reads from the local processed Parquet dataset (weather_regional_grid.parquet)
    using BallTree spatial indexing on the 0.5-degree grid.
    """

    def __init__(self, parquet_path: Optional[str] = None, max_distance_km: float = 100.0):
        self.parquet_path = parquet_path or WEATHER_PARQUET_PATH
        self.max_distance_km = max_distance_km
        self.date_groups = {}
        self._load_data()

    def _load_data(self):
        if not os.path.exists(self.parquet_path):
            raise FileNotFoundError(f"Weather dataset not found at: {self.parquet_path}")

        df = pd.read_parquet(self.parquet_path)
        
        # Ensure date is string format 'YYYY-MM-DD'
        df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        for date_str, group in df.groupby('date_str'):
            valid_group = group.dropna(subset=['latitude', 'longitude'])
            if valid_group.empty:
                continue

            coords_rad = np.deg2rad(valid_group[['latitude', 'longitude']].values)
            tree = BallTree(coords_rad, metric='haversine')
            
            self.date_groups[date_str] = {
                'tree': tree,
                'data': valid_group.reset_index(drop=True)
            }

    def get_weather(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Finds the nearest 0.5-degree grid observation for the requested location/date.
        """
        if not (-90 <= lat <= 90):
            return {
                "success": False,
                "error": "Invalid latitude",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }
        if not (-180 <= lon <= 180):
            return {
                "success": False,
                "error": "Invalid longitude",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }
            
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return {
                "success": False,
                "error": "Invalid date format",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }

        if date_str not in self.date_groups:
            return {
                "success": False,
                "error": f"Date {date_str} is outside the available historical range.",
                "requested": {"lat": lat, "lon": lon, "date": date_str}
            }

        group_info = self.date_groups[date_str]
        tree = group_info['tree']
        group_df = group_info['data']

        query_coords_rad = np.deg2rad([[lat, lon]])
        distances_rad, indices = tree.query(query_coords_rad, k=1)
        
        distance_km = distances_rad[0][0] * 6371.0
        nearest_idx = indices[0][0]

        if distance_km > self.max_distance_km:
            return {
                "success": False, 
                "error": "No valid weather grid point within distance threshold.",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
                "distance_km": round(distance_km, 2)
            }

        nearest_row = group_df.iloc[nearest_idx]

        return {
            "success": True,
            "latitude": lat,
            "longitude": lon,
            "date": date_str,
            "matched_latitude": nearest_row['latitude'],
            "matched_longitude": nearest_row['longitude'],
            "distance_km": round(distance_km, 2),
            "wind_speed_knots": float(nearest_row['max_wind_speed_knots']) if pd.notna(nearest_row['max_wind_speed_knots']) else None,
            "wave_height_meters": float(nearest_row['max_wave_height_meters']) if pd.notna(nearest_row['max_wave_height_meters']) else None,
            "surface_pressure_hpa": float(nearest_row['mean_surface_pressure_hpa']) if pd.notna(nearest_row['mean_surface_pressure_hpa']) else None,
            "wind_direction": None,
            "wave_direction": None,
            "wave_period_seconds": None,
            "source": "Historical Weather Cache (October 2025)",
            "data_status": "historical",
            "observation_type": "historical_observation",
        }
