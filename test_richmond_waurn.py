#!/usr/bin/env python3
"""Test Richmond to Waurn Ponds journey."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.data.stop_index import StopIndex
from src.routing.multimodal_planner import MultiModalJourneyPlanner

print("="*60)
print("Testing: Richmond → Waurn Ponds")
print("="*60)

# Load data
print("\n1. Loading GTFS data...")
parser = MultiModalGTFSParser(base_gtfs_dir='data/gtfs', modes_to_load=['1', '2', '3'])
parser.load_all()
print(f"✓ Loaded {len(parser.stops)} stops")

# Check which modes have which stations
print("\n2. Checking if stops exist in each mode...")

for mode_id, mode_parser in parser.mode_parsers.items():
    mode_info = parser.get_mode_info(mode_id)
    print(f"\n{mode_info['name']} (Folder {mode_id}):")

    # Search for Richmond
    richmond_stops = [s for s in mode_parser.stops.values() if 'richmond' in s.stop_name.lower()]
    if richmond_stops:
        print(f"  Richmond stops: {len(richmond_stops)}")
        for s in richmond_stops[:3]:
            print(f"    - {s.stop_name} (ID: {s.stop_id})")
    else:
        print(f"  Richmond: NOT FOUND")

    # Search for Waurn Ponds
    waurn_stops = [s for s in mode_parser.stops.values() if 'waurn' in s.stop_name.lower()]
    if waurn_stops:
        print(f"  Waurn Ponds stops: {len(waurn_stops)}")
        for s in waurn_stops[:3]:
            print(f"    - {s.stop_name} (ID: {s.stop_id})")
    else:
        print(f"  Waurn Ponds: NOT FOUND")

# Try fuzzy matching
print("\n3. Using fuzzy matching to find stations...")
stop_index = StopIndex(parser)

richmond_matches = stop_index.find_stop_fuzzy('Richmond', limit=5)
print(f"\nRichmond matches ({len(richmond_matches)}):")
for stop, score in richmond_matches:
    mode = parser.get_mode_for_stop(stop.stop_id)
    mode_name = parser.get_mode_info(mode)['name'] if mode else 'Unknown'
    print(f"  {stop.stop_name} (score: {score}, mode: {mode_name}, ID: {stop.stop_id})")

waurn_matches = stop_index.find_stop_fuzzy('Waurn Ponds', limit=5)
print(f"\nWaurn Ponds matches ({len(waurn_matches)}):")
for stop, score in waurn_matches:
    mode = parser.get_mode_for_stop(stop.stop_id)
    mode_name = parser.get_mode_info(mode)['name'] if mode else 'Unknown'
    print(f"  {stop.stop_name} (score: {score}, mode: {mode_name}, ID: {stop.stop_id})")

# Try to plan journey
if richmond_matches and waurn_matches:
    print("\n4. Attempting to plan journey...")
    origin_stop = richmond_matches[0][0]
    dest_stop = waurn_matches[0][0]

    print(f"\nOrigin: {origin_stop.stop_name} (ID: {origin_stop.stop_id})")
    print(f"Destination: {dest_stop.stop_name} (ID: {dest_stop.stop_id})")

    planner = MultiModalJourneyPlanner(parser)

    journeys = planner.find_journeys_by_mode(
        origin_stop_id=origin_stop.stop_id,
        destination_stop_id=dest_stop.stop_id,
        departure_time=None
    )

    print("\n5. Results by mode:")
    for mode_type, journey in journeys.items():
        if journey:
            print(f"  {mode_type.upper()}: ✓ Found ({journey.duration_minutes}m, {journey.num_transfers} transfers)")
        else:
            print(f"  {mode_type.upper()}: ✗ No route")
else:
    print("\n✗ Could not find both stations!")

print("\n" + "="*60)
