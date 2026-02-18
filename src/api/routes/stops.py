"""
Stops search endpoint.

Provides stop lookup and search functionality with fuzzy matching support.
"""

from fastapi import APIRouter, Depends, Query, HTTPException

from ..models import StopSearchResponse, StopResponse, ErrorResponse
from ..dependencies import get_transit_service, TransitService
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stops", tags=["stops"])


@router.get(
    "/search",
    response_model=StopSearchResponse,
    responses={
        200: {
            "description": "Search results with matching stops",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Found 3 stop(s) matching 'Tarneit'",
                        "query": "Tarneit",
                        "count": 3,
                        "stops": [
                            {
                                "stop_id": "47648",
                                "stop_name": "Tarneit Station",
                                "stop_lat": -37.832,
                                "stop_lon": 144.694,
                                "match_score": 100
                            }
                        ]
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid query (too short)"},
        503: {"description": "Stop index not available"}
    },
    summary="Search Stops",
    description="""Search for stops by name with optional fuzzy matching.

Supports partial name matching and handles typos when fuzzy matching is enabled.
Results are sorted by match score (highest first).

**Examples:**
- "Tarneit" - finds Tarneit Station
- "southern cross" - finds Southern Cross Station
- "flindrrs" - finds Flinders Street (with fuzzy matching)"""
)
def search_stops(
    query: str = Query(
        ...,
        min_length=2,
        description="Search query for stop name (minimum 2 characters)",
        examples=["Tarneit", "Southern Cross", "Flinders"]
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results (1-20)"
    ),
    fuzzy: bool = Query(
        default=True,
        description="Use fuzzy matching to handle typos and partial names"
    ),
    service: TransitService = Depends(get_transit_service)
) -> StopSearchResponse:
    """
    Search for stops by name.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        fuzzy: Whether to use fuzzy matching
        service: Transit service dependency

    Returns:
        StopSearchResponse with matching stops
    """
    logger.debug(f"Searching stops: query='{query}', limit={limit}, fuzzy={fuzzy}")

    stop_index = service.stop_index
    if not stop_index:
        raise HTTPException(status_code=503, detail="Stop index not available")

    stops = []

    if fuzzy:
        # Fuzzy search returns (Stop, score) tuples
        matches = stop_index.find_stop_fuzzy(query, limit=limit)
        for stop, score in matches:
            stops.append(StopResponse(
                stop_id=stop.stop_id,
                stop_name=stop.stop_name,
                stop_lat=stop.stop_lat,
                stop_lon=stop.stop_lon,
                match_score=score
            ))
    else:
        # Exact search
        stop = stop_index.find_stop_exact(query)
        if stop:
            stops.append(StopResponse(
                stop_id=stop.stop_id,
                stop_name=stop.stop_name,
                stop_lat=stop.stop_lat,
                stop_lon=stop.stop_lon,
                match_score=100
            ))

    logger.info(f"Stop search for '{query}' returned {len(stops)} results")

    return StopSearchResponse(
        success=True,
        message=f"Found {len(stops)} stop(s) matching '{query}'",
        query=query,
        count=len(stops),
        stops=stops
    )


@router.get(
    "/{stop_id}",
    response_model=StopResponse,
    responses={
        200: {
            "description": "Stop details",
            "content": {
                "application/json": {
                    "example": {
                        "stop_id": "47648",
                        "stop_name": "Tarneit Station",
                        "stop_lat": -37.832,
                        "stop_lon": 144.694,
                        "match_score": None
                    }
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Stop not found"},
        503: {"description": "GTFS data not available"}
    },
    summary="Get Stop by ID",
    description="""Retrieve detailed information for a specific stop by its GTFS stop ID.

Returns the stop name and geographic coordinates (latitude/longitude)."""
)
def get_stop(
    stop_id: str,
    service: TransitService = Depends(get_transit_service)
) -> StopResponse:
    """
    Get a specific stop by ID.

    Args:
        stop_id: Stop identifier
        service: Transit service dependency

    Returns:
        StopResponse with stop details

    Raises:
        HTTPException: If stop not found
    """
    parser = service.parser
    if not parser:
        raise HTTPException(status_code=503, detail="GTFS data not available")

    stop = parser.get_stop(stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail=f"Stop '{stop_id}' not found")

    return StopResponse(
        stop_id=stop.stop_id,
        stop_name=stop.stop_name,
        stop_lat=stop.stop_lat,
        stop_lon=stop.stop_lon
    )
