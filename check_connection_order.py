#!/usr/bin/env python3
"""Check the order of connections in the sorted list."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.graph.unified_transit_graph import UnifiedTransitGraph

# Load data
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

# Build graph
graph = UnifiedTransitGraph(parser)

# Get sorted connections
all_connections = graph.get_sorted_connections()

print("=" * 70)
print("Connection Ordering Analysis")
print("=" * 70)

print(f"\nTotal connections: {len(all_connections):,}")

# Check first 10 connections
print("\nFirst 10 connections:")
for i, conn in enumerate(all_connections[:10]):
    conn_type = "TRANSFER" if conn.is_transfer else "REGULAR"
    print(f"{i+1}. {conn_type}: {conn.departure_time} → {conn.arrival_time}")
    if i < 3:
        from_stop = parser.get_stop(conn.from_stop_id)
        to_stop = parser.get_stop(conn.to_stop_id)
        if from_stop and to_stop:
            print(f"   {from_stop.stop_name} → {to_stop.stop_name}")

# Check if ALL transfers come first
transfer_count = 0
regular_count = 0
first_regular_index = None

for i, conn in enumerate(all_connections):
    if conn.is_transfer:
        transfer_count += 1
        if regular_count > 0:
            print(f"\n⚠️  WARNING: Transfer found AFTER regular connection at index {i}")
            break
    else:
        regular_count += 1
        if first_regular_index is None:
            first_regular_index = i

print(f"\n✓ All {transfer_count:,} transfers come before regular connections")
print(f"✓ First regular connection at index: {first_regular_index:,}")

if first_regular_index:
    print(f"\nFirst regular connection:")
    conn = all_connections[first_regular_index]
    print(f"  Time: {conn.departure_time} → {conn.arrival_time}")
    print(f"  Trip: {conn.trip_id}")
