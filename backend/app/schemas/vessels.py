from pydantic import BaseModel
from typing import Optional

class VesselObservation(BaseModel):
    mmsi: str
    vessel_name: Optional[str] = None
    latitude: float
    longitude: float
    speed_over_ground: Optional[float] = None
    course_over_ground: Optional[float] = None
    timestamp: str
    data_status: str
    source: str = "AISStream"
    provider: str = "AISStreamVesselProvider"
