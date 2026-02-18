"""
PTV Transit Assistant API - Main Application.

FastAPI application for journey planning with Melbourne's public transport.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .routes import journey_router, stops_router, health_router, vehicles_router, alerts_router
from .routes.admin import router as admin_router
from .dependencies import get_transit_service
from ..utils.logging_config import setup_logging, get_logger

logger = get_logger(__name__)

# OpenAPI Tags metadata for documentation organization
TAGS_METADATA = [
    {
        "name": "health",
        "description": "Health check and API status endpoints. Use these to verify the API is running and check loaded data statistics.",
    },
    {
        "name": "stops",
        "description": "Stop search and lookup operations. Find stops by name (with fuzzy matching) or retrieve details by stop ID.",
    },
    {
        "name": "journey",
        "description": "Journey planning endpoints. Plan multi-leg trips between stops with optional realtime delay information.",
    },
    {
        "name": "vehicles",
        "description": "Live vehicle position tracking. Get real-time locations, speeds, and occupancy for metro, tram, bus, and V/Line vehicles.",
    },
    {
        "name": "alerts",
        "description": "Service alerts and disruptions. View current and upcoming service disruptions, delays, and detours. Note: Only metro and tram have service alerts from PTV.",
    },
    {
        "name": "admin",
        "description": "Administrative endpoints for GTFS data management. Trigger manual updates, check update status, and reload services. Requires admin API key authentication.",
    },
    {
        "name": "root",
        "description": "Root endpoint with API information and navigation links.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Loads transit data on startup.
    """
    # Setup logging
    setup_logging()
    logger.info("Starting PTV Transit Assistant API")

    # Pre-load transit data
    try:
        service = get_transit_service()
        logger.info(f"Transit data loaded: {service.parser.stops if service.parser else 0} stops")
    except Exception as e:
        logger.error(f"Failed to load transit data: {e}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down PTV Transit Assistant API")


# API Description for OpenAPI documentation
API_DESCRIPTION = """
Journey planning API for Melbourne's public transport network.

## Features

- **Journey Planning**: Find optimal routes between stops with multi-leg support
- **Stop Search**: Search for stops by name with fuzzy matching
- **Realtime Integration**: Get live delay and cancellation information
- **Vehicle Positions**: Track live vehicle locations on routes
- **Service Alerts**: View disruption and delay alerts

## Transport Modes

This API supports all four Melbourne transport modes:
- **Metro**: Metropolitan train services
- **V/Line**: Regional train and coach services
- **Tram**: Melbourne's iconic tram network
- **Bus**: Metropolitan and regional bus services

## Realtime Data

Vehicle positions and service alerts are sourced from PTV's GTFS-Realtime feeds.
Note that service alerts are only available for metro and tram modes (PTV limitation).

## Data Source

This API uses GTFS (General Transit Feed Specification) data from
[PTV Open Data](https://opendata.transport.vic.gov.au/).

## Getting Started

1. Check API health: `GET /api/v1/health`
2. Search for stops: `GET /api/v1/stops/search?query=Flinders`
3. Plan a journey: `POST /api/v1/journey/plan`
4. Track vehicles: `GET /api/v1/vehicles?mode=metro`
5. View alerts: `GET /api/v1/alerts?mode=metro`
"""

# Create FastAPI application
app = FastAPI(
    title="PTV Transit Assistant API",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "PTV Transit Assistant",
        "url": "https://github.com/caprihan/PTV_Assistant",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(stops_router, prefix="/api/v1")
app.include_router(journey_router, prefix="/api/v1")
app.include_router(vehicles_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")  # Admin endpoints


@app.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "name": "PTV Transit Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
