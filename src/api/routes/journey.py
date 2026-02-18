"""
Journey planning endpoint.

Provides journey planning functionality with optional realtime integration.
Supports multi-leg journeys with transfer handling.
"""

from fastapi import APIRouter, Depends, HTTPException, Body

from ..models import (
    JourneyPlanRequest,
    JourneyPlanResponse,
    JourneyResponse,
    LegResponse,
    ErrorResponse
)
from ..dependencies import get_transit_service, TransitService
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/journey", tags=["journey"])


def _resolve_stop_id(
    stop_input: str,
    service: TransitService
) -> str:
    """
    Resolve a stop name or ID to a stop ID.

    Args:
        stop_input: Stop name or ID
        service: Transit service

    Returns:
        Stop ID

    Raises:
        ValueError: If stop not found
    """
    parser = service.parser
    stop_index = service.stop_index

    # Check if it's already a valid stop ID
    if parser and parser.get_stop(stop_input):
        return stop_input

    # Try to find by name
    if stop_index:
        stop = stop_index.find_stop(stop_input, fuzzy=True)
        if stop:
            return stop.stop_id

    raise ValueError(f"Stop not found: {stop_input}")


def _journey_to_response(journey) -> JourneyResponse:
    """
    Convert internal Journey object to JourneyResponse.

    Args:
        journey: Internal Journey object

    Returns:
        JourneyResponse for API
    """
    legs = []
    for leg in journey.legs:
        leg_response = LegResponse(
            from_stop_id=leg.from_stop_id,
            from_stop_name=leg.from_stop_name,
            to_stop_id=leg.to_stop_id,
            to_stop_name=leg.to_stop_name,
            departure_time=leg.departure_time,
            arrival_time=leg.arrival_time,
            trip_id=leg.trip_id,
            route_id=leg.route_id,
            route_name=leg.route_name,
            mode=leg.get_mode_name() if hasattr(leg, 'get_mode_name') else None,
            num_stops=leg.num_stops,
            scheduled_departure_time=leg.scheduled_departure_time,
            actual_departure_time=leg.actual_departure_time,
            scheduled_arrival_time=leg.scheduled_arrival_time,
            actual_arrival_time=leg.actual_arrival_time,
            departure_delay_seconds=leg.departure_delay_seconds,
            arrival_delay_seconds=leg.arrival_delay_seconds,
            is_cancelled=leg.is_cancelled,
            platform_name=leg.platform_name,
            has_realtime_data=leg.has_realtime_data
        )
        legs.append(leg_response)

    # Calculate duration
    duration_minutes = journey.get_duration_minutes() if hasattr(journey, 'get_duration_minutes') else 0

    # Get modes used
    modes_used = journey.get_modes_used() if hasattr(journey, 'get_modes_used') else []
    is_multi_modal = journey.is_multi_modal() if hasattr(journey, 'is_multi_modal') else False

    # Realtime info
    has_realtime = any(leg.has_realtime_data for leg in journey.legs)
    total_delay = sum(leg.arrival_delay_seconds for leg in journey.legs if leg.has_realtime_data)

    return JourneyResponse(
        origin_stop_id=journey.origin_stop_id,
        origin_stop_name=journey.origin_stop_name,
        destination_stop_id=journey.destination_stop_id,
        destination_stop_name=journey.destination_stop_name,
        departure_time=journey.departure_time,
        arrival_time=journey.arrival_time,
        duration_minutes=duration_minutes,
        num_transfers=journey.get_num_transfers() if hasattr(journey, 'get_num_transfers') else len(legs) - 1,
        legs=legs,
        modes_used=modes_used,
        is_multi_modal=is_multi_modal,
        has_realtime_data=has_realtime,
        total_delay_seconds=total_delay,
        is_valid=journey.is_valid if hasattr(journey, 'is_valid') else True,
        validity_message=journey.validity_message if hasattr(journey, 'validity_message') else None
    )


@router.post(
    "/plan",
    response_model=JourneyPlanResponse,
    responses={
        200: {
            "description": "Journey plan found",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Journey found",
                        "journey": {
                            "origin_stop_id": "47648",
                            "origin_stop_name": "Tarneit Station",
                            "destination_stop_id": "47641",
                            "destination_stop_name": "Waurn Ponds Station",
                            "departure_time": "14:57:00",
                            "arrival_time": "15:48:00",
                            "duration_minutes": 51,
                            "num_transfers": 0,
                            "legs": [
                                {
                                    "from_stop_id": "47648",
                                    "from_stop_name": "Tarneit Station",
                                    "to_stop_id": "47641",
                                    "to_stop_name": "Waurn Ponds Station",
                                    "departure_time": "14:57:00",
                                    "arrival_time": "15:48:00",
                                    "trip_id": "1-GEL-vpt-1.T1.1-MFSu-1",
                                    "route_id": "1-GEL",
                                    "route_name": "Geelong Line",
                                    "mode": "rail"
                                }
                            ],
                            "modes_used": ["rail"],
                            "is_multi_modal": False
                        },
                        "alternatives": []
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Origin or destination stop not found"},
        503: {"description": "Journey planner not available"}
    },
    summary="Plan Journey",
    description="""Plan a journey between two stops with optional realtime information.

**Features:**
- Accepts stop names (with fuzzy matching) or stop IDs
- Supports multi-leg journeys with configurable transfer limits
- Optional realtime delay and cancellation information

**Request Body:**
- `origin`: Origin stop name or ID (e.g., "Tarneit Station" or "47648")
- `destination`: Destination stop name or ID
- `departure_time`: Departure time in HH:MM:SS format
- `include_realtime`: Include live delay/cancellation data (requires PTV API key)
- `max_transfers`: Maximum transfers allowed (0-5, default 3)

**Response:**
Returns the best journey option with detailed leg-by-leg information."""
)
def plan_journey(
    request: JourneyPlanRequest = Body(
        ...,
        examples=[
            {
                "origin": "Tarneit Station",
                "destination": "Waurn Ponds Station",
                "departure_time": "14:00:00",
                "include_realtime": False,
                "max_transfers": 3
            }
        ]
    ),
    service: TransitService = Depends(get_transit_service)
) -> JourneyPlanResponse:
    """
    Plan a journey between two stops.

    Args:
        request: Journey planning request
        service: Transit service dependency

    Returns:
        JourneyPlanResponse with journey details
    """
    logger.info(
        f"Planning journey: {request.origin} -> {request.destination} "
        f"at {request.departure_time}"
    )

    planner = service.planner
    if not planner:
        raise HTTPException(status_code=503, detail="Journey planner not available")

    # Resolve stop names to IDs
    try:
        origin_id = _resolve_stop_id(request.origin, service)
        destination_id = _resolve_stop_id(request.destination, service)
    except ValueError as e:
        return JourneyPlanResponse(
            success=False,
            message=str(e),
            journey=None
        )

    # Find journey
    try:
        journey = planner.find_journey(
            origin_stop_id=origin_id,
            destination_stop_id=destination_id,
            departure_time=request.departure_time,
            max_transfers=request.max_transfers
        )
    except ValueError as e:
        return JourneyPlanResponse(
            success=False,
            message=str(e),
            journey=None
        )

    if not journey:
        return JourneyPlanResponse(
            success=False,
            message=f"No journey found from {request.origin} to {request.destination}",
            journey=None
        )

    # Apply realtime updates if requested
    if request.include_realtime:
        integrator = service.get_realtime_integrator()
        if integrator:
            try:
                journey = integrator.apply_realtime_to_journey(journey)
                logger.debug("Applied realtime updates to journey")
            except Exception as e:
                logger.warning(f"Failed to apply realtime updates: {e}")

    # Convert to response
    journey_response = _journey_to_response(journey)

    logger.info(
        f"Journey found: {journey_response.departure_time} -> {journey_response.arrival_time}, "
        f"{journey_response.duration_minutes} min, {journey_response.num_transfers} transfer(s)"
    )

    return JourneyPlanResponse(
        success=True,
        message="Journey found",
        journey=journey_response
    )
