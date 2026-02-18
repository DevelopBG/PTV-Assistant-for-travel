"""
Journey planning using Connection Scan Algorithm (CSA).

This module implements the Connection Scan Algorithm for finding optimal
journeys in transit networks. CSA is particularly efficient for GTFS data
as it processes timetabled connections directly.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import sys

from ..data.gtfs_parser import GTFSParser
from ..data.models import StopTime
from ..graph.transit_graph import TransitGraph, Connection
from .models import Journey, Leg

logger = logging.getLogger(__name__)


@dataclass
class ConnectionWithMeta:
    """Connection with additional metadata for CSA."""
    connection: Connection
    stop_sequence_from: int
    stop_sequence_to: int


class JourneyPlanner:
    """
    Journey planner using Connection Scan Algorithm.

    The CSA processes all connections (timetabled trip segments) in chronological
    order to find the earliest arrival time to the destination.
    """

    def __init__(self, gtfs_parser: GTFSParser, transit_graph: Optional[TransitGraph] = None):
        """
        Initialize journey planner.

        Args:
            gtfs_parser: GTFSParser with loaded GTFS data
            transit_graph: Optional pre-built TransitGraph (will be created if not provided)
        """
        self.parser = gtfs_parser
        self.graph = transit_graph or TransitGraph(gtfs_parser)

    def find_journey(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: str,
        max_transfers: int = 3
    ) -> Optional[Journey]:
        """
        Find the earliest arrival journey from origin to destination.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Earliest departure time in HH:MM:SS format
            max_transfers: Maximum number of transfers allowed

        Returns:
            Journey object if route found, None otherwise
        """
        logger.debug(
            f"Finding journey: {origin_stop_id} -> {destination_stop_id} at {departure_time}"
        )

        # Validate stops exist
        if not self.graph.has_stop(origin_stop_id):
            logger.warning(f"Origin stop {origin_stop_id} not found")
            raise ValueError(f"Origin stop {origin_stop_id} not found")
        if not self.graph.has_stop(destination_stop_id):
            logger.warning(f"Destination stop {destination_stop_id} not found")
            raise ValueError(f"Destination stop {destination_stop_id} not found")

        # Handle same origin and destination
        if origin_stop_id == destination_stop_id:
            return None

        # Run Connection Scan Algorithm
        return self._connection_scan(
            origin_stop_id,
            destination_stop_id,
            departure_time,
            max_transfers
        )

    def _connection_scan(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: str,
        max_transfers: int
    ) -> Optional[Journey]:
        """
        Connection Scan Algorithm implementation.

        Algorithm:
        1. Initialize earliest arrival time for all stops to infinity
        2. Set origin earliest arrival to departure time
        3. Process all connections in chronological order
        4. For each connection, check if it improves arrival time at destination stop
        5. Reconstruct journey from tracked connections

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Departure time string
            max_transfers: Maximum transfers

        Returns:
            Journey if found, None otherwise
        """
        # Convert time to seconds for comparison
        dep_seconds = self._time_to_seconds(departure_time)

        # Initialize earliest arrival times (in seconds since midnight)
        earliest_arrival = {stop_id: sys.maxsize for stop_id in self.parser.stops.keys()}
        earliest_arrival[origin_stop_id] = dep_seconds

        # Track the connection used to reach each stop (for reconstruction)
        enter_connection: Dict[str, Connection] = {}

        # Track which trip we're currently on at each stop
        in_trip: Dict[str, Optional[str]] = {stop_id: None for stop_id in self.parser.stops.keys()}

        # Use pre-sorted connections from graph (optimization)
        all_connections = self.graph.get_sorted_connections()

        # Separate regular connections and transfers
        regular_connections = [c for c in all_connections if not c.is_transfer]
        transfer_connections = [c for c in all_connections if c.is_transfer]

        # Get current date and day of week for service calendar validation
        now = datetime.now()
        check_date = now.strftime("%Y%m%d")
        day_of_week = now.weekday()  # 0=Monday, 6=Sunday

        # PERFORMANCE: Filter connections by time window (4 hours) AND service calendar
        # Most journeys complete within 4 hours
        time_window_seconds = 4 * 3600

        # Keep original list for future day searching if needed
        regular_connections_backup = regular_connections

        # First, try to find trips today within the time window
        # Don't let max_time exceed midnight (86400 seconds)
        max_time_today = min(dep_seconds + time_window_seconds, 86400)

        today_connections = [
            c for c in regular_connections
            if (dep_seconds <= self._time_to_seconds(c.departure_time) < 86400
                and (c.service_id is None or self._is_trip_operating(c.service_id, check_date, day_of_week)))
        ]

        # If no connections found today AND time window extends past midnight,
        # search tomorrow's early morning trips
        if not today_connections and (dep_seconds + time_window_seconds) > 86400:
            tomorrow = now + timedelta(days=1)
            tomorrow_date = tomorrow.strftime("%Y%m%d")
            tomorrow_dow = tomorrow.weekday()

            # Calculate how far into tomorrow we should search
            max_time_tomorrow = (dep_seconds + time_window_seconds) - 86400

            tomorrow_connections = [
                c for c in regular_connections_backup
                if (0 <= self._time_to_seconds(c.departure_time) <= max_time_tomorrow
                    and (c.service_id is None or self._is_trip_operating(c.service_id, tomorrow_date, tomorrow_dow)))
            ]

            regular_connections = tomorrow_connections
            logger.debug(f"No service today in time window, checking tomorrow: {len(tomorrow_connections):,} connections")
        else:
            regular_connections = today_connections

        # If STILL no connections (no service today or in time window),
        # find the next available trip (could be tomorrow or later)
        if not regular_connections:
            logger.info("No service in time window, searching up to 7 days ahead...")
            # Search up to 7 days ahead for next available trip
            for days_ahead in range(1, 8):
                future_date_obj = now + timedelta(days=days_ahead)
                future_date = future_date_obj.strftime("%Y%m%d")
                future_dow = future_date_obj.weekday()

                # Look for trips starting from 00:00 on this future day
                future_connections = [
                    c for c in regular_connections_backup
                    if (c.service_id is None or self._is_trip_operating(c.service_id, future_date, future_dow))
                ]

                if future_connections:
                    # Found trips on this day, take earliest ones (limit to prevent performance issues)
                    future_connections.sort(key=lambda c: self._time_to_seconds(c.departure_time))
                    regular_connections = future_connections[:1000]  # Limit to first 1000 connections
                    logger.info(f"Found next service on {future_date} ({days_ahead} days ahead): {len(regular_connections):,} connections")
                    break

        logger.debug(f"Filtered to {len(regular_connections):,} connections with calendar validation")

        # Phase 1: Scan regular timetabled connections
        for conn in regular_connections:
            dep_time = self._time_to_seconds(conn.departure_time)
            arr_time = self._time_to_seconds(conn.arrival_time)

            # Skip connections that depart before we can reach the departure stop
            if dep_time < earliest_arrival[conn.from_stop_id]:
                continue

            # PERFORMANCE: Early termination if destination reached and we've passed its arrival
            if destination_stop_id in enter_connection and dep_time > earliest_arrival[destination_stop_id]:
                logger.debug(f"Early termination: destination reached at {earliest_arrival[destination_stop_id]}")
                break

            # Check if this connection improves arrival time
            if arr_time < earliest_arrival[conn.to_stop_id]:
                # Update earliest arrival
                earliest_arrival[conn.to_stop_id] = arr_time

                # Track the connection
                enter_connection[conn.to_stop_id] = conn

                # Update trip tracking
                if in_trip[conn.from_stop_id] == conn.trip_id:
                    in_trip[conn.to_stop_id] = conn.trip_id
                else:
                    in_trip[conn.to_stop_id] = conn.trip_id

        # Phase 2: Apply transfers iteratively until no improvements
        # This allows multi-leg journeys with transfers
        # PERFORMANCE: Limit to 3 rounds maximum (most real journeys need 1-2)
        max_transfer_rounds = min(3, max_transfers + 1)
        for round_num in range(max_transfer_rounds):
            improvements = 0

            for conn in transfer_connections:
                # Transfer available anytime
                dep_time = earliest_arrival[conn.from_stop_id]

                # Skip if we haven't reached the from_stop yet
                if dep_time == sys.maxsize:
                    continue

                arr_time = dep_time + conn.travel_time_seconds

                # Check if this transfer improves arrival time
                if arr_time < earliest_arrival[conn.to_stop_id]:
                    earliest_arrival[conn.to_stop_id] = arr_time
                    enter_connection[conn.to_stop_id] = conn
                    in_trip[conn.to_stop_id] = conn.trip_id
                    improvements += 1

            # If no improvements, we're done
            if improvements == 0:
                break

            # After transfers, scan regular connections again
            # to see if newly reachable stops can catch new trips
            for conn in regular_connections:
                dep_time = self._time_to_seconds(conn.departure_time)
                arr_time = self._time_to_seconds(conn.arrival_time)

                if dep_time < earliest_arrival[conn.from_stop_id]:
                    continue

                # PERFORMANCE: Early termination in transfer rounds too
                if destination_stop_id in enter_connection and dep_time > earliest_arrival[destination_stop_id]:
                    break

                if arr_time < earliest_arrival[conn.to_stop_id]:
                    earliest_arrival[conn.to_stop_id] = arr_time
                    enter_connection[conn.to_stop_id] = conn

                    if in_trip[conn.from_stop_id] == conn.trip_id:
                        in_trip[conn.to_stop_id] = conn.trip_id
                    else:
                        in_trip[conn.to_stop_id] = conn.trip_id

        # Check if destination is reachable
        if destination_stop_id not in enter_connection:
            logger.debug(f"No route found to {destination_stop_id}")
            return None

        # Reconstruct journey
        return self._reconstruct_journey(
            origin_stop_id,
            destination_stop_id,
            enter_connection,
            earliest_arrival
        )

    def _reconstruct_journey(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        enter_connection: Dict[str, Connection],
        earliest_arrival: Dict[str, int]
    ) -> Optional[Journey]:
        """
        Reconstruct journey from tracked connections.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            enter_connection: Map of stop_id to connection used to reach it
            earliest_arrival: Map of stop_id to earliest arrival time

        Returns:
            Journey object
        """
        # Backtrack from destination to origin
        path_connections: List[Connection] = []
        current_stop = destination_stop_id

        while current_stop != origin_stop_id:
            if current_stop not in enter_connection:
                return None  # No path found

            conn = enter_connection[current_stop]
            path_connections.append(conn)
            current_stop = conn.from_stop_id

        # Reverse to get origin -> destination order
        path_connections.reverse()

        # Group consecutive connections on same trip into legs
        legs: List[Leg] = []
        current_leg_start = 0

        for i in range(len(path_connections)):
            # Check if next connection is on different trip (transfer point)
            is_last = (i == len(path_connections) - 1)
            is_transfer = not is_last and path_connections[i].trip_id != path_connections[i + 1].trip_id

            if is_last or is_transfer:
                # Create leg from current_leg_start to i (inclusive)
                leg = self._create_leg(
                    path_connections[current_leg_start:i + 1]
                )
                legs.append(leg)
                current_leg_start = i + 1

        # Get stop names
        origin_stop = self.parser.get_stop(origin_stop_id)
        dest_stop = self.parser.get_stop(destination_stop_id)

        # Create journey
        # Use first non-transfer leg's departure and last non-transfer leg's arrival
        # (transfer legs may have "00:00:00" times which would cause incorrect durations)
        first_non_transfer = next((leg for leg in legs if not leg.is_transfer), legs[0])
        last_non_transfer = next((leg for leg in reversed(legs) if not leg.is_transfer), legs[-1])

        journey = Journey(
            origin_stop_id=origin_stop_id,
            origin_stop_name=origin_stop.stop_name if origin_stop else origin_stop_id,
            destination_stop_id=destination_stop_id,
            destination_stop_name=dest_stop.stop_name if dest_stop else destination_stop_id,
            departure_time=first_non_transfer.departure_time,
            arrival_time=last_non_transfer.arrival_time,
            legs=legs
        )

        logger.info(
            f"Journey found: {journey.origin_stop_name} -> {journey.destination_stop_name}, "
            f"{journey.departure_time} -> {journey.arrival_time}, {len(legs)} leg(s)"
        )
        return journey

    def _create_leg(self, connections: List[Connection]) -> Leg:
        """
        Create a Leg from a list of consecutive connections on the same trip.

        Args:
            connections: List of connections on the same trip

        Returns:
            Leg object
        """
        first_conn = connections[0]
        last_conn = connections[-1]

        from_stop = self.parser.get_stop(first_conn.from_stop_id)
        to_stop = self.parser.get_stop(last_conn.to_stop_id)

        trip = self.parser.get_trip(first_conn.trip_id)
        route = self.parser.get_route(first_conn.route_id) if first_conn.route_id else None

        # Build list of intermediate stops with coordinates
        intermediate_stops = []
        intermediate_stop_ids = []
        intermediate_coords = []

        for conn in connections:
            # Add the destination stop of each connection (which becomes next stop's origin)
            stop = self.parser.get_stop(conn.to_stop_id)
            if stop and conn.to_stop_id != last_conn.to_stop_id:
                # Don't include the final destination in intermediate list
                intermediate_stops.append(stop.stop_name)
                intermediate_stop_ids.append(conn.to_stop_id)
                intermediate_coords.append({
                    "name": stop.stop_name,
                    "id": conn.to_stop_id,
                    "lat": float(stop.stop_lat),
                    "lon": float(stop.stop_lon)
                })

        return Leg(
            from_stop_id=first_conn.from_stop_id,
            from_stop_name=from_stop.stop_name if from_stop else first_conn.from_stop_id,
            to_stop_id=last_conn.to_stop_id,
            to_stop_name=to_stop.stop_name if to_stop else last_conn.to_stop_id,
            departure_time=first_conn.departure_time,
            arrival_time=last_conn.arrival_time,
            trip_id=first_conn.trip_id,
            route_id=first_conn.route_id,
            route_name=route.route_long_name if route else None,
            route_type=first_conn.route_type,
            is_transfer=first_conn.is_transfer,
            num_stops=len(connections) + 1,  # Number of stops including first and last
            intermediate_stops=intermediate_stops,  # List of intermediate stop names
            intermediate_stop_ids=intermediate_stop_ids,  # List of intermediate stop IDs
            intermediate_coords=intermediate_coords  # List of intermediate stop coordinates
        )

    def _time_to_seconds(self, time_str: str) -> int:
        """
        Convert GTFS time string to seconds since midnight.

        GTFS times can exceed 24:00:00 for trips past midnight.

        Args:
            time_str: Time in HH:MM:SS format

        Returns:
            Seconds since midnight
        """
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def _is_trip_operating(
        self,
        service_id: str,
        check_date: str,
        day_of_week: int
    ) -> bool:
        """
        Check if a trip operates on the specified date.

        Args:
            service_id: Service ID from GTFS trip
            check_date: Date in YYYYMMDD format (e.g., "20260120")
            day_of_week: Day of week (0=Monday, 6=Sunday)

        Returns:
            True if trip operates on this date, False otherwise
        """
        if not service_id:
            return True  # Transfer connections have no service_id

        # Get calendar entry
        calendar = self.parser.calendars.get(service_id)
        if not calendar:
            # Service not found - assume it doesn't operate
            logger.warning(f"Service {service_id} not found in calendar")
            return False

        # Check date range
        if check_date < calendar.start_date or check_date > calendar.end_date:
            return False

        # Check day of week
        day_fields = [
            calendar.monday,
            calendar.tuesday,
            calendar.wednesday,
            calendar.thursday,
            calendar.friday,
            calendar.saturday,
            calendar.sunday
        ]

        # Convert string "0"/"1" to boolean
        if not int(day_fields[day_of_week]):
            return False  # Service doesn't run on this day

        # Check calendar_dates exceptions
        for exception in self.parser.calendar_dates:
            if exception.service_id == service_id and exception.date == check_date:
                exception_type = int(exception.exception_type)
                if exception_type == 2:
                    return False  # Service removed on this date
                elif exception_type == 1:
                    return True  # Service added on this date

        return True

    def find_multiple_journeys(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: str,
        max_results: int = 3,
        max_transfers: int = 4
    ) -> List[Journey]:
        """
        Find multiple alternative journey options using iterative CSA.

        Uses an iterative approach:
        1. Find the earliest arrival journey
        2. Ban critical connections from that journey
        3. Re-run CSA to find next best alternative
        4. Repeat until max_results found or no more routes exist

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Earliest departure time
            max_results: Maximum number of results to return
            max_transfers: Maximum transfers allowed per journey

        Returns:
            List of Journey objects, sorted by duration (fastest first)
        """
        journeys = []
        banned_connection_sets: List[Set[Tuple[str, str, str]]] = []  # (from_stop, to_stop, trip_id)

        for attempt in range(max_results * 2):  # Try up to 2x max to account for similar routes
            # Find journey with current bans
            journey = self._connection_scan_with_bans(
                origin_stop_id,
                destination_stop_id,
                departure_time,
                max_transfers,
                banned_connection_sets
            )

            if not journey:
                break  # No more routes found

            # Check if this is a significantly different journey
            if self._is_unique_journey(journey, journeys):
                journeys.append(journey)

            # Ban critical connections from this journey to find alternatives
            banned_connections = self._get_critical_connections(journey)
            banned_connection_sets.append(banned_connections)

            if len(journeys) >= max_results:
                break

        # Sort by duration (fastest first)
        journeys.sort(key=lambda j: j.duration_minutes)

        logger.info(f"Found {len(journeys)} alternative journeys")
        return journeys

    def _connection_scan_with_bans(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: str,
        max_transfers: int,
        banned_connection_sets: List[Set[Tuple[str, str, str]]]
    ) -> Optional[Journey]:
        """
        Connection Scan Algorithm with banned connections.

        Same as regular CSA but skips banned connections to find alternatives.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Departure time string
            max_transfers: Maximum transfers allowed
            banned_connection_sets: List of banned connection sets

        Returns:
            Journey if found, None otherwise
        """
        dep_seconds = self._time_to_seconds(departure_time)

        # Initialize earliest arrival times
        earliest_arrival = {stop_id: sys.maxsize for stop_id in self.parser.stops.keys()}
        earliest_arrival[origin_stop_id] = dep_seconds

        # Track connections and trips
        enter_connection: Dict[str, Connection] = {}
        in_trip: Dict[str, Optional[str]] = {stop_id: None for stop_id in self.parser.stops.keys()}

        # Track number of transfers to each stop
        num_transfers: Dict[str, int] = {stop_id: sys.maxsize for stop_id in self.parser.stops.keys()}
        num_transfers[origin_stop_id] = 0

        all_connections = self.graph.get_sorted_connections()

        # Scan all connections
        for conn in all_connections:
            # Check if this connection is banned
            conn_tuple = (conn.from_stop_id, conn.to_stop_id, conn.trip_id)
            is_banned = any(conn_tuple in banned_set for banned_set in banned_connection_sets)
            if is_banned:
                continue

            # Handle transfer connections specially
            if conn.is_transfer:
                # Transfer connections are available anytime
                dep_time = earliest_arrival[conn.from_stop_id]
                arr_time = dep_time + conn.travel_time_seconds

                # Skip if we haven't reached the from_stop yet
                if dep_time == sys.maxsize:
                    continue
            else:
                # Regular timetabled connection
                dep_time = self._time_to_seconds(conn.departure_time)
                arr_time = self._time_to_seconds(conn.arrival_time)

                # Skip if we can't reach the departure stop in time
                if dep_time < earliest_arrival[conn.from_stop_id]:
                    continue

            # Check transfer limit
            # Count transfer if changing trips (including transfers)
            is_changing_trip = (in_trip[conn.from_stop_id] != conn.trip_id and
                               in_trip[conn.from_stop_id] is not None)

            potential_transfers = num_transfers[conn.from_stop_id]
            if is_changing_trip:
                potential_transfers += 1

            if potential_transfers > max_transfers:
                continue  # Exceeds transfer limit

            # Check if this improves arrival time
            if arr_time < earliest_arrival[conn.to_stop_id]:
                # Update earliest arrival
                earliest_arrival[conn.to_stop_id] = arr_time
                enter_connection[conn.to_stop_id] = conn
                in_trip[conn.to_stop_id] = conn.trip_id
                num_transfers[conn.to_stop_id] = potential_transfers

        # Check if destination is reachable
        if destination_stop_id not in enter_connection:
            return None

        # Reconstruct journey
        return self._reconstruct_journey(
            origin_stop_id,
            destination_stop_id,
            enter_connection,
            earliest_arrival
        )

    def _get_critical_connections(self, journey: Journey) -> Set[Tuple[str, str, str]]:
        """
        Get critical connections from a journey to ban for finding alternatives.

        Bans the longest leg or a leg with few alternatives to force different route.

        Args:
            journey: Journey to extract connections from

        Returns:
            Set of connection tuples (from_stop, to_stop, trip_id)
        """
        banned = set()

        # Find the longest leg (most constraining)
        longest_leg = max(journey.legs, key=lambda leg: leg.duration_minutes)

        # Ban all connections in the longest leg
        # This forces the algorithm to find a different route
        for leg in journey.legs:
            if leg == longest_leg:
                # Ban this specific trip segment
                banned.add((leg.from_stop_id, leg.to_stop_id, leg.trip_id))

        return banned

    def _is_unique_journey(self, new_journey: Journey, existing_journeys: List[Journey]) -> bool:
        """
        Check if a journey is sufficiently different from existing ones.

        Args:
            new_journey: New journey to check
            existing_journeys: List of existing journeys

        Returns:
            True if journey is unique enough to include
        """
        if not existing_journeys:
            return True

        for existing in existing_journeys:
            # Check if routes overlap significantly
            new_stops = set()
            for leg in new_journey.legs:
                new_stops.add(leg.from_stop_id)
                new_stops.add(leg.to_stop_id)

            existing_stops = set()
            for leg in existing.legs:
                existing_stops.add(leg.from_stop_id)
                existing_stops.add(leg.to_stop_id)

            # Calculate overlap
            overlap = len(new_stops & existing_stops)
            total = len(new_stops | existing_stops)

            if total > 0:
                overlap_ratio = overlap / total
                # If >80% overlap, consider it too similar
                if overlap_ratio > 0.8:
                    return False

        return True
