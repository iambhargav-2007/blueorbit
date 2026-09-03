from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseMarineProvider(ABC):
    """
    Abstract contract for marine environmental data providers.
    Both CacheMarineProvider and LiveMarineProvider must implement this interface.
    """

    @abstractmethod
    def get_marine_data(self, lat: float, lon: float, date_str: str) -> Dict[str, Any]:
        """
        Retrieves marine environmental observations for a specific coordinate and date.

        Args:
            lat (float): Requested latitude in WGS84 decimal degrees.
            lon (float): Requested longitude in WGS84 decimal degrees.
            date_str (str): Target date in 'YYYY-MM-DD' format.

        Returns:
            Dict[str, Any]: Standardized marine observation dictionary containing:
                - requested_latitude
                - requested_longitude
                - requested_date
                - matched_latitude
                - matched_longitude
                - temperature
                - chlorophyll
                - distance_km
                - data_validity
                - success (bool)
        """
        pass
