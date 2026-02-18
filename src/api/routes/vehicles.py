"""
Vehicle Positions API endpoints - Phase 8

Provides real-time vehicle position information from GTFS Realtime feeds.
Supports metro, tram, bus, and V/Line transport modes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from ..dependencies import get_transit_service, TransitService
from ...utils.logging_config import get_logger
from ...realtime.vehicle_positions import VehiclePositionParser
from ...realtime.models import VehiclePosition as VehiclePositionModel
from pydantic import BaseModel, Field, ConfigDict

logger = get_logger(__name__)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


# ============== Response Models ==============

class VehiclePositionResponse(BaseModel):
    """Response model for a single vehicle position."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vehicle_id": "1234",
                "latitude": -37.8136,
                "longitude": 144.9631,
                "timestamp": 1705300200,
                "trip_id": "1-GEL-vpt-1.T1.1-MFSu-1",
                "route_id": "1-GEL",
                "direction_id": 0,
                "label": "Geelong Express",
                "bearing": 225.5,
                "speed_kmh": 85.0,
                "stop_id": "47648",
                "current_status": "IN_TRANSIT_TO",
                "occupancy_status": "MANY_SEATS_AVAILABLE",
                "occupancy_percentage": 35
            }
        }
    )

    vehicle_id: str = Field(..., description="Unique vehicle identifier from GTFS Realtime")
    latitude: float = Field(..., description="Current latitude (WGS84)")
    longitude: float = Field(..., description="Current longitude (WGS84)")
    timestamp: int = Field(..., description="Unix timestamp of position update")

    # Trip information
    trip_id: Optional[str] = Field(None, description="GTFS trip ID if vehicle is assigned to a trip")
    route_id: Optional[str] = Field(None, description="GTFS route ID")
    direction_id: Optional[int] = Field(None, description="Direction of travel (0=outbound, 1=inbound)")

    # Vehicle details
    label: Optional[str] = Field(None, description="Human-readable vehicle label (e.g., train number)")

    # Position details
    bearing: Optional[float] = Field(None, description="Direction of travel in degrees (0=North, 90=East)")
    speed_kmh: Optional[float] = Field(None, description="Current speed in kilometers per hour")

    # Stop relationship
    stop_id: Optional[str] = Field(None, description="Current or next stop ID")
    current_status: Optional[str] = Field(
        None,
        description="Status relative to stop: INCOMING_AT, STOPPED_AT, IN_TRANSIT_TO"
    )

    # Crowding
    occupancy_status: Optional[str] = Field(
        None,
        description="Passenger load: EMPTY, MANY_SEATS_AVAILABLE, FEW_SEATS_AVAILABLE, STANDING_ROOM_ONLY, FULL"
    )
    occupancy_percentage: Optional[int] = Field(None, description="Occupancy percentage (0-100)")


class VehicleListResponse(BaseModel):
    """Response model for a list of vehicle positions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Found 42 vehicles",
                "mode": "metro",
                "count": 42,
                "vehicles": []
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable response message")
    mode: str = Field(..., description="Transport mode queried")
    count: int = Field(..., description="Number of vehicles returned")
    vehicles: List[VehiclePositionResponse] = Field(..., description="List of vehicle positions")


class VehicleSummaryResponse(BaseModel):
    """Response model for vehicle position summary statistics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "mode": "metro",
                "total_vehicles": 42,
                "vehicles_with_trip": 38,
                "vehicles_in_transit": 35,
                "vehicles_at_stop": 7,
                "average_speed_kmh": 45.2,
                "timestamp": 1705300200
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    mode: str = Field(..., description="Transport mode queried")
    total_vehicles: int = Field(..., description="Total number of vehicles in feed")
    vehicles_with_trip: int = Field(..., description="Vehicles assigned to a trip")
    vehicles_in_transit: int = Field(..., description="Vehicles currently moving between stops")
    vehicles_at_stop: int = Field(..., description="Vehicles stopped at a station")
    average_speed_kmh: Optional[float] = Field(None, description="Average speed of moving vehicles")
    timestamp: Optional[int] = Field(None, description="Feed timestamp (Unix)")


# ============== Helper Functions ==============

def _position_to_response(position: VehiclePositionModel) -> VehiclePositionResponse:
    """Convert internal VehiclePosition to API response model."""
    return VehiclePositionResponse(
        vehicle_id=position.vehicle_id,
        latitude=position.latitude,
        longitude=position.longitude,
        timestamp=position.timestamp,
        trip_id=position.trip_id,
        route_id=position.route_id,
        direction_id=position.direction_id,
        label=position.label,
        bearing=position.bearing,
        speed_kmh=position.get_speed_kmh(),
        stop_id=position.stop_id,
        current_status=position.current_status.value if position.current_status else None,
        occupancy_status=position.occupancy_status.value if position.occupancy_status else None,
        occupancy_percentage=position.occupancy_percentage
    )


def _get_parser(service: TransitService) -> VehiclePositionParser:
    """Get or create a VehiclePositionParser instance."""
    # Get the realtime fetcher from the service
    fetcher = service.get_realtime_fetcher()
    if not fetcher:
        raise HTTPException(
            status_code=503,
            detail="Realtime data not available. PTV API key may not be configured."
        )
    return VehiclePositionParser(fetcher=fetcher)


# ============== Endpoints ==============

@router.get(
    "",
    response_model=VehicleListResponse,
    summary="Get All Vehicle Positions",
    description="""Fetch all vehicle positions for a transport mode.

Returns real-time GPS positions of all vehicles currently operating on the selected mode.
Data is sourced from PTV's GTFS-Realtime vehicle positions feed.

**Supported Modes:**
- `metro` - Melbourne metropolitan trains
- `vline` - Regional trains and coaches
- `tram` - Melbourne trams
- `bus` - Metropolitan and regional buses

**Note:** Requires PTV API key to be configured.""",
    responses={
        200: {
            "description": "List of vehicle positions",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Found 42 vehicles",
                        "mode": "metro",
                        "count": 42,
                        "vehicles": [
                            {
                                "vehicle_id": "1234",
                                "latitude": -37.8136,
                                "longitude": 144.9631,
                                "timestamp": 1705300200,
                                "trip_id": "1-GEL-vpt-1.T1.1-MFSu-1",
                                "route_id": "1-GEL",
                                "speed_kmh": 85.0,
                                "current_status": "IN_TRANSIT_TO"
                            }
                        ]
                    }
                }
            }
        },
        503: {"description": "Realtime data unavailable (API key not configured)"}
    }
)
def get_all_vehicles(
    mode: str = Query(
        default="vline",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus'",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "vline", "tram", "bus"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> VehicleListResponse:
    """
    Get all vehicle positions for a transport mode.

    Args:
        mode: Transport mode ('metro', 'vline', 'tram', or 'bus')
        service: Transit service dependency

    Returns:
        VehicleListResponse with all vehicle positions
    """
    logger.info(f"Fetching all vehicle positions for mode: {mode}")

    try:
        parser = _get_parser(service)
        positions = parser.fetch_positions(mode=mode)

        vehicles = [_position_to_response(p) for p in positions]

        return VehicleListResponse(
            success=True,
            message=f"Found {len(vehicles)} vehicles",
            mode=mode,
            count=len(vehicles),
            vehicles=vehicles
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch vehicle positions: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch vehicle positions: {e}")


@router.get(
    "/summary",
    response_model=VehicleSummaryResponse,
    summary="Get Vehicle Summary",
    description="""Get aggregated statistics about vehicle positions for a transport mode.

Returns a summary including:
- Total number of vehicles in the feed
- Vehicles assigned to trips vs deadheading
- Vehicles in transit vs stopped at stations
- Average speed of moving vehicles

Useful for dashboards and monitoring.""",
    responses={
        200: {
            "description": "Vehicle position summary",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "mode": "metro",
                        "total_vehicles": 42,
                        "vehicles_with_trip": 38,
                        "vehicles_in_transit": 35,
                        "vehicles_at_stop": 7,
                        "average_speed_kmh": 45.2,
                        "timestamp": 1705300200
                    }
                }
            }
        },
        503: {"description": "Realtime data unavailable"}
    }
)
def get_vehicle_summary(
    mode: str = Query(
        default="vline",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus'",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "vline"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> VehicleSummaryResponse:
    """
    Get a summary of vehicle positions.

    Args:
        mode: Transport mode
        service: Transit service dependency

    Returns:
        VehicleSummaryResponse with aggregated statistics
    """
    logger.info(f"Fetching vehicle summary for mode: {mode}")

    try:
        parser = _get_parser(service)
        positions = parser.fetch_positions(mode=mode)
        summary = parser.get_summary(positions, mode=mode)

        return VehicleSummaryResponse(
            success=True,
            mode=mode,
            total_vehicles=summary.total_vehicles,
            vehicles_with_trip=summary.vehicles_with_trip,
            vehicles_in_transit=summary.vehicles_in_transit,
            vehicles_at_stop=summary.vehicles_at_stop,
            average_speed_kmh=summary.average_speed_kmh,
            timestamp=summary.timestamp
        )
    except Exception as e:
        logger.error(f"Failed to fetch vehicle summary: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch vehicle data: {e}")


@router.get(
    "/{vehicle_id}",
    response_model=VehiclePositionResponse,
    summary="Get Vehicle by ID",
    description="""Get detailed position information for a specific vehicle.

Returns the current GPS position, trip assignment, speed, bearing, and occupancy
information for a single vehicle identified by its ID.""",
    responses={
        200: {"description": "Vehicle position details"},
        404: {"description": "Vehicle not found in the specified mode's feed"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_vehicle_by_id(
    vehicle_id: str,
    mode: str = Query(
        default="vline",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus'",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "vline"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> VehiclePositionResponse:
    """
    Get position for a specific vehicle.

    Args:
        vehicle_id: Vehicle identifier
        mode: Transport mode
        service: Transit service dependency

    Returns:
        VehiclePositionResponse for the vehicle

    Raises:
        HTTPException: 404 if vehicle not found
    """
    logger.info(f"Fetching vehicle {vehicle_id} for mode: {mode}")

    try:
        parser = _get_parser(service)
        positions = parser.fetch_positions(mode=mode)
        vehicle = parser.get_vehicle_by_id(vehicle_id, positions)

        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle {vehicle_id} not found in {mode} feed"
            )

        return _position_to_response(vehicle)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch vehicle data: {e}")


@router.get(
    "/route/{route_id}",
    response_model=VehicleListResponse,
    summary="Get Vehicles on Route",
    description="""Get all vehicle positions currently operating on a specific route.

Filters vehicles by route ID and returns their real-time positions.
Useful for tracking all vehicles on a particular line.""",
    responses={
        200: {"description": "List of vehicles on the route"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_vehicles_for_route(
    route_id: str,
    mode: str = Query(
        default="vline",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus'",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "vline"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> VehicleListResponse:
    """
    Get all vehicles on a specific route.

    Args:
        route_id: Route identifier
        mode: Transport mode
        service: Transit service dependency

    Returns:
        VehicleListResponse with vehicles on the route
    """
    logger.info(f"Fetching vehicles for route {route_id} in mode: {mode}")

    try:
        parser = _get_parser(service)
        positions = parser.fetch_positions(mode=mode)
        route_vehicles = parser.get_vehicles_for_route(route_id, positions)

        vehicles = [_position_to_response(p) for p in route_vehicles]

        return VehicleListResponse(
            success=True,
            message=f"Found {len(vehicles)} vehicles on route {route_id}",
            mode=mode,
            count=len(vehicles),
            vehicles=vehicles
        )
    except Exception as e:
        logger.error(f"Failed to fetch vehicles for route {route_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch vehicle data: {e}")


@router.get(
    "/near/{stop_id}",
    response_model=VehicleListResponse,
    summary="Get Vehicles Near Stop",
    description="""Get vehicle positions within a specified radius of a stop.

Performs a geographic search to find all vehicles near a station or stop.
Results are sorted by distance from the stop. Useful for arrival predictions
and "vehicles approaching" displays.""",
    responses={
        200: {"description": "List of nearby vehicles sorted by distance"},
        404: {"description": "Stop not found"},
        503: {"description": "Realtime or GTFS data unavailable"}
    }
)
def get_vehicles_near_stop(
    stop_id: str,
    radius_km: float = Query(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Search radius in kilometers (0.1-10km)",
        examples=[0.5, 1.0, 2.0]
    ),
    mode: str = Query(
        default="vline",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus'",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "vline"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> VehicleListResponse:
    """
    Get vehicles near a specific stop.

    Args:
        stop_id: Stop identifier
        radius_km: Search radius in kilometers
        mode: Transport mode
        service: Transit service dependency

    Returns:
        VehicleListResponse with nearby vehicles sorted by distance

    Raises:
        HTTPException: 404 if stop not found
    """
    logger.info(f"Fetching vehicles within {radius_km}km of stop {stop_id}")

    # Get stop coordinates
    parser_gtfs = service.parser
    if not parser_gtfs:
        raise HTTPException(status_code=503, detail="GTFS data not available")

    stop = parser_gtfs.get_stop(stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail=f"Stop {stop_id} not found")

    try:
        parser = _get_parser(service)
        positions = parser.fetch_positions(mode=mode)
        nearby = parser.get_vehicles_near_stop(
            stop_lat=stop.stop_lat,
            stop_lon=stop.stop_lon,
            radius_km=radius_km,
            positions=positions
        )

        vehicles = [_position_to_response(p) for p in nearby]

        return VehicleListResponse(
            success=True,
            message=f"Found {len(vehicles)} vehicles within {radius_km}km of {stop.stop_name}",
            mode=mode,
            count=len(vehicles),
            vehicles=vehicles
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch vehicles near stop {stop_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch vehicle data: {e}")


@router.get(
    "/trip/{trip_id}",
    response_model=VehicleListResponse,
    summary="Get Vehicle for Trip",
    description="""Get the vehicle currently serving a specific GTFS trip.

Returns the vehicle assigned to a particular trip ID. Usually returns 0 or 1 vehicle.
Useful for correlating realtime vehicle data with scheduled trips.""",
    responses={
        200: {"description": "Vehicle serving the trip (may be empty if trip not active)"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_vehicle_for_trip(
    trip_id: str,
    mode: str = Query(
        default="vline",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus'",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "vline"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> VehicleListResponse:
    """
    Get the vehicle serving a specific trip.

    Args:
        trip_id: Trip identifier
        mode: Transport mode
        service: Transit service dependency

    Returns:
        VehicleListResponse (usually 0 or 1 vehicle)
    """
    logger.info(f"Fetching vehicle for trip {trip_id} in mode: {mode}")

    try:
        parser = _get_parser(service)
        positions = parser.fetch_positions(mode=mode)
        trip_vehicles = parser.get_vehicles_for_trip(trip_id, positions)

        vehicles = [_position_to_response(p) for p in trip_vehicles]

        return VehicleListResponse(
            success=True,
            message=f"Found {len(vehicles)} vehicle(s) for trip {trip_id}",
            mode=mode,
            count=len(vehicles),
            vehicles=vehicles
        )
    except Exception as e:
        logger.error(f"Failed to fetch vehicle for trip {trip_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch vehicle data: {e}")
