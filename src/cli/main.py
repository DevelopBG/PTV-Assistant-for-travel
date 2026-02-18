"""
PTV Transit Assistant CLI - Command Line Interface.

Provides command-line access to journey planning functionality.
"""

import argparse
import sys
import os
from typing import Optional

from ..data.gtfs_parser import GTFSParser
from ..data.stop_index import StopIndex
from ..graph.transit_graph import TransitGraph
from ..routing.journey_planner import JourneyPlanner
from ..realtime.feed_fetcher import GTFSRealtimeFetcher
from ..realtime.integration import RealtimeIntegrator
from ..utils.logging_config import setup_logging, get_logger

logger = get_logger(__name__)

# Default GTFS data directory
DEFAULT_GTFS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "gtfs"
)


class TransitCLI:
    """Command-line interface for transit journey planning."""

    def __init__(self, gtfs_dir: Optional[str] = None):
        """
        Initialize CLI with GTFS data.

        Args:
            gtfs_dir: Path to GTFS data directory
        """
        self.gtfs_dir = gtfs_dir or DEFAULT_GTFS_DIR
        self.parser: Optional[GTFSParser] = None
        self.stop_index: Optional[StopIndex] = None
        self.graph: Optional[TransitGraph] = None
        self.planner: Optional[JourneyPlanner] = None

    def load(self) -> "TransitCLI":
        """Load GTFS data."""
        logger.info(f"Loading GTFS data from {self.gtfs_dir}")

        self.parser = GTFSParser(self.gtfs_dir)
        self.parser.load_all()

        self.stop_index = StopIndex(self.parser)
        self.graph = TransitGraph(self.parser)
        self.planner = JourneyPlanner(self.parser, self.graph)

        logger.info(
            f"Loaded: {len(self.parser.stops)} stops, "
            f"{len(self.parser.routes)} routes"
        )
        return self

    def search_stops(self, query: str, limit: int = 5, fuzzy: bool = True) -> None:
        """
        Search for stops and print results.

        Args:
            query: Search query
            limit: Maximum results
            fuzzy: Use fuzzy matching
        """
        if not self.stop_index:
            print("Error: GTFS data not loaded")
            return

        print(f"\nSearching for: '{query}'")
        print("-" * 50)

        if fuzzy:
            matches = self.stop_index.find_stop_fuzzy(query, limit=limit)
            if matches:
                for stop, score in matches:
                    print(f"  {stop.stop_name}")
                    print(f"    ID: {stop.stop_id}, Score: {score}%")
                print(f"\nFound {len(matches)} stop(s)")
            else:
                print("No stops found")
        else:
            stop = self.stop_index.find_stop_exact(query)
            if stop:
                print(f"  {stop.stop_name}")
                print(f"    ID: {stop.stop_id}")
                print("\nFound 1 stop")
            else:
                print("No exact match found")

    def plan_journey(
        self,
        origin: str,
        destination: str,
        departure_time: str,
        realtime: bool = False,
        max_transfers: int = 3
    ) -> None:
        """
        Plan and display a journey.

        Args:
            origin: Origin stop name or ID
            destination: Destination stop name or ID
            departure_time: Departure time (HH:MM:SS)
            realtime: Include realtime information
            max_transfers: Maximum transfers allowed
        """
        if not self.planner or not self.stop_index:
            print("Error: GTFS data not loaded")
            return

        # Resolve stop names to IDs
        origin_stop = self._resolve_stop(origin)
        if not origin_stop:
            print(f"Error: Origin stop not found: {origin}")
            return

        dest_stop = self._resolve_stop(destination)
        if not dest_stop:
            print(f"Error: Destination stop not found: {destination}")
            return

        print(f"\nPlanning journey:")
        print(f"  From: {origin_stop.stop_name} ({origin_stop.stop_id})")
        print(f"  To:   {dest_stop.stop_name} ({dest_stop.stop_id})")
        print(f"  Departure: {departure_time}")
        print("-" * 50)

        try:
            journey = self.planner.find_journey(
                origin_stop_id=origin_stop.stop_id,
                destination_stop_id=dest_stop.stop_id,
                departure_time=departure_time,
                max_transfers=max_transfers
            )
        except ValueError as e:
            print(f"Error: {e}")
            return

        if not journey:
            print("No journey found")
            return

        # Apply realtime if requested
        if realtime:
            api_key = os.environ.get("PTV_API_KEY")
            if api_key:
                try:
                    fetcher = GTFSRealtimeFetcher(api_key)
                    integrator = RealtimeIntegrator(fetcher, self.parser)
                    journey = integrator.apply_realtime_to_journey(journey)
                    print("(Realtime data applied)")
                except Exception as e:
                    print(f"(Realtime unavailable: {e})")
            else:
                print("(Set PTV_API_KEY for realtime data)")

        # Display journey
        self._display_journey(journey)

    def _resolve_stop(self, stop_input: str):
        """Resolve stop name or ID to Stop object."""
        # Check if it's a stop ID
        if self.parser:
            stop = self.parser.get_stop(stop_input)
            if stop:
                return stop

        # Try fuzzy search
        if self.stop_index:
            return self.stop_index.find_stop(stop_input, fuzzy=True)

        return None

    def _display_journey(self, journey) -> None:
        """Display journey details."""
        print(f"\nJourney Found!")
        print(f"  Depart: {journey.departure_time}")
        print(f"  Arrive: {journey.arrival_time}")

        if hasattr(journey, 'get_duration_minutes'):
            print(f"  Duration: {journey.get_duration_minutes()} minutes")

        if hasattr(journey, 'get_num_transfers'):
            print(f"  Transfers: {journey.get_num_transfers()}")

        print("\nLegs:")
        for i, leg in enumerate(journey.legs, 1):
            print(f"\n  Leg {i}:")
            print(f"    {leg.from_stop_name} → {leg.to_stop_name}")
            print(f"    Depart: {leg.departure_time} → Arrive: {leg.arrival_time}")

            if leg.route_name:
                print(f"    Route: {leg.route_name}")

            if hasattr(leg, 'get_mode_name'):
                print(f"    Mode: {leg.get_mode_name()}")

            if leg.has_realtime_data:
                if leg.departure_delay_seconds != 0:
                    delay_min = leg.departure_delay_seconds // 60
                    status = f"{delay_min} min late" if delay_min > 0 else f"{abs(delay_min)} min early"
                    print(f"    Status: {status}")
                if leg.platform_name:
                    print(f"    Platform: {leg.platform_name}")
                if leg.is_cancelled:
                    print(f"    ⚠️  CANCELLED")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="ptv",
        description="PTV Transit Assistant - Journey planning CLI"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search for stops by name"
    )
    search_parser.add_argument(
        "query",
        help="Stop name to search for"
    )
    search_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=5,
        help="Maximum number of results (default: 5)"
    )
    search_parser.add_argument(
        "--exact",
        action="store_true",
        help="Use exact matching instead of fuzzy"
    )

    # Plan command
    plan_parser = subparsers.add_parser(
        "plan",
        help="Plan a journey between two stops"
    )
    plan_parser.add_argument(
        "origin",
        help="Origin stop name or ID"
    )
    plan_parser.add_argument(
        "destination",
        help="Destination stop name or ID"
    )
    plan_parser.add_argument(
        "time",
        help="Departure time (HH:MM:SS)"
    )
    plan_parser.add_argument(
        "-r", "--realtime",
        action="store_true",
        help="Include realtime delay information"
    )
    plan_parser.add_argument(
        "-t", "--max-transfers",
        type=int,
        default=3,
        help="Maximum number of transfers (default: 3)"
    )

    # Common arguments
    parser.add_argument(
        "-d", "--data-dir",
        help="Path to GTFS data directory"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Setup logging
    if parsed.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
    setup_logging()

    if not parsed.command:
        parser.print_help()
        return 0

    try:
        cli = TransitCLI(gtfs_dir=parsed.data_dir)
        cli.load()

        if parsed.command == "search":
            cli.search_stops(
                query=parsed.query,
                limit=parsed.limit,
                fuzzy=not parsed.exact
            )

        elif parsed.command == "plan":
            cli.plan_journey(
                origin=parsed.origin,
                destination=parsed.destination,
                departure_time=parsed.time,
                realtime=parsed.realtime,
                max_transfers=parsed.max_transfers
            )

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
