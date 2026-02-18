"""
Realtime Integration Module - Phase 5

Applies real-time updates from GTFS Realtime feeds to scheduled journeys.
Handles delays, cancellations, platform information, and transfer validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

from .feed_fetcher import GTFSRealtimeFetcher
from .time_utils import add_delay_to_time, time_diff_seconds
from .vehicle_positions import VehiclePositionParser
from .models import VehiclePosition
from ..routing.models import Journey, Leg

logger = logging.getLogger(__name__)


@dataclass
class StopUpdate:
    """
    Realtime information for a specific stop on a trip.

    Contains delay and platform information for a single stop.
    """
    stop_id: str
    stop_sequence: int
    departure_delay_seconds: int = 0
    arrival_delay_seconds: int = 0
    platform_name: Optional[str] = None


@dataclass
class TripUpdateInfo:
    """
    Structured realtime data for a single trip.

    Aggregates all realtime information for a trip including
    delays, cancellations, and stop-specific updates.
    """
    trip_id: str
    route_id: str
    is_cancelled: bool = False
    stop_updates: Dict[str, StopUpdate] = field(default_factory=dict)  # stop_id → update
    alerts: List[str] = field(default_factory=list)


class RealtimeIntegrator:
    """
    Integrates real-time GTFS feed data with scheduled journeys.

    Uses the post-processing pattern: applies realtime updates to
    journeys after they've been planned using scheduled data.
    """

    def __init__(self, fetcher: Optional[GTFSRealtimeFetcher] = None):
        """
        Initialize realtime integrator.

        Args:
            fetcher: GTFSRealtimeFetcher instance (required for fetching realtime data)
        """
        self.fetcher = fetcher
        self._trip_updates_cache: Dict[str, Dict[str, TripUpdateInfo]] = {}  # mode → trip_id → info

    def apply_realtime_to_journey(
        self,
        journey: Journey,
        mode: str = 'vline',
        min_transfer_time_seconds: int = 120
    ) -> Journey:
        """
        Apply realtime updates to a journey.

        Args:
            journey: Scheduled journey from JourneyPlanner
            mode: Transport mode ('metro' or 'vline')
            min_transfer_time_seconds: Minimum time needed for transfers (default: 2 min)

        Returns:
            Journey with realtime fields populated

        Note:
            Original journey is not modified - returns same instance with updated fields.
        """
        logger.info(f"Applying realtime data to journey {journey.origin_stop_name} → "
                   f"{journey.destination_stop_name}")

        # Check if fetcher is available
        if not self.fetcher:
            logger.warning("No fetcher provided. Using scheduled times.")
            return journey

        # Fetch and parse realtime data
        try:
            feed = self.fetcher.fetch_trip_updates(mode=mode)
            trip_updates = self._parse_trip_updates(feed)
            logger.info(f"Parsed {len(trip_updates)} trip updates from realtime feed")
        except Exception as e:
            logger.warning(f"Failed to fetch realtime data: {e}. Using scheduled times.")
            return journey  # Return unchanged journey

        # Apply delays to each leg
        total_delay = 0
        any_cancelled = False
        has_any_realtime_data = False

        for leg in journey.legs:
            if leg.trip_id in trip_updates:
                trip_info = trip_updates[leg.trip_id]
                self._apply_delays_to_leg(leg, trip_info)
                has_any_realtime_data = True

                if leg.is_cancelled:
                    any_cancelled = True

                total_delay += leg.departure_delay_seconds

        # Update journey-level realtime fields
        journey.has_realtime_data = has_any_realtime_data
        journey.total_delay_seconds = total_delay

        if has_any_realtime_data and len(journey.legs) > 0:
            # Update actual departure/arrival times
            first_leg = journey.legs[0]
            last_leg = journey.legs[-1]

            if first_leg.actual_departure_time:
                journey.actual_departure_time = first_leg.actual_departure_time

            if last_leg.actual_arrival_time:
                journey.actual_arrival_time = last_leg.actual_arrival_time

        # Validate transfers still feasible
        if has_any_realtime_data and journey.num_transfers > 0:
            is_valid, reason = self._validate_transfers(journey, min_transfer_time_seconds)
            journey.is_realtime_valid = is_valid
            if not is_valid:
                journey.invalidity_reason = reason
                logger.warning(f"Journey no longer valid: {reason}")

        # Mark as invalid if any leg cancelled
        if any_cancelled:
            journey.is_realtime_valid = False
            journey.invalidity_reason = "One or more services have been cancelled"

        logger.info(f"Realtime integration complete. Delay: {total_delay}s, Valid: {journey.is_realtime_valid}")
        return journey

    def _parse_trip_updates(self, feed) -> Dict[str, TripUpdateInfo]:
        """
        Parse GTFS Realtime feed into structured trip updates.

        Args:
            feed: FeedMessage from GTFS Realtime protobuf

        Returns:
            Dictionary mapping trip_id to TripUpdateInfo
        """
        trip_updates = {}

        for entity in feed.entity:
            if not entity.HasField('trip_update'):
                continue

            trip_update = entity.trip_update
            trip_id = trip_update.trip.trip_id
            route_id = trip_update.trip.route_id if trip_update.trip.HasField('route_id') else ""

            # Check for cancellation
            is_cancelled = False
            if trip_update.trip.HasField('schedule_relationship'):
                from google.transit import gtfs_realtime_pb2
                if trip_update.trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED:
                    is_cancelled = True

            # Parse stop time updates
            stop_updates = {}
            for stu in trip_update.stop_time_update:
                stop_id = stu.stop_id
                stop_sequence = stu.stop_sequence if stu.HasField('stop_sequence') else 0

                # Extract delays
                dep_delay = 0
                arr_delay = 0

                if stu.HasField('departure') and stu.departure.HasField('delay'):
                    dep_delay = stu.departure.delay

                if stu.HasField('arrival') and stu.arrival.HasField('delay'):
                    arr_delay = stu.arrival.delay

                # Extract platform (if available)
                platform = None
                # Note: Platform info might be in different fields depending on the feed
                # PTV may not provide this in trip updates

                stop_update = StopUpdate(
                    stop_id=stop_id,
                    stop_sequence=stop_sequence,
                    departure_delay_seconds=dep_delay,
                    arrival_delay_seconds=arr_delay,
                    platform_name=platform
                )
                stop_updates[stop_id] = stop_update

            trip_info = TripUpdateInfo(
                trip_id=trip_id,
                route_id=route_id,
                is_cancelled=is_cancelled,
                stop_updates=stop_updates
            )
            trip_updates[trip_id] = trip_info

        return trip_updates

    def _apply_delays_to_leg(self, leg: Leg, trip_info: TripUpdateInfo) -> None:
        """
        Apply realtime delays to a single journey leg.

        Args:
            leg: Leg to update (modified in place)
            trip_info: Realtime information for the trip

        Note:
            Modifies leg in place, setting realtime fields.
        """
        # Check if trip is cancelled
        if trip_info.is_cancelled:
            leg.is_cancelled = True
            leg.has_realtime_data = True
            return

        # Find stop updates for this leg's from/to stops
        from_update = trip_info.stop_updates.get(leg.from_stop_id)
        to_update = trip_info.stop_updates.get(leg.to_stop_id)

        if not from_update and not to_update:
            # No realtime data for this leg
            return

        # Store original times as scheduled
        leg.scheduled_departure_time = leg.departure_time
        leg.scheduled_arrival_time = leg.arrival_time

        # Apply departure delay
        if from_update and from_update.departure_delay_seconds != 0:
            leg.departure_delay_seconds = from_update.departure_delay_seconds
            leg.actual_departure_time = add_delay_to_time(
                leg.departure_time,
                from_update.departure_delay_seconds
            )
            if from_update.platform_name:
                leg.platform_name = from_update.platform_name
        else:
            leg.actual_departure_time = leg.departure_time

        # Apply arrival delay
        if to_update and to_update.arrival_delay_seconds != 0:
            leg.arrival_delay_seconds = to_update.arrival_delay_seconds
            leg.actual_arrival_time = add_delay_to_time(
                leg.arrival_time,
                to_update.arrival_delay_seconds
            )
            if to_update.platform_name:
                leg.platform_name = to_update.platform_name
        else:
            leg.actual_arrival_time = leg.arrival_time

        leg.has_realtime_data = True

    def _validate_transfers(
        self,
        journey: Journey,
        min_transfer_time_seconds: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that transfers are still feasible after delays.

        Args:
            journey: Journey with realtime updates applied
            min_transfer_time_seconds: Minimum time needed for transfers

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        for i in range(len(journey.legs) - 1):
            current_leg = journey.legs[i]
            next_leg = journey.legs[i + 1]

            # Get actual times (or scheduled if no realtime data)
            actual_arrival = current_leg.actual_arrival_time or current_leg.arrival_time
            actual_departure = next_leg.actual_departure_time or next_leg.departure_time

            # Calculate transfer window
            transfer_window = time_diff_seconds(actual_arrival, actual_departure)

            if transfer_window < min_transfer_time_seconds:
                transfer_mins = transfer_window // 60
                min_mins = min_transfer_time_seconds // 60
                reason = (f"Transfer at {current_leg.to_stop_name} no longer feasible: "
                         f"only {transfer_mins} min available, need {min_mins} min")
                return False, reason

        return True, None

    def _extract_platform_info(self, leg: Leg, trip_info: TripUpdateInfo) -> Optional[str]:
        """
        Extract platform information from realtime data.

        Args:
            leg: Journey leg
            trip_info: Realtime trip information

        Returns:
            Platform name if available, None otherwise

        Note:
            PTV may not provide platform info in trip updates.
            This is a placeholder for future enhancement.
        """
        # Check if we have stop updates for this leg
        from_update = trip_info.stop_updates.get(leg.from_stop_id)
        if from_update and from_update.platform_name:
            return from_update.platform_name

        return None

    def get_vehicle_for_leg(
        self,
        leg: Leg,
        mode: str = 'vline'
    ) -> Optional[VehiclePosition]:
        """
        Get the vehicle position for a journey leg.

        Args:
            leg: Journey leg with trip_id
            mode: Transport mode ('metro' or 'vline')

        Returns:
            VehiclePosition if found, None otherwise
        """
        if not self.fetcher or not leg.trip_id:
            return None

        try:
            parser = VehiclePositionParser(fetcher=self.fetcher)
            positions = parser.fetch_positions(mode=mode)
            vehicles = parser.get_vehicles_for_trip(leg.trip_id, positions)

            if vehicles:
                return vehicles[0]
            return None
        except Exception as e:
            logger.warning(f"Failed to get vehicle for leg: {e}")
            return None

    def get_vehicles_for_journey(
        self,
        journey: Journey,
        mode: str = 'vline'
    ) -> Dict[str, Optional[VehiclePosition]]:
        """
        Get vehicle positions for all legs in a journey.

        Args:
            journey: Journey with legs
            mode: Transport mode ('metro' or 'vline')

        Returns:
            Dictionary mapping trip_id to VehiclePosition (or None if not found)
        """
        if not self.fetcher:
            return {}

        result = {}

        try:
            parser = VehiclePositionParser(fetcher=self.fetcher)
            positions = parser.fetch_positions(mode=mode)

            for leg in journey.legs:
                if leg.trip_id:
                    vehicles = parser.get_vehicles_for_trip(leg.trip_id, positions)
                    result[leg.trip_id] = vehicles[0] if vehicles else None

        except Exception as e:
            logger.warning(f"Failed to get vehicles for journey: {e}")

        return result
