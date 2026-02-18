#!/usr/bin/env python3
"""Test script to understand which GTFS data is being loaded."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.gtfs_parser import GTFSParser

# Test each folder
folders = {
    '1': 'V/Line Regional (route_type=2)',
    '2': 'Metro Trains (route_type=400)',
    '3': 'Trams (route_type=0)',
    '4': 'Buses (route_type=3)',
    '5': 'SkyBus (route_type=204)',
    '6': 'Regional Buses (route_type=701)',
    '10': 'Unknown (route_type=102)',
    '11': 'Unknown (route_type=3)'
}

print("=" * 80)
print("GTFS Data Folder Analysis")
print("=" * 80)
print()

for folder, desc in folders.items():
    path = f"data/gtfs/{folder}"
    try:
        parser = GTFSParser(path)
        parser.load_stops()
        parser.load_routes()

        # Get first route to verify route_type
        first_route = list(parser.routes.values())[0] if parser.routes else None
        route_type = first_route.route_type if first_route else 'N/A'

        print(f"Folder {folder}: {desc}")
        print(f"  Stops: {len(parser.stops)}")
        print(f"  Routes: {len(parser.routes)}")
        print(f"  Route Type: {route_type}")

        # Sample stop names
        sample_stops = list(parser.stops.values())[:3]
        print(f"  Sample stops:")
        for stop in sample_stops:
            print(f"    - {stop.stop_name}")
        print()

    except Exception as e:
        print(f"Folder {folder}: ERROR - {e}")
        print()

print("=" * 80)
print("App Loading Priority Test (from app.py)")
print("=" * 80)
print()

GTFS_PATHS = [
    "data/gtfs/2",  # Metro Trains Melbourne
    "data/gtfs/1",  # V/Line Regional Rail
    "data/gtfs/3",  # Melbourne Trams
    "data/gtfs",
    "gtfs_data",
    "gtfs",
]

for path in GTFS_PATHS:
    try:
        parser = GTFSParser(path)
        parser.load_stops()
        parser.load_routes()
        print(f"✓ SUCCESS: Loaded {len(parser.stops)} stops from {path}")
        print(f"  First stop: {list(parser.stops.values())[0].stop_name}")
        break
    except FileNotFoundError:
        print(f"✗ NOT FOUND: {path}")
        continue
