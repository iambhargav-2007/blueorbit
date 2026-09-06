from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseCycloneProvider(ABC):
    """
    Abstract base class for marine cyclone and severe weather providers.
    """

    @abstractmethod
    async def get_current_alerts(self) -> Dict[str, Any]:
        """
        Fetch active cyclone and severe weather alerts.
        """
        pass

    @abstractmethod
    async def get_alerts_for_location(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch alerts affecting a specific coordinate.
        """
        pass

    @abstractmethod
    async def get_alerts_for_date(self, date: str) -> Dict[str, Any]:
        """
        Fetch historical or forecast alerts for a specific date (YYYY-MM-DD).
        """
        pass

    @abstractmethod
    async def get_active_systems(self) -> Dict[str, Any]:
        """
        Fetch all currently active tropical systems or severe weather entities.
        """
        pass
