from datetime import datetime
from src.data.multimodal_parser import MultiModalGTFSParser
from src.data.stop_index import StopIndex
from src.routing.journey_planner import JourneyPlanner
import os

# Optional: real-time alerts (requires PTV_API_KEY)
try:
    from src.realtime.feed_fetcher import GTFSRealtimeFetcher
    from src.realtime.service_alerts import ServiceAlertParser
    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False

def main():
    print("=" * 60)
    print("GEELONG -> WAURN PONDS - Next Train Query")
    print("=" * 60)

    # 1. Load GTFS data
    print("\n[1/4] Loading V/Line GTFS data...")
    parser = MultiModalGTFSParser(modes_to_load=['1'])
    parser.load_all()
    print(f"  ✓ Loaded {len(parser.all_stops)} stops, {len(parser.all_trips)} trips")

    # 2. Find stations
    print("\n[2/4] Finding stations...")
    stop_index = StopIndex(parser)
    geelong = stop_index.find_stop("Geelong Station")
    waurn = stop_index.find_stop("Waurn Ponds Station")

    if not geelong or not waurn:
        print("  ✗ Could not find one or both stations")
        return

    print(f"  ✓ From: {geelong.stop_name} (ID: {geelong.stop_id})")
    print(f"  ✓ To: {waurn.stop_name} (ID: {waurn.stop_id})")

    # 3. Find next journey
    print("\n[3/4] Finding next train...")
    planner = JourneyPlanner(parser)
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    journey = planner.find_journey(
        geelong.stop_id,
        waurn.stop_id,
        departure_time=current_time
    )

    print(f"\n{'=' * 60}")
    print(f"QUERY TIME: {now.strftime('%A, %d %B %Y at %H:%M')}")
    print(f"{'=' * 60}")

    if journey:
        print(f"\n✓ NEXT TRAIN FOUND:")
        print(f"  Departs: {journey.departure_time}")
        print(f"  Arrives: {journey.arrival_time}")
        print(f"  Duration: {journey.duration_minutes} minutes")
        print(f"  Transfers: {journey.num_transfers}")

        for i, leg in enumerate(journey.legs, 1):
            print(f"\n  Leg {i}:")
            print(f"    Route: {leg.route_name}")
            print(f"    Mode: {leg.get_mode_name()}")
            print(f"    From: {leg.from_stop_name} @ {leg.departure_time}")
            print(f"    To: {leg.to_stop_name} @ {leg.arrival_time}")
            if leg.intermediate_stops:
                print(f"    Stops: {len(leg.intermediate_stops)} intermediate stops")
    else:
        print("\n✗ NO SERVICE FOUND")
        print("  No trains available from Geelong to Waurn Ponds at this time.")
        print("  This may be due to:")
        print("    - No service scheduled for current time")
        print("    - Service only operates on specific days")
        print("    - Late night/early morning hours")

    # 4. Fetch service alerts (optional)
    print(f"\n{'=' * 60}")
    print("[4/4] Checking for service disruptions...")
    print(f"{'=' * 60}")

    api_key = os.getenv('PTV_API_KEY')

    if not api_key:
        print("\n⚠ PTV_API_KEY not set")
        print("  Set environment variable to check real-time service disruptions")
        print("  Example: export PTV_API_KEY='your-key-here'")
        print("  Get key from: https://opendata.transport.vic.gov.au/")
    elif not REALTIME_AVAILABLE:
        print("\n⚠ Real-time modules not available")
    else:
        try:
            fetcher = GTFSRealtimeFetcher(api_key=api_key)
            alerts_parser = ServiceAlertParser(fetcher)

            print("\n  Fetching V/Line service alerts...")
            alerts = alerts_parser.fetch_alerts(mode='vline')
            active_alerts = alerts_parser.get_active_alerts(alerts)

            # Filter for this route/stops
            relevant_alerts = []

            if journey and journey.legs:
                route_alerts = alerts_parser.get_alerts_for_route(journey.legs[0].route_id)
                relevant_alerts.extend(route_alerts)

            stop_alerts_geelong = alerts_parser.get_alerts_for_stop(geelong.stop_id)
            stop_alerts_waurn = alerts_parser.get_alerts_for_stop(waurn.stop_id)

            relevant_alerts.extend(stop_alerts_geelong)
            relevant_alerts.extend(stop_alerts_waurn)

            # Remove duplicates
            unique_alerts = {alert.id: alert for alert in relevant_alerts}.values()

            if unique_alerts:
                print(f"\n⚠️  SERVICE DISRUPTIONS DETECTED ({len(unique_alerts)} alert(s)):")
                for alert in unique_alerts:
                    print(f"\n  Alert: {alert.header_text}")
                    if alert.description_text:
                        print(f"  Details: {alert.description_text[:200]}...")
                    print(f"  Effect: {alert.effect}")
                    print(f"  Severity: {alert.severity}")
                    if alert.active_periods:
                        print(f"  Active: {len(alert.active_periods)} period(s)")
            else:
                print(f"\n✓ NO SERVICE DISRUPTIONS")
                print(f"  All systems operating normally on this route")
                print(f"  Total active V/Line alerts: {len(active_alerts)} (none affecting this route)")

        except Exception as e:
            print(f"\n✗ Error fetching alerts: {str(e)}")

    print(f"\n{'=' * 60}\n")

if __name__ == "__main__":
    main()
