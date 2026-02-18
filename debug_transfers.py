#!/usr/bin/env python3
"""Debug script to check transfer hub detection and connections."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.graph.unified_transit_graph import UnifiedTransitGraph

print("=" * 70)
print("Transfer Hub Detection Diagnostics")
print("=" * 70)

# Load data
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

print(f"\n✓ Loaded {len(parser.stops)} stops")

# Build unified graph
print("\n🔧 Building unified transit graph...")
graph = UnifiedTransitGraph(parser)

# Get transfer hubs
hubs = graph.get_transfer_hubs()

print(f"\n📍 Found {len(hubs)} transfer hubs:")
print()

for hub_name, stop_ids in sorted(hubs.items()):
    print(f"Hub: {hub_name}")
    print(f"  Number of stops: {len(stop_ids)}")

    # Show modes at this hub
    modes = set()
    for stop_id in stop_ids:
        mode_id = parser.get_mode_for_stop(stop_id)
        if mode_id:
            mode_info = parser.get_mode_info(mode_id)
            modes.add(mode_info['name'])

    print(f"  Modes: {', '.join(sorted(modes))}")

    # Show a few stop names
    for i, stop_id in enumerate(stop_ids[:3]):
        stop = parser.get_stop(stop_id)
        if stop:
            print(f"    - {stop.stop_name} (ID: {stop_id})")

    if len(stop_ids) > 3:
        print(f"    ... and {len(stop_ids) - 3} more stops")
    print()

# Check specific stations
print("\n" + "=" * 70)
print("Checking Key Transfer Stations")
print("=" * 70)

key_stations = ['Richmond', 'Southern Cross', 'Flinders Street', 'Melbourne Central']

for station_name in key_stations:
    matching_stops = [s for s in parser.stops.values() if station_name.lower() in s.stop_name.lower()]

    print(f"\n🚉 {station_name}: {len(matching_stops)} stop(s)")

    modes_at_station = {}
    for stop in matching_stops[:10]:  # Limit to 10
        mode_id = parser.get_mode_for_stop(stop.stop_id)
        if mode_id:
            mode_name = parser.get_mode_info(mode_id)['name']
            if mode_name not in modes_at_station:
                modes_at_station[mode_name] = []
            modes_at_station[mode_name].append(stop)

    for mode_name, stops in modes_at_station.items():
        print(f"  {mode_name}: {len(stops)} stop(s)")
        for stop in stops[:2]:
            is_hub = graph.is_transfer_hub(stop.stop_id)
            hub_name = graph.get_hub_for_stop(stop.stop_id)
            hub_status = f"✓ Hub: {hub_name}" if is_hub else "✗ Not a hub"
            print(f"    - {stop.stop_name} ({stop.stop_id}) - {hub_status}")

# Count transfer connections
print("\n" + "=" * 70)
print("Transfer Connection Statistics")
print("=" * 70)

transfer_connections = [c for c in graph.connections if c.is_transfer]
regular_connections = [c for c in graph.connections if not c.is_transfer]

print(f"\n📊 Connection breakdown:")
print(f"  Total connections: {len(graph.connections):,}")
print(f"  Regular connections: {len(regular_connections):,}")
print(f"  Transfer connections: {len(transfer_connections):,}")

if transfer_connections:
    print(f"\n Sample transfer connections:")
    for i, conn in enumerate(transfer_connections[:5]):
        from_stop = parser.get_stop(conn.from_stop_id)
        to_stop = parser.get_stop(conn.to_stop_id)
        print(f"  {i+1}. {from_stop.stop_name if from_stop else conn.from_stop_id}")
        print(f"      → {to_stop.stop_name if to_stop else conn.to_stop_id}")
        print(f"      Walk: {conn.travel_time_seconds // 60} min")
        print()

print("=" * 70)
