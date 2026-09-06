import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.chat import router as chat_router
from app.location.router import router as location_router
from app.api.spatial import router as spatial_router
from app.api.cyclone import router as cyclone_router
from app.api.voice import router as voice_router
from app.api.vessels import router as vessels_router
import asyncio
from app.providers.aisstream_vessel_provider import state_manager

# Load environment variables from .env if present
load_dotenv()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the AIS background connection
    task = asyncio.create_task(state_manager.run())
    yield
    # Shutdown
    state_manager.running = False
    task.cancel()

app = FastAPI(
    title="Blue Orbit - ORCA Marine Intelligence Platform",
    description="Backend API for Blue Orbit (ORCA) marine decision support system.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS (Cross-Origin Resource Sharing) configuration
# Allows the React frontend to communicate with this FastAPI backend
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
origins = [
    frontend_url,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(location_router)
app.include_router(spatial_router)
app.include_router(cyclone_router)
app.include_router(voice_router)
app.include_router(vessels_router, prefix="/api/v1/vessels")

@app.get("/")
def root():
    """
    Root endpoint returning basic project metadata and status.
    """
    return {
        "project": "Blue Orbit",
        "system": "ORCA",
        "status": "running",
    }


@app.get("/api/health")
def health_check():
    """
    Health check endpoint to verify backend service availability.
    """
    return {
        "status": "healthy"
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
