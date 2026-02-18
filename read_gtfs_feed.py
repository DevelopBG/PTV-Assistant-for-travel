#!/usr/bin/env python3
"""
GTFS Realtime Trip Updates - Metro Train Feed Reader
Reads and parses the Transport Victoria GTFS Realtime protobuf feed for metro trains.

Documentation: https://opendata.transport.vic.gov.au/dataset/gtfs-realtime/resource/0010d606-47bf-4abb-a04f-63add63a4d23
License: Creative Commons Attribution 4.0
"""

import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import sys
import os
import argparse
from dotenv import load_dotenv


def fetch_gtfs_feed(url, api_key):
    """
    Fetch the GTFS Realtime protobuf feed from the given URL.

    Args:
        url (str): The URL of the GTFS Realtime feed
        api_key (str): The API subscription key for authentication

    Returns:
        gtfs_realtime_pb2.FeedMessage: Parsed feed message
    """
    try:
        # Set up headers with API key
        headers = {
            'KeyID': api_key
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse the protobuf feed
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        return feed
    except requests.exceptions.RequestException as e:
        print(f"Error fetching feed: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}", file=sys.stderr)
            print(f"Response content: {e.response.text[:200]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing feed: {e}", file=sys.stderr)
        sys.exit(1)


def display_feed_header(feed):
    """Display feed header information."""
    print("=" * 80)
    print("GTFS Realtime Feed - Metro Train Trip Updates")
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
    """
    Display information for a single trip update entity.

    Args:
        entity: GTFS Realtime feed entity containing trip update
    """
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

    if trip.HasField('schedule_relationship'):
        print(f"  Schedule Relationship: {trip.schedule_relationship}")

    # Display stop time updates
    if trip_update.stop_time_update:
        stops = trip_update.stop_time_update
        print(f"  Stop Time Updates ({len(stops)}):")
        
        # Display STARTING POINT (first stop)
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
        
        # Display intermediate stops (if there are more than 2 stops)
        if len(stops) > 2:
            print(f"    ... {len(stops) - 2} intermediate stop(s)")
        
        # Display ENDING POINT (last stop)
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
            # Only one stop in the update (could be current position)
            print(f"    (Single stop update - current position)")

    print()


def main():
    """Main function to fetch and display GTFS Realtime feed."""
    # Load environment variables from .env file
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Read GTFS Realtime Trip Updates for Melbourne Metro Trains',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variable for API key
  export PTV_API_KEY='your-api-key-here'
  python read_gtfs_feed.py

  # Using command line argument
  python read_gtfs_feed.py --api-key 'your-api-key-here'

  # Display more trip updates
  python read_gtfs_feed.py --max-display 10

To obtain an API key, register at:
https://opendata.transport.vic.gov.au/
        """
    )

    parser.add_argument(
        '--api-key',
        help='API subscription key (or set PTV_API_KEY environment variable)',
        default=os.environ.get('PTV_API_KEY')
    )

    parser.add_argument(
        '--max-display',
        type=int,
        default=5,
        help='Maximum number of trip updates to display (default: 5, use 0 for all)'
    )

    parser.add_argument(
        '--url',
        default='https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/metro/trip-updates',
        help='GTFS Realtime feed URL (default: PTV Metro Train Trip Updates)'
    )

    args = parser.parse_args()

    # Check if API key is provided
    if not args.api_key:
        print("Error: API key is required!", file=sys.stderr)
        print("\nPlease provide your API key either:", file=sys.stderr)
        print("  1. Via command line: --api-key 'your-key'", file=sys.stderr)
        print("  2. Via environment variable: export PTV_API_KEY='your-key'", file=sys.stderr)
        print("\nTo obtain an API key, register at:", file=sys.stderr)
        print("  https://opendata.transport.vic.gov.au/", file=sys.stderr)
        sys.exit(1)

    print("Fetching GTFS Realtime feed...")
    feed = fetch_gtfs_feed(args.url, args.api_key)

    # Display feed header
    display_feed_header(feed)

    # Display trip updates
    print("Trip Updates:")
    print("-" * 80)

    # Count total trip updates
    total_trip_updates = sum(1 for e in feed.entity if e.HasField('trip_update'))

    # Show trip updates
    count = 0
    max_display = args.max_display if args.max_display > 0 else total_trip_updates

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


if __name__ == "__main__":
    main()
