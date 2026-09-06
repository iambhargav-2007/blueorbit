import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from sklearn.neighbors import BallTree

class HistoricalMarineEngine:
    def __init__(self, marine_parquet_path: str, weather_parquet_path: str, max_distance_km: float = 50.0):
        self.marine_parquet_path = marine_parquet_path
        self.weather_parquet_path = weather_parquet_path
        self.max_distance_km = max_distance_km
        self.marine_df = None
        self.weather_df = None
        self.marine_tree = None
        self.weather_tree = None
        self._load_data()

    def _load_data(self):
        if not os.path.exists(self.marine_parquet_path):
            raise FileNotFoundError(f"Marine dataset not found at: {self.marine_parquet_path}")
        if not os.path.exists(self.weather_parquet_path):
            raise FileNotFoundError(f"Weather dataset not found at: {self.weather_parquet_path}")

        # Load Marine Data
        self.marine_df = pd.read_parquet(self.marine_parquet_path)
        self.marine_df['time_str'] = pd.to_datetime(self.marine_df['time']).dt.strftime('%Y-%m-%d')
        
        # Build spatial index for marine data (all unique coordinates)
        marine_coords = self.marine_df[['latitude', 'longitude']].drop_duplicates().dropna()
        self.marine_coords_df = marine_coords.reset_index(drop=True)
        if not self.marine_coords_df.empty:
            self.marine_tree = BallTree(np.deg2rad(self.marine_coords_df.values), metric='haversine')

        # Load Weather Data
        self.weather_df = pd.read_parquet(self.weather_parquet_path)
        if 'date' in self.weather_df.columns:
            self.weather_df['time_str'] = pd.to_datetime(self.weather_df['date']).dt.strftime('%Y-%m-%d')
        else:
            self.weather_df['time_str'] = pd.to_datetime(self.weather_df['time']).dt.strftime('%Y-%m-%d')

        # Build spatial index for weather data
        weather_coords = self.weather_df[['latitude', 'longitude']].drop_duplicates().dropna()
        self.weather_coords_df = weather_coords.reset_index(drop=True)
        if not self.weather_coords_df.empty:
            self.weather_tree = BallTree(np.deg2rad(self.weather_coords_df.values), metric='haversine')

    def _get_nearest_coords(self, lat: float, lon: float, tree: BallTree, coords_df: pd.DataFrame) -> Optional[tuple]:
        if tree is None: return None
        query_coords_rad = np.deg2rad([[lat, lon]])
        distances_rad, indices = tree.query(query_coords_rad, k=1)
        distance_km = distances_rad[0][0] * 6371.0
        if distance_km > self.max_distance_km:
            return None
        nearest_idx = indices[0][0]
        row = coords_df.iloc[nearest_idx]
        return (row['latitude'], row['longitude'])

    def _calculate_stats(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
        stats = {}
        valid_obs = len(df)
        stats['valid_observations'] = valid_obs
        
        if valid_obs == 0:
            stats['data_status'] = "INSUFFICIENT_DATA"
            for col in columns:
                stats[col] = {"mean": None, "min": None, "max": None}
            return stats

        stats['data_status'] = "AVAILABLE"
        for col in columns:
            if col in df.columns:
                valid_data = df[col].dropna()
                if len(valid_data) > 0:
                    stats[col] = {
                        "mean": round(float(valid_data.mean()), 2),
                        "min": round(float(valid_data.min()), 2),
                        "max": round(float(valid_data.max()), 2)
                    }
                else:
                    stats[col] = {"mean": None, "min": None, "max": None}
        return stats

    def analyze_point_history(self, lat: float, lon: float, start_date: str, end_date: str = None) -> Dict[str, Any]:
        """Analyzes historical data at a specific point for a date or date range."""
        if end_date is None:
            end_date = start_date

        marine_nearest = self._get_nearest_coords(lat, lon, self.marine_tree, self.marine_coords_df)
        weather_nearest = self._get_nearest_coords(lat, lon, self.weather_tree, self.weather_coords_df)

        marine_stats = {"data_status": "INSUFFICIENT_DATA"}
        weather_stats = {"data_status": "INSUFFICIENT_DATA"}

        if marine_nearest:
            mlat, mlon = marine_nearest
            mask = (self.marine_df['latitude'] == mlat) & (self.marine_df['longitude'] == mlon) & \
                   (self.marine_df['time_str'] >= start_date) & (self.marine_df['time_str'] <= end_date)
            subset = self.marine_df[mask]
            marine_stats = self._calculate_stats(subset, ['temperature_c', 'chlorophyll_mg_m3'])

        if weather_nearest:
            wlat, wlon = weather_nearest
            mask = (self.weather_df['latitude'] == wlat) & (self.weather_df['longitude'] == wlon) & \
                   (self.weather_df['time_str'] >= start_date) & (self.weather_df['time_str'] <= end_date)
            subset = self.weather_df[mask]
            weather_stats = self._calculate_stats(subset, ['mean_wind_speed_knots', 'mean_wave_height_meters'])

        return {
            "analysis_type": "POINT_ANALYSIS",
            "temporal_range": f"{start_date} to {end_date}" if start_date != end_date else start_date,
            "location": {"latitude": lat, "longitude": lon},
            "marine": marine_stats,
            "weather": weather_stats,
            "provenance": {
                "source": "Copernicus Marine & ECMWF",
                "dataset": "Historical Marine Cache & Weather Grid",
                "coverage": f"{start_date} to {end_date}"
            }
        }
    
    def compare_locations(self, lat1: float, lon1: float, lat2: float, lon2: float, date_str: str) -> Dict[str, Any]:
        """Compares historical data between two locations on a specific date."""
        loc1_stats = self.analyze_point_history(lat1, lon1, date_str, date_str)
        loc2_stats = self.analyze_point_history(lat2, lon2, date_str, date_str)
        
        return {
            "analysis_type": "SPATIAL_COMPARISON",
            "temporal_range": date_str,
            "locations": [
                {"id": "loc1", "latitude": lat1, "longitude": lon1, "data": loc1_stats},
                {"id": "loc2", "latitude": lat2, "longitude": lon2, "data": loc2_stats}
            ],
            "provenance": loc1_stats["provenance"]
        }
