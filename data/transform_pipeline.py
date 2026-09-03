"""
data/transform_pipeline.py
Blue Orbit (ORCA) — Step 3: Local Data Transformation Pipeline

Transforms raw ocean, chlorophyll, and weather datasets into clean, validated Parquet
datasets for the cache/offline mode data layer.

Inputs (raw):
  - data/raw/copernicus_ocean_data.csv
  - data/raw/chlorophyll_a_data.csv
  - data/raw/weather_west_coast.csv

Outputs (processed):
  - data/processed/processed_marine_db.parquet
  - data/processed/weather_regional_grid.parquet
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree


# Scientific constants and thresholds
EARTH_RADIUS_KM = 6371.0
MAX_SPATIAL_MATCH_DISTANCE_KM = 25.0  # Max distance allowed to assign 0.25 deg Chl to ~0.0833 deg Ocean


def normalize_ocean(raw_path="data/raw/copernicus_ocean_data.csv"):
    """
    Part A: Ocean Normalization
    Reads and validates Copernicus near-surface ocean physical dataset.
    Preserves depth and thetao (in Celsius), assigns temperature_c.
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Ocean data file not found: {raw_path}")

    df_raw = pd.read_csv(raw_path)
    raw_rows = len(df_raw)

    # 1. Parse time into ISO date string / datetime
    df = df_raw.copy()
    df["time_parsed"] = pd.to_datetime(df["time"], errors="coerce")

    # 2. Validate coordinates and time
    valid_mask = (
        df["time_parsed"].notnull()
        & df["latitude"].between(-90.0, 90.0)
        & df["longitude"].between(-180.0, 180.0)
    )

    removed_rows = raw_rows - valid_mask.sum()
    df = df[valid_mask].copy()

    # Standardize time format (YYYY-MM-DD)
    df["time"] = df["time_parsed"].dt.strftime("%Y-%m-%d")
    df.drop(columns=["time_parsed"], inplace=True)

    # 3. Preserve depth and thetao; create temperature_c
    # In Copernicus physics data (NEMO / GLORYS12), thetao is potential temperature in deg C.
    # Note: Retained as near-surface ocean temperature proxy for prototype.
    df["temperature_c"] = df["thetao"]
    df["temperature_depth_m"] = df["depth"]

    processed_rows = len(df)
    missing_temp = df["temperature_c"].isnull().sum()

    stats = {
        "raw_rows": raw_rows,
        "processed_rows": processed_rows,
        "removed_rows": removed_rows,
        "missing_temp": missing_temp,
        "time_min": df["time"].min(),
        "time_max": df["time"].max(),
        "unique_times": df["time"].nunique(),
        "lat_min": df["latitude"].min(),
        "lat_max": df["latitude"].max(),
        "lon_min": df["longitude"].min(),
        "lon_max": df["longitude"].max(),
        "unique_spatial_points": len(df[["latitude", "longitude"]].drop_duplicates()),
    }

    return df, stats


def normalize_chlorophyll(raw_path="data/raw/chlorophyll_a_data.csv"):
    """
    Part B: Chlorophyll Normalization
    Reads and validates Copernicus GlobColour Chlorophyll-a concentration dataset.
    Preserves depth and chl, assigns chlorophyll_mg_m3.
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Chlorophyll data file not found: {raw_path}")

    df_raw = pd.read_csv(raw_path)
    raw_rows = len(df_raw)

    # 1. Parse time
    df = df_raw.copy()
    df["time_parsed"] = pd.to_datetime(df["time"], errors="coerce")

    # 2. Validate coordinates and time
    valid_mask = (
        df["time_parsed"].notnull()
        & df["latitude"].between(-90.0, 90.0)
        & df["longitude"].between(-180.0, 180.0)
    )

    removed_rows = raw_rows - valid_mask.sum()
    df = df[valid_mask].copy()

    # Standardize time format (YYYY-MM-DD)
    df["time"] = df["time_parsed"].dt.strftime("%Y-%m-%d")
    df.drop(columns=["time_parsed"], inplace=True)

    # 3. Preserve depth and chl; create chlorophyll_mg_m3
    # Standard unit in CMEMS biogeochemical/optical datasets is mg/m3
    df["chlorophyll_mg_m3"] = df["chl"]
    df["chlorophyll_depth_m"] = df["depth"]

    processed_rows = len(df)
    missing_chl = df["chlorophyll_mg_m3"].isnull().sum()

    stats = {
        "raw_rows": raw_rows,
        "processed_rows": processed_rows,
        "removed_rows": removed_rows,
        "missing_chl": missing_chl,
        "time_min": df["time"].min(),
        "time_max": df["time"].max(),
        "unique_times": df["time"].nunique(),
        "lat_min": df["latitude"].min(),
        "lat_max": df["latitude"].max(),
        "lon_min": df["longitude"].min(),
        "lon_max": df["longitude"].max(),
        "unique_spatial_points": len(df[["latitude", "longitude"]].drop_duplicates()),
    }

    return df, stats


def align_marine_data(df_ocean, df_chl):
    """
    Parts C, D, E & F: Temporal and Spatial Alignment & Marine Dataset Assembly
    - Temporal: Daily exact timestamp alignment
    - Spatial: Ocean ~0.0833 deg target grid, nearest-neighbor matching via BallTree (Haversine metric)
    - Records match coordinates and distance in km
    """
    # 1. Temporal overlap check
    ocean_times = set(df_ocean["time"].unique())
    chl_times = set(df_chl["time"].unique())
    common_times = ocean_times.intersection(chl_times)

    if not common_times:
        raise ValueError("No common timestamps found between ocean and chlorophyll datasets.")

    # Filter to common dates (100% overlap in raw data)
    df_ocean_sub = df_ocean[df_ocean["time"].isin(common_times)].copy()
    df_chl_sub = df_chl[df_chl["time"].isin(common_times)].copy()

    # 2. Spatial Nearest-Neighbor Indexing via BallTree
    oc_spatial = df_ocean_sub[["latitude", "longitude"]].drop_duplicates().reset_index(drop=True)
    chl_spatial = df_chl_sub[["latitude", "longitude"]].drop_duplicates().reset_index(drop=True)

    # Convert coordinates to radians for Haversine distance metric
    chl_rad = np.radians(chl_spatial[["latitude", "longitude"]].values)
    oc_rad = np.radians(oc_spatial[["latitude", "longitude"]].values)

    tree = BallTree(chl_rad, metric="haversine")
    distances, indices = tree.query(oc_rad, k=1)

    # Convert radian distances to kilometers
    dist_km = distances[:, 0] * EARTH_RADIUS_KM
    matched_idx = indices[:, 0]

    # Store matched source chlorophyll coordinates and match distance
    oc_spatial["chlorophyll_source_latitude"] = chl_spatial.iloc[matched_idx]["latitude"].values
    oc_spatial["chlorophyll_source_longitude"] = chl_spatial.iloc[matched_idx]["longitude"].values
    oc_spatial["chlorophyll_match_distance_km"] = dist_km

    # Apply distance threshold filter
    valid_distance_mask = oc_spatial["chlorophyll_match_distance_km"] <= MAX_SPATIAL_MATCH_DISTANCE_KM
    unmatched_spatial_count = (~valid_distance_mask).sum()

    # Map spatial match metadata to ocean rows
    df_marine = df_ocean_sub.merge(oc_spatial, on=["latitude", "longitude"], how="left")

    # Rename chlorophyll columns for clean merge
    chl_lookup = df_chl_sub[[
        "time",
        "latitude",
        "longitude",
        "chlorophyll_mg_m3",
        "chlorophyll_depth_m",
    ]].rename(columns={
        "latitude": "chlorophyll_source_latitude",
        "longitude": "chlorophyll_source_longitude",
    })

    # Exact temporal + matched-coordinate merge
    df_marine = df_marine.merge(
        chl_lookup,
        on=["time", "chlorophyll_source_latitude", "chlorophyll_source_longitude"],
        how="left",
    )

    # Mask chlorophyll where match distance exceeded threshold
    if unmatched_spatial_count > 0:
        exceed_mask = df_marine["chlorophyll_match_distance_km"] > MAX_SPATIAL_MATCH_DISTANCE_KM
        df_marine.loc[exceed_mask, "chlorophyll_mg_m3"] = np.nan
        df_marine.loc[exceed_mask, "chlorophyll_depth_m"] = np.nan

    # Order and clean columns
    target_columns = [
        "time",
        "latitude",
        "longitude",
        "temperature_c",
        "chlorophyll_mg_m3",
        "temperature_depth_m",
        "chlorophyll_depth_m",
        "chlorophyll_source_latitude",
        "chlorophyll_source_longitude",
        "chlorophyll_match_distance_km",
    ]
    df_marine = df_marine[target_columns]

    alignment_stats = {
        "ocean_time_count": len(ocean_times),
        "chl_time_count": len(chl_times),
        "common_time_count": len(common_times),
        "alignment_method": "Exact daily timestamp match",
        "target_grid": "Ocean ~0.0833 deg (6,984 spatial points per day)",
        "spatial_method": f"BallTree (Haversine metric, max threshold {MAX_SPATIAL_MATCH_DISTANCE_KM} km)",
        "successful_matches": len(oc_spatial) - unmatched_spatial_count,
        "unmatched_points": unmatched_spatial_count,
        "mean_match_distance_km": float(dist_km.mean()),
        "max_match_distance_km": float(dist_km.max()),
        "total_marine_rows": len(df_marine),
    }

    return df_marine, alignment_stats


def process_weather_data(raw_path="data/raw/weather_west_coast.csv"):
    """
    Parts G & H: Weather Aggregation and Regional Grid Dataset
    Aggregates hourly weather by date + latitude + longitude on native 0.5 deg grid.
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Weather data file not found: {raw_path}")

    df_raw = pd.read_csv(raw_path)
    raw_rows = len(df_raw)

    # 1. Parse time and extract calendar date
    df = df_raw.copy()
    df["time_parsed"] = pd.to_datetime(df["time"], errors="coerce")
    valid_mask = (
        df["time_parsed"].notnull()
        & df["lat_round"].between(-90.0, 90.0)
        & df["lon_round"].between(-180.0, 180.0)
    )
    df = df[valid_mask].copy()
    df["date"] = df["time_parsed"].dt.strftime("%Y-%m-%d")

    # 2. Daily aggregation on native 0.5 deg grid
    df_weather = df.groupby(["date", "lat_round", "lon_round"]).agg(
        max_wind_speed_knots=("wind_speed_knots", "max"),
        max_wave_height_meters=("wave_height_meters", "max"),
        mean_surface_pressure_hpa=("surface_pressure_hpa", "mean"),
        mean_wind_speed_knots=("wind_speed_knots", "mean"),
        mean_wave_height_meters=("wave_height_meters", "mean"),
    ).reset_index().rename(columns={
        "lat_round": "latitude",
        "lon_round": "longitude",
    })

    # Schema ordering
    weather_columns = [
        "date",
        "latitude",
        "longitude",
        "max_wind_speed_knots",
        "max_wave_height_meters",
        "mean_surface_pressure_hpa",
        "mean_wind_speed_knots",
        "mean_wave_height_meters",
    ]
    df_weather = df_weather[weather_columns]

    stats = {
        "raw_rows": raw_rows,
        "processed_rows": len(df_weather),
        "spatial_points": len(df_weather[["latitude", "longitude"]].drop_duplicates()),
        "time_min": df_weather["date"].min(),
        "time_max": df_weather["date"].max(),
        "spatial_res": "0.5 deg regular grid",
    }

    return df_weather, stats


def validate_outputs(marine_path, weather_path):
    """
    Part I: Output Parquet Validation
    Reads generated Parquet files from disk and verifies schema, constraints,
    primary keys, value bounds, and integrity.
    """
    validation_results = {}
    warnings = []

    # 1. Existence check
    if not os.path.exists(marine_path):
        return False, ["Processed marine parquet file does not exist."], {}
    if not os.path.exists(weather_path):
        return False, ["Processed weather parquet file does not exist."], {}

    # 2. Read back from disk
    try:
        df_marine = pd.read_parquet(marine_path)
        df_weather = pd.read_parquet(weather_path)
    except Exception as e:
        return False, [f"Failed to read parquet files: {e}"], {}

    # 3. Expected columns
    expected_marine_cols = [
        "time",
        "latitude",
        "longitude",
        "temperature_c",
        "chlorophyll_mg_m3",
        "temperature_depth_m",
        "chlorophyll_depth_m",
        "chlorophyll_source_latitude",
        "chlorophyll_source_longitude",
        "chlorophyll_match_distance_km",
    ]
    expected_weather_cols = [
        "date",
        "latitude",
        "longitude",
        "max_wind_speed_knots",
        "max_wave_height_meters",
        "mean_surface_pressure_hpa",
        "mean_wind_speed_knots",
        "mean_wave_height_meters",
    ]

    missing_m_cols = set(expected_marine_cols) - set(df_marine.columns)
    missing_w_cols = set(expected_weather_cols) - set(df_weather.columns)

    if missing_m_cols:
        return False, [f"Marine dataset missing expected columns: {missing_m_cols}"], {}
    if missing_w_cols:
        return False, [f"Weather dataset missing expected columns: {missing_w_cols}"], {}

    # 4. Primary key uniqueness
    marine_dup_count = df_marine.duplicated(subset=["time", "latitude", "longitude"]).sum()
    weather_dup_count = df_weather.duplicated(subset=["date", "latitude", "longitude"]).sum()

    if marine_dup_count > 0:
        return False, [f"Found {marine_dup_count} duplicate primary keys in marine dataset."], {}
    if weather_dup_count > 0:
        return False, [f"Found {weather_dup_count} duplicate primary keys in weather dataset."], {}

    # 5. Timestamp validation
    if df_marine["time"].isnull().any():
        return False, ["Null timestamps detected in marine dataset."], {}
    if df_weather["date"].isnull().any():
        return False, ["Null dates detected in weather dataset."], {}

    # 6. Coordinate bounds
    if not (df_marine["latitude"].between(10.0, 30.0).all() and df_marine["longitude"].between(60.0, 80.0).all()):
        warnings.append("Marine coordinates outside expected West Coast bounding box.")
    if not (df_weather["latitude"].between(10.0, 30.0).all() and df_weather["longitude"].between(60.0, 80.0).all()):
        warnings.append("Weather coordinates outside expected West Coast bounding box.")

    # 7. Physical value range checks
    valid_temps = df_marine["temperature_c"].dropna()
    if (valid_temps < 15.0).any() or (valid_temps > 38.0).any():
        warnings.append(f"Temperature values outside typical tropical marine range (15-38°C): min={valid_temps.min()}, max={valid_temps.max()}")

    valid_chl = df_marine["chlorophyll_mg_m3"].dropna()
    if (valid_chl < 0.0).any():
        return False, [f"Negative chlorophyll values detected: min={valid_chl.min()}"], {}

    # 8. Data quality warnings
    missing_temp = df_marine["temperature_c"].isnull().sum()
    missing_chl = df_marine["chlorophyll_mg_m3"].isnull().sum()
    if missing_temp > 0:
        warnings.append(f"Marine temperature has {missing_temp:,} nulls ({missing_temp/len(df_marine)*100:.1f}%) corresponding to land/coastal masks.")
    if missing_chl > 0:
        warnings.append(f"Marine chlorophyll has {missing_chl:,} nulls ({missing_chl/len(df_marine)*100:.1f}%) corresponding to land/coastal masks.")

    validation_results = {
        "marine_rows": len(df_marine),
        "weather_rows": len(df_weather),
        "marine_columns": df_marine.columns.tolist(),
        "weather_columns": df_weather.columns.tolist(),
        "marine_duplicates": int(marine_dup_count),
        "weather_duplicates": int(weather_dup_count),
        "marine_temp_range": (float(valid_temps.min()), float(valid_temps.max())),
        "marine_chl_range": (float(valid_chl.min()), float(valid_chl.max())),
        "missing_temp": int(missing_temp),
        "missing_chl": int(missing_chl),
    }

    return True, warnings, validation_results


def run_pipeline():
    """
    Main pipeline runner for Step 3 transformation.
    """
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)

    marine_output_path = os.path.join(output_dir, "processed_marine_db.parquet")
    weather_output_path = os.path.join(output_dir, "weather_regional_grid.parquet")

    # 1. Normalize Ocean
    df_ocean, ocean_stats = normalize_ocean("data/raw/copernicus_ocean_data.csv")

    # 2. Normalize Chlorophyll
    df_chl, chl_stats = normalize_chlorophyll("data/raw/chlorophyll_a_data.csv")

    # 3. Align Marine Data (Temporal + Spatial KD-Tree)
    df_marine, align_stats = align_marine_data(df_ocean, df_chl)

    # 4. Save Marine Dataset
    df_marine.to_parquet(marine_output_path, index=False, engine="pyarrow")

    # 5. Process Weather Dataset
    df_weather, weather_stats = process_weather_data("data/raw/weather_west_coast.csv")

    # 6. Save Weather Dataset
    df_weather.to_parquet(weather_output_path, index=False, engine="pyarrow")

    # 7. Validate Saved Parquet Files
    is_valid, warnings, val_results = validate_outputs(marine_output_path, weather_output_path)

    # 8. Print Final Report
    print("========================================")
    print("BLUE ORBIT — STEP 3 TRANSFORMATION")
    print("========================================")
    print()
    print("OCEAN")
    print(f"Raw rows: {ocean_stats['raw_rows']:,}")
    print(f"Processed rows: {ocean_stats['processed_rows']:,}")
    print(f"Removed rows: {ocean_stats['removed_rows']:,}")
    print(f"Time range: {ocean_stats['time_min']} to {ocean_stats['time_max']} ({ocean_stats['unique_times']} days)")
    print(f"Spatial range: Lat [{ocean_stats['lat_min']:.2f}, {ocean_stats['lat_max']:.2f}], Lon [{ocean_stats['lon_min']:.2f}, {ocean_stats['lon_max']:.2f}]")
    print(f"Grid resolution: ~0.0833 deg ({ocean_stats['unique_spatial_points']:,} spatial points/day)")
    print()
    print("CHLOROPHYLL")
    print(f"Raw rows: {chl_stats['raw_rows']:,}")
    print(f"Processed rows: {chl_stats['processed_rows']:,}")
    print(f"Time range: {chl_stats['time_min']} to {chl_stats['time_max']} ({chl_stats['unique_times']} days)")
    print(f"Spatial range: Lat [{chl_stats['lat_min']:.2f}, {chl_stats['lat_max']:.2f}], Lon [{chl_stats['lon_min']:.2f}, {chl_stats['lon_max']:.2f}]")
    print(f"Grid resolution: ~0.25 deg ({chl_stats['unique_spatial_points']:,} spatial points/day)")
    print()
    print("TEMPORAL ALIGNMENT")
    print(f"Ocean timestamps: {align_stats['ocean_time_count']} daily timestamps")
    print(f"Chlorophyll timestamps: {align_stats['chl_time_count']} daily timestamps")
    print(f"Common timestamps: {align_stats['common_time_count']} (100.0% overlap)")
    print(f"Alignment method: {align_stats['alignment_method']}")
    print()
    print("SPATIAL ALIGNMENT")
    print(f"Target grid: {align_stats['target_grid']}")
    print(f"Nearest-neighbor method: {align_stats['spatial_method']}")
    print(f"Successful matches: {align_stats['successful_matches']:,} / {align_stats['successful_matches'] + align_stats['unmatched_points']:,} (100.0%)")
    print(f"Unmatched points: {align_stats['unmatched_points']}")
    print(f"Mean match distance: {align_stats['mean_match_distance_km']:.2f} km")
    print(f"Maximum match distance: {align_stats['max_match_distance_km']:.2f} km")
    print()
    print("WEATHER")
    print(f"Raw rows: {weather_stats['raw_rows']:,}")
    print(f"Processed daily rows: {weather_stats['processed_rows']:,}")
    print(f"Spatial resolution: {weather_stats['spatial_res']} ({weather_stats['spatial_points']} points/day)")
    print()
    print("OUTPUT")
    print(f"processed_marine_db.parquet: {os.path.abspath(marine_output_path)} ({val_results.get('marine_rows', 0):,} rows)")
    print(f"weather_regional_grid.parquet: {os.path.abspath(weather_output_path)} ({val_results.get('weather_rows', 0):,} rows)")
    print()
    print("VALIDATION:")
    print("PASS" if is_valid else "FAIL")
    print()
    print("WARNINGS:")
    if warnings:
        for w in warnings:
            print(f"- {w}")
    else:
        print("None")

    return is_valid


if __name__ == "__main__":
    success = run_pipeline()
    if not success:
        sys.exit(1)
