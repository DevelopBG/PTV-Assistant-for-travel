#!/usr/bin/env python3
"""Test Richmond → Waurn Ponds with simplified single-route planner."""

import sys
import time
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.transfer_journey_planner import TransferJourneyPlanner

print("=" * 70)
print("Testing Simplified Single-Route Journey Planner")
print("=" * 70)

# Load data
print("\n📦 Loading GTFS data...")
start_time = time.time()
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()
load_time = time.time() - start_time
print(f"✓ Loaded {len(parser.stops)} stops in {load_time:.1f}s")

# Create planner
print("\n🔧 Initializing planner...")
start_time = time.time()
planner = TransferJourneyPlanner(parser)
init_time = time.time() - start_time
print(f"✓ Planner ready in {init_time:.1f}s")

# Test 1: Direct Route (Should be FAST)
print("\n" + "=" * 70)
print("TEST 1: Tarneit → Waurn Ponds (Direct V/Line)")
print("=" * 70)

start_time = time.time()
journey = planner.find_best_journey('47648', '47641')  # Tarneit → Waurn Ponds
query_time = time.time() - start_time

if journey:
    print(f"✅ SUCCESS in {query_time:.2f}s")
    print(f"  Duration: {journey.duration_minutes} min")
    print(f"  Transfers: {journey.num_transfers}")
    print(f"  Modes: {', '.join(journey.get_modes_used())}")
else:
    print(f"❌ FAILED in {query_time:.2f}s - No route found")

# Test 2: Richmond → Waurn Ponds (Multi-modal with transfer)
print("\n" + "=" * 70)
print("TEST 2: Richmond (V/Line) → Waurn Ponds (V/Line)")
print("=" * 70)
print("Expected: V/Line → Southern Cross → Transfer → V/Line")

start_time = time.time()
journey = planner.find_best_journey('12253', '47641')  # Richmond → Waurn Ponds
query_time = time.time() - start_time

if journey:
    print(f"✅ SUCCESS in {query_time:.2f}s")
    print(f"  Duration: {journey.duration_minutes} min")
    print(f"  Transfers: {journey.num_transfers}")
    print(f"  Modes: {', '.join(journey.get_modes_used())}")
    print(f"\n  Journey details:")
    for i, leg in enumerate(journey.legs, 1):
        if leg.is_transfer:
            print(f"    [{i}] 🚶 TRANSFER: {leg.from_stop_name} → {leg.to_stop_name} ({leg.duration_minutes}m)")
        else:
            print(f"    [{i}] {leg.get_mode_name()}: {leg.route_name}")
            print(f"        {leg.from_stop_name} → {leg.to_stop_name}")
            print(f"        {leg.departure_time} - {leg.arrival_time} ({leg.duration_minutes}m)")
else:
    print(f"❌ FAILED in {query_time:.2f}s - No route found")

print("\n" + "=" * 70)
print("Testing Complete!")
print("=" * 70)
