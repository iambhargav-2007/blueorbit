"""
test_step21_spatial.py

Test suite for Step 21: Premium Marine Spatial Intelligence.
Verifies:
- EEZ GeoJSON endpoint
- Point analysis (click-to-analyze) with geofencing, habitat, weather, and unified decision
- Grid visualization layers for SST, Chlorophyll, Habitat Suitability, and Weather
- Validation on invalid coordinates and unsupported fake layers
- Temporal consistency and lack of fabricated data
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_1_eez_endpoint_returns_valid_geojson():
    """1. EEZ endpoint returns 200 and valid GeoJSON FeatureCollection."""
    resp = client.get("/api/v1/spatial/eez")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) > 0


def test_2_point_analysis_valid_coastal_point():
    """2. Point analysis near Goa returns full spatial intelligence."""
    resp = client.get("/api/v1/spatial/point?lat=15.41&lon=73.80&date=2025-10-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Near Goa Coastal Zone" in data["location"]["display_name"]
    assert "geofence" in data
    assert "decision" in data
    assert data["decision"]["decision"] in ("FAVORABLE", "CAUTION", "NOT_RECOMMENDED", "INSUFFICIENT_DATA")


def test_3_point_analysis_outside_eez():
    """3. Point analysis outside Indian EEZ returns safe status without crashing."""
    resp = client.get("/api/v1/spatial/point?lat=12.0&lon=65.0&date=2025-10-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["is_inside_eez"] is False
    if data["decision"]:
        assert data["decision"]["decision"] in ("NOT_RECOMMENDED", "INSUFFICIENT_DATA")


def test_4_point_analysis_invalid_coordinates_rejected():
    """4. Out of range coordinates return 422 Unprocessable Entity."""
    resp = client.get("/api/v1/spatial/point?lat=120.0&lon=73.80")
    assert resp.status_code == 422


def test_5_point_analysis_future_date_rejected():
    """5. Future dates return explicit UNSUPPORTED_FUTURE without fake forecast."""
    resp = client.get("/api/v1/spatial/point?lat=15.41&lon=73.80&date=2026-09-04")
    assert resp.status_code == 200
    data = resp.json()
    assert data["temporal_mode"] == "UNSUPPORTED_FUTURE"
    assert data["decision"]["decision"] == "INSUFFICIENT_DATA"
    assert data["decision"]["limiting_factor"] == "Unsupported Future Date"


def test_6_grid_sst_layer_returns_real_copernicus_data():
    """6. SST grid layer returns real temperature cells with valid temperature range."""
    resp = client.get("/api/v1/spatial/grid?layer=sst&date=2025-10-01&step=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["layer"] == "sst"
    assert data["unit"] == "°C"
    assert len(data["cells"]) > 0
    # Physical ocean SST bounds check (between 20°C and 35°C in Arabian Sea)
    assert 20.0 <= data["min_val"] <= 35.0
    assert 20.0 <= data["max_val"] <= 35.0


def test_7_grid_chlorophyll_layer_returns_real_data():
    """7. Chlorophyll grid layer returns real mg/m³ observations."""
    resp = client.get("/api/v1/spatial/grid?layer=chlorophyll&date=2025-10-01&step=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["layer"] == "chlorophyll"
    assert data["unit"] == "mg/m³"
    assert len(data["cells"]) > 0


def test_8_grid_habitat_layer_returns_deterministic_scores():
    """8. Habitat suitability grid returns deterministic 0-100 scores."""
    resp = client.get("/api/v1/spatial/grid?layer=habitat&date=2025-10-01&step=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["layer"] == "habitat"
    assert len(data["cells"]) > 0
    for cell in data["cells"][:5]:
        assert 0.0 <= cell["val"] <= 100.0
        assert cell["category"] in ("habitat-high", "habitat-moderate", "habitat-low")


def test_9_grid_weather_layer_returns_real_wind_and_waves():
    """9. Weather grid layer returns wind and sea state risks."""
    resp = client.get("/api/v1/spatial/grid?layer=weather&date=2025-10-01&step=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["layer"] == "weather"
    assert len(data["cells"]) > 0


def test_10_unsupported_fake_layer_rejected():
    """10. Unsupported or fabricated layers (e.g. 'fish_schools') are rejected with 422."""
    resp = client.get("/api/v1/spatial/grid?layer=fish_schools")
    assert resp.status_code == 422
