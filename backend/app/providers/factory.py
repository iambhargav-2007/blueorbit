from typing import Optional

from ..config import LIVE_MODE
from .base_marine_provider import BaseMarineProvider
from .cache_marine_provider import CacheMarineProvider
from .live_marine_provider import LiveMarineProvider
from .smart_marine_router import SmartMarineRouter

from .base_weather_provider import BaseWeatherProvider
from .cache_weather_provider import CacheWeatherProvider
from .live_weather_provider import InterimLiveWeatherProvider, LiveWeatherProvider
from .smart_weather_router import SmartWeatherRouter

def get_smart_marine_router(**kwargs) -> SmartMarineRouter:
    """
    Factory function to instantiate the SmartMarineRouter.
    """
    return SmartMarineRouter(**kwargs)

def get_smart_weather_router(**kwargs) -> SmartWeatherRouter:
    """
    Factory function to instantiate the SmartWeatherRouter (Step 19).
    """
    return SmartWeatherRouter(**kwargs)

def get_marine_provider(live_mode: Optional[bool] = None, **kwargs) -> BaseMarineProvider:
    """
    Factory function to instantiate the appropriate marine data provider.
    
    Args:
        live_mode (Optional[bool]): If None, uses the system default LIVE_MODE from config.
        **kwargs: Additional parameters passed to provider constructor (e.g. parquet_path).
        
    Returns:
        BaseMarineProvider: CacheMarineProvider if live_mode is False, otherwise LiveMarineProvider.
    """
    is_live = LIVE_MODE if live_mode is None else live_mode
    if is_live:
        return LiveMarineProvider(**kwargs)
    return CacheMarineProvider(**kwargs)

def get_weather_provider(live_mode: Optional[bool] = None, **kwargs) -> BaseWeatherProvider:
    """
    Factory function to instantiate the appropriate weather data provider.
    
    Args:
        live_mode (Optional[bool]): If None, uses the system default LIVE_MODE from config.
        **kwargs: Additional parameters passed to provider constructor (e.g. parquet_path).
        
    Returns:
        BaseWeatherProvider: CacheWeatherProvider if live_mode is False, otherwise InterimLiveWeatherProvider.
    """
    is_live = LIVE_MODE if live_mode is None else live_mode
    if is_live:
        return InterimLiveWeatherProvider(**kwargs)
    return CacheWeatherProvider(**kwargs)
