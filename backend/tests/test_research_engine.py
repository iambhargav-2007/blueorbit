import pytest
from app.services.historical_marine_engine import HistoricalMarineEngine

@pytest.fixture
def mock_engine(tmp_path):
    import pandas as pd
    import numpy as np

    marine_data = {
        "time": ["2025-10-01", "2025-10-02"],
        "latitude": [15.0, 15.0],
        "longitude": [71.0, 71.0],
        "temperature_c": [28.5, 29.0],
        "chlorophyll_mg_m3": [0.5, 0.6]
    }
    
    weather_data = {
        "date": ["2025-10-01", "2025-10-02"],
        "latitude": [15.0, 15.0],
        "longitude": [71.0, 71.0],
        "mean_wind_speed_knots": [10.0, 12.0],
        "mean_wave_height_meters": [1.5, 2.0]
    }

    marine_path = tmp_path / "marine.parquet"
    weather_path = tmp_path / "weather.parquet"

    pd.DataFrame(marine_data).to_parquet(marine_path)
    pd.DataFrame(weather_data).to_parquet(weather_path)

    return HistoricalMarineEngine(str(marine_path), str(weather_path))

def test_point_analysis_single_date(mock_engine):
    res = mock_engine.analyze_point_history(15.0, 71.0, "2025-10-01")
    assert res["analysis_type"] == "POINT_ANALYSIS"
    assert res["marine"]["data_status"] == "AVAILABLE"
    assert res["marine"]["temperature_c"]["mean"] == 28.5

def test_point_analysis_date_range(mock_engine):
    res = mock_engine.analyze_point_history(15.0, 71.0, "2025-10-01", "2025-10-02")
    assert res["analysis_type"] == "POINT_ANALYSIS"
    assert res["marine"]["temperature_c"]["mean"] == 28.75  # (28.5 + 29.0)/2
    assert res["marine"]["temperature_c"]["min"] == 28.5
    assert res["marine"]["temperature_c"]["max"] == 29.0

def test_spatial_comparison(mock_engine):
    res = mock_engine.compare_locations(15.0, 71.0, 16.0, 72.0, "2025-10-01")
    assert res["analysis_type"] == "SPATIAL_COMPARISON"
    assert len(res["locations"]) == 2
    
    loc1 = res["locations"][0]
    loc2 = res["locations"][1]
    
    assert loc1["data"]["marine"]["data_status"] == "AVAILABLE"
    assert loc2["data"]["marine"]["data_status"] == "INSUFFICIENT_DATA" # out of range

def test_missing_data_handling(mock_engine):
    res = mock_engine.analyze_point_history(10.0, 70.0, "2025-10-01") # out of range
    assert res["marine"]["data_status"] == "INSUFFICIENT_DATA"
    assert res["weather"]["data_status"] == "INSUFFICIENT_DATA"
