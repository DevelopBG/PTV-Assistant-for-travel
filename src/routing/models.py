"""
Data models for journey planning results.

This module defines the structure for journey results including
individual journey legs and complete journey itineraries.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta


@dataclass
class Leg:
    """
    Represents one segment of a journey (e.g., one trip on a route).

    A leg is a continuous journey on a single trip/route without transfers.
    """

    from_stop_id: str
    from_stop_name: str
    to_stop_id: str
    to_stop_name: str

    departure_time: str  # HH:MM:SS format
    arrival_time: str    # HH:MM:SS format

    trip_id: str
    route_id: str
    route_name: Optional[str] = None
    route_type: Optional[int] = None  # GTFS route_type for multi-modal support
    is_transfer: bool = False  # True if this is a walking transfer

    # Number of stops between origin and destination (including both)
    num_stops: int = 0

    # Intermediate stops (list of stop names between origin and destination)
    intermediate_stops: List[str] = field(default_factory=list)

    # NEW: Intermediate stop IDs for coordinate lookup
    intermediate_stop_ids: List[str] = field(default_factory=list)

    # NEW: Intermediate stop coordinates for map visualization
    # Format: [{"name": str, "id": str, "lat": float, "lon": float}, ...]
    intermediate_coords: List[dict] = field(default_factory=list)

    # Realtime fields (Phase 5)
    scheduled_departure_time: Optional[str] = None  # For realtime comparison
    actual_departure_time: Optional[str] = None  # With delay applied
    scheduled_arrival_time: Optional[str] = None  # For realtime comparison
    actual_arrival_time: Optional[str] = None  # With delay applied

    departure_delay_seconds: int = 0  # Negative = early, positive = late
    arrival_delay_seconds: int = 0
    is_cancelled: bool = False

    platform_name: Optional[str] = None  # "Platform 5", "Track 1"
    has_realtime_data: bool = False  # Whether realtime info is available

    def __post_init__(self):
        """Validate and convert types."""
        self.num_stops = int(self.num_stops)
        if self.route_type is not None:
            self.route_type = int(self.route_type)

    def get_mode_name(self) -> str:
        """Get human-readable mode name."""
        if self.is_transfer:
            return "Walking"
        mode_map = {
            0: "Tram",
            1: "Metro",
            2: "Regional Train",
            3: "Bus",
            4: "Ferry",
            700: "Bus",  # PTV uses 700 for buses
            900: "Tram"   # PTV uses 900 for trams
        }
        return mode_map.get(self.route_type, "Unknown")

    @property
    def duration_seconds(self) -> int:
        """Calculate leg duration in seconds, handling midnight crossings."""
        def time_to_seconds(time_str: str) -> int:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        dep = time_to_seconds(self.departure_time)
        arr = time_to_seconds(self.arrival_time)

        # Handle midnight crossing (arrival before departure)
        # This occurs when journey spans midnight (e.g., depart 23:00, arrive 01:00)
        if arr < dep:
            arr += 86400  # Add 24 hours (next day)

        return arr - dep

    @property
    def duration_minutes(self) -> int:
        """Calculate leg duration in minutes."""
        return self.duration_seconds // 60

    def format_duration(self) -> str:
        """Format duration as human-readable string."""
        minutes = self.duration_minutes
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"


@dataclass
class Journey:
    """
    Represents a complete journey from origin to destination.

    A journey consists of one or more legs, possibly with transfers.
    """

    origin_stop_id: str
    origin_stop_name: str
    destination_stop_id: str
    destination_stop_name: str

    departure_time: str  # HH:MM:SS format
    arrival_time: str    # HH:MM:SS format

    legs: List[Leg]

    # Realtime fields (Phase 5)
    actual_departure_time: Optional[str] = None  # With delays applied
    actual_arrival_time: Optional[str] = None  # With delays applied
    total_delay_seconds: int = 0  # Sum of all delays
    has_realtime_data: bool = False  # Any leg has realtime info
    is_realtime_valid: bool = True  # Is journey still feasible?
    invalidity_reason: Optional[str] = None  # Why journey is no longer valid
    journey_alerts: List[str] = field(default_factory=list)  # Service alerts

    def __post_init__(self):
        """Validate journey data."""
        if not self.legs:
            raise ValueError("Journey must have at least one leg")

        # Validate leg continuity
        for i in range(len(self.legs) - 1):
            if self.legs[i].to_stop_id != self.legs[i + 1].from_stop_id:
                raise ValueError(
                    f"Discontinuous journey: leg {i} ends at {self.legs[i].to_stop_id} "
                    f"but leg {i+1} starts at {self.legs[i + 1].from_stop_id}"
                )

    @property
    def num_transfers(self) -> int:
        """Number of transfers (changes between vehicles)."""
        return len(self.legs) - 1

    @property
    def duration_seconds(self) -> int:
        """Calculate total journey duration in seconds, handling midnight crossings."""
        def time_to_seconds(time_str: str) -> int:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        dep = time_to_seconds(self.departure_time)
        arr = time_to_seconds(self.arrival_time)

        # Handle midnight crossing (arrival before departure)
        # This occurs when journey spans midnight (e.g., depart 23:00, arrive 01:00)
        if arr < dep:
            arr += 86400  # Add 24 hours (next day)

        return arr - dep

    @property
    def duration_minutes(self) -> int:
        """Calculate total journey duration in minutes."""
        return self.duration_seconds // 60

    def format_duration(self) -> str:
        """Format duration as human-readable string."""
        minutes = self.duration_minutes
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"

    def get_modes_used(self) -> List[str]:
        """
        Get list of transport modes used in this journey.

        Returns:
            List of unique mode names (e.g., ["Regional Train", "Bus"])
        """
        modes = []
        seen = set()
        for leg in self.legs:
            mode = leg.get_mode_name()
            if mode not in seen and mode != "Walking":
                modes.append(mode)
                seen.add(mode)
        return modes

    def is_multi_modal(self) -> bool:
        """
        Check if journey uses multiple transport modes.

        Returns:
            True if journey uses more than one mode (excluding walking transfers)
        """
        return len(self.get_modes_used()) > 1

    def get_transfer_wait_times(self) -> List[int]:
        """
        Get wait times at each transfer in seconds.

        Returns:
            List of wait times in seconds (empty if no transfers)
        """
        if self.num_transfers == 0:
            return []

        wait_times = []
        for i in range(len(self.legs) - 1):
            # Time between arrival of current leg and departure of next leg
            def time_to_seconds(time_str: str) -> int:
                parts = time_str.split(':')
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds

            arrival = time_to_seconds(self.legs[i].arrival_time)
            next_departure = time_to_seconds(self.legs[i + 1].departure_time)
            wait_times.append(next_departure - arrival)

        return wait_times

    def get_delay_summary(self) -> str:
        """
        Get human-readable delay summary.

        Returns:
            String like "5 min delay" or "On time" or "2 min early"
        """
        if not self.has_realtime_data:
            return "No realtime data"

        if self.total_delay_seconds == 0:
            return "On time"

        delay_mins = abs(self.total_delay_seconds) // 60
        if self.total_delay_seconds > 0:
            return f"{delay_mins} min delay"
        else:
            return f"{delay_mins} min early"

    def has_significant_delays(self, threshold_minutes: int = 5) -> bool:
        """
        Check if delays exceed threshold.

        Args:
            threshold_minutes: Delay threshold in minutes (default: 5)

        Returns:
            True if total delay exceeds threshold
        """
        delay_mins = abs(self.total_delay_seconds) // 60
        return delay_mins >= threshold_minutes

    def format_summary(self) -> str:
        """
        Format journey as a human-readable summary string.

        Returns:
            Multi-line string with journey details
        """
        lines = []
        lines.append(f"Journey: {self.origin_stop_name} → {self.destination_stop_name}")

        # Show scheduled and actual times if realtime data available
        if self.has_realtime_data and self.actual_departure_time:
            lines.append(f"Departure: {self.departure_time} → {self.actual_departure_time}")
        else:
            lines.append(f"Departure: {self.departure_time}")

        if self.has_realtime_data and self.actual_arrival_time:
            lines.append(f"Arrival: {self.arrival_time} → {self.actual_arrival_time}")
        else:
            lines.append(f"Arrival: {self.arrival_time}")

        lines.append(f"Duration: {self.format_duration()}")
        lines.append(f"Transfers: {self.num_transfers}")

        # Add realtime status
        if self.has_realtime_data:
            lines.append(f"Status: {self.get_delay_summary()}")
            if not self.is_realtime_valid:
                lines.append(f"⚠️  INVALID: {self.invalidity_reason}")

        lines.append("")

        for i, leg in enumerate(self.legs, 1):
            lines.append(f"Leg {i}:")
            lines.append(f"  {leg.from_stop_name} → {leg.to_stop_name}")
            lines.append(f"  Mode: {leg.get_mode_name()}")

            # Show realtime times if available
            if leg.has_realtime_data:
                if leg.actual_departure_time and leg.actual_arrival_time:
                    lines.append(f"  Depart: {leg.departure_time} → {leg.actual_departure_time}  "
                               f"Arrive: {leg.arrival_time} → {leg.actual_arrival_time}")
                    if leg.departure_delay_seconds != 0:
                        delay_mins = abs(leg.departure_delay_seconds) // 60
                        status = "delay" if leg.departure_delay_seconds > 0 else "early"
                        lines.append(f"  ⚠️  {delay_mins} min {status}")
                else:
                    lines.append(f"  Depart: {leg.departure_time}  Arrive: {leg.arrival_time}")
            else:
                lines.append(f"  Depart: {leg.departure_time}  Arrive: {leg.arrival_time}")

            lines.append(f"  Duration: {leg.format_duration()}")
            if leg.route_name:
                lines.append(f"  Route: {leg.route_name}")
            if leg.platform_name:
                lines.append(f"  Platform: {leg.platform_name}")
            if leg.is_cancelled:
                lines.append(f"  ❌ CANCELLED")
            if not leg.is_transfer:
                lines.append(f"  Stops: {leg.num_stops}")
                # Show intermediate stops if available
                if leg.intermediate_stops:
                    lines.append(f"  Via: {', '.join(leg.intermediate_stops)}")

            # Add transfer wait time if not last leg
            if i < len(self.legs):
                wait_times = self.get_transfer_wait_times()
                if wait_times:
                    wait_mins = wait_times[i - 1] // 60
                    lines.append(f"  Transfer wait: {wait_mins}m")

            lines.append("")

        return "\n".join(lines)
