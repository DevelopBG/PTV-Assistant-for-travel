"""
Health check endpoint.

Provides service health status and basic statistics about loaded GTFS data.
"""

from datetime import datetime
from fastapi import APIRouter, Depends

from ..models import HealthResponse
from ..dependencies import get_transit_service, TransitService

router = APIRouter(prefix="/health", tags=["health"])

API_VERSION = "1.0.0"


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="""Check API health status and get statistics about loaded GTFS data.

Use this endpoint to verify the API is running and GTFS data has been loaded.
Returns counts of stops, routes, and trips in the current dataset.

**Status values:**
- `healthy` - API is running and GTFS data is loaded
- `unhealthy` - GTFS data failed to load or is unavailable""",
    responses={
        200: {
            "description": "Health status and data statistics",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "1.0.0",
                        "gtfs_loaded": True,
                        "stops_count": 497,
                        "routes_count": 13,
                        "trips_count": 8096,
                        "timestamp": "2026-01-15T10:30:00.123456"
                    }
                }
            }
        }
    }
)
def health_check(
    service: TransitService = Depends(get_transit_service)
) -> HealthResponse:
    """
    Health check endpoint.

    Returns service status and statistics about loaded GTFS data.
    """
    parser = service.parser

    return HealthResponse(
        status="healthy" if service.is_loaded else "unhealthy",
        version=API_VERSION,
        gtfs_loaded=service.is_loaded,
        stops_count=len(parser.stops) if parser else 0,
        routes_count=len(parser.routes) if parser else 0,
        trips_count=len(parser.trips) if parser else 0,
        timestamp=datetime.now().isoformat()
    )
