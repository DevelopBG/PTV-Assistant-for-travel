#!/usr/bin/env python3
"""Simple test to debug journey planning"""

import sys

# Fix Windows encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from datetime import datetime
from src.data.gtfs_parser import GTFSParser
from src.data.stop_index import StopIndex
from src.graph.transit_graph import TransitGraph
from src.routing.journey_planner import JourneyPlanner

print("Loading GTFS data from data/gtfs/2...")
parser = GTFSParser("data/gtfs/2")
parser.load_stops()
parser.load_routes()
parser.load_trips()
parser.load_stop_times()
print(f"✓ Loaded {len(parser.stops)} stops")

print("\nBuilding graph...")
graph = TransitGraph(parser)
planner = JourneyPlanner(parser, graph)
print("✓ Graph ready")

print("\nSearching for stations...")
stop_index = StopIndex(parser)

# Find Flinders Street
flinders_matches = stop_index.find_stop_fuzzy("Flinders Street", limit=5)
print(f"\nFlinders Street matches:")
for stop, score in flinders_matches:
    print(f"  {stop.stop_name} (ID: {stop.stop_id}) - Score: {score}")

# Find Southern Cross
southern_matches = stop_index.find_stop_fuzzy("Southern Cross", limit=5)
print(f"\nSouthern Cross matches:")
for stop, score in southern_matches:
    print(f"  {stop.stop_name} (ID: {stop.stop_id}) - Score: {score}")

if flinders_matches and southern_matches:
    origin = flinders_matches[0][0]
    dest = southern_matches[0][0]

    print(f"\nPlanning journey from {origin.stop_name} to {dest.stop_name}...")

    # Use current time
    departure_time = datetime.now().strftime("%H:%M:%S")
    print(f"Departure time: {departure_time}")

    journey = planner.find_journey(
        origin.stop_id,
        dest.stop_id,
        departure_time
    )

    if journey:
        print("\n✓ Journey found!")
        print(journey.format_summary())
    else:
        print("\n✗ No journey found")

        # Debug: Check if these stops have any connections
        print(f"\nChecking connections from {origin.stop_name}...")
        neighbors = graph.get_neighbors(origin.stop_id)
        print(f"  Neighbors: {len(neighbors)}")
        if neighbors:
            print(f"  Sample neighbors: {list(neighbors)[:5]}")
