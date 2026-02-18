#!/usr/bin/env python3
"""
View GTFS Realtime Feed - CLI Tool

Simple CLI tool to view real-time trip updates from PTV.
Uses the refactored feed_fetcher module.
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.realtime.feed_fetcher import GTFSRealtimeFetcher


def display_feed_header(feed):
    """Display feed header information."""
    print("=" * 80)
    print("GTFS Realtime Feed - Trip Updates")
    print("=" * 80)
    print(f"GTFS Realtime Version: {feed.header.gtfs_realtime_version}")
    print(f"Incrementality: {feed.header.incrementality}")

    if feed.header.HasField('timestamp'):
        timestamp = datetime.fromtimestamp(feed.header.timestamp)
        print(f"Feed Timestamp: {timestamp} ({feed.header.timestamp})")

    print(f"Number of entities: {len(feed.entity)}")
    print("=" * 80)
    print()


def display_trip_update(entity):
    """Display a single trip update."""
    if not entity.HasField('trip_update'):
        return

    trip_update = entity.trip_update
    trip = trip_update.trip

    print(f"Entity ID: {entity.id}")
    print(f"  Trip ID: {trip.trip_id}")

    if trip.HasField('route_id'):
        print(f"  Route ID: {trip.route_id}")

    if trip.HasField('direction_id'):
        print(f"  Direction: {trip.direction_id}")

    if trip.HasField('start_date'):
        print(f"  Start Date: {trip.start_date}")

    if trip.HasField('start_time'):
        print(f"  Start Time: {trip.start_time}")

    # Display stop time updates
    if trip_update.stop_time_update:
        stops = trip_update.stop_time_update
        print(f"  Stop Time Updates ({len(stops)}):")

        # Display first stop
        if len(stops) > 0:
            first_stop = stops[0]
            start_info = ["🟢 STARTING POINT"]

            if first_stop.HasField('stop_sequence'):
                start_info.append(f"Seq: {first_stop.stop_sequence}")

            if first_stop.HasField('stop_id'):
                start_info.append(f"Stop: {first_stop.stop_id}")

            if first_stop.HasField('departure') and first_stop.departure.HasField('time'):
                dep_time = datetime.fromtimestamp(first_stop.departure.time)
                start_info.append(f"Dep: {dep_time.strftime('%H:%M:%S')}")
            elif first_stop.HasField('arrival') and first_stop.arrival.HasField('time'):
                arr_time = datetime.fromtimestamp(first_stop.arrival.time)
                start_info.append(f"Time: {arr_time.strftime('%H:%M:%S')}")

            print(f"    {', '.join(start_info)}")

        # Display intermediate stops
        if len(stops) > 2:
            print(f"    ... {len(stops) - 2} intermediate stop(s)")

        # Display last stop
        if len(stops) > 1:
            last_stop = stops[-1]
            end_info = ["🔴 ENDING POINT"]

            if last_stop.HasField('stop_sequence'):
                end_info.append(f"Seq: {last_stop.stop_sequence}")

            if last_stop.HasField('stop_id'):
                end_info.append(f"Stop: {last_stop.stop_id}")

            if last_stop.HasField('arrival') and last_stop.arrival.HasField('time'):
                arr_time = datetime.fromtimestamp(last_stop.arrival.time)
                end_info.append(f"Arr: {arr_time.strftime('%H:%M:%S')}")
            elif last_stop.HasField('departure') and last_stop.departure.HasField('time'):
                dep_time = datetime.fromtimestamp(last_stop.departure.time)
                end_info.append(f"Time: {dep_time.strftime('%H:%M:%S')}")

            print(f"    {', '.join(end_info)}")
        elif len(stops) == 1:
            print(f"    (Single stop update - current position)")

    print()


def main():
    """Main CLI function."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='View GTFS Realtime Trip Updates',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--api-key',
        help='API subscription key (or set PTV_API_KEY environment variable)',
        default=os.environ.get('PTV_API_KEY')
    )

    parser.add_argument(
        '--mode',
        choices=['metro', 'vline'],
        default='metro',
        help='Transport mode (default: metro)'
    )

    parser.add_argument(
        '--max-display',
        type=int,
        default=5,
        help='Maximum number of trip updates to display (default: 5, use 0 for all)'
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key is required!", file=sys.stderr)
        print("\nSet PTV_API_KEY environment variable or use --api-key", file=sys.stderr)
        sys.exit(1)

    try:
        # Create fetcher
        fetcher = GTFSRealtimeFetcher(args.api_key)

        # Fetch feed
        print(f"Fetching {args.mode} trip updates...")
        feed = fetcher.fetch_trip_updates(args.mode)

        # Display header
        display_feed_header(feed)

        # Display trip updates
        print("Trip Updates:")
        print("-" * 80)

        total_trip_updates = sum(1 for e in feed.entity if e.HasField('trip_update'))
        max_display = args.max_display if args.max_display > 0 else total_trip_updates

        count = 0
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                display_trip_update(entity)
                count += 1
                if count >= max_display:
                    remaining = total_trip_updates - count
                    if remaining > 0:
                        print(f"... and {remaining} more trip updates")
                    break

        if count == 0:
            print("No trip updates found in feed.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
