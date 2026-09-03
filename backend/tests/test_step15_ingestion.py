import pytest
import os
import shutil
from unittest.mock import patch, MagicMock
import pandas as pd
from app.ingestion.marine_ingestion import ingest_marine_data
from app.providers.historical_marine_provider import HistoricalMarineProvider
from app.config import MARINE_HISTORICAL_DIR

# We'll use a temporary directory for tests
TEST_HISTORICAL_DIR = os.path.join(os.path.dirname(__file__), "test_historical_marine")

class MockXarrayDataset:
    def __init__(self, df, vars_list=None):
        self.df = df
        self.dims = ['time', 'depth', 'latitude', 'longitude']
        self.coords = ['depth']
        self.variables = vars_list or df.columns.tolist()

    def sel(self, **kwargs):
        return self

    def to_dataframe(self):
        return self.df.set_index(['latitude', 'longitude'])

    def __getitem__(self, cols):
        cols_to_keep = cols + ['latitude', 'longitude']
        cols_to_keep = [c for c in cols_to_keep if c in self.df.columns]
        return MockXarrayDataset(self.df[cols_to_keep])

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup
    os.makedirs(TEST_HISTORICAL_DIR, exist_ok=True)
    
    yield
    
    # Teardown
    if os.path.exists(TEST_HISTORICAL_DIR):
        shutil.rmtree(TEST_HISTORICAL_DIR)

def test_ingestion_success():
    df_theta = pd.DataFrame({
        'latitude': [19.5, 19.6],
        'longitude': [70.5, 70.6],
        'thetao': [28.5, 28.6]
    })
    
    df_chl = pd.DataFrame({
        'latitude': [19.5, 19.6],
        'longitude': [70.5, 70.6],
        'chl': [0.8, 0.9]
    })
    
    with patch('app.ingestion.marine_ingestion.COPERNICUS_AVAILABLE', True), \
         patch('app.ingestion.marine_ingestion.MARINE_HISTORICAL_DIR', TEST_HISTORICAL_DIR), \
         patch('app.ingestion.marine_ingestion.copernicusmarine.open_dataset') as mock_open:
        
        mock_open.side_effect = [
            MockXarrayDataset(df_theta, ['thetao']),
            MockXarrayDataset(df_chl, ['chl']),
            MockXarrayDataset(df_theta, ['thetao']),
            MockXarrayDataset(df_chl, ['chl'])
        ]
        
        result = ingest_marine_data("2026-09-02")
        
        assert result["success"] is True
        assert result["rows"] == 2
        assert os.path.exists(result["output_path"])
        
        # Verify idempotency
        result2 = ingest_marine_data("2026-09-02")
        assert result2["success"] is True
        assert result2["rows"] == 2
        
        # Verify Parquet content
        df_saved = pd.read_parquet(result["output_path"])
        assert "temperature_c" in df_saved.columns
        assert "chlorophyll_mg_m3" in df_saved.columns
        assert df_saved["temperature_c"].iloc[0] == 28.5
        assert df_saved["chlorophyll_mg_m3"].iloc[0] == 0.8

def test_historical_provider_resolves_cache():
    with patch('app.providers.historical_marine_provider.MARINE_HISTORICAL_DIR', TEST_HISTORICAL_DIR):
        provider = HistoricalMarineProvider()
        # Mock the underlying cache engine
        with patch.object(provider, '_get_baseline_engine') as mock_baseline:
            mock_engine = MagicMock()
            mock_engine.query.return_value = {"success": True, "temperature": 27.0}
            mock_baseline.return_value = mock_engine
            
            res = provider.get_marine_data(19.5, 70.5, "2025-10-01")
            assert res["success"] is True
            assert res["temperature"] == 27.0
            mock_baseline.assert_called_once()
