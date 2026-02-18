"""
Transit network graph construction and querying.

This module builds a directed graph representing the transit network
where nodes are stops and edges are connections between stops on the
same trip with travel time weights.
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging
import networkx as nx
from datetime import datetime, timedelta

from ..data.models import Stop, Trip, StopTime
from ..data.gtfs_parser import GTFSParser

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents a connection between two stops."""
    from_stop_id: str
    to_stop_id: str
    trip_id: str
    departure_time: str
    arrival_time: str
    travel_time_seconds: int
    route_id: str
    route_type: Optional[int] = None  # GTFS route_type (0=tram, 1=metro, 2=rail, 3=bus, etc.)
    is_transfer: bool = False  # True if this is a walking transfer
    service_id: Optional[str] = None  # Service calendar ID for validating operating days

    def __post_init__(self):
        """Validate and convert types."""
        self.travel_time_seconds = int(self.travel_time_seconds)
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


class TransitGraph:
    """
    Transit network graph with stops as nodes and connections as edges.

    The graph is built from GTFS data and supports queries for:
    - Direct connections between stops
    - Travel times
    - Routes serving a stop
    - Neighboring stops
    """

    def __init__(self, gtfs_parser: Optional[GTFSParser] = None):
        """
        Initialize transit graph.

        Args:
            gtfs_parser: Optional GTFSParser with loaded GTFS data.
                        If provided, graph will be built automatically.
        """
        self.graph = nx.DiGraph()
        self.parser = gtfs_parser
        self.connections: List[Connection] = []
        self._sorted_connections: Optional[List[Connection]] = None  # Cached sorted connections

        if gtfs_parser:
            self.build_from_parser(gtfs_parser)

    def build_from_parser(self, parser: GTFSParser) -> 'TransitGraph':
        """
        Build graph from GTFS parser data.

        Args:
            parser: GTFSParser with loaded GTFS data

        Returns:
            Self for method chaining
        """
        logger.info("Building transit graph from GTFS data")
        self.parser = parser
        self._add_stop_nodes()
        self._add_trip_connections()
        self._add_transfer_edges()
        self._sort_connections()  # Pre-sort for faster journey planning
        stats = self.get_stats()
        logger.info(
            f"Graph built: {stats['num_stops']} stops, {stats['num_connections']} edges, "
            f"{stats['num_total_connections']} total connections"
        )
        return self

    def _sort_connections(self) -> None:
        """
        Pre-sort connections by departure time for efficient journey planning.

        Transfer connections are sorted to the END so they're processed after
        regular timetabled connections. This ensures earliest_arrival times
        are updated by regular connections before transfers are considered.
        """
        logger.debug(f"Pre-sorting {len(self.connections)} connections by departure time")
        self._sorted_connections = sorted(
            self.connections,
            key=lambda c: (
                1 if c.is_transfer else 0,  # Transfers last
                self._time_to_seconds(c.departure_time)  # Then by time
            )
        )

    def _time_to_seconds(self, time_str: str) -> int:
        """Convert GTFS time string to seconds since midnight."""
        parts = time_str.split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

    def get_sorted_connections(self) -> List[Connection]:
        """
        Get connections sorted by departure time.

        Returns:
            List of connections sorted by departure time (cached).
        """
        if self._sorted_connections is None:
            self._sort_connections()
        return self._sorted_connections

    def _add_stop_nodes(self):
        """Add all stops as nodes to the graph."""
        if not self.parser:
            return

        logger.debug(f"Adding {len(self.parser.stops)} stop nodes to graph")
        for stop_id, stop in self.parser.stops.items():
            self.graph.add_node(
                stop_id,
                stop_name=stop.stop_name,
                lat=stop.stop_lat,
                lon=stop.stop_lon,
                location_type=stop.location_type,
                parent_station=stop.parent_station
            )

    def _add_trip_connections(self):
        """Add edges for consecutive stops in each trip."""
        if not self.parser:
            return

        logger.debug(f"Processing connections for {len(self.parser.stop_times)} trips")
        for trip_id, stop_times in self.parser.stop_times.items():
            # Stop times are already sorted by stop_sequence
            for i in range(len(stop_times) - 1):
                current_stop = stop_times[i]
                next_stop = stop_times[i + 1]

                # Calculate travel time
                travel_time = self._calculate_travel_time(
                    current_stop.departure_time,
                    next_stop.arrival_time
                )

                # Get trip and route info
                trip = self.parser.trips.get(trip_id)
                route_id = trip.route_id if trip else ""
                service_id = trip.service_id if trip else None

                # Get route type for multi-modal support
                route_type = None
                if route_id:
                    route = self.parser.routes.get(route_id)
                    route_type = route.route_type if route else None

                # Create connection
                connection = Connection(
                    from_stop_id=current_stop.stop_id,
                    to_stop_id=next_stop.stop_id,
                    trip_id=trip_id,
                    departure_time=current_stop.departure_time,
                    arrival_time=next_stop.arrival_time,
                    travel_time_seconds=travel_time,
                    route_id=route_id,
                    route_type=route_type,
                    is_transfer=False,
                    service_id=service_id
                )
                self.connections.append(connection)

                # Add edge to graph (or update with minimum travel time)
                self._add_or_update_edge(
                    current_stop.stop_id,
                    next_stop.stop_id,
                    travel_time,
                    route_id,
                    trip_id
                )

    def _calculate_travel_time(self, departure_time: str, arrival_time: str) -> int:
        """
        Calculate travel time in seconds between two GTFS times.

        GTFS times can exceed 24:00:00 for trips past midnight.

        Args:
            departure_time: Departure time in HH:MM:SS format
            arrival_time: Arrival time in HH:MM:SS format

        Returns:
            Travel time in seconds
        """
        def parse_gtfs_time(time_str: str) -> int:
            """Convert GTFS time string to seconds since midnight."""
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        dep_seconds = parse_gtfs_time(departure_time)
        arr_seconds = parse_gtfs_time(arrival_time)

        return arr_seconds - dep_seconds

    def _add_or_update_edge(
        self,
        from_stop: str,
        to_stop: str,
        travel_time: int,
        route_id: str,
        trip_id: str
    ):
        """
        Add edge or update existing edge with minimum travel time.

        Args:
            from_stop: Source stop ID
            to_stop: Destination stop ID
            travel_time: Travel time in seconds
            route_id: Route ID
            trip_id: Trip ID
        """
        if self.graph.has_edge(from_stop, to_stop):
            # Update with minimum travel time
            current_time = self.graph[from_stop][to_stop]['weight']
            if travel_time < current_time:
                self.graph[from_stop][to_stop]['weight'] = travel_time
                self.graph[from_stop][to_stop]['min_travel_time'] = travel_time

            # Add route and trip to lists
            routes = self.graph[from_stop][to_stop].get('routes', set())
            routes.add(route_id)
            self.graph[from_stop][to_stop]['routes'] = routes

            trips = self.graph[from_stop][to_stop].get('trips', set())
            trips.add(trip_id)
            self.graph[from_stop][to_stop]['trips'] = trips
        else:
            # Add new edge
            self.graph.add_edge(
                from_stop,
                to_stop,
                weight=travel_time,
                min_travel_time=travel_time,
                routes={route_id},
                trips={trip_id}
            )

    def _add_transfer_edges(self):
        """Add edges for transfers between stops."""
        if not self.parser or not self.parser.transfers:
            return

        logger.debug(f"Adding {len(self.parser.transfers)} transfer edges")
        for transfer in self.parser.transfers:
            # Add transfer edge with min_transfer_time as weight
            # Default to 120 seconds (2 minutes) if not specified
            transfer_time = int(transfer.min_transfer_time) if transfer.min_transfer_time else 120

            self.graph.add_edge(
                transfer.from_stop_id,
                transfer.to_stop_id,
                weight=transfer_time,
                min_travel_time=transfer_time,
                is_transfer=True,
                transfer_type=transfer.transfer_type
            )

    def get_neighbors(self, stop_id: str) -> List[str]:
        """
        Get all stops directly reachable from a given stop.

        Args:
            stop_id: Stop ID to query

        Returns:
            List of stop IDs reachable from the given stop
        """
        if not self.graph.has_node(stop_id):
            return []

        return list(self.graph.successors(stop_id))

    def get_travel_time(self, from_stop_id: str, to_stop_id: str) -> Optional[int]:
        """
        Get minimum travel time between two directly connected stops.

        Args:
            from_stop_id: Source stop ID
            to_stop_id: Destination stop ID

        Returns:
            Travel time in seconds, or None if no direct connection
        """
        if not self.graph.has_edge(from_stop_id, to_stop_id):
            return None

        return self.graph[from_stop_id][to_stop_id]['weight']

    def get_routes_between(self, from_stop_id: str, to_stop_id: str) -> Set[str]:
        """
        Get all routes that directly connect two stops.

        Args:
            from_stop_id: Source stop ID
            to_stop_id: Destination stop ID

        Returns:
            Set of route IDs, or empty set if no direct connection
        """
        if not self.graph.has_edge(from_stop_id, to_stop_id):
            return set()

        return self.graph[from_stop_id][to_stop_id].get('routes', set())

    def get_stop_info(self, stop_id: str) -> Optional[Dict]:
        """
        Get stop information from graph.

        Args:
            stop_id: Stop ID to query

        Returns:
            Dictionary with stop attributes, or None if stop not found
        """
        if not self.graph.has_node(stop_id):
            return None

        return dict(self.graph.nodes[stop_id])

    def get_connections_from(self, stop_id: str) -> List[Connection]:
        """
        Get all connections departing from a stop.

        Args:
            stop_id: Stop ID to query

        Returns:
            List of Connection objects
        """
        return [conn for conn in self.connections if conn.from_stop_id == stop_id]

    def get_connections_between(self, from_stop_id: str, to_stop_id: str) -> List[Connection]:
        """
        Get all connections between two stops.

        Args:
            from_stop_id: Source stop ID
            to_stop_id: Destination stop ID

        Returns:
            List of Connection objects
        """
        return [
            conn for conn in self.connections
            if conn.from_stop_id == from_stop_id and conn.to_stop_id == to_stop_id
        ]

    def get_stats(self) -> Dict:
        """
        Get graph statistics.

        Returns:
            Dictionary with node count, edge count, and other stats
        """
        return {
            'num_stops': self.graph.number_of_nodes(),
            'num_connections': self.graph.number_of_edges(),
            'num_total_connections': len(self.connections),
            'avg_degree': sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1)
        }

    def has_stop(self, stop_id: str) -> bool:
        """Check if stop exists in graph."""
        return self.graph.has_node(stop_id)

    def has_connection(self, from_stop_id: str, to_stop_id: str) -> bool:
        """Check if direct connection exists between stops."""
        return self.graph.has_edge(from_stop_id, to_stop_id)
