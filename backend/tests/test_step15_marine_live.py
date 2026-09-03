import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from app.providers.live_marine_provider import LiveMarineProvider

class MockDataset:
    def __init__(self, val_dict, vars_list=None):
        self.val_dict = val_dict
        self.variables = vars_list or list(val_dict.keys())
        self.dims = ['time', 'depth', 'latitude', 'longitude']
        self.coords = ['depth']

    def sel(self, **kwargs):
        return MockPoint(self.val_dict)

class MockPoint:
    def __init__(self, val_dict):
        self.val_dict = val_dict
        self.latitude = MagicMock(values=val_dict.get('latitude', 19.5))
        self.longitude = MagicMock(values=val_dict.get('longitude', 70.5))
        
        if 'thetao' in val_dict:
            self.thetao = MagicMock(values=val_dict['thetao'])
        if 'chl' in val_dict:
            self.chl = MagicMock(values=val_dict['chl'])
            
        self.variables = list(val_dict.keys())

def test_live_marine_provider_success():
    with patch('app.providers.live_marine_provider.COPERNICUS_AVAILABLE', True):
        provider = LiveMarineProvider()
        
        # Mock open_dataset
        with patch('app.providers.live_marine_provider.copernicusmarine.open_dataset') as mock_open:
            # First call for thetao, second for chl
            mock_open.side_effect = [
                MockDataset({'thetao': 28.5, 'latitude': 19.5, 'longitude': 70.5}),
                MockDataset({'chl': 0.8, 'latitude': 19.5, 'longitude': 70.5})
            ]
            
            result = provider.get_marine_data(19.5, 70.5, "2026-09-01")
            
            assert result["success"] is True
            assert result["temperature"] == 28.5
            assert result["chlorophyll"] == 0.8
            assert result["matched_latitude"] == 19.5
            assert result["matched_longitude"] == 70.5

def test_live_marine_provider_missing_chl():
    with patch('app.providers.live_marine_provider.COPERNICUS_AVAILABLE', True):
        provider = LiveMarineProvider()
        
        with patch('app.providers.live_marine_provider.copernicusmarine.open_dataset') as mock_open:
            # thetao exists, chl is missing or NaN
            mock_open.side_effect = [
                MockDataset({'thetao': 28.5, 'latitude': 19.5, 'longitude': 70.5}),
                MockDataset({'chl': pd.NA, 'latitude': 19.5, 'longitude': 70.5})
            ]
            
            result = provider.get_marine_data(19.5, 70.5, "2026-09-01")
            
            assert result["success"] is True
            assert result["temperature"] == 28.5
            assert result["chlorophyll"] is None
            assert result["data_validity"] == "Valid values found"

def test_live_marine_provider_network_failure():
    with patch('app.providers.live_marine_provider.COPERNICUS_AVAILABLE', True):
        provider = LiveMarineProvider()
        
        with patch('app.providers.live_marine_provider.copernicusmarine.open_dataset') as mock_open:
            mock_open.side_effect = Exception("Network timeout")
            
            result = provider.get_marine_data(19.5, 70.5, "2026-09-01")
            
            assert result["success"] is False
            assert "Network timeout" in result["error"]
