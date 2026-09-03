"""
Blue Orbit (ORCA) - Step 2A: Local Data Audit & Scientific Validation Script
Audits raw datasets in data/raw/ without modifying any data or creating transformed files.
"""

import os
import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure clean UTF-8 encoding on Windows terminal output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def format_bytes(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB ({size_bytes:,} bytes)"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB ({size_bytes:,} bytes)"


def calculate_spacing(coords: np.ndarray) -> dict:
    """Calculate coordinate spacing statistics for sorted 1D array of coordinates."""
    unique_coords = np.sort(np.unique(coords[~np.isnan(coords)]))
    if len(unique_coords) < 2:
        return {"unique_count": len(unique_coords), "diffs": [], "common_spacing": None}
    
    diffs = np.round(np.diff(unique_coords), 6)
    diff_series = pd.Series(diffs)
    mode_spacing = diff_series.mode()
    common_val = mode_spacing.iloc[0] if not mode_spacing.empty else None
    
    counts = diff_series.value_counts()
    top_spacings = [f"{k:.4f}° ({v} steps, {v/len(diffs)*100:.1f}%)" for k, v in counts.head(3).items()]
    
    return {
        "unique_count": len(unique_coords),
        "min": float(unique_coords.min()),
        "max": float(unique_coords.max()),
        "diffs": diffs,
        "common_spacing": common_val,
        "top_spacings_str": ", ".join(top_spacings)
    }


def audit_general(df: pd.DataFrame, file_path: Path, name: str):
    """General audit for dataset."""
    file_size = file_path.stat().st_size
    print(f"\n--- General Overview: {name} ---")
    print(f"File Path:              {file_path.as_posix()}")
    print(f"File Size:              {format_bytes(file_size)}")
    print(f"Number of Rows:         {len(df):,}")
    print(f"Number of Columns:      {len(df.columns)}")
    print(f"Duplicate Rows:         {df.duplicated().sum():,}")
    
    print("\nColumn Information & Missing Values:")
    col_info = []
    for col in df.columns:
        null_count = df[col].isnull().sum()
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0.0
        col_info.append({
            "Column": col,
            "Dtype": str(df[col].dtype),
            "Missing Count": f"{null_count:,}",
            "Missing %": f"{null_pct:.2f}%"
        })
    info_df = pd.DataFrame(col_info)
    print(info_df.to_string(index=False))

    print("\nFirst 5 Rows:")
    print(df.head(5).to_string())
    print("\nLast 5 Rows:")
    print(df.tail(5).to_string())


def audit_time(df: pd.DataFrame, time_col: str):
    """Audit time column in dataframe."""
    print(f"\n--- Temporal Audit (Column: '{time_col}') ---")
    if time_col not in df.columns:
        print(f"Time column '{time_col}' not found.")
        return None
    
    raw_unique = df[time_col].nunique()
    parsed_time = pd.to_datetime(df[time_col], errors="coerce")
    invalid_count = parsed_time.isnull().sum() - df[time_col].isnull().sum()
    
    print(f"Unique Timestamps (Raw):   {raw_unique:,}")
    print(f"Invalid Datetime Parse:    {invalid_count:,} rows")
    
    valid_times = parsed_time.dropna()
    if not valid_times.empty:
        min_t = valid_times.min()
        max_t = valid_times.max()
        print(f"Minimum Timestamp:         {min_t}")
        print(f"Maximum Timestamp:         {max_t}")
        print(f"Temporal Span:             {max_t - min_t}")
        print(f"Unique Valid Timestamps:   {valid_times.nunique():,}")
        return {"min": min_t, "max": max_t, "unique_count": valid_times.nunique(), "series": valid_times}
    return None


def audit_geographic(df: pd.DataFrame, lat_col: str, lon_col: str):
    """Audit geographic coordinates."""
    print(f"\n--- Geographic Audit (Lat: '{lat_col}', Lon: '{lon_col}') ---")
    if lat_col not in df.columns or lon_col not in df.columns:
        print(f"Coordinate columns '{lat_col}', '{lon_col}' not found.")
        return None
    
    lat_spacing = calculate_spacing(df[lat_col].values)
    lon_spacing = calculate_spacing(df[lon_col].values)
    
    coord_pairs = df[[lat_col, lon_col]].drop_duplicates()
    
    print(f"Latitude Range:            [{lat_spacing['min']:.4f}°, {lat_spacing['max']:.4f}°]")
    print(f"Longitude Range:           [{lon_spacing['min']:.4f}°, {lon_spacing['max']:.4f}°]")
    print(f"Unique Latitudes:          {lat_spacing['unique_count']:,}")
    print(f"Unique Longitudes:         {lon_spacing['unique_count']:,}")
    print(f"Unique (Lat, Lon) Pairs:   {len(coord_pairs):,}")
    print(f"Latitude Spacing Patterns: {lat_spacing['top_spacings_str']}")
    print(f"Longitude Spacing Patterns:{lon_spacing['top_spacings_str']}")
    print(f"Dominant Spatial Step:     Lat ~ {lat_spacing['common_spacing']}°, Lon ~ {lon_spacing['common_spacing']}°")
    
    return {
        "lat_min": lat_spacing["min"], "lat_max": lat_spacing["max"],
        "lon_min": lon_spacing["min"], "lon_max": lon_spacing["max"],
        "lat_count": lat_spacing["unique_count"], "lon_count": lon_spacing["unique_count"],
        "lat_spacing": lat_spacing["common_spacing"], "lon_spacing": lon_spacing["common_spacing"],
        "pairs_count": len(coord_pairs),
        "unique_lats": np.sort(df[lat_col].dropna().unique()),
        "unique_lons": np.sort(df[lon_col].dropna().unique()),
        "pairs_set": set(zip(coord_pairs[lat_col], coord_pairs[lon_col]))
    }


def detect_geometry_in_df(df: pd.DataFrame) -> dict:
    """Inspect all columns to check if geometry (WKT, GeoJSON, coordinate strings) exists."""
    # Strict WKT pattern requires geometry type keyword followed by coordinates in parentheses
    wkt_patterns = re.compile(
        r"^\s*(POINT|LINESTRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON|GEOMETRYCOLLECTION)\s*(Z|M|ZM)?\s*\(",
        re.IGNORECASE
    )
    geojson_keys = re.compile(r'("type"\s*:\s*"Feature"|"coordinates"\s*:\s*\[)', re.IGNORECASE)
    coord_pair_pattern = re.compile(r"^\s*\[?\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\]?\s*$")
    
    findings = {}
    for col in df.columns:
        sample_vals = df[col].dropna().astype(str)
        if sample_vals.empty:
            continue
        has_wkt = any(wkt_patterns.search(str(val)) for val in sample_vals.head(500))
        has_geojson = any(geojson_keys.search(str(val)) for val in sample_vals.head(500))
        has_coords = any(coord_pair_pattern.match(str(val)) for val in sample_vals.head(500))
        
        if has_wkt or has_geojson or has_coords:
            findings[col] = {"has_wkt": has_wkt, "has_geojson": has_geojson, "has_coords": has_coords}
            
    return findings


def main():
    root_dir = Path(__file__).resolve().parent
    raw_dir = root_dir / "data" / "raw"
    
    print("=" * 60)
    print("        BLUE ORBIT — LOCAL DATA AUDIT & VALIDATION")
    print("=" * 60)
    print(f"Working Directory: {root_dir.as_posix()}")
    print(f"Raw Data Directory: {raw_dir.as_posix()}")
    
    # 1. OCEAN DATA
    print("\n" + "=" * 60)
    print("DATASET 1 — OCEAN (copernicus_ocean_data.csv)")
    print("=" * 60)
    ocean_path = raw_dir / "copernicus_ocean_data.csv"
    if not ocean_path.exists():
        print(f"ERROR: {ocean_path} not found!")
        ocean_df, ocean_geo, ocean_time = None, None, None
    else:
        ocean_df = pd.read_csv(ocean_path)
        audit_general(ocean_df, ocean_path, "Copernicus Ocean Data")
        ocean_time = audit_time(ocean_df, "time")
        ocean_geo = audit_geographic(ocean_df, "latitude", "longitude")
        
        print("\n--- Ocean-Specific Variable Audit (depth & thetao) ---")
        if "depth" in ocean_df.columns:
            depth_vals = np.sort(ocean_df["depth"].dropna().unique())
            print(f"Unique Depth Values:       {depth_vals.tolist()}")
            print(f"Number of Depth Levels:    {len(depth_vals)}")
            print(f"Depth Range:               [{depth_vals.min():.2f}m, {depth_vals.max():.2f}m]")
        else:
            print("No 'depth' column found.")
            depth_vals = np.array([])
            
        if "thetao" in ocean_df.columns:
            t_min = float(ocean_df["thetao"].min())
            t_max = float(ocean_df["thetao"].max())
            t_mean = float(ocean_df["thetao"].mean())
            t_median = float(ocean_df["thetao"].median())
            print(f"Thetao (Temp) Minimum:     {t_min:.4f} °C")
            print(f"Thetao (Temp) Maximum:     {t_max:.4f} °C")
            print(f"Thetao (Temp) Mean:        {t_mean:.4f} °C")
            print(f"Thetao (Temp) Median:      {t_median:.4f} °C")
            
            # Physical validation check
            suspicious = ((ocean_df["thetao"] < -2.0) | (ocean_df["thetao"] > 40.0)).sum()
            print(f"Physically Suspicious Vals (< -2°C or > 40°C): {suspicious:,} rows")
            
            print("\nObservation on Temperature & Depth:")
            if len(depth_vals) == 1 and depth_vals[0] <= 1.0:
                print(f"Temperature depth information suggests: Data is recorded at a single shallow depth level ({depth_vals[0]}m), representing near-surface ocean temperature.")
            else:
                print(f"Temperature depth information suggests: Data contains depth levels {depth_vals.tolist()}. Cannot unconditionally assume surface SST without referencing depth = {depth_vals[0]}m.")

    # 2. CHLOROPHYLL DATA
    print("\n" + "=" * 60)
    print("DATASET 2 — CHLOROPHYLL (chlorophyll_a_data.csv)")
    print("=" * 60)
    chl_path = raw_dir / "chlorophyll_a_data.csv"
    if not chl_path.exists():
        print(f"ERROR: {chl_path} not found!")
        chl_df, chl_geo, chl_time = None, None, None
    else:
        chl_df = pd.read_csv(chl_path)
        audit_general(chl_df, chl_path, "Chlorophyll-a Data")
        chl_time = audit_time(chl_df, "time")
        chl_geo = audit_geographic(chl_df, "latitude", "longitude")
        
        print("\n--- Chlorophyll-Specific Variable Audit (depth & chl) ---")
        if "depth" in chl_df.columns:
            chl_depth_vals = np.sort(chl_df["depth"].dropna().unique())
            print(f"Unique Depth Values:       {chl_depth_vals.tolist()}")
            print(f"Number of Depth Levels:    {len(chl_depth_vals)}")
            print(f"Depth Range:               [{chl_depth_vals.min():.2f}m, {chl_depth_vals.max():.2f}m]")
        else:
            print("No 'depth' column found.")
            chl_depth_vals = np.array([])
            
        if "chl" in chl_df.columns:
            c_min = float(chl_df["chl"].min())
            c_max = float(chl_df["chl"].max())
            c_mean = float(chl_df["chl"].mean())
            c_median = float(chl_df["chl"].median())
            print(f"Chlorophyll-a Minimum:     {c_min:.4f} mg/m³")
            print(f"Chlorophyll-a Maximum:     {c_max:.4f} mg/m³")
            print(f"Chlorophyll-a Mean:        {c_mean:.4f} mg/m³")
            print(f"Chlorophyll-a Median:      {c_median:.4f} mg/m³")
            
            neg_chl = (chl_df["chl"] < 0).sum()
            neg_pct = (neg_chl / len(chl_df)) * 100
            print(f"Negative Chlorophyll Values: {neg_chl:,} rows ({neg_pct:.3f}%)")
            if neg_chl > 0:
                print("  -> Flagged: Negative values present (likely sensor artifact/below detection limit; kept unmodified).")
            else:
                print("  -> No negative chlorophyll values found.")

    # 3. WEATHER DATA
    print("\n" + "=" * 60)
    print("DATASET 3 — WEATHER (weather_west_coast.csv)")
    print("=" * 60)
    weather_path = raw_dir / "weather_west_coast.csv"
    if not weather_path.exists():
        print(f"ERROR: {weather_path} not found!")
        weather_df, weather_geo, weather_time = None, None, None
    else:
        weather_df = pd.read_csv(weather_path)
        audit_general(weather_df, weather_path, "Weather West Coast Data")
        weather_time = audit_time(weather_df, "time")
        weather_geo = audit_geographic(weather_df, "lat_round", "lon_round")
        
        print("\n--- Weather-Specific Variable Ranges ---")
        numeric_cols = [
            ("wind_speed_knots", "knots"),
            ("wind_direction", "degrees"),
            ("surface_pressure_hpa", "hPa"),
            ("wave_height_meters", "meters"),
            ("wave_direction", "degrees"),
            ("wave_period_seconds", "seconds")
        ]
        for col, unit in numeric_cols:
            if col in weather_df.columns:
                c_min = float(weather_df[col].min())
                c_max = float(weather_df[col].max())
                c_mean = float(weather_df[col].mean())
                c_median = float(weather_df[col].median())
                print(f"{col:<23}: [{c_min:8.2f}, {c_max:8.2f}] {unit:<8} (Mean: {c_mean:7.2f}, Median: {c_median:7.2f})")
            else:
                print(f"{col:<23}: Column missing")
                
        if weather_geo:
            # Check regular grid representation
            expected_pairs = weather_geo["lat_count"] * weather_geo["lon_count"]
            actual_pairs = weather_geo["pairs_count"]
            is_full_grid = (actual_pairs == expected_pairs)
            print(f"\nGrid Regularity Assessment:")
            print(f"Unique Latitudes ({weather_geo['lat_count']}) x Unique Longitudes ({weather_geo['lon_count']}) = {expected_pairs:,} possible points.")
            print(f"Actual distinct (lat_round, lon_round) combinations: {actual_pairs:,}")
            if is_full_grid:
                print("  -> lat_round / lon_round form a complete regular rectangular grid.")
            else:
                print(f"  -> lat_round / lon_round form a regular grid subset ({actual_pairs}/{expected_pairs} points present, e.g. coastal/marine mask).")

    # 4. GEOBOUNDARIES DATA
    print("\n" + "=" * 60)
    print("DATASET 4 — GEOBOUNDARIES (geoboundaries.csv)")
    print("=" * 60)
    geo_path = raw_dir / "geoboundaries.csv"
    if not geo_path.exists():
        print(f"ERROR: {geo_path} not found!")
        geo_df = None
    else:
        geo_df = pd.read_csv(geo_path, low_memory=False)
        audit_general(geo_df, geo_path, "GeoBoundaries Metadata")
        
        print("\n--- GeoBoundaries-Specific Attribute Audit ---")
        if "SITE_ID" in geo_df.columns:
            print(f"Unique SITE_ID Count:      {geo_df['SITE_ID'].nunique():,}")
            
        if "SITE_TYPE" in geo_df.columns:
            print("\nSITE_TYPE Distribution:")
            print(geo_df["SITE_TYPE"].value_counts(dropna=False).to_string())
            
        if "NAME_ENG" in geo_df.columns:
            print("\nNAME_ENG Examples (Sample 5 non-null):")
            sample_names = geo_df["NAME_ENG"].dropna().unique()[:5]
            for s in sample_names:
                print(f"  - {s}")
                
        if "DESIG_ENG" in geo_df.columns:
            print("\nDESIG_ENG Examples (Sample 5 non-null):")
            sample_desig = geo_df["DESIG_ENG"].dropna().unique()[:5]
            for s in sample_desig:
                print(f"  - {s}")
                
        if "ISO3" in geo_df.columns:
            print("\nISO3 Distribution (Top 5):")
            print(geo_df["ISO3"].value_counts(dropna=False).head(5).to_string())
            
        if "STATUS" in geo_df.columns:
            print("\nSTATUS Distribution:")
            print(geo_df["STATUS"].value_counts(dropna=False).to_string())
            
        print("\n--- Spatial Geometry Detection ---")
        geom_findings = detect_geometry_in_df(geo_df)
        if geom_findings:
            print("Detected potential geometry columns:")
            for col, d in geom_findings.items():
                print(f"  - {col}: WKT={d['has_wkt']}, GeoJSON={d['has_geojson']}")
        else:
            print("NO GEOMETRY DETECTED IN CSV.")
            print("Observation: The geoboundaries.csv file contains marine protected area attribute/metadata information (IDs, designations, governance, reporting areas) without spatial geometry (no WKT, no GeoJSON, no boundary polygons/coordinates).")

    # OCEAN VS CHLOROPHYLL SPATIAL ALIGNMENT
    print("\n" + "=" * 60)
    print("OCEAN / CHLOROPHYLL SPATIAL ALIGNMENT")
    print("=" * 60)
    
    if ocean_df is not None and chl_df is not None and ocean_geo is not None and chl_geo is not None:
        ocean_lats_set = set(ocean_geo["unique_lats"])
        chl_lats_set = set(chl_geo["unique_lats"])
        lats_exact_match = (ocean_lats_set == chl_lats_set)
        
        ocean_lons_set = set(ocean_geo["unique_lons"])
        chl_lons_set = set(chl_geo["unique_lons"])
        lons_exact_match = (ocean_lons_set == chl_lons_set)
        
        lat_overlap = not (ocean_geo["lat_max"] < chl_geo["lat_min"] or ocean_geo["lat_min"] > chl_geo["lat_max"])
        lon_overlap = not (ocean_geo["lon_max"] < chl_geo["lon_min"] or ocean_geo["lon_min"] > chl_geo["lon_max"])
        
        ocean_depths = set(ocean_df["depth"].dropna().unique()) if "depth" in ocean_df.columns else set()
        chl_depths = set(chl_df["depth"].dropna().unique()) if "depth" in chl_df.columns else set()
        exact_depth_overlap = bool(ocean_depths & chl_depths)
        approx_depth_overlap = any(any(np.isclose(d1, d2, atol=1e-3) for d2 in chl_depths) for d1 in ocean_depths)
        
        ocean_times = set(ocean_df["time"].dropna().unique()) if "time" in ocean_df.columns else set()
        chl_times = set(chl_df["time"].dropna().unique()) if "time" in chl_df.columns else set()
        times_overlap = bool(ocean_times & chl_times)
        
        shared_pairs = ocean_geo["pairs_set"] & chl_geo["pairs_set"]
        shared_pairs_count = len(shared_pairs)
        
        print(f"1. Latitude grids exact match:       {lats_exact_match}")
        print(f"   Ocean Lat Count: {len(ocean_lats_set)}, Chl Lat Count: {len(chl_lats_set)}")
        print(f"2. Longitude grids exact match:      {lons_exact_match}")
        print(f"   Ocean Lon Count: {len(ocean_lons_set)}, Chl Lon Count: {len(chl_lons_set)}")
        print(f"3. Coordinate ranges overlap:        Lat Overlap={lat_overlap}, Lon Overlap={lon_overlap}")
        print(f"   Ocean Lat: [{ocean_geo['lat_min']:.4f}, {ocean_geo['lat_max']:.4f}], Chl Lat: [{chl_geo['lat_min']:.4f}, {chl_geo['lat_max']:.4f}]")
        print(f"   Ocean Lon: [{ocean_geo['lon_min']:.4f}, {ocean_geo['lon_max']:.4f}], Chl Lon: [{chl_geo['lon_min']:.4f}, {chl_geo['lon_max']:.4f}]")
        print(f"4. Depth levels overlap:             Exact={exact_depth_overlap}, Approx (~0.494m)={approx_depth_overlap} (Ocean: {sorted([float(x) for x in ocean_depths])}, Chl: {sorted([float(x) for x in chl_depths])})")
        print(f"5. Timestamps overlap:               {times_overlap} (Shared unique timestamps: {len(ocean_times & chl_times):,})")
        print(f"6. Exact (Lat, Lon) pairs in both:   {shared_pairs_count:,} pairs")
        print(f"   (Ocean total pairs: {ocean_geo['pairs_count']:,}, Chl total pairs: {chl_geo['pairs_count']:,})")
        
        practical_join = shared_pairs_count > 0 and (shared_pairs_count == min(ocean_geo['pairs_count'], chl_geo['pairs_count']))
        print(f"7. Would an exact coordinate join be practical?")
        if lats_exact_match and lons_exact_match:
            print("   -> YES: Grids match identically on exact coordinates.")
        elif shared_pairs_count > 0:
            print(f"   -> PARTIALLY: Exact coordinate join is only possible on {shared_pairs_count:,} shared grid points. Spatial interpolation or grid unification will be required for complete coverage.")
        else:
            print("   -> NO: Zero shared exact coordinate pairs. Grid resolutions or offsets differ; spatial alignment / nearest-neighbor / interpolation needed.")
    else:
        print("Could not compare Ocean and Chlorophyll data due to missing datasets.")

    # SCIENTIFIC VALIDATION NOTES
    print("\n" + "=" * 60)
    print("SCIENTIFIC VALIDATION NOTES")
    print("=" * 60)
    print("1. Temperature (thetao):")
    print("   - Inspect depth column to ensure whether temperature represents bulk/surface or multi-layer.")
    print("   - Units and value distribution should be checked against physical oceanographic limits (-2°C to 35°C in Arabian Sea / Indian Ocean).")
    print("2. Chlorophyll-a (chl):")
    print("   - Chlorophyll concentration represents biological productivity in mg/m³.")
    print("   - Values < 0 indicate non-physical measurement noise or sensor artifacts requiring treatment in processing steps.")
    print("3. Weather variables:")
    print("   - Wind speed (knots), direction (°), wave height (m), wave period (s), and pressure (hPa) are critical for vessel safety / navigability.")
    print("   - Check for physical validity (wave heights >= 0, pressures ~ 980-1030 hPa, wind >= 0).")
    print("4. Marine Boundaries:")
    print("   - Protected area metadata provides regulatory constraints (e.g. no-take zones).")
    print("   - Spatial geometries are currently absent in the CSV and will require boundary polygons or GeoJSON spatial representations in subsequent steps.")

    # RECOMMENDED NEXT DATA-PIPELINE ACTIONS
    print("\n" + "=" * 60)
    print("RECOMMENDED NEXT DATA-PIPELINE ACTIONS")
    print("=" * 60)
    print("1. Review the local audit output thoroughly with domain requirements.")
    print("2. Define a unified spatial grid and spatial resolution strategy (e.g., handling differences between Ocean, Chl, and Weather coordinate grids).")
    print("3. Formulate data cleaning rules (handling negative chl values, missing timestamps, coordinate precision).")
    print("4. Source or generate GeoJSON spatial boundaries for MPA/protected zones matching geoboundaries metadata.")
    print("5. Proceed to STEP 2B (Data Transformation Pipeline & Parquet/GeoJSON creation) after design alignment.")

    # CONCISE SUMMARY
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    
    depth_str = f"{ocean_df['depth'].unique().tolist()}" if ocean_df is not None and "depth" in ocean_df.columns else "N/A"
    ocean_res_str = f"Lat ~ {ocean_geo['lat_spacing']}°, Lon ~ {ocean_geo['lon_spacing']}°" if ocean_geo else "N/A"
    chl_res_str = f"Lat ~ {chl_geo['lat_spacing']}°, Lon ~ {chl_geo['lon_spacing']}°" if chl_geo else "N/A"
    weather_res_str = f"Lat ~ {weather_geo['lat_spacing']}°, Lon ~ {weather_geo['lon_spacing']}°" if weather_geo else "N/A"
    
    if ocean_geo and chl_geo:
        aligned_str = "Exact match" if (ocean_geo["unique_lats"].tolist() == chl_geo["unique_lats"].tolist() and ocean_geo["unique_lons"].tolist() == chl_geo["unique_lons"].tolist()) else "Mismatched / Different grid resolution"
    else:
        aligned_str = "N/A"
        
    geom_str = "No geometry detected (attributes/metadata only)" if (geo_df is not None and not geom_findings) else "Geometry detected"
    
    issues = []
    if chl_df is not None and "chl" in chl_df.columns and (chl_df["chl"] < 0).sum() > 0:
        issues.append(f"Negative chlorophyll values present ({(chl_df['chl'] < 0).sum():,} rows)")
    if geo_df is not None and not geom_findings:
        issues.append("geoboundaries.csv lacks spatial geometry columns")
    if ocean_geo and chl_geo and aligned_str != "Exact match":
        issues.append("Ocean and Chlorophyll spatial grids are not identically aligned")
    
    major_issues_str = "; ".join(issues) if issues else "None observed"

    print(f"Ocean temperature depth:            {depth_str}")
    print(f"Ocean spatial resolution:           {ocean_res_str}")
    print(f"Chlorophyll spatial resolution:     {chl_res_str}")
    print(f"Weather spatial resolution:         {weather_res_str}")
    print(f"Ocean/chlorophyll grids aligned:    {aligned_str}")
    print(f"Geometry present in geoboundaries:  {geom_str}")
    print(f"Major data-quality issues:          {major_issues_str}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
