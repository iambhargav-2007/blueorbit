import pytest
from app.services.severe_weather_engine import SevereWeatherEngine

def test_no_data():
    engine = SevereWeatherEngine()
    result = engine.evaluate(None, None, None, None, None)
    assert result.risk_level == "INSUFFICIENT_DATA"
    assert result.affected_status == "NO_VERIFIED_DATA"

def test_extreme_wind():
    engine = SevereWeatherEngine()
    result = engine.evaluate(wind_speed_knots=65, wave_height_meters=2.0)
    assert result.risk_level == "EXTREME"
    assert result.is_affected is True

def test_severe_waves():
    engine = SevereWeatherEngine()
    result = engine.evaluate(wind_speed_knots=10, wave_height_meters=4.5)
    assert result.risk_level == "SEVERE"
    assert result.is_affected is True

def test_verified_cyclone_within_radius():
    engine = SevereWeatherEngine()
    cyclone = {
        "status": "ACTIVE",
        "severity": "SEVERE",
        "affected_radius_km": 150
    }
    result = engine.evaluate(
        wind_speed_knots=15, 
        cyclone_alert=cyclone, 
        distance_to_center_km=100
    )
    assert result.risk_level == "EXTREME"
    assert result.affected_status == "AFFECTED"
    assert result.is_affected is True

def test_verified_cyclone_outside_radius():
    engine = SevereWeatherEngine()
    cyclone = {
        "status": "ACTIVE",
        "severity": "SEVERE",
        "affected_radius_km": 150
    }
    result = engine.evaluate(
        wind_speed_knots=15, 
        cyclone_alert=cyclone, 
        distance_to_center_km=200
    )
    assert result.risk_level == "NORMAL"
    assert result.affected_status == "NOT_AFFECTED"
    assert result.is_affected is False
