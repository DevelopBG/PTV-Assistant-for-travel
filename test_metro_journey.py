#!/usr/bin/env python3
"""
Test Metro Melbourne journey planning
"""

import requests
import json

url = "http://localhost:5001/api/plan"

# Test 1: Flinders Street to Melbourne Central
print("Test 1: Flinders Street to Melbourne Central")
print("=" * 60)
payload = {
    "origin": "Flinders Street",
    "destination": "Melbourne Central",
    "time": "09:00"
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        journey = result['journey']
        print(f"✓ Journey Found!")
        print(f"  Departure: {journey['departure_time']}")
        print(f"  Arrival: {journey['arrival_time']}")
        print(f"  Duration: {journey['duration_minutes']} minutes")
        print(f"  Transfers: {journey['transfers']}")
        print(f"  Mode: {journey['mode']}")
    else:
        print(f"✗ Error: {result.get('error')}")
else:
    print(f"Response: {response.json()}")
print()

# Test 2: Southern Cross to Parliament
print("Test 2: Southern Cross to Parliament")
print("=" * 60)
payload = {
    "origin": "Southern Cross",
    "destination": "Parliament",
    "time": "now"
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        journey = result['journey']
        print(f"✓ Journey Found!")
        print(f"  Departure: {journey['departure_time']}")
        print(f"  Arrival: {journey['arrival_time']}")
        print(f"  Duration: {journey['duration_minutes']} minutes")
        print(f"  Transfers: {journey['transfers']}")
    else:
        print(f"✗ Error: {result.get('error')}")
else:
    print(f"Response: {response.json()}")
print()

# Test 3: Check available stations
print("Test 3: Check Metro Stations")
print("=" * 60)
response = requests.get("http://localhost:5001/api/stations")
stations = response.json()
print(f"Total stations: {len(stations)}")

# Find some key stations
key_stations = ["Flinders Street", "Southern Cross", "Melbourne Central", "Parliament"]
for search in key_stations:
    matches = [s for s in stations if search.lower() in s['name'].lower()]
    if matches:
        print(f"  {search}: Found {len(matches)} matches")
        print(f"    - {matches[0]['name']} (ID: {matches[0]['id']})")
