#!/usr/bin/env python3
"""Detailed debugging of multi-modal routing."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.journey_planner import JourneyPlanner
from src.graph.unified_transit_graph import UnifiedTransitGraph

# Load data
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

# Build graph
graph = UnifiedTransitGraph(parser)

# Create planner
planner = JourneyPlanner(parser, graph)

print("=" * 70)
print("Detailed Debug: Melbourne Central (Metro) → Southern Cross (Metro)")
print("=" * 70)

# First test: Can we go Melbourne Central (Metro) → Southern Cross (Metro)?
# This should be a simple Metro journey
melbourne_central = parser.get_stop('10922')  # Metro MC
southern_cross_stops = [s for s in parser.stops.values()
                        if 'southern cross station' == s.stop_name.lower()]

# Find Metro Southern Cross
metro_sc = None
for stop in southern_cross_stops:
    mode_id = parser.get_mode_for_stop(stop.stop_id)
    if mode_id == '2':  # Metro
        metro_sc = stop
        break

if melbourne_central and metro_sc:
    print(f"\nOrigin: {melbourne_central.stop_name} ({melbourne_central.stop_id})")
    print(f"Destination: {metro_sc.stop_name} ({metro_sc.stop_id})")
    print()

    # Try to find a simple Metro journey
    journey = planner.find_journey(
        origin_stop_id=melbourne_central.stop_id,
        destination_stop_id=metro_sc.stop_id,
        departure_time="08:00:00"
    )

    if journey:
        print(f"✅ Metro route exists: {journey.duration_minutes} min")
        print(f"  Departure: {journey.departure_time}")
        print(f"  Arrival: {journey.arrival_time}")
        print(f"  Legs: {len(journey.legs)}")
    else:
        print("❌ No Metro route found from Melbourne Central to Southern Cross!")
        print("   This means there's no direct Metro connection.")
        print("   User would need to change trains.")

# Test 2: Can we go from Melbourne Central to ANY V/Line stop that connects to Waurn Ponds?
print("\n" + "=" * 70)
print("Alternative: Check Tarneit (V/Line) → Waurn Ponds (V/Line)")
print("=" * 70)

tarneit = parser.get_stop('47648')
waurn = parser.get_stop('47641')

if tarneit and waurn:
    journey = planner.find_journey(
        origin_stop_id=tarneit.stop_id,
        destination_stop_id=waurn.stop_id,
        departure_time="08:00:00"
    )

    if journey:
        print(f"✅ V/Line route exists: {journey.duration_minutes} min")
    else:
        print("❌ V/Line route broken!")

print("\n" + "=" * 70)
