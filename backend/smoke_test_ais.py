import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY")

async def test_ais():
    if not AISSTREAM_API_KEY:
        print("AISSTREAM_API_KEY is not configured.")
        return
    
    # Simple smoke test connecting to aisstream.io
    url = "wss://stream.aisstream.io/v0/stream"
    messages_received = 0
    unique_mmsi = set()
    
    try:
        async with websockets.connect(url, ping_interval=None) as websocket:
            subscribe_message = {
                "APIKey": AISSTREAM_API_KEY,
                "BoundingBoxes": [[[15.0, 68.0], [23.5, 74.1]]],
                "FilterMessageTypes": ["PositionReport"]
            }
            await websocket.send(json.dumps(subscribe_message))
            print("Connected and subscribed to AISStream.")
            
            # Wait for messages with a timeout of 30 seconds
            end_time = asyncio.get_event_loop().time() + 30.0
            
            while True:
                remaining_time = end_time - asyncio.get_event_loop().time()
                if remaining_time <= 0:
                    break
                    
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=remaining_time)
                    data = json.loads(message)
                    messages_received += 1
                    
                    if "Message" in data and "PositionReport" in data["Message"]:
                        pr = data["Message"]["PositionReport"]
                        mmsi = data["MetaData"]["MMSI"]
                        unique_mmsi.add(mmsi)
                        print(f"AIS message received")
                        print(f"MMSI: {mmsi}")
                        print(f"Name: {data['MetaData'].get('ShipName', 'N/A')}")
                        print(f"Latitude: {pr.get('Latitude')}")
                        print(f"Longitude: {pr.get('Longitude')}")
                        print(f"SOG: {pr.get('Sog')}")
                        print(f"COG: {pr.get('Cog')}")
                        print(f"Timestamp: {data['MetaData'].get('time_utc')}")
                        print(f"Message type: PositionReport")
                        print("---")
                        
                        if messages_received >= 5: # Just stop early if we have enough evidence
                            break
                            
                except asyncio.TimeoutError:
                    break
                
            if messages_received == 0:
                print("Connected but no AIS messages were received during the smoke-test window.")
            else:
                print(f"Smoke test successful. Received {messages_received} messages from {len(unique_mmsi)} unique MMSIs.")
                
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_ais())
