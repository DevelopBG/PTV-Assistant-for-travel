"""
Service Alerts API endpoints - Phase 9

Provides service alert information from GTFS Realtime feeds.
Supports metro and tram modes (PTV limitation: bus/vline have no alerts feed).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any

from ..dependencies import get_transit_service, TransitService
from ...utils.logging_config import get_logger
from ...realtime.service_alerts import ServiceAlertParser
from ...realtime.models import ServiceAlert as ServiceAlertModel, AlertSeverity, AlertEffect
from ...realtime.modes import has_service_alerts
from pydantic import BaseModel, Field, ConfigDict

logger = get_logger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ============== Response Models ==============

class InformedEntityResponse(BaseModel):
    """Response model for an entity affected by an alert."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agency_id": None,
                "route_id": "1-CRL",
                "route_type": 2,
                "stop_id": None,
                "trip_id": None,
                "direction_id": None,
                "description": "Route: 1-CRL"
            }
        }
    )

    agency_id: Optional[str] = Field(None, description="Agency ID if alert affects entire agency")
    route_id: Optional[str] = Field(None, description="Route ID if alert affects a specific route")
    route_type: Optional[int] = Field(None, description="GTFS route type (0=tram, 1=metro, 2=rail)")
    stop_id: Optional[str] = Field(None, description="Stop ID if alert affects a specific stop")
    trip_id: Optional[str] = Field(None, description="Trip ID if alert affects a specific trip")
    direction_id: Optional[int] = Field(None, description="Direction ID (0 or 1)")
    description: str = Field(..., description="Human-readable description of affected entity")


class ActivePeriodResponse(BaseModel):
    """Response model for an alert's active time period."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start": 1705300200,
                "end": 1705386600
            }
        }
    )

    start: Optional[int] = Field(None, description="Start time (Unix timestamp), null = already active")
    end: Optional[int] = Field(None, description="End time (Unix timestamp), null = no scheduled end")


class ServiceAlertResponse(BaseModel):
    """Response model for a single service alert."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "alert_id": "12345",
                "cause": "CONSTRUCTION",
                "effect": "REDUCED_SERVICE",
                "severity": "WARNING",
                "header_text": "Track works: Cranbourne Line",
                "description_text": "Buses replace trains between Dandenong and Cranbourne from 8pm Friday to last service Sunday.",
                "url": "https://ptv.vic.gov.au/disruptions",
                "active_periods": [{"start": 1705300200, "end": 1705386600}],
                "informed_entities": [{"route_id": "1-CRB", "description": "Route: Cranbourne Line"}],
                "affected_routes": ["1-CRB"],
                "affected_stops": [],
                "timestamp": 1705300000
            }
        }
    )

    alert_id: str = Field(..., description="Unique alert identifier")
    cause: str = Field(..., description="Cause of the disruption (e.g., CONSTRUCTION, ACCIDENT, WEATHER)")
    effect: str = Field(..., description="Effect on service (e.g., REDUCED_SERVICE, NO_SERVICE, DETOUR)")
    severity: str = Field(..., description="Severity level: INFO, WARNING, SEVERE")

    header_text: Optional[str] = Field(None, description="Short description/headline")
    description_text: Optional[str] = Field(None, description="Full description with details")
    url: Optional[str] = Field(None, description="Link for more information")

    active_periods: List[ActivePeriodResponse] = Field(default_factory=list, description="Time periods when alert is active")
    informed_entities: List[InformedEntityResponse] = Field(default_factory=list, description="Routes/stops/trips affected")
    affected_routes: List[str] = Field(default_factory=list, description="List of affected route IDs")
    affected_stops: List[str] = Field(default_factory=list, description="List of affected stop IDs")

    timestamp: Optional[int] = Field(None, description="When alert was fetched (Unix timestamp)")


class AlertListResponse(BaseModel):
    """Response model for a list of service alerts."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Found 5 active alerts",
                "mode": "metro",
                "count": 5,
                "alerts": []
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Human-readable response message")
    mode: str = Field(..., description="Transport mode queried")
    count: int = Field(..., description="Number of alerts returned")
    alerts: List[ServiceAlertResponse] = Field(..., description="List of service alerts")


class AlertSummaryResponse(BaseModel):
    """Response model for service alert summary statistics."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "mode": "metro",
                "total_alerts": 12,
                "by_severity": {"INFO": 5, "WARNING": 6, "SEVERE": 1},
                "by_effect": {"REDUCED_SERVICE": 4, "MODIFIED_SERVICE": 5, "OTHER_EFFECT": 3},
                "affected_routes": ["1-CRB", "1-SDM", "1-PKM"],
                "affected_stops": ["19842", "19843"],
                "timestamp": 1705300000
            }
        }
    )

    success: bool = Field(..., description="Whether the request was successful")
    mode: str = Field(..., description="Transport mode queried")
    total_alerts: int = Field(..., description="Total number of alerts")
    by_severity: Dict[str, int] = Field(default_factory=dict, description="Count of alerts by severity level")
    by_effect: Dict[str, int] = Field(default_factory=dict, description="Count of alerts by effect type")
    affected_routes: List[str] = Field(default_factory=list, description="All routes with active alerts")
    affected_stops: List[str] = Field(default_factory=list, description="All stops with active alerts")
    timestamp: Optional[int] = Field(None, description="Feed timestamp (Unix)")


# ============== Helper Functions ==============

def _alert_to_response(alert: ServiceAlertModel) -> ServiceAlertResponse:
    """Convert internal ServiceAlert to API response model."""
    active_periods = [
        ActivePeriodResponse(start=p.start, end=p.end)
        for p in alert.active_periods
    ]

    informed_entities = [
        InformedEntityResponse(
            agency_id=e.agency_id,
            route_id=e.route_id,
            route_type=e.route_type,
            stop_id=e.stop_id,
            trip_id=e.trip_id,
            direction_id=e.direction_id,
            description=e.get_description()
        )
        for e in alert.informed_entities
    ]

    return ServiceAlertResponse(
        alert_id=alert.alert_id,
        cause=alert.cause.value,
        effect=alert.effect.value,
        severity=alert.severity.value,
        header_text=alert.header_text,
        description_text=alert.description_text,
        url=alert.url,
        active_periods=active_periods,
        informed_entities=informed_entities,
        affected_routes=alert.get_affected_routes(),
        affected_stops=alert.get_affected_stops(),
        timestamp=alert.timestamp
    )


def _get_parser(service: TransitService) -> ServiceAlertParser:
    """Get or create a ServiceAlertParser instance."""
    fetcher = service.get_realtime_fetcher()
    if not fetcher:
        raise HTTPException(
            status_code=503,
            detail="Realtime data not available. PTV API key may not be configured."
        )
    return ServiceAlertParser(fetcher=fetcher)


# ============== Endpoints ==============

@router.get(
    "",
    response_model=AlertListResponse,
    summary="Get All Service Alerts",
    description="""Fetch all service alerts for a transport mode.

**Important:** Only `metro` and `tram` modes have service alert feeds from PTV.
Requests for `bus` or `vline` will return an empty list gracefully.

Alerts include disruptions, delays, track works, and service changes.
Use `active_only=true` (default) to filter out expired alerts.""",
    responses={
        200: {
            "description": "List of service alerts",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Found 5 active alerts",
                        "mode": "metro",
                        "count": 5,
                        "alerts": [
                            {
                                "alert_id": "12345",
                                "cause": "CONSTRUCTION",
                                "effect": "REDUCED_SERVICE",
                                "severity": "WARNING",
                                "header_text": "Track works: Cranbourne Line"
                            }
                        ]
                    }
                }
            }
        },
        503: {"description": "Realtime data unavailable (API key not configured)"}
    }
)
def get_all_alerts(
    mode: str = Query(
        default="metro",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus' (alerts only available for metro/tram)",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "tram"]
    ),
    active_only: bool = Query(
        default=True,
        description="Only return currently active alerts (recommended)"
    ),
    service: TransitService = Depends(get_transit_service)
) -> AlertListResponse:
    """
    Get all service alerts for a transport mode.

    Args:
        mode: Transport mode ('metro', 'vline', 'tram', or 'bus')
        active_only: If True, only return currently active alerts
        service: Transit service dependency

    Returns:
        AlertListResponse with all alerts
    """
    logger.info(f"Fetching service alerts for mode: {mode}")

    try:
        parser = _get_parser(service)
        alerts = parser.fetch_alerts(mode=mode)

        if active_only:
            alerts = parser.get_active_alerts(alerts)

        alert_responses = [_alert_to_response(a) for a in alerts]

        return AlertListResponse(
            success=True,
            message=f"Found {len(alert_responses)} {'active ' if active_only else ''}alerts",
            mode=mode,
            count=len(alert_responses),
            alerts=alert_responses
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch service alerts: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch service alerts: {e}")


@router.get(
    "/summary",
    response_model=AlertSummaryResponse,
    summary="Get Alert Summary",
    description="""Get aggregated statistics about service alerts for a transport mode.

Returns counts grouped by severity (INFO, WARNING, SEVERE) and effect type,
plus lists of all affected routes and stops. Useful for dashboards.""",
    responses={
        200: {"description": "Alert summary statistics"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_alert_summary(
    mode: str = Query(
        default="metro",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus' (alerts only for metro/tram)",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "tram"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> AlertSummaryResponse:
    """
    Get a summary of service alerts.

    Args:
        mode: Transport mode
        service: Transit service dependency

    Returns:
        AlertSummaryResponse with aggregated statistics
    """
    logger.info(f"Fetching alert summary for mode: {mode}")

    try:
        parser = _get_parser(service)
        alerts = parser.fetch_alerts(mode=mode)
        summary = parser.get_summary(alerts, mode=mode)

        return AlertSummaryResponse(
            success=True,
            mode=mode,
            total_alerts=summary.total_alerts,
            by_severity=summary.by_severity,
            by_effect=summary.by_effect,
            affected_routes=summary.affected_routes,
            affected_stops=summary.affected_stops,
            timestamp=summary.timestamp
        )
    except Exception as e:
        logger.error(f"Failed to fetch alert summary: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch alert data: {e}")


@router.get(
    "/{alert_id}",
    response_model=ServiceAlertResponse,
    summary="Get Alert by ID",
    description="""Get detailed information for a specific service alert by its ID.

Returns full alert details including description, affected entities, and active periods.""",
    responses={
        200: {"description": "Alert details"},
        404: {"description": "Alert not found in the specified mode's feed"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_alert_by_id(
    alert_id: str,
    mode: str = Query(
        default="metro",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus' (alerts only for metro/tram)",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "tram"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> ServiceAlertResponse:
    """
    Get a specific alert by ID.

    Args:
        alert_id: Alert identifier
        mode: Transport mode
        service: Transit service dependency

    Returns:
        ServiceAlertResponse for the alert

    Raises:
        HTTPException: 404 if alert not found
    """
    logger.info(f"Fetching alert {alert_id} for mode: {mode}")

    try:
        parser = _get_parser(service)
        alerts = parser.fetch_alerts(mode=mode)
        alert = parser.get_alert_by_id(alert_id, alerts)

        if not alert:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found in {mode} feed"
            )

        return _alert_to_response(alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch alert {alert_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch alert data: {e}")


@router.get(
    "/route/{route_id}",
    response_model=AlertListResponse,
    summary="Get Alerts for Route",
    description="""Get all service alerts affecting a specific route.

Filters alerts to only those that mention the given route ID in their
informed entities. Useful for showing disruptions on a specific line.""",
    responses={
        200: {"description": "List of alerts affecting the route"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_alerts_for_route(
    route_id: str,
    mode: str = Query(
        default="metro",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus' (alerts only for metro/tram)",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "tram"]
    ),
    active_only: bool = Query(
        default=True,
        description="Only return currently active alerts"
    ),
    service: TransitService = Depends(get_transit_service)
) -> AlertListResponse:
    """
    Get alerts affecting a specific route.

    Args:
        route_id: Route identifier
        mode: Transport mode
        active_only: If True, only return currently active alerts
        service: Transit service dependency

    Returns:
        AlertListResponse with alerts affecting the route
    """
    logger.info(f"Fetching alerts for route {route_id} in mode: {mode}")

    try:
        parser = _get_parser(service)
        alerts = parser.fetch_alerts(mode=mode)
        route_alerts = parser.get_alerts_for_route(route_id, alerts)

        if active_only:
            route_alerts = parser.get_active_alerts(route_alerts)

        alert_responses = [_alert_to_response(a) for a in route_alerts]

        return AlertListResponse(
            success=True,
            message=f"Found {len(alert_responses)} alerts for route {route_id}",
            mode=mode,
            count=len(alert_responses),
            alerts=alert_responses
        )
    except Exception as e:
        logger.error(f"Failed to fetch alerts for route {route_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch alert data: {e}")


@router.get(
    "/stop/{stop_id}",
    response_model=AlertListResponse,
    summary="Get Alerts for Stop",
    description="""Get all service alerts affecting a specific stop.

Filters alerts to only those that mention the given stop ID in their
informed entities. Useful for station-specific disruption displays.""",
    responses={
        200: {"description": "List of alerts affecting the stop"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_alerts_for_stop(
    stop_id: str,
    mode: str = Query(
        default="metro",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus' (alerts only for metro/tram)",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "tram"]
    ),
    active_only: bool = Query(
        default=True,
        description="Only return currently active alerts"
    ),
    service: TransitService = Depends(get_transit_service)
) -> AlertListResponse:
    """
    Get alerts affecting a specific stop.

    Args:
        stop_id: Stop identifier
        mode: Transport mode
        active_only: If True, only return currently active alerts
        service: Transit service dependency

    Returns:
        AlertListResponse with alerts affecting the stop
    """
    logger.info(f"Fetching alerts for stop {stop_id} in mode: {mode}")

    try:
        parser = _get_parser(service)
        alerts = parser.fetch_alerts(mode=mode)
        stop_alerts = parser.get_alerts_for_stop(stop_id, alerts)

        if active_only:
            stop_alerts = parser.get_active_alerts(stop_alerts)

        alert_responses = [_alert_to_response(a) for a in stop_alerts]

        return AlertListResponse(
            success=True,
            message=f"Found {len(alert_responses)} alerts for stop {stop_id}",
            mode=mode,
            count=len(alert_responses),
            alerts=alert_responses
        )
    except Exception as e:
        logger.error(f"Failed to fetch alerts for stop {stop_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch alert data: {e}")


@router.get(
    "/severity/{severity}",
    response_model=AlertListResponse,
    summary="Get Alerts by Severity",
    description="""Get all service alerts of a specific severity level.

**Severity levels:**
- `INFO` - Informational notices, minor changes
- `WARNING` - Significant disruptions, delays
- `SEVERE` - Major disruptions, service cancellations""",
    responses={
        200: {"description": "List of alerts matching the severity"},
        400: {"description": "Invalid severity level"},
        503: {"description": "Realtime data unavailable"}
    }
)
def get_alerts_by_severity(
    severity: str,
    mode: str = Query(
        default="metro",
        description="Transport mode: 'metro', 'vline', 'tram', or 'bus' (alerts only for metro/tram)",
        pattern="^(metro|vline|tram|bus)$",
        examples=["metro", "tram"]
    ),
    service: TransitService = Depends(get_transit_service)
) -> AlertListResponse:
    """
    Get alerts by severity level.

    Args:
        severity: Severity level (INFO, WARNING, SEVERE, UNKNOWN_SEVERITY)
        mode: Transport mode
        service: Transit service dependency

    Returns:
        AlertListResponse with alerts of matching severity
    """
    logger.info(f"Fetching alerts with severity {severity} for mode: {mode}")

    # Validate severity
    try:
        sev = AlertSeverity(severity.upper())
    except ValueError:
        valid = [s.value for s in AlertSeverity]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity '{severity}'. Must be one of: {valid}"
        )

    try:
        parser = _get_parser(service)
        alerts = parser.fetch_alerts(mode=mode)
        severity_alerts = parser.get_alerts_by_severity(sev, alerts)

        alert_responses = [_alert_to_response(a) for a in severity_alerts]

        return AlertListResponse(
            success=True,
            message=f"Found {len(alert_responses)} {severity} alerts",
            mode=mode,
            count=len(alert_responses),
            alerts=alert_responses
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch alerts by severity: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch alert data: {e}")
