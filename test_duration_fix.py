#!/usr/bin/env python3
"""Test duration calculation fix for Richmond to Waurn Ponds."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.multimodal_parser import MultiModalGTFSParser
from src.routing.transfer_journey_planner import TransferJourneyPlanner

print("=" * 70)
print("Testing Duration Fix: Richmond to Waurn Ponds")
print("=" * 70)

# Load all modes
print("\n1. Loading GTFS data...")
parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
parser.load_all()
print(f"   Loaded {len(parser.stops)} stops")

# Initialize transfer-aware planner
print("\n2. Initializing TransferJourneyPlanner...")
planner = TransferJourneyPlanner(parser)
print("   Planner ready!")

# Find best journey
print("\n3. Finding best journey Richmond to Waurn Ponds...")
journey = planner.find_best_journey(
    origin_stop_id='12253',      # Richmond Station (V/Line)
    destination_stop_id='47641',  # Waurn Ponds Station
    departure_time=None,
    max_transfers=4
)

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

if journey:
    print(f"\nRoute found!")
    print(f"  Origin: {journey.origin_stop_name}")
    print(f"  Destination: {journey.destination_stop_name}")
    print(f"  Departure: {journey.departure_time}")
    print(f"  Arrival: {journey.arrival_time}")
    print(f"  Duration: {journey.duration_minutes} min ({journey.format_duration()})")
    print(f"  Transfers: {journey.num_transfers}")
    print(f"  Modes: {', '.join(journey.get_modes_used())}")

    print(f"\n  Leg Details:")
    for i, leg in enumerate(journey.legs, 1):
        mode = leg.get_mode_name()
        print(f"    {i}. {mode}: {leg.from_stop_name} to {leg.to_stop_name}")
        print(f"       {leg.departure_time} to {leg.arrival_time} ({leg.format_duration()})")

    # Check if duration is correct
    if journey.duration_minutes < 0:
        print(f"\n  ERROR: Negative duration detected!")
    elif journey.duration_minutes > 300:
        print(f"\n  WARNING: Duration seems too long (>5 hours)")
    elif 60 <= journey.duration_minutes <= 150:
        print(f"\n  PASS: Duration is reasonable for this journey")
else:
    print("\nNo route found!")

print("\n" + "=" * 70)
