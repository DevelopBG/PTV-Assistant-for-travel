#!/usr/bin/env python3
"""
Test Metro to V/Line transfer journey planning.
Using East Richmond (Metro) → Waurn Ponds (V/Line).
"""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.transfer_journey_planner import TransferJourneyPlanner

print("=" * 70)
print("Testing Metro → V/Line Transfer Journey Planning")
print("=" * 70)

# Load data
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()

# Create planner
planner = TransferJourneyPlanner(parser)

# Test: East Richmond (Metro) → Waurn Ponds (V/Line)
print("\n" + "=" * 70)
print("TEST: East Richmond (Metro) → Waurn Ponds (V/Line)")
print("=" * 70)
print("Expected: Metro → transfer at hub → V/Line")
print()

# Use East Richmond Station (Metro)
east_richmond = parser.get_stop('12251')  # East Richmond (Metro)
waurn_ponds = parser.get_stop('47641')    # Waurn Ponds (V/Line)

if east_richmond and waurn_ponds:
    print(f"Origin: {east_richmond.stop_name} (ID: {east_richmond.stop_id})")
    mode_from = parser.get_mode_for_stop(east_richmond.stop_id)
    print(f"  Mode: {parser.get_mode_info(mode_from)['name']}")

    print(f"\nDestination: {waurn_ponds.stop_name} (ID: {waurn_ponds.stop_id})")
    mode_to = parser.get_mode_for_stop(waurn_ponds.stop_id)
    print(f"  Mode: {parser.get_mode_info(mode_to)['name']}")
    print()

    print("🔍 Searching for transfer routes...")
    journeys = planner.find_journeys(
        origin_stop_id=east_richmond.stop_id,
        destination_stop_id=waurn_ponds.stop_id,
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

# Also test Flinders Street → Waurn Ponds (should work - Flinders is a hub)
print("\n" + "=" * 70)
print("TEST: Flinders Street (Metro) → Waurn Ponds (V/Line)")
print("=" * 70)

flinders_stops = [s for s in parser.stops.values()
                  if 'flinders street station' == s.stop_name.lower()]
if flinders_stops and waurn_ponds:
    # Find Metro Flinders
    metro_flinders = None
    for stop in flinders_stops:
        mode_id = parser.get_mode_for_stop(stop.stop_id)
        if mode_id == '2':  # Metro
            metro_flinders = stop
            break

    if metro_flinders:
        print(f"Origin: {metro_flinders.stop_name}")
        print(f"Destination: {waurn_ponds.stop_name}")
        print()

        journeys = planner.find_journeys(
            origin_stop_id=metro_flinders.stop_id,
            destination_stop_id=waurn_ponds.stop_id,
            num_routes=3,
            max_transfers=4
        )

        if journeys:
            print(f"✅ Found {len(journeys)} route(s)")
            for i, journey in enumerate(journeys, 1):
                modes = ' → '.join(journey.get_modes_used())
                print(f"  Route {i}: {journey.duration_minutes}m, {journey.num_transfers} transfers, {modes}")
        else:
            print("❌ No routes found")

print("\n" + "=" * 70)
