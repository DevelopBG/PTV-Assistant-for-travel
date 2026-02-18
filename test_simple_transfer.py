#!/usr/bin/env python3
"""Test simplest possible transfer: within same hub."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.transfer_journey_planner import TransferJourneyPlanner
from src.graph.unified_transit_graph import UnifiedTransitGraph

# Load data
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

# Build graph
graph = UnifiedTransitGraph(parser)
planner = TransferJourneyPlanner(parser)

print("=" * 70)
print("Simple Transfer Test: Within Southern Cross Hub")
print("=" * 70)

# Get Southern Cross stops
southern_cross_stops = [s for s in parser.stops.values()
                        if 'southern cross station' == s.stop_name.lower()]

print(f"\nFound {len(southern_cross_stops)} Southern Cross Station stops")

# Group by mode
by_mode = {}
for stop in southern_cross_stops:
    mode_id = parser.get_mode_for_stop(stop.stop_id)
    if mode_id:
        mode_name = parser.get_mode_info(mode_id)['name']
        if mode_name not in by_mode:
            by_mode[mode_name] = []
        by_mode[mode_name].append(stop)

for mode_name, stops in by_mode.items():
    print(f"\n{mode_name}: {len(stops)} stops")
    for stop in stops[:2]:
        is_hub = graph.is_transfer_hub(stop.stop_id)
        print(f"  - {stop.stop_name} ({stop.stop_id}) - Hub: {is_hub}")

# Test: Can we "transfer" between two Southern Cross stops?
print("\n" + "=" * 70)
print("TEST: Southern Cross (Metro) → Southern Cross (V/Line)")
print("=" * 70)

if 'Metro Trains' in by_mode and 'V/Line Regional' in by_mode:
    metro_sc = by_mode['Metro Trains'][0]
    vline_sc = by_mode['V/Line Regional'][0]

    print(f"\nFrom: {metro_sc.stop_name} ({metro_sc.stop_id}) - Metro")
    print(f"To:   {vline_sc.stop_name} ({vline_sc.stop_id}) - V/Line")

    # Check if there's a direct transfer connection
    print("\nLooking for transfer connection...")
    transfer_found = False
    for conn in graph.connections:
        if conn.is_transfer and conn.from_stop_id == metro_sc.stop_id and conn.to_stop_id == vline_sc.stop_id:
            print(f"✓ Found transfer connection: {conn.travel_time_seconds // 60} min walk")
            transfer_found = True
            break

    if not transfer_found:
        print("✗ No direct transfer connection found between these stops")

    # Try to plan a journey
    print("\n🔍 Planning journey...")
    journeys = planner.find_journeys(
        origin_stop_id=metro_sc.stop_id,
        destination_stop_id=vline_sc.stop_id,
        num_routes=1,
        max_transfers=1
    )

    if journeys:
        print(f"✅ Found {len(journeys)} route(s)")
        journey = journeys[0]
        print(f"  Duration: {journey.duration_minutes} min")
        print(f"  Transfers: {journey.num_transfers}")
        for i, leg in enumerate(journey.legs, 1):
            print(f"  Leg {i}: {leg.get_mode_name()} - {leg.route_name}")
    else:
        print("❌ No routes found (even for same-hub transfer!)")

# Also test if basic V/Line routing still works
print("\n" + "=" * 70)
print("TEST: Tarneit → Waurn Ponds (V/Line only, sanity check)")
print("=" * 70)

tarneit = parser.get_stop('47648')
waurn = parser.get_stop('47641')

if tarneit and waurn:
    journeys = planner.find_journeys(
        origin_stop_id=tarneit.stop_id,
        destination_stop_id=waurn.stop_id,
        num_routes=1
    )

    if journeys:
        print(f"✅ Basic V/Line routing works: {journeys[0].duration_minutes} min")
    else:
        print("❌ ERROR: Basic V/Line routing broken!")
