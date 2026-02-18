"""
Real Journey Finder - Tarneit to Waurn Ponds

This script demonstrates the complete journey planning system using real GTFS data.
It shows how to:
1. Load GTFS data
2. Build the transit network graph
3. Find stations by name
4. Plan optimal journeys
5. Display multi-modal journey information
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.gtfs_parser import GTFSParser
from src.data.stop_index import StopIndex
from src.graph.transit_graph import TransitGraph
from src.routing.journey_planner import JourneyPlanner


def print_header(text):
    """Print a formatted header."""
    print()
    print("=" * 80)
    print(f"  {text}")
    print("=" * 80)
    print()


def print_section(text):
    """Print a formatted section header."""
    print()
    print("-" * 80)
    print(f"  {text}")
    print("-" * 80)
    print()


def main():
    print_header("PTV Transit Assistant - Real Journey Finder")

    print("This demonstration uses real GTFS data from V/Line regional trains.")
    print("We'll find journeys between Tarneit Station and Waurn Ponds Station.")
    print()

    # =========================================================================
    # Step 1: Load GTFS Data
    # =========================================================================
    print_section("Step 1: Loading GTFS Data")

    gtfs_path = project_root / "data" / "gtfs"
    print(f"Loading from: {gtfs_path}")
    print()

    parser = GTFSParser(str(gtfs_path))

    print("Loading GTFS files...")
    parser.load_stops()
    print(f"✓ Loaded {len(parser.stops)} stops")

    parser.load_routes()
    print(f"✓ Loaded {len(parser.routes)} routes")

    parser.load_trips()
    print(f"✓ Loaded {len(parser.trips)} trips")

    parser.load_stop_times()
    total_stop_times = sum(len(times) for times in parser.stop_times.values())
    print(f"✓ Loaded {total_stop_times:,} stop times across {len(parser.stop_times)} trips")

    # Reference the internal dictionaries
    stops = parser.stops
    routes = parser.routes
    trips = parser.trips
    stop_times = parser.stop_times

    # =========================================================================
    # Step 2: Build Transit Network Graph
    # =========================================================================
    print_section("Step 2: Building Transit Network Graph")

    print("Creating graph from GTFS data...")
    graph = TransitGraph(parser)

    print(f"✓ Graph built successfully!")
    stats = graph.get_stats()
    print(f"  - Nodes (stops): {stats['num_stops']}")
    print(f"  - Total connections: {stats['num_total_connections']:,}")
    print(f"  - Graph edges: {stats['num_connections']:,}")

    # =========================================================================
    # Step 3: Find Stations
    # =========================================================================
    print_section("Step 3: Finding Stations")

    stop_index = StopIndex(parser)

    # Find Tarneit
    print("Searching for 'Tarneit'...")
    origin = stop_index.find_stop("Tarneit")

    if not origin:
        print("❌ Tarneit Station not found!")
        return

    print(f"✓ Found: {origin.stop_name} (ID: {origin.stop_id})")
    print(f"  Location: {origin.stop_lat}, {origin.stop_lon}")

    # Find Waurn Ponds
    print()
    print("Searching for 'Waurn Ponds'...")
    destination = stop_index.find_stop("Waurn Ponds")

    if not destination:
        print("❌ Waurn Ponds Station not found!")
        return

    print(f"✓ Found: {destination.stop_name} (ID: {destination.stop_id})")
    print(f"  Location: {destination.stop_lat}, {destination.stop_lon}")

    # =========================================================================
    # Step 4: Plan Journeys at Different Times
    # =========================================================================
    print_section("Step 4: Finding Journeys at Different Departure Times")

    planner = JourneyPlanner(parser, graph)

    # Test times
    test_times = [
        "06:00:00",  # Early morning
        "08:00:00",  # Morning peak
        "12:00:00",  # Midday
        "14:00:00",  # Afternoon (2 PM as mentioned)
        "17:00:00",  # Evening peak
        "20:00:00",  # Evening
    ]

    journeys_found = []

    for departure_time in test_times:
        print(f"\nSearching for journey departing after {departure_time}...")

        journey = planner.find_journey(
            origin.stop_id,
            destination.stop_id,
            departure_time=departure_time
        )

        if journey:
            journeys_found.append((departure_time, journey))
            print(f"  ✓ Found journey:")
            print(f"    Depart: {journey.departure_time}")
            print(f"    Arrive: {journey.arrival_time}")
            print(f"    Duration: {journey.format_duration()}")
            print(f"    Transfers: {journey.num_transfers}")

            # Show mode information (Phase 4 feature!)
            modes = journey.get_modes_used()
            print(f"    Modes: {', '.join(modes)}")
        else:
            print(f"  ❌ No journey found")

    # =========================================================================
    # Step 5: Display Detailed Journey Information
    # =========================================================================
    if journeys_found:
        print_section("Step 5: Detailed Journey Information")

        # Show the 2 PM journey in detail
        selected_time = "14:00:00"
        selected_journey = None

        for dep_time, journey in journeys_found:
            if dep_time == selected_time:
                selected_journey = journey
                break

        if not selected_journey and journeys_found:
            # Use first available journey if 2 PM not found
            selected_time, selected_journey = journeys_found[0]
            print(f"Note: No journey found at 2 PM, showing {selected_time} journey instead")
            print()

        if selected_journey:
            print(f"Journey Details: {origin.stop_name} → {destination.stop_name}")
            print(f"Requested departure: {selected_time}")
            print()

            # Use the built-in format_summary method
            summary = selected_journey.format_summary()
            print(summary)

            # Additional Phase 4 analysis
            print()
            print("=" * 80)
            print("PHASE 4: Multi-Modal Analysis")
            print("=" * 80)
            print()

            modes_used = selected_journey.get_modes_used()
            is_multimodal = selected_journey.is_multi_modal()

            print(f"Transport Modes Used: {', '.join(modes_used)}")
            print(f"Multi-modal Journey: {'Yes' if is_multimodal else 'No'}")
            print()

            if is_multimodal:
                print("⚠️  This journey requires changing between different transport types.")
                print("    Make sure to allow extra time for transfers!")
            else:
                print("✓ Direct journey on the same transport mode - no mode changes needed.")

            # Show what each leg uses
            print()
            print("Journey Breakdown:")
            for i, leg in enumerate(selected_journey.legs, 1):
                mode_icon = {
                    "Metro": "🚇",
                    "Regional Train": "🚆",
                    "Tram": "🚊",
                    "Bus": "🚌",
                    "Ferry": "⛴️",
                    "Walking": "🚶"
                }.get(leg.get_mode_name(), "🚉")

                print(f"  {mode_icon} Leg {i}: {leg.get_mode_name()}")
                print(f"     {leg.from_stop_name} → {leg.to_stop_name}")
                print(f"     {leg.departure_time} - {leg.arrival_time} ({leg.format_duration()})")

    # =========================================================================
    # Summary Statistics
    # =========================================================================
    print_section("Summary Statistics")

    print(f"Origin: {origin.stop_name}")
    print(f"Destination: {destination.stop_name}")
    print()
    print(f"Departure times tested: {len(test_times)}")
    print(f"Journeys found: {len(journeys_found)}")
    print(f"Success rate: {len(journeys_found)/len(test_times)*100:.0f}%")
    print()

    if journeys_found:
        durations = [j.duration_minutes for _, j in journeys_found]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        print(f"Journey Duration Statistics:")
        print(f"  Average: {int(avg_duration)} minutes")
        print(f"  Fastest: {min_duration} minutes")
        print(f"  Slowest: {max_duration} minutes")

    print()
    print_header("Demo Complete!")
    print()
    print("This demonstrates:")
    print("  ✓ Phase 1: GTFS data parsing")
    print("  ✓ Phase 2: Transit network graph construction")
    print("  ✓ Phase 3: Journey planning with Connection Scan Algorithm")
    print("  ✓ Phase 4: Multi-modal routing with mode tracking")
    print()
    print("Next: Phase 5 will add real-time delays and cancellations!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
