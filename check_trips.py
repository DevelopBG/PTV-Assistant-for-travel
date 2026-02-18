#!/usr/bin/env python3
"""Check if there are actual trips from Richmond to Waurn Ponds."""

import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.data.gtfs_parser import GTFSParser

print("="*60)
print("Analyzing V/Line trips: Richmond → Waurn Ponds")
print("="*60)

# Load V/Line data only (folder 1)
parser = GTFSParser('data/gtfs/1')
parser.load_all()

print(f"\n✓ Loaded {len(parser.stops)} stops")
print(f"✓ Loaded {len(parser.routes)} routes")
print(f"✓ Loaded {len(parser.trips)} trips")

# Find Richmond and Waurn Ponds stop IDs
richmond_stops = [s for s in parser.stops.values() if 'richmond' in s.stop_name.lower() and 'station' in s.stop_name.lower()]
waurn_stops = [s for s in parser.stops.values() if 'waurn' in s.stop_name.lower()]

print(f"\nRichmond Station variants: {len(richmond_stops)}")
for s in richmond_stops[:3]:
    print(f"  - {s.stop_name} (ID: {s.stop_id})")

print(f"\nWaurn Ponds Station variants: {len(waurn_stops)}")
for s in waurn_stops:
    print(f"  - {s.stop_name} (ID: {s.stop_id})")

# Check which trips serve Richmond
print("\n" + "="*60)
print("Checking which trips serve Richmond Station...")
print("="*60)

richmond_stop_ids = {s.stop_id for s in richmond_stops}
trips_via_richmond = set()

for trip_id, stop_times in parser.stop_times.items():
    stop_ids_in_trip = {st.stop_id for st in stop_times}
    if richmond_stop_ids & stop_ids_in_trip:  # Intersection
        trips_via_richmond.add(trip_id)

print(f"\nTrips serving Richmond: {len(trips_via_richmond)}")

# Check which of those trips also serve Waurn Ponds
waurn_stop_ids = {s.stop_id for s in waurn_stops}
trips_via_both = set()

for trip_id in trips_via_richmond:
    stop_times = parser.stop_times.get(trip_id, [])
    stop_ids_in_trip = {st.stop_id for st in stop_times}
    if waurn_stop_ids & stop_ids_in_trip:
        trips_via_both.add(trip_id)

print(f"Trips serving BOTH Richmond AND Waurn Ponds: {len(trips_via_both)}")

if trips_via_both:
    print("\n✓ Direct trips exist! Let's examine one:")
    sample_trip_id = list(trips_via_both)[0]
    trip = parser.get_trip(sample_trip_id)
    route = parser.get_route(trip.route_id)

    print(f"\nTrip ID: {sample_trip_id}")
    print(f"Route: {route.route_long_name}")
    print(f"Headsign: {trip.trip_headsign}")

    # Show stop sequence
    stop_times = parser.get_trip_stop_times(sample_trip_id)
    print(f"\nStop sequence ({len(stop_times)} stops):")
    for st in stop_times[:10]:  # First 10 stops
        stop = parser.get_stop(st.stop_id)
        print(f"  {st.stop_sequence:3d}. {stop.stop_name:40s} {st.departure_time}")
    if len(stop_times) > 10:
        print(f"  ... ({len(stop_times) - 10} more stops)")

else:
    print("\n✗ NO direct trips found from Richmond to Waurn Ponds!")
    print("\nPossible reasons:")
    print("  1. Richmond might only be on Metro lines (not V/Line)")
    print("  2. Need to transfer at Southern Cross or Geelong")
    print("  3. Richmond on V/Line data might be a different platform")

    # Check which routes serve Richmond
    print("\n" + "="*60)
    print("Routes serving Richmond:")
    print("="*60)
    richmond_routes = set()
    for trip_id in trips_via_richmond:
        trip = parser.get_trip(trip_id)
        richmond_routes.add(trip.route_id)

    for route_id in richmond_routes:
        route = parser.get_route(route_id)
        print(f"  - {route.route_long_name}")

    # Check which routes serve Waurn Ponds
    print("\n" + "="*60)
    print("Routes serving Waurn Ponds:")
    print("="*60)
    trips_via_waurn = set()
    for trip_id, stop_times in parser.stop_times.items():
        stop_ids_in_trip = {st.stop_id for st in stop_times}
        if waurn_stop_ids & stop_ids_in_trip:
            trips_via_waurn.add(trip_id)

    waurn_routes = set()
    for trip_id in trips_via_waurn:
        trip = parser.get_trip(trip_id)
        waurn_routes.add(trip.route_id)

    for route_id in waurn_routes:
        route = parser.get_route(route_id)
        print(f"  - {route.route_long_name}")

print("\n" + "="*60)
