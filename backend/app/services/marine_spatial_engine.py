import os
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
from datetime import datetime
from typing import Dict, Any

class MarineSpatialEngine:
    def __init__(self, parquet_path: str, max_distance_km: float = 50.0):
        """
        Initializes the spatial engine by loading the parquet dataset
        and building a BallTree for fast nearest-neighbor lookups.

        Args:
            parquet_path: Path to the processed_marine_db.parquet file.
            max_distance_km: Configurable maximum spatial search distance in kilometers.
        """
        self.parquet_path = parquet_path
        self.max_distance_km = max_distance_km
        self.df = None
        self.date_groups = {}

        self._load_data()

    def _load_data(self):
        """Loads data efficiently and builds the spatial index per date."""
        if not os.path.exists(self.parquet_path):
            raise FileNotFoundError(f"Dataset not found at: {self.parquet_path}")

        # Load the parquet file
        self.df = pd.read_parquet(self.parquet_path)
        
        # Ensure time column is converted to strings (e.g. 'YYYY-MM-DD') for easy filtering
        self.df['time_str'] = pd.to_datetime(self.df['time']).dt.strftime('%Y-%m-%d')
        
        # Build index for each unique date to optimize searching by date first
        for date_str, group in self.df.groupby('time_str'):
            # Filter out entirely null lat/lon rows if any exist
            valid_group = group.dropna(subset=['latitude', 'longitude'])
            if valid_group.empty:
                continue

            # Convert lat/lon to radians for the Haversine metric
            coords_rad = np.deg2rad(valid_group[['latitude', 'longitude']].values)
            
            # Build BallTree with Haversine metric (built once)
            tree = BallTree(coords_rad, metric='haversine')
            
            # Store the group dataframe (reset index for easy location) and tree
            self.date_groups[date_str] = {
                'tree': tree,
                'data': valid_group.reset_index(drop=True)
            }

    def query(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Queries the nearest valid marine observation for a given location and date.

        Args:
            lat: Latitude of the requested coordinate.
            lon: Longitude of the requested coordinate.
            date_str: Requested date in 'YYYY-MM-DD' format.

        Returns:
            Dictionary with match information or failure reason.
        """
        # 1. Validate coordinates
        if not (-90 <= lat <= 90):
            return {"error": "Invalid latitude.", "requested": {"lat": lat, "lon": lon, "date": date_str}}
        if not (-180 <= lon <= 180):
            return {"error": "Invalid longitude.", "requested": {"lat": lat, "lon": lon, "date": date_str}}
        
        # 2. Validate date format
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return {"error": "Invalid date format. Expected YYYY-MM-DD.", "requested": {"lat": lat, "lon": lon, "date": date_str}}

        # 3. Check if date is within available cache
        if date_str not in self.date_groups:
            return {"error": f"Date {date_str} is outside the available historical range.", "requested": {"lat": lat, "lon": lon, "date": date_str}}

        # 4. Find the nearest spatial observation
        group_info = self.date_groups[date_str]
        tree = group_info['tree']
        group_df = group_info['data']

        # Query BallTree
        query_coords_rad = np.deg2rad([[lat, lon]])
        distances_rad, indices = tree.query(query_coords_rad, k=1)
        
        # 5. Calculate the geographic distance in kilometers (Earth radius ~ 6371 km)
        distance_km = distances_rad[0][0] * 6371.0
        nearest_idx = indices[0][0]

        # 6. Check against configurable maximum spatial search distance
        if distance_km > self.max_distance_km:
            return {
                "error": "No valid observation available within distance threshold.",
                "requested": {"lat": lat, "lon": lon, "date": date_str},
                "closest_distance_km": round(distance_km, 2)
            }

        nearest_row = group_df.iloc[nearest_idx]

        # 7. Check if environmental values are valid (not null)
        # Note: we don't invent or interpolate values. Nulls are kept as null (None/NaN)
        temp_val = nearest_row['temperature_c']
        chloro_val = nearest_row['chlorophyll_mg_m3']
        
        is_valid = pd.notna(temp_val) or pd.notna(chloro_val)
        
        # 8. Return a structured Python dictionary/object
        return {
            "requested_latitude": lat,
            "requested_longitude": lon,
            "requested_date": date_str,
            "matched_latitude": nearest_row['latitude'],
            "matched_longitude": nearest_row['longitude'],
            "temperature": float(temp_val) if pd.notna(temp_val) else None,
            "chlorophyll": float(chloro_val) if pd.notna(chloro_val) else None,
            "distance_km": round(distance_km, 2),
            "data_validity": "Valid values found" if is_valid else "Null values (land/coastal mask)",
            "success": True
        }
