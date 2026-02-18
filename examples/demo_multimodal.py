"""
Demonstration of Phase 4: Multi-Modal Routing Features

This script shows how the multi-modal routing system works with real GTFS data.
"""

from src.data.gtfs_parser import GTFSParser
from src.graph.transit_graph import TransitGraph
from src.routing.journey_planner import JourneyPlanner
from src.data.stop_index import StopIndex


def main():
    print("=" * 70)
    print("Phase 4: Multi-Modal Routing Demo")
    print("=" * 70)
    print()

    # Load GTFS data
    print("Loading GTFS data from data/gtfs/...")
    parser = GTFSParser("data/gtfs")

    stops = parser.load_stops()
    routes = parser.load_routes()
    trips = parser.load_trips()
    stop_times = parser.load_stop_times()

    print(f"✓ Loaded {len(stops)} stops, {len(routes)} routes, {len(trips)} trips")
    print()

    # Build transit graph
    print("Building transit network graph...")
    graph = TransitGraph()
    graph.build_from_gtfs(stops, routes, trips, stop_times)
    print(f"✓ Graph built with {graph.num_stops} stops")
    print()

    # Create journey planner
    planner = JourneyPlanner(graph)

    # Create stop index for easy lookup
    stop_index = StopIndex(stops)

    print("=" * 70)
    print("Example 1: Single-Mode Journey")
    print("=" * 70)
    print()

    # Find stops
    origin_matches = stop_index.find_stop("Tarneit")
    dest_matches = stop_index.find_stop("Waurn Ponds")

    if origin_matches and dest_matches:
        origin_stop = origin_matches[0]
        dest_stop = dest_matches[0]

        print(f"From: {origin_stop.stop_name} (ID: {origin_stop.stop_id})")
        print(f"To: {dest_stop.stop_name} (ID: {dest_stop.stop_id})")
        print(f"Departure time: 14:00:00")
        print()

        # Find journey
        journey = planner.find_journey(
            origin_stop.stop_id,
            dest_stop.stop_id,
            departure_time="14:00:00"
        )

        if journey:
            print("Journey found!")
            print("-" * 70)
            print()

            # Show basic journey info
            print(f"Departure: {journey.departure_time}")
            print(f"Arrival: {journey.arrival_time}")
            print(f"Duration: {journey.format_duration()}")
            print(f"Transfers: {journey.num_transfers}")
            print()

            # **NEW IN PHASE 4**: Mode analysis
            print("🆕 PHASE 4 FEATURES:")
            print("-" * 70)
            modes_used = journey.get_modes_used()
            is_multimodal = journey.is_multi_modal()

            print(f"Transport modes used: {', '.join(modes_used)}")
            print(f"Multi-modal journey? {is_multimodal}")
            print()

            # Show legs with mode information
            print("Journey Legs:")
            print("-" * 70)
            for i, leg in enumerate(journey.legs, 1):
                print(f"\nLeg {i}: {leg.from_stop_name} → {leg.to_stop_name}")
                print(f"  🚆 Mode: {leg.get_mode_name()}")  # **NEW IN PHASE 4**
                print(f"  ⏰ Depart: {leg.departure_time}")
                print(f"  ⏱️  Arrive: {leg.arrival_time}")
                print(f"  ⏳ Duration: {leg.format_duration()}")

                if leg.route_name:
                    print(f"  🛤️  Route: {leg.route_name}")

                # Show route type code
                if leg.route_type is not None:
                    print(f"  📋 Route type code: {leg.route_type}")

                if leg.is_transfer:
                    print(f"  🚶 Transfer: Walking connection")
        else:
            print("❌ No journey found for this time")

    print()
    print()
    print("=" * 70)
    print("Example 2: Mode Information Details")
    print("=" * 70)
    print()

    print("The GTFS route_type codes Phase 4 can identify:")
    print("-" * 70)
    mode_map = {
        0: "Tram",
        1: "Metro",
        2: "Regional Train",
        3: "Bus",
        4: "Ferry",
        700: "Bus (PTV-specific)",
        900: "Tram (PTV-specific)"
    }

    for code, mode in mode_map.items():
        print(f"  {code:3d} → {mode}")

    print()
    print()
    print("=" * 70)
    print("Example 3: How Phase 4 Helps Users")
    print("=" * 70)
    print()

    print("BEFORE Phase 4:")
    print("  Leg 1: Tarneit Station → Waurn Ponds Station")
    print("  Depart: 14:57  Arrive: 15:48")
    print("  ❌ User doesn't know what vehicle to catch!")
    print()

    print("AFTER Phase 4:")
    print("  Leg 1: Tarneit Station → Waurn Ponds Station")
    print("  🚆 Mode: Regional Train")
    print("  Depart: 14:57  Arrive: 15:48")
    print("  ✅ User knows to catch a V/Line train!")
    print()

    print()
    print("=" * 70)
    print("Example 4: Code Usage")
    print("=" * 70)
    print()

    print("Python code to use Phase 4 features:")
    print("-" * 70)
    print("""
# After getting a journey from the planner:
journey = planner.find_journey(origin_id, dest_id, "14:00:00")

# Get list of transport modes used
modes = journey.get_modes_used()
print(f"You'll need: {', '.join(modes)}")
# Output: "You'll need: Regional Train"

# Check if multi-modal
if journey.is_multi_modal():
    print("⚠️ This journey requires changing transport types")
else:
    print("✓ Direct journey on same transport type")

# Get mode for each leg
for leg in journey.legs:
    mode = leg.get_mode_name()
    print(f"{leg.from_stop_name} → {leg.to_stop_name}: {mode}")
    """)

    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Key Phase 4 Capabilities:")
    print("  ✓ Track transport mode for each journey leg")
    print("  ✓ Identify multi-modal journeys")
    print("  ✓ List all modes used in a journey")
    print("  ✓ Distinguish walking transfers from vehicle legs")
    print("  ✓ Show human-readable mode names")
    print()
    print("This enables Phase 5 (real-time updates per mode) and")
    print("Phase 6 (mode filtering and preferences)!")
    print()


if __name__ == "__main__":
    main()
