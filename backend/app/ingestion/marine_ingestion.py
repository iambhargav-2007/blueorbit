import os
import argparse
import logging
import xarray as xr
import pandas as pd
from datetime import datetime

# Lazy import
try:
    import copernicusmarine
    COPERNICUS_AVAILABLE = True
except ImportError:
    COPERNICUS_AVAILABLE = False

from app.config import (
    COPERNICUS_THETAO_DATASET,
    COPERNICUS_CHL_DATASET,
    COPERNICUS_SURFACE_DEPTH,
    MARINE_INGESTION_MIN_LAT,
    MARINE_INGESTION_MAX_LAT,
    MARINE_INGESTION_MIN_LON,
    MARINE_INGESTION_MAX_LON,
    MARINE_HISTORICAL_DIR
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_marine_data(date_str: str) -> dict:
    """
    Ingests marine data (thetao and chl) for a specific date and regional bounding box.
    Saves the data as a Parquet file partitioned by date.
    Idempotent: Re-running for the same date overwrites the existing partition.
    """
    if not COPERNICUS_AVAILABLE:
        return {"success": False, "error": "copernicusmarine library not installed."}

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return {"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}

    # Ensure output directory exists
    date_dir = os.path.join(MARINE_HISTORICAL_DIR, f"date={date_str}")
    os.makedirs(date_dir, exist_ok=True)
    output_path = os.path.join(date_dir, "marine.parquet")

    logger.info(f"Starting ingestion for {date_str}")
    logger.info(f"Bounding Box: Lat [{MARINE_INGESTION_MIN_LAT}, {MARINE_INGESTION_MAX_LAT}], Lon [{MARINE_INGESTION_MIN_LON}, {MARINE_INGESTION_MAX_LON}]")

    try:
        # 1. Fetch Temperature Data
        logger.info(f"Fetching thetao from {COPERNICUS_THETAO_DATASET}...")
        ds_theta = copernicusmarine.open_dataset(dataset_id=COPERNICUS_THETAO_DATASET)
        
        # Subset
        ds_theta_sub = ds_theta.sel(
            time=date_str,
            depth=COPERNICUS_SURFACE_DEPTH,
            latitude=slice(MARINE_INGESTION_MIN_LAT, MARINE_INGESTION_MAX_LAT),
            longitude=slice(MARINE_INGESTION_MIN_LON, MARINE_INGESTION_MAX_LON)
        )
        # Convert to pandas dataframe
        df_theta = ds_theta_sub[['thetao']].to_dataframe().reset_index()
        # Drop completely null rows (e.g. land)
        df_theta = df_theta.dropna(subset=['thetao'])
        
        if df_theta.empty:
            logger.warning("No valid thetao data found in the specified bounding box.")
        else:
            logger.info(f"Retrieved {len(df_theta)} valid thetao records.")

        # 2. Fetch Chlorophyll Data
        logger.info(f"Fetching chl from {COPERNICUS_CHL_DATASET}...")
        ds_chl = copernicusmarine.open_dataset(dataset_id=COPERNICUS_CHL_DATASET)
        
        sel_kwargs = {
            "time": date_str,
            "latitude": slice(MARINE_INGESTION_MIN_LAT, MARINE_INGESTION_MAX_LAT),
            "longitude": slice(MARINE_INGESTION_MIN_LON, MARINE_INGESTION_MAX_LON)
        }
        if "depth" in ds_chl.dims or "depth" in ds_chl.coords:
            sel_kwargs["depth"] = COPERNICUS_SURFACE_DEPTH

        ds_chl_sub = ds_chl.sel(**sel_kwargs)
        
        if 'chl' in ds_chl_sub.variables:
            df_chl = ds_chl_sub[['chl']].to_dataframe().reset_index()
            df_chl = df_chl.dropna(subset=['chl'])
        else:
            df_chl = pd.DataFrame()

        if df_chl.empty:
            logger.warning("No valid chl data found in the specified bounding box.")
        else:
            logger.info(f"Retrieved {len(df_chl)} valid chl records.")

        # 3. Merge Datasets
        # We merge them efficiently. Since they are at different resolutions, a direct merge on lat/lon
        # will result in very few exact matches. We will interpolate/nearest neighbor match them using pandas merge_asof
        # or we simply save them with their native lat/lon and let the spatial engine handle nearest neighbor lookup
        # per variable. To keep it simple and consistent with CacheMarineProvider which expects a single row 
        # per observation with both values, we will use the higher resolution (thetao) as the base grid
        # and attach the nearest chlorophyll value.

        if not df_theta.empty and not df_chl.empty:
            logger.info("Merging thetao and chl data...")
            # We use BallTree to find the nearest chl point for each thetao point
            from sklearn.neighbors import BallTree
            import numpy as np
            
            tree = BallTree(np.deg2rad(df_chl[['latitude', 'longitude']].values), metric='haversine')
            query_coords = np.deg2rad(df_theta[['latitude', 'longitude']].values)
            distances, indices = tree.query(query_coords, k=1)
            
            # Distance in km
            distances_km = distances.flatten() * 6371.0
            
            # We attach chl values to thetao grid, but only if they are within a reasonable distance (e.g. 50km)
            valid_mask = distances_km <= 50.0
            
            nearest_chl = df_chl.iloc[indices.flatten()]
            df_theta['chlorophyll_mg_m3'] = np.where(valid_mask, nearest_chl['chl'].values, np.nan)
            df_theta['chlorophyll_match_distance_km'] = np.where(valid_mask, distances_km, np.nan)
            
        elif not df_theta.empty:
            df_theta['chlorophyll_mg_m3'] = np.nan
            df_theta['chlorophyll_match_distance_km'] = np.nan
        else:
            df_theta = df_chl.copy()
            if not df_theta.empty:
                df_theta['thetao'] = np.nan
                df_theta['chlorophyll_mg_m3'] = df_theta['chl']
                df_theta['chlorophyll_match_distance_km'] = 0.0

        # Rename standard columns to match CacheMarineProvider expectations
        if not df_theta.empty:
            if 'thetao' in df_theta.columns:
                df_theta = df_theta.rename(columns={'thetao': 'temperature_c'})
            # ensure time column is a string for the engine
            df_theta['time'] = date_str
            
            # Save to Parquet
            df_theta.to_parquet(output_path, engine='pyarrow', index=False)
            logger.info(f"Saved {len(df_theta)} records to {output_path}")
            
            return {
                "success": True,
                "date": date_str,
                "rows": len(df_theta),
                "output_path": output_path,
                "status": "ingested"
            }
        else:
            return {
                "success": False,
                "error": "No valid data found for either thetao or chl.",
                "date": date_str
            }

    except Exception as e:
        logger.exception("Ingestion failed.")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Marine Data Ingestion")
    parser.add_argument("--date", type=str, required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--smoke-test", action="store_true", help="Run a fast smoke test (not fully implemented as flag yet)")
    args = parser.parse_args()

    result = ingest_marine_data(args.date)
    print(result)
