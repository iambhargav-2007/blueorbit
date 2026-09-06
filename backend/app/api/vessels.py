from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel
import time
from ..providers.aisstream_vessel_provider import state_manager, VesselObservation

router = APIRouter()

@router.get("/", response_model=List[VesselObservation])
async def get_vessels():
    return state_manager.get_live_vessels()
