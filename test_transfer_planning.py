#!/usr/bin/env python3
"""
Test script for transfer-aware journey planning.
Tests the Richmond → Waurn Ponds journey that previously failed.
"""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.transfer_journey_planner import TransferJourneyPlanner

print("=" * 70)
print("Testing Transfer-Aware Multi-Modal Journey Planning")
print("=" * 70)

# Load all transport modes (V/Line, Metro, Trams)
print("\n📦 Loading GTFS data for all transport modes...")
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

print(f"✓ Loaded {len(parser.stops)} stops across all modes")
print(f"✓ Modes: {', '.join([parser.get_mode_info(m)['name'] for m in parser.get_loaded_modes()])}")

# Create transfer-aware planner
print("\n🔧 Initializing transfer-aware journey planner...")
planner = TransferJourneyPlanner(parser)

# Test Case 1: Richmond → Waurn Ponds (Previously Failed)
print("\n" + "=" * 70)
print("TEST CASE 1: Richmond → Waurn Ponds")
print("=" * 70)
print("This journey previously failed because:")
print("  - Richmond is on Metro Trains (not V/Line)")
print("  - Waurn Ponds is on V/Line (Warrnambool line)")
print("  - Requires transfer from Metro to V/Line")
print()

# Find Richmond station
richmond_stops = [s for s in parser.stops.values() if 'richmond' in s.stop_name.lower() and 'station' in s.stop_name.lower()]
waurn_stops = [s for s in parser.stops.values() if 'waurn' in s.stop_name.lower()]

if richmond_stops and waurn_stops:
    richmond = richmond_stops[0]
    waurn = waurn_stops[0]

    print(f"Origin: {richmond.stop_name} (ID: {richmond.stop_id})")
    print(f"Destination: {waurn.stop_name} (ID: {waurn.stop_id})")
    print()

    print("🔍 Searching for routes (max 3 alternatives, max 4 transfers)...")
    journeys = planner.find_journeys(
        origin_stop_id=richmond.stop_id,
        destination_stop_id=waurn.stop_id,
        num_routes=3,
        max_transfers=4
    )

    if journeys:
        print(f"\n✅ SUCCESS! Found {len(journeys)} route(s):\n")

        for i, journey in enumerate(journeys, 1):
            print(f"{'='*70}")
            print(f"ROUTE {i}:")
            print(f"{'='*70}")
            print(f"⏱  {journey.departure_time} → {journey.arrival_time} ({journey.duration_minutes} minutes)")
            print(f"🔄 {journey.num_transfers} transfer(s)")
            print(f"🚉 Modes: {' → '.join(journey.get_modes_used())}")
            print()

            for j, leg in enumerate(journey.legs, 1):
                if leg.is_transfer:
                    print(f"  [{j}] 🚶 TRANSFER - {leg.route_name}")
                    print(f"      From: {leg.from_stop_name}")
                    print(f"      To:   {leg.to_stop_name}")
                    print(f"      Walk: {leg.duration_minutes} min")
                else:
                    print(f"  [{j}] {leg.get_mode_name()} - {leg.route_name}")
                    print(f"      From: {leg.from_stop_name} at {leg.departure_time}")
                    print(f"      To:   {leg.to_stop_name} at {leg.arrival_time}")
                    print(f"      Duration: {leg.duration_minutes} min ({leg.num_stops} stops)")
                print()
    else:
        print("\n❌ No routes found")
        print("This might indicate an issue with:")
        print("  - Transfer hub detection")
        print("  - Inter-mode transfer connections")
        print("  - Connection scan algorithm")
else:
    print("❌ Could not find Richmond or Waurn Ponds stations")

# Test Case 2: Simple Direct Route (Sanity Check)
print("\n" + "=" * 70)
print("TEST CASE 2: Tarneit → Waurn Ponds (Direct Route Sanity Check)")
print("=" * 70)

tarneit_stops = [s for s in parser.stops.values() if 'tarneit' in s.stop_name.lower()]
if tarneit_stops and waurn_stops:
    tarneit = tarneit_stops[0]

    print(f"Origin: {tarneit.stop_name}")
    print(f"Destination: {waurn.stop_name}")
    print()

    journeys = planner.find_journeys(
        origin_stop_id=tarneit.stop_id,
        destination_stop_id=waurn.stop_id,
        num_routes=3,
        max_transfers=4
    )

    if journeys:
        print(f"✅ Found {len(journeys)} route(s)")
        for i, journey in enumerate(journeys, 1):
            modes = ' → '.join(journey.get_modes_used())
            print(f"  Route {i}: {journey.duration_minutes}m, {journey.num_transfers} transfers, {modes}")
    else:
        print("❌ No routes found (unexpected - these should connect)")

print("\n" + "=" * 70)
print("Testing Complete!")
print("=" * 70)
