#!/usr/bin/env python3
"""
Batch Journey Planner - Test multiple routes at once
"""

from journey_planner import JourneyPlanner

def main():
    # Test routes
    test_routes = [
        ("Flinders Street", "Richmond", "City to Inner East"),
        ("Melbourne Central", "Caulfield", "City to South East"),
        ("Southern Cross", "Parliament", "City Loop"),
        ("Flinders Street", "South Yarra", "City to Inner South"),
        ("Richmond", "Caulfield", "Cross-suburban"),
    ]
    
    planner = JourneyPlanner()
    planner.initialize()
    
    print("PTV Journey Planner - Batch Test")
    print("=" * 60)
    
    for i, (origin, destination, description) in enumerate(test_routes, 1):
        print(f"\n{i}. {description}")
        print(f"   Route: {origin} to {destination}")
        print("-" * 40)
        
        try:
            journeys = planner.plan_journey(origin, destination)
            if journeys:
                journey = journeys[0]
                print(f"   Duration: {journey.duration_minutes} minutes")
                print(f"   Departure: {journey.departure_time.strftime('%H:%M')} from {journey.platform}")
                print(f"   Line: {journey.route_name}")
                print(f"   Status: OK Route found")
            else:
                print(f"   Status: ERROR No route found")
                
        except Exception as e:
            print(f"   Status: ERROR - {e}")
    
    print(f"\n" + "=" * 60)
    print("Batch test completed!")
    print("\nTo plan individual journeys:")
    print('python journey_planner.py "Flinders Street" "Richmond"')

if __name__ == "__main__":
    main()