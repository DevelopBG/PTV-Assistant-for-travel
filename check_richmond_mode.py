#!/usr/bin/env python3
"""Check which transport mode Richmond Station (12253) belongs to."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser

# Load all modes
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

# Find Richmond stations
richmond_stops = [s for s in parser.stops.values() if 'richmond' in s.stop_name.lower() and 'station' in s.stop_name.lower()]

print("=" * 70)
print(f"Found {len(richmond_stops)} Richmond Station stops")
print("=" * 70)

# Group by mode
by_mode = {}
for stop in richmond_stops:
    mode_id = parser.get_mode_for_stop(stop.stop_id)
    if mode_id:
        mode_info = parser.get_mode_info(mode_id)
        mode_name = mode_info['name']
        if mode_name not in by_mode:
            by_mode[mode_name] = []
        by_mode[mode_name].append(stop)

for mode_name, stops in by_mode.items():
    print(f"\n{mode_name}: {len(stops)} stops")
    for stop in sorted(stops, key=lambda s: s.stop_id)[:5]:
        print(f"  - {stop.stop_name} (ID: {stop.stop_id})")
    if len(stops) > 5:
        print(f"  ... and {len(stops) - 5} more")

# Check stop 12253 specifically
print("\n" + "=" * 70)
print("Checking stop 12253 (from previous test):")
print("=" * 70)

stop_12253 = parser.get_stop('12253')
if stop_12253:
    print(f"Name: {stop_12253.stop_name}")
    mode_id = parser.get_mode_for_stop('12253')
    if mode_id:
        mode_info = parser.get_mode_info(mode_id)
        print(f"Mode: {mode_info['name']} (ID: {mode_id})")
        print(f"Route Type: {mode_info['route_type']}")
    else:
        print("ERROR: No mode found for this stop!")
else:
    print("ERROR: Stop 12253 not found!")

# Also check if there's a Metro Richmond
print("\n" + "=" * 70)
print("Searching for Metro Richmond:")
print("=" * 70)

if 'Metro Trains' in by_mode:
    metro_richmonds = by_mode['Metro Trains']
    if metro_richmonds:
        print(f"✓ Found {len(metro_richmonds)} Metro Richmond stops")
        for stop in metro_richmonds[:3]:
            print(f"  - {stop.stop_name} (ID: {stop.stop_id})")
    else:
        print("✗ No Metro Richmond stops found")
else:
    print("✗ No Metro Trains at Richmond")

# Check Tarneit for comparison (we know it works)
print("\n" + "=" * 70)
print("Checking Tarneit (known working station):")
print("=" * 70)

tarneit_stops = [s for s in parser.stops.values() if 'tarneit' in s.stop_name.lower()]
for stop in tarneit_stops[:2]:
    mode_id = parser.get_mode_for_stop(stop.stop_id)
    if mode_id:
        mode_info = parser.get_mode_info(mode_id)
        print(f"- {stop.stop_name} (ID: {stop.stop_id}) - Mode: {mode_info['name']}")
