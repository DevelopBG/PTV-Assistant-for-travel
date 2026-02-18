#!/usr/bin/env python3
"""Test full multi-modal journey: Metro → Transfer → V/Line."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.transfer_journey_planner import TransferJourneyPlanner

# Load data
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()
planner = TransferJourneyPlanner(parser)

print("=" * 70)
print("Full Multi-Modal Journey Test")
print("=" * 70)

# Test 1: Melbourne Central (Metro) → Waurn Ponds (V/Line)
print("\n" + "=" * 70)
print("TEST 1: Melbourne Central (Metro) → Waurn Ponds (V/Line)")
print("=" * 70)
print("Expected: Metro → Southern Cross → Transfer → V/Line to Waurn Ponds")
print()

melbourne_central_stops = [s for s in parser.stops.values()
                          if 'melbourne central station' == s.stop_name.lower()]
waurn_ponds = parser.get_stop('47641')

# Find Metro Melbourne Central
metro_mc = None
for stop in melbourne_central_stops:
    mode_id = parser.get_mode_for_stop(stop.stop_id)
    if mode_id == '2':  # Metro
        metro_mc = stop
        break

if metro_mc and waurn_ponds:
    print(f"Origin: {metro_mc.stop_name} ({metro_mc.stop_id})")
    print(f"Destination: {waurn_ponds.stop_name} ({waurn_ponds.stop_id})")
    print()

    journeys = planner.find_journeys(
        origin_stop_id=metro_mc.stop_id,
        destination_stop_id=waurn_ponds.stop_id,
        num_routes=3,
        max_transfers=4
    )

    if journeys:
        print(f"✅ SUCCESS! Found {len(journeys)} route(s):\n")

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
        print("❌ No routes found")
else:
    print("ERROR: Could not find Melbourne Central or Waurn Ponds")

# Test 2: Flinders Street (Metro) → Geelong (V/Line)
print("\n" + "=" * 70)
print("TEST 2: Flinders Street (Metro) → Geelong (V/Line)")
print("=" * 70)

flinders_stops = [s for s in parser.stops.values()
                 if 'flinders street station' == s.stop_name.lower()]
geelong_stops = [s for s in parser.stops.values()
                if 'geelong station' == s.stop_name.lower()]

metro_flinders = None
for stop in flinders_stops:
    mode_id = parser.get_mode_for_stop(stop.stop_id)
    if mode_id == '2':  # Metro
        metro_flinders = stop
        break

vline_geelong = None
if geelong_stops:
    for stop in geelong_stops:
        mode_id = parser.get_mode_for_stop(stop.stop_id)
        if mode_id == '1':  # V/Line
            vline_geelong = stop
            break

if metro_flinders and vline_geelong:
    print(f"\nOrigin: {metro_flinders.stop_name}")
    print(f"Destination: {vline_geelong.stop_name}")
    print()

    journeys = planner.find_journeys(
        origin_stop_id=metro_flinders.stop_id,
        destination_stop_id=vline_geelong.stop_id,
        num_routes=2,
        max_transfers=3
    )

    if journeys:
        print(f"✅ Found {len(journeys)} route(s)")
        for i, journey in enumerate(journeys, 1):
            modes = ' → '.join(journey.get_modes_used())
            print(f"  Route {i}: {journey.duration_minutes}m, {journey.num_transfers} transfers, {modes}")
    else:
        print("❌ No routes found")
else:
    print("  Skipping (stations not found)")

print("\n" + "=" * 70)
print("Testing Complete!")
print("=" * 70)
