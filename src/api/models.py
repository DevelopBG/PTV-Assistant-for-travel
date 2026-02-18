"""
Pydantic models for API request/response validation.

These models define the schema for API endpoints with comprehensive
examples for OpenAPI documentation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union
from datetime import datetime


# ============== Request Models ==============

class JourneyPlanRequest(BaseModel):
    """Request model for journey planning."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "origin": "Tarneit Station",
                    "destination": "Waurn Ponds Station",
                    "departure_time": "14:00:00",
                    "include_realtime": False,
                    "max_transfers": 3
                },
                {
                    "origin": "47648",
                    "destination": "47641",
                    "departure_time": "08:30:00",
                    "include_realtime": True,
                    "max_transfers": 2
                }
            ]
        }
    )

    origin: str = Field(
        ...,
        description="Origin stop name or ID. Can be a station name (e.g., 'Tarneit Station') or numeric stop ID (e.g., '47648').",
        examples=["Tarneit Station", "47648"]
    )
    destination: str = Field(
        ...,
        description="Destination stop name or ID. Can be a station name (e.g., 'Waurn Ponds Station') or numeric stop ID (e.g., '47641').",
        examples=["Waurn Ponds Station", "47641"]
    )
    departure_time: str = Field(
        ...,
        description="Departure time in HH:MM:SS format (24-hour). Must be a valid time within the service day.",
        examples=["14:00:00", "08:30:00"]
    )
    include_realtime: bool = Field(
        default=False,
        description="Include real-time delay and cancellation information from GTFS-Realtime feeds. Requires PTV_API_KEY environment variable."
    )
    max_transfers: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum number of transfers (connections) allowed in the journey. Set to 0 for direct services only."
    )


class StopSearchRequest(BaseModel):
    """Request model for stop search."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "Tarneit",
                    "limit": 5,
                    "fuzzy": True
                },
                {
                    "query": "Southern Cross",
                    "limit": 10,
                    "fuzzy": False
                }
            ]
        }
    )

    query: str = Field(
        ...,
        min_length=2,
        description="Search query for stop name. Minimum 2 characters. Supports partial matching and fuzzy search.",
        examples=["Tarneit", "Southern Cross", "Flinders"]
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results to return. Defaults to 5, maximum 20."
    )
    fuzzy: bool = Field(
        default=True,
        description="Use fuzzy matching for search. When enabled, handles typos and partial matches. Disable for exact prefix matching."
    )


# ============== Response Models ==============

class StopResponse(BaseModel):
    """Response model for a single stop."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stop_id": "47648",
                "stop_name": "Tarneit Station",
                "stop_lat": -37.832,
                "stop_lon": 144.694,
                "match_score": 100
            }
        }
    )

    stop_id: str = Field(..., description="Unique stop identifier from GTFS data")
    stop_name: str = Field(..., description="Human-readable stop name")
    stop_lat: Optional[Union[str, float]] = Field(None, description="Latitude coordinate (WGS84)")
    stop_lon: Optional[Union[str, float]] = Field(None, description="Longitude coordinate (WGS84)")
    match_score: Optional[int] = Field(
        None,
        description="Fuzzy match score (0-100). Only present in search results. 100 = exact match."
    )


class LegResponse(BaseModel):
    """Response model for a journey leg (single trip segment)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "from_stop_id": "47648",
                "from_stop_name": "Tarneit Station",
                "to_stop_id": "47649",
                "to_stop_name": "Wyndham Vale Station",
                "departure_time": "14:57:00",
                "arrival_time": "15:02:00",
                "trip_id": "1-GEL-vpt-1.T1.1-MFSu-1",
                "route_id": "1-GEL",
                "route_name": "Geelong Line",
                "mode": "rail",
                "num_stops": 2,
                "scheduled_departure_time": "14:57:00",
                "actual_departure_time": "14:59:00",
                "departure_delay_seconds": 120,
                "arrival_delay_seconds": 90,
                "is_cancelled": False,
                "platform_name": "Platform 1",
                "has_realtime_data": True
            }
        }
    )

    from_stop_id: str = Field(..., description="Origin stop ID for this leg")
    from_stop_name: str = Field(..., description="Origin stop name")
    to_stop_id: str = Field(..., description="Destination stop ID for this leg")
    to_stop_name: str = Field(..., description="Destination stop name")
    departure_time: str = Field(..., description="Scheduled departure time (HH:MM:SS)")
    arrival_time: str = Field(..., description="Scheduled arrival time (HH:MM:SS)")
    trip_id: str = Field(..., description="GTFS trip identifier")
    route_id: str = Field(..., description="GTFS route identifier")
    route_name: Optional[str] = Field(None, description="Human-readable route name")
    mode: Optional[str] = Field(None, description="Transport mode (rail, bus, tram, ferry)")
    num_stops: int = Field(0, description="Number of stops on this leg")

    # Realtime fields
    scheduled_departure_time: Optional[str] = Field(None, description="Originally scheduled departure time")
    actual_departure_time: Optional[str] = Field(None, description="Actual/predicted departure time from realtime feed")
    scheduled_arrival_time: Optional[str] = Field(None, description="Originally scheduled arrival time")
    actual_arrival_time: Optional[str] = Field(None, description="Actual/predicted arrival time from realtime feed")
    departure_delay_seconds: int = Field(0, description="Departure delay in seconds (positive = late)")
    arrival_delay_seconds: int = Field(0, description="Arrival delay in seconds (positive = late)")
    is_cancelled: bool = Field(False, description="Whether this trip is cancelled")
    platform_name: Optional[str] = Field(None, description="Platform/stop position information")
    has_realtime_data: bool = Field(False, description="Whether realtime data is available for this leg")


class JourneyResponse(BaseModel):
    """Response model for a complete journey (may have multiple legs)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_stop_id": "47648",
                "origin_stop_name": "Tarneit Station",
                "destination_stop_id": "47641",
                "destination_stop_name": "Waurn Ponds Station",
                "departure_time": "14:57:00",
                "arrival_time": "15:48:00",
                "duration_minutes": 51,
                "num_transfers": 0,
                "legs": [],
                "modes_used": ["rail"],
                "is_multi_modal": False,
                "has_realtime_data": False,
                "total_delay_seconds": 0,
                "is_valid": True,
                "validity_message": None
            }
        }
    )

    origin_stop_id: str = Field(..., description="Journey origin stop ID")
    origin_stop_name: str = Field(..., description="Journey origin stop name")
    destination_stop_id: str = Field(..., description="Journey destination stop ID")
    destination_stop_name: str = Field(..., description="Journey destination stop name")
    departure_time: str = Field(..., description="Journey start time (HH:MM:SS)")
    arrival_time: str = Field(..., description="Journey end time (HH:MM:SS)")
    duration_minutes: int = Field(..., description="Total journey duration in minutes")
    num_transfers: int = Field(..., description="Number of transfers required")
    legs: List[LegResponse] = Field(..., description="List of journey legs (trip segments)")
    modes_used: List[str] = Field(default=[], description="Transport modes used (e.g., ['rail', 'bus'])")
    is_multi_modal: bool = Field(False, description="Whether journey uses multiple transport modes")

    # Realtime fields
    has_realtime_data: bool = Field(False, description="Whether any leg has realtime data")
    total_delay_seconds: int = Field(0, description="Cumulative delay across all legs")
    is_valid: bool = Field(True, description="Whether journey is still valid (no cancellations)")
    validity_message: Optional[str] = Field(None, description="Explanation if journey is invalid")


class JourneyPlanResponse(BaseModel):
    """Response model for journey planning endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Found 3 journey options",
                "journey": None,
                "alternatives": []
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable response message")
    journey: Optional[JourneyResponse] = Field(None, description="Best journey option")
    alternatives: List[JourneyResponse] = Field(default=[], description="Alternative journey options")


class StopSearchResponse(BaseModel):
    """Response model for stop search endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Found 3 stops matching 'Tarneit'",
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
    )

    success: bool = Field(..., description="Whether the search was successful")
    message: str = Field(..., description="Human-readable response message")
    query: str = Field(..., description="Original search query")
    count: int = Field(..., description="Number of stops found")
    stops: List[StopResponse] = Field(..., description="List of matching stops")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "gtfs_loaded": True,
                "stops_count": 497,
                "routes_count": 13,
                "trips_count": 8096,
                "timestamp": "2026-01-15T10:30:00"
            }
        }
    )

    status: str = Field(..., description="Service status: 'healthy' or 'unhealthy'")
    version: str = Field(..., description="API version number")
    gtfs_loaded: bool = Field(..., description="Whether GTFS static data has been loaded")
    stops_count: int = Field(0, description="Number of stops loaded from GTFS")
    routes_count: int = Field(0, description="Number of routes loaded from GTFS")
    trips_count: int = Field(0, description="Number of trips loaded from GTFS")
    timestamp: str = Field(..., description="Current server timestamp (ISO 8601)")


class ErrorResponse(BaseModel):
    """Response model for error responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "Stop not found",
                "detail": "No stop found with ID '99999'"
            }
        }
    )

    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type or category")
    detail: Optional[str] = Field(None, description="Detailed error message")
