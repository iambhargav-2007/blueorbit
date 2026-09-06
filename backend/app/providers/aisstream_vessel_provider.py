import asyncio
import json
import os
import time
import websockets
from typing import Dict
from ..schemas.vessels import VesselObservation

class VesselStateManager:
    def __init__(self):
        self.vessels: Dict[str, VesselObservation] = {}
        self.api_key = os.getenv("AISSTREAM_API_KEY")
        self.running = False
        
    async def run(self):
        self.api_key = os.getenv("AISSTREAM_API_KEY")
        if not self.api_key:
            print("AISSTREAM_API_KEY missing, vessel provider will not start.")
            return
            
        self.running = True
        url = "wss://stream.aisstream.io/v0/stream"
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=None) as websocket:
                    subscribe_message = {
                        "APIKey": self.api_key,
                        "BoundingBoxes": [[[-10.0, 50.0], [30.0, 100.0]]],
                        "FilterMessageTypes": ["PositionReport"]
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    
                    while self.running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        if "Message" in data and "PositionReport" in data["Message"]:
                            pr = data["Message"]["PositionReport"]
                            mmsi = str(data["MetaData"]["MMSI"])
                            
                            obs = VesselObservation(
                                mmsi=mmsi,
                                vessel_name=data["MetaData"].get("ShipName"),
                                latitude=pr.get("Latitude", 0),
                                longitude=pr.get("Longitude", 0),
                                speed_over_ground=pr.get("Sog"),
                                course_over_ground=pr.get("Cog"),
                                timestamp=data["MetaData"].get("time_utc", str(time.time())),
                                data_status="LIVE"
                            )
                            self.vessels[mmsi] = obs
            except Exception as e:
                print(f"AIS connection error: {e}")
                if self.running:
                    await asyncio.sleep(5)
                    
    def get_live_vessels(self):
        return list(self.vessels.values())

# Global singleton
state_manager = VesselStateManager()
