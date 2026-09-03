import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables — look for backend/.env first
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)
load_dotenv(override=False)  # fallback to any .env in CWD

# Base project directory
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Mode Configuration
# False = Cache Mode (local Parquet / GeoJSON datasets)
# True = Live Mode (live external APIs: Copernicus / Open-Meteo)
# For Step 8, the default is strictly False.
LIVE_MODE: bool = os.getenv("LIVE_MODE", "False").strip().lower() in ("true", "1", "yes", "t")

# Data File Paths
MARINE_PARQUET_PATH = os.getenv(
    "MARINE_PARQUET_PATH",
    str(PROJECT_ROOT / "data" / "processed" / "processed_marine_db.parquet")
)

MARINE_HISTORICAL_DIR = os.getenv(
    "MARINE_HISTORICAL_DIR",
    str(PROJECT_ROOT / "data" / "historical" / "marine")
)

# Copernicus Marine Configuration (Step 15)
COPERNICUS_THETAO_DATASET = os.getenv("COPERNICUS_THETAO_DATASET", "cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m")
COPERNICUS_CHL_DATASET = os.getenv("COPERNICUS_CHL_DATASET", "cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m")
COPERNICUS_SURFACE_DEPTH = float(os.getenv("COPERNICUS_SURFACE_DEPTH", "0.494025"))

# Default West Coast India Bounding Box for ingestion
MARINE_INGESTION_MIN_LAT = float(os.getenv("MARINE_INGESTION_MIN_LAT", "8.0"))
MARINE_INGESTION_MAX_LAT = float(os.getenv("MARINE_INGESTION_MAX_LAT", "23.0"))
MARINE_INGESTION_MIN_LON = float(os.getenv("MARINE_INGESTION_MIN_LON", "68.0"))
MARINE_INGESTION_MAX_LON = float(os.getenv("MARINE_INGESTION_MAX_LON", "78.0"))

WEATHER_PARQUET_PATH = os.getenv(
    "WEATHER_PARQUET_PATH",
    str(PROJECT_ROOT / "data" / "processed" / "weather_regional_grid.parquet")
)

EEZ_GEOJSON_PATH = os.getenv(
    "EEZ_GEOJSON_PATH",
    str(PROJECT_ROOT / "data" / "boundaries" / "india_eez.geojson")
)

# Engine Config Paths
SUITABILITY_CONFIG_PATH = str(APP_DIR / "config" / "suitability_config.json")
WEATHER_SAFETY_CONFIG_PATH = str(APP_DIR / "config" / "weather_safety_config.json")
GEOFENCE_CONFIG_PATH = str(APP_DIR / "config" / "geofence_config.json")

# LLM Configuration (Step 9: Fishing/Habitat Agent)
# All sensitive credentials must be set via environment variables — never hard-coded.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
