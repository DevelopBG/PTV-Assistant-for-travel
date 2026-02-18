"""
Unified Multi-Modal Transit Graph.

Combines GTFS data from multiple transport modes (trains, trams, buses)
into a single unified graph with inter-mode transfer connections.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import logging

from ..data.multimodal_parser import MultiModalGTFSParser
from ..utils.geo import haversine_distance, calculate_transfer_time_seconds
from .transit_graph import TransitGraph, Connection

logger = logging.getLogger(__name__)


class UnifiedTransitGraph(TransitGraph):
    """
    Unified graph combining multiple transport modes with transfer connections.

    Extends TransitGraph to:
    - Merge connections from all transport modes
    - Identify transfer hubs (stops serving multiple modes)
    - Add inter-mode transfer edges with walking times
    """

    def __init__(self, multimodal_parser: MultiModalGTFSParser):
        """
        Initialize unified multi-modal transit graph.

        Args:
            multimodal_parser: MultiModalGTFSParser with loaded data for all modes
        """
        # Don't call super().__init__ with parser - we'll build manually
        super().__init__(gtfs_parser=None)

        self.multimodal_parser = multimodal_parser
        self.parser = multimodal_parser  # For compatibility with base class

        # Track which mode each stop/route belongs to
        self.stop_modes: Dict[str, str] = {}  # stop_id -> mode_id
        self.transfer_hubs: Dict[str, List[str]] = {}  # hub_name -> [stop_ids]

        # Build the unified graph
        self.build_unified_graph()

    def build_unified_graph(self):
        """Build unified graph from all transport modes."""
        logger.info("Building unified multi-modal transit graph...")

        # Step 1: Add all stop nodes
        self._add_all_stop_nodes()

        # Step 2: Add connections from all modes
        self._add_all_mode_connections()

        # Step 3: Identify transfer hubs
        self._identify_transfer_hubs()

        # Step 4: Add inter-mode transfer edges
        self._add_intermode_transfers()

        # Step 5: Sort connections for CSA
        self._sort_connections()

        # Log statistics
        stats = self.get_stats()
        logger.info(
            f"Unified graph built: {stats['num_stops']} stops, "
            f"{stats['num_connections']} connections, "
            f"{len(self.transfer_hubs)} transfer hubs"
        )

    def _add_all_stop_nodes(self):
        """Add stop nodes from all transport modes."""
        for stop_id, stop in self.multimodal_parser.stops.items():
            self.graph.add_node(
                stop_id,
                name=stop.stop_name,
                lat=float(stop.stop_lat),
                lon=float(stop.stop_lon),
                location_type=stop.location_type
            )

            # Track which mode this stop belongs to
            mode_id = self.multimodal_parser.get_mode_for_stop(stop_id)
            if mode_id:
                self.stop_modes[stop_id] = mode_id

        logger.debug(f"Added {len(self.multimodal_parser.stops)} stop nodes")

    def _add_all_mode_connections(self):
        """Add trip connections from all transport modes."""
        total_connections = 0

        for mode_id, mode_parser in self.multimodal_parser.mode_parsers.items():
            mode_info = self.multimodal_parser.get_mode_info(mode_id)
            logger.debug(f"Adding connections for {mode_info['name']}...")

            # Add connections for each trip in this mode
            for trip_id, stop_times in mode_parser.stop_times.items():
                if len(stop_times) < 2:
                    continue  # Need at least 2 stops

                # Get trip and route info
                trip = mode_parser.get_trip(trip_id)
                if not trip:
                    continue

                route = mode_parser.get_route(trip.route_id)
                route_type = int(route.route_type) if route else None

                # Create connections between consecutive stops
                for i in range(len(stop_times) - 1):
                    st_from = stop_times[i]
                    st_to = stop_times[i + 1]

                    # Calculate travel time
                    dep_seconds = self._time_to_seconds(st_from.departure_time)
                    arr_seconds = self._time_to_seconds(st_to.arrival_time)
                    travel_time = arr_seconds - dep_seconds

                    # Handle overnight trips (arrival next day)
                    if travel_time < 0:
                        travel_time += 86400  # Add 24 hours

                    # Create connection
                    conn = Connection(
                        from_stop_id=st_from.stop_id,
                        to_stop_id=st_to.stop_id,
                        trip_id=trip_id,
                        departure_time=st_from.departure_time,
                        arrival_time=st_to.arrival_time,
                        travel_time_seconds=travel_time,
                        route_id=trip.route_id,
                        route_type=route_type,
                        is_transfer=False,
                        service_id=trip.service_id  # Include service calendar ID
                    )

                    self.connections.append(conn)
                    total_connections += 1

            logger.debug(f"  Added connections for {mode_info['name']}")

        logger.info(f"Added {total_connections} trip connections from all modes")

    def _identify_transfer_hubs(self):
        """
        Identify transfer hub stations where multiple modes meet.

        Uses three methods:
        1. Exact name matching (e.g., "Southern Cross Station")
        2. Coordinate proximity (<100m = same location)
        3. Parent station relationships
        """
        logger.debug("Identifying transfer hubs...")

        # Group stops by name
        stops_by_name: Dict[str, List[str]] = defaultdict(list)
        for stop_id, stop in self.multimodal_parser.stops.items():
            # Normalize name (remove platform info, lowercase)
            normalized_name = self._normalize_stop_name(stop.stop_name)
            stops_by_name[normalized_name].append(stop_id)

        # Find hubs with multiple stops (potential transfer points)
        for name, stop_ids in stops_by_name.items():
            if len(stop_ids) > 1:
                # Check if they're from different modes
                modes = set(self.stop_modes.get(sid, 'unknown') for sid in stop_ids)
                if len(modes) > 1:
                    # Multiple modes serve this station - it's a transfer hub!
                    self.transfer_hubs[name] = stop_ids
                    logger.debug(f"  Hub found: {name} ({len(stop_ids)} stops, {len(modes)} modes)")

        # Also identify nearby stops (coordinate-based matching)
        self._identify_nearby_hubs()

        logger.info(f"Identified {len(self.transfer_hubs)} transfer hubs")

    def _identify_nearby_hubs(self):
        """Identify hubs by coordinate proximity (same physical location)."""
        # Get all unique stop coordinates
        processed = set()

        for stop_id1, stop1 in self.multimodal_parser.stops.items():
            if stop_id1 in processed:
                continue

            lat1 = float(stop1.stop_lat)
            lon1 = float(stop1.stop_lon)
            nearby_stops = [stop_id1]

            # Find all stops within 100m
            for stop_id2, stop2 in self.multimodal_parser.stops.items():
                if stop_id2 == stop_id1 or stop_id2 in processed:
                    continue

                lat2 = float(stop2.stop_lat)
                lon2 = float(stop2.stop_lon)
                distance = haversine_distance(lat1, lon1, lat2, lon2)

                if distance <= 100:  # Within 100 meters
                    nearby_stops.append(stop_id2)
                    processed.add(stop_id2)

            # If multiple stops nearby from different modes, it's a hub
            if len(nearby_stops) > 1:
                modes = set(self.stop_modes.get(sid, 'unknown') for sid in nearby_stops)
                if len(modes) > 1:
                    hub_name = f"{stop1.stop_name} (Coord Hub)"
                    # Merge with existing hub if name matches
                    base_name = self._normalize_stop_name(stop1.stop_name)
                    if base_name in self.transfer_hubs:
                        # Add to existing hub
                        self.transfer_hubs[base_name].extend(
                            s for s in nearby_stops if s not in self.transfer_hubs[base_name]
                        )
                    else:
                        self.transfer_hubs[hub_name] = nearby_stops

            processed.add(stop_id1)

    def _add_intermode_transfers(self):
        """Add walking transfer connections between stops at transfer hubs."""
        transfer_count = 0

        for hub_name, stop_ids in self.transfer_hubs.items():
            # Create transfer edges between all pairs of stops at this hub
            for i, origin_stop_id in enumerate(stop_ids):
                origin_stop = self.multimodal_parser.get_stop(origin_stop_id)
                if not origin_stop:
                    continue

                origin_lat = float(origin_stop.stop_lat)
                origin_lon = float(origin_stop.stop_lon)

                for dest_stop_id in stop_ids[i+1:]:  # Only forward pairs to avoid duplicates
                    if origin_stop_id == dest_stop_id:
                        continue

                    dest_stop = self.multimodal_parser.get_stop(dest_stop_id)
                    if not dest_stop:
                        continue

                    dest_lat = float(dest_stop.stop_lat)
                    dest_lon = float(dest_stop.stop_lon)

                    # Calculate walking time
                    walking_seconds = calculate_transfer_time_seconds(
                        origin_lat, origin_lon,
                        dest_lat, dest_lon
                    )

                    # Create bidirectional transfer connections
                    # (transfers can happen in both directions)
                    for from_id, to_id in [(origin_stop_id, dest_stop_id),
                                          (dest_stop_id, origin_stop_id)]:
                        # Create transfer connection for every minute of the day
                        # This allows transferring at any time
                        transfer_conn = Connection(
                            from_stop_id=from_id,
                            to_stop_id=to_id,
                            trip_id="TRANSFER",
                            departure_time="00:00:00",  # Available all day
                            arrival_time=self._seconds_to_time(walking_seconds),
                            travel_time_seconds=walking_seconds,
                            route_id="WALK",
                            route_type=None,
                            is_transfer=True,
                            service_id=None  # Transfers have no service calendar (always available)
                        )

                        self.connections.append(transfer_conn)
                        transfer_count += 1

        logger.info(f"Added {transfer_count} inter-mode transfer connections")

    def _normalize_stop_name(self, name: str) -> str:
        """
        Normalize stop name for matching.

        Removes platform numbers, direction indicators, and extra whitespace.
        """
        # Remove common suffixes
        name = name.replace(" Station", "")
        name = name.replace(" Railway Station", "")
        name = name.replace(" Platform", "")

        # Remove numbers (platform numbers)
        import re
        name = re.sub(r'\s+#?\d+$', '', name)  # Remove trailing numbers
        name = re.sub(r'\s+\(.*?\)$', '', name)  # Remove parenthetical info

        # Normalize whitespace
        name = ' '.join(name.split())

        return name.strip().lower()

    def _time_to_seconds(self, time_str: str) -> int:
        """Convert GTFS time string to seconds since midnight."""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def _seconds_to_time(self, seconds: int) -> str:
        """Convert seconds to GTFS time string (HH:MM:SS)."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_transfer_hubs(self) -> Dict[str, List[str]]:
        """Get all identified transfer hubs."""
        return self.transfer_hubs

    def is_transfer_hub(self, stop_id: str) -> bool:
        """Check if a stop is part of a transfer hub."""
        for stop_ids in self.transfer_hubs.values():
            if stop_id in stop_ids:
                return True
        return False

    def get_hub_for_stop(self, stop_id: str) -> Optional[str]:
        """Get the hub name for a given stop (if it's part of a hub)."""
        for hub_name, stop_ids in self.transfer_hubs.items():
            if stop_id in stop_ids:
                return hub_name
        return None
