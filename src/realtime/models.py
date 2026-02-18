"""
Realtime data models for GTFS Realtime entities.

These dataclasses represent GTFS Realtime data structures including
vehicle positions, service alerts, and related entities.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


class VehicleStopStatus(Enum):
    """Vehicle's relationship to a stop."""
    INCOMING_AT = "INCOMING_AT"      # Vehicle is about to arrive at the stop
    STOPPED_AT = "STOPPED_AT"        # Vehicle is standing at the stop
    IN_TRANSIT_TO = "IN_TRANSIT_TO"  # Vehicle has departed previous stop, en route


class CongestionLevel(Enum):
    """Congestion level affecting the vehicle."""
    UNKNOWN_CONGESTION_LEVEL = "UNKNOWN"
    RUNNING_SMOOTHLY = "RUNNING_SMOOTHLY"
    STOP_AND_GO = "STOP_AND_GO"
    CONGESTION = "CONGESTION"
    SEVERE_CONGESTION = "SEVERE_CONGESTION"


class OccupancyStatus(Enum):
    """Passenger occupancy status of the vehicle."""
    EMPTY = "EMPTY"
    MANY_SEATS_AVAILABLE = "MANY_SEATS_AVAILABLE"
    FEW_SEATS_AVAILABLE = "FEW_SEATS_AVAILABLE"
    STANDING_ROOM_ONLY = "STANDING_ROOM_ONLY"
    CRUSHED_STANDING_ROOM_ONLY = "CRUSHED_STANDING_ROOM_ONLY"
    FULL = "FULL"
    NOT_ACCEPTING_PASSENGERS = "NOT_ACCEPTING_PASSENGERS"


@dataclass
class VehiclePosition:
    """
    Represents a real-time vehicle position from GTFS Realtime.

    Contains location, status, and trip information for a single vehicle.
    """
    vehicle_id: str
    latitude: float
    longitude: float
    timestamp: int  # Unix timestamp

    # Trip information
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    direction_id: Optional[int] = None

    # Vehicle details
    label: Optional[str] = None  # Human-readable vehicle label (e.g., "Train 123")
    license_plate: Optional[str] = None

    # Position details
    bearing: Optional[float] = None  # Direction of travel in degrees (0-360)
    speed: Optional[float] = None    # Speed in meters per second
    odometer: Optional[float] = None # Odometer value in meters

    # Stop relationship
    stop_id: Optional[str] = None
    current_stop_sequence: Optional[int] = None
    current_status: Optional[VehicleStopStatus] = None

    # Crowding information
    congestion_level: Optional[CongestionLevel] = None
    occupancy_status: Optional[OccupancyStatus] = None
    occupancy_percentage: Optional[int] = None  # 0-100

    def get_status_display(self) -> str:
        """
        Get human-readable status display.

        Returns:
            Status string like "Stopped at stop 47648" or "In transit"
        """
        if self.current_status is None:
            return "Unknown"

        status_text = self.current_status.value.replace("_", " ").title()

        if self.stop_id:
            return f"{status_text} stop {self.stop_id}"
        return status_text

    def get_speed_kmh(self) -> Optional[float]:
        """
        Get speed in km/h.

        Returns:
            Speed in km/h or None if speed not available
        """
        if self.speed is not None:
            return round(self.speed * 3.6, 1)
        return None

    def get_occupancy_display(self) -> str:
        """
        Get human-readable occupancy status.

        Returns:
            Occupancy string like "Many seats available"
        """
        if self.occupancy_status is None:
            return "Unknown"
        return self.occupancy_status.value.replace("_", " ").title()

    def has_location(self) -> bool:
        """
        Check if vehicle has valid location data.

        Returns:
            True if latitude and longitude are valid
        """
        return (
            self.latitude is not None and
            self.longitude is not None and
            -90 <= self.latitude <= 90 and
            -180 <= self.longitude <= 180
        )


@dataclass
class VehiclePositionSummary:
    """
    Summary of vehicle positions for a route or area.

    Provides aggregated statistics about vehicle positions.
    """
    total_vehicles: int
    vehicles_with_trip: int
    vehicles_in_transit: int
    vehicles_at_stop: int
    average_speed_kmh: Optional[float] = None
    timestamp: Optional[int] = None

    # Mode information
    mode: Optional[str] = None  # 'metro', 'vline', 'tram', 'bus'
    route_id: Optional[str] = None


# ============== Service Alert Enums ==============

class AlertCause(Enum):
    """Cause of the service alert."""
    UNKNOWN_CAUSE = "UNKNOWN_CAUSE"
    OTHER_CAUSE = "OTHER_CAUSE"
    TECHNICAL_PROBLEM = "TECHNICAL_PROBLEM"
    STRIKE = "STRIKE"
    DEMONSTRATION = "DEMONSTRATION"
    ACCIDENT = "ACCIDENT"
    HOLIDAY = "HOLIDAY"
    WEATHER = "WEATHER"
    MAINTENANCE = "MAINTENANCE"
    CONSTRUCTION = "CONSTRUCTION"
    POLICE_ACTIVITY = "POLICE_ACTIVITY"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"


class AlertEffect(Enum):
    """Effect of the service alert on service."""
    NO_SERVICE = "NO_SERVICE"
    REDUCED_SERVICE = "REDUCED_SERVICE"
    SIGNIFICANT_DELAYS = "SIGNIFICANT_DELAYS"
    DETOUR = "DETOUR"
    ADDITIONAL_SERVICE = "ADDITIONAL_SERVICE"
    MODIFIED_SERVICE = "MODIFIED_SERVICE"
    OTHER_EFFECT = "OTHER_EFFECT"
    UNKNOWN_EFFECT = "UNKNOWN_EFFECT"
    STOP_MOVED = "STOP_MOVED"
    NO_EFFECT = "NO_EFFECT"
    ACCESSIBILITY_ISSUE = "ACCESSIBILITY_ISSUE"


class AlertSeverity(Enum):
    """Severity level of the service alert."""
    UNKNOWN_SEVERITY = "UNKNOWN_SEVERITY"
    INFO = "INFO"
    WARNING = "WARNING"
    SEVERE = "SEVERE"


# ============== Service Alert Dataclasses ==============

@dataclass
class InformedEntity:
    """
    Entity affected by a service alert.

    Identifies specific routes, stops, trips, or agencies affected.
    """
    agency_id: Optional[str] = None
    route_id: Optional[str] = None
    route_type: Optional[int] = None
    stop_id: Optional[str] = None
    trip_id: Optional[str] = None
    direction_id: Optional[int] = None

    def affects_route(self, route_id: str) -> bool:
        """Check if this entity affects a specific route."""
        return self.route_id == route_id

    def affects_stop(self, stop_id: str) -> bool:
        """Check if this entity affects a specific stop."""
        return self.stop_id == stop_id

    def affects_trip(self, trip_id: str) -> bool:
        """Check if this entity affects a specific trip."""
        return self.trip_id == trip_id

    def get_description(self) -> str:
        """Get a human-readable description of the affected entity."""
        parts = []
        if self.route_id:
            parts.append(f"Route {self.route_id}")
        if self.stop_id:
            parts.append(f"Stop {self.stop_id}")
        if self.trip_id:
            parts.append(f"Trip {self.trip_id}")
        if self.agency_id and not parts:
            parts.append(f"Agency {self.agency_id}")
        return ", ".join(parts) if parts else "Entire network"


@dataclass
class ActivePeriod:
    """
    Time period during which an alert is active.

    Both start and end are Unix timestamps. If start is 0/None, alert is
    already active. If end is 0/None, alert has no scheduled end.
    """
    start: Optional[int] = None  # Unix timestamp, None = already active
    end: Optional[int] = None    # Unix timestamp, None = no end time

    def is_active(self, current_time: int) -> bool:
        """
        Check if the alert is active at a given time.

        Args:
            current_time: Unix timestamp to check

        Returns:
            True if alert is active at current_time
        """
        start_ok = self.start is None or self.start == 0 or current_time >= self.start
        end_ok = self.end is None or self.end == 0 or current_time <= self.end
        return start_ok and end_ok


@dataclass
class ServiceAlert:
    """
    Represents a service alert from GTFS Realtime.

    Contains information about disruptions, delays, or other service
    changes affecting routes, stops, or trips.
    """
    alert_id: str
    cause: AlertCause = AlertCause.UNKNOWN_CAUSE
    effect: AlertEffect = AlertEffect.UNKNOWN_EFFECT
    severity: AlertSeverity = AlertSeverity.UNKNOWN_SEVERITY

    # Text content
    header_text: Optional[str] = None       # Short description
    description_text: Optional[str] = None  # Full description
    url: Optional[str] = None               # More info link

    # Time periods
    active_periods: List[ActivePeriod] = field(default_factory=list)

    # Affected entities
    informed_entities: List[InformedEntity] = field(default_factory=list)

    # Timestamp when alert was created/updated
    timestamp: Optional[int] = None

    def is_active(self, current_time: int) -> bool:
        """
        Check if the alert is active at a given time.

        Args:
            current_time: Unix timestamp to check

        Returns:
            True if any active period contains current_time,
            or True if no active periods defined (always active)
        """
        if not self.active_periods:
            return True  # No periods means always active
        return any(period.is_active(current_time) for period in self.active_periods)

    def affects_route(self, route_id: str) -> bool:
        """Check if this alert affects a specific route."""
        return any(entity.affects_route(route_id) for entity in self.informed_entities)

    def affects_stop(self, stop_id: str) -> bool:
        """Check if this alert affects a specific stop."""
        return any(entity.affects_stop(stop_id) for entity in self.informed_entities)

    def affects_trip(self, trip_id: str) -> bool:
        """Check if this alert affects a specific trip."""
        return any(entity.affects_trip(trip_id) for entity in self.informed_entities)

    def get_cause_display(self) -> str:
        """Get human-readable cause string."""
        return self.cause.value.replace("_", " ").title()

    def get_effect_display(self) -> str:
        """Get human-readable effect string."""
        return self.effect.value.replace("_", " ").title()

    def get_severity_display(self) -> str:
        """Get human-readable severity string."""
        return self.severity.value.replace("_", " ").title()

    def get_affected_routes(self) -> List[str]:
        """Get list of affected route IDs."""
        return [e.route_id for e in self.informed_entities if e.route_id]

    def get_affected_stops(self) -> List[str]:
        """Get list of affected stop IDs."""
        return [e.stop_id for e in self.informed_entities if e.stop_id]

    def get_summary(self) -> str:
        """
        Get a summary of the alert.

        Returns:
            Short summary string for display
        """
        if self.header_text:
            return self.header_text
        return f"{self.get_effect_display()} - {self.get_cause_display()}"


@dataclass
class ServiceAlertSummary:
    """
    Summary of service alerts for a mode or area.

    Provides aggregated statistics about active alerts.
    """
    total_alerts: int
    by_severity: dict = field(default_factory=dict)  # severity -> count
    by_effect: dict = field(default_factory=dict)    # effect -> count
    affected_routes: List[str] = field(default_factory=list)
    affected_stops: List[str] = field(default_factory=list)
    timestamp: Optional[int] = None
    mode: Optional[str] = None
