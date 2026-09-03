from pydantic import BaseModel, Field
from typing import Optional
from ..location.schemas import LocationContext

class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    message: str = Field(..., min_length=1, description="Natural language user input")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional latitude")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional longitude")
    date_str: Optional[str] = Field(None, description="Optional date string (YYYY-MM-DD or 'tomorrow')")
    location_context: Optional[LocationContext] = Field(None, description="Optional normalized LocationContext")
