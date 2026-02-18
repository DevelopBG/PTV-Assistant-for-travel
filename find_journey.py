#!/usr/bin/env python3
"""
Quick Journey Finder - Find a journey between two stations

Usage:
    python find_journey.py "Tarneit" "Waurn Ponds"
    python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00"
    python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00" --realtime

Environment Variables:
    PTV_API_KEY - Required for realtime features
"""

import sys
import os
from datetime import datetime
from src.data.gtfs_parser import GTFSParser
from src.data.stop_index import StopIndex
from src.graph.transit_graph import TransitGraph
from src.routing.journey_planner import JourneyPlanner
from src.realtime.feed_fetcher import GTFSRealtimeFetcher
from src.realtime.integration import RealtimeIntegrator

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def find_journey(origin_name, destination_name, departure_time=None, use_realtime=False):
    """Find a journey between two stations."""

    # Default to current time if not specified
    if not departure_time:
        now = datetime.now()
        departure_time = now.strftime("%H:%M:%S")
        print(f"No departure time specified, using current time: {departure_time}")
        print()

    print(f"🔍 Finding journey: {origin_name} → {destination_name}")
    print(f"⏰ Departure time: {departure_time}")
    if use_realtime:
        print(f"🔴 Realtime mode: ENABLED")
    print()

    # Load GTFS data - try multiple locations
    print("Loading data...")
    gtfs_paths = ["data/gtfs/1", "data/gtfs/2", "data/gtfs/3", "data/gtfs"]
    parser = None

    for path in gtfs_paths:
        try:
            parser = GTFSParser(path)
            parser.load_stops()
            parser.load_routes()
            parser.load_trips()
            parser.load_stop_times()
            print(f"✓ Loaded {len(parser.stops)} stops from {path}")
            break
        except FileNotFoundError:
            continue

    if parser is None:
        print("❌ No GTFS data found. Please download and extract GTFS data.")
        print("See data/gtfs/README.md for instructions.")
        return
    print()

    # Build graph
    print("Building transit network...")
    graph = TransitGraph(parser)
    print("✓ Network ready")
    print()

    # Find stations
    print("Finding stations...")
    stop_index = StopIndex(parser)

    origin = stop_index.find_stop(origin_name)
    if not origin:
        print(f"❌ Could not find station: {origin_name}")
        return
    print(f"✓ Origin: {origin.stop_name}")

    destination = stop_index.find_stop(destination_name)
    if not destination:
        print(f"❌ Could not find station: {destination_name}")
        return
    print(f"✓ Destination: {destination.stop_name}")
    print()

    # Plan journey
    print("Planning journey...")
    planner = JourneyPlanner(parser, graph)

    journey = planner.find_journey(
        origin.stop_id,
        destination.stop_id,
        departure_time=departure_time
    )

    if not journey:
        print("❌ No journey found for this time")
        print()
        print("Try a different time or check if the route is available.")
        return

    # Apply realtime updates (Phase 5)
    if use_realtime:
        api_key = os.getenv('PTV_API_KEY')
        if not api_key:
            print()
            print("⚠️  Realtime requested but PTV_API_KEY not set.")
            print("   Set PTV_API_KEY environment variable to enable realtime features.")
            print("   Using scheduled times only.")
            print()
        else:
            try:
                print("Fetching realtime data...")
                fetcher = GTFSRealtimeFetcher(api_key=api_key)
                integrator = RealtimeIntegrator(fetcher=fetcher)
                journey = integrator.apply_realtime_to_journey(journey, mode='vline')

                if journey.has_realtime_data:
                    print(f"✓ Realtime data applied")
                else:
                    print("⚠️  No realtime data available for this journey")
                print()
            except Exception as e:
                print(f"⚠️  Realtime fetch failed: {e}")
                print("   Using scheduled times only.")
                print()

    # Display journey
    print()
    print("=" * 80)
    print("✅ JOURNEY FOUND!")
    print("=" * 80)
    print()

    print(journey.format_summary())

    # Phase 4: Multi-modal analysis
    modes = journey.get_modes_used()
    print()
    print("=" * 80)
    print("🚆 TRANSPORT INFORMATION")
    print("=" * 80)
    print()
    print(f"Modes: {', '.join(modes)}")
    print(f"Multi-modal journey: {'Yes' if journey.is_multi_modal() else 'No'}")
    print()

    if journey.num_transfers > 0:
        print(f"⚠️  This journey has {journey.num_transfers} transfer(s).")
        print("   Make sure to allow time to change between services.")
    else:
        print("✓ Direct journey - no transfers needed!")

    # Phase 5: Realtime status
    if use_realtime and journey.has_realtime_data:
        print()
        if not journey.is_realtime_valid:
            print(f"❌ JOURNEY NO LONGER VALID: {journey.invalidity_reason}")
        elif journey.has_significant_delays():
            print(f"⚠️  SIGNIFICANT DELAYS: {journey.get_delay_summary()}")
        elif journey.total_delay_seconds != 0:
            print(f"ℹ️  {journey.get_delay_summary()}")

    print()
    print("=" * 80)
    print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python find_journey.py <origin> <destination> [departure_time] [--realtime]")
        print()
        print("Examples:")
        print('  python find_journey.py "Tarneit" "Waurn Ponds"')
        print('  python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00"')
        print('  python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00" --realtime')
        print('  python find_journey.py "Tarneit" "Geelong"')
        print()
        print("Options:")
        print("  --realtime    Apply real-time delays and cancellations (requires PTV_API_KEY)")
        print()
        sys.exit(1)

    origin = sys.argv[1]
    destination = sys.argv[2]

    # Parse optional arguments
    departure_time = None
    use_realtime = False

    for arg in sys.argv[3:]:
        if arg == '--realtime':
            use_realtime = True
        elif ':' in arg:  # Looks like a time
            departure_time = arg

    find_journey(origin, destination, departure_time, use_realtime)


if __name__ == "__main__":
    main()
