#!/usr/bin/env python3
"""
Station List - Show all available stations in the PTV Journey Planner
"""

from journey_planner import JourneyPlanner

def main():
    planner = JourneyPlanner()
    planner.initialize()
    
    print("Available Melbourne Metro Stations:")
    print("=" * 50)
    
    stations = sorted(planner.gtfs_data.stops.values(), key=lambda x: x.name)
    
    for i, station in enumerate(stations, 1):
        print(f"{i:2d}. {station.name}")
        print(f"    Platform: {station.platform_code}")
        print(f"    Location: {station.lat:.4f}, {station.lon:.4f}")
        print()
    
    print(f"Total stations: {len(stations)}")
    print("\nUsage examples:")
    print('python journey_planner.py "Flinders Street" "Richmond"')
    print('python journey_planner.py "Melbourne Central" "Caulfield" --time "14:30"')

if __name__ == "__main__":
    main()