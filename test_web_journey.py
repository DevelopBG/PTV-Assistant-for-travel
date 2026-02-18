#!/usr/bin/env python3
"""
Test script to verify web journey planning API
"""

import requests
import json

# Test the /api/plan endpoint
url = "http://localhost:5001/api/plan"

# Test 1: Tarneit to Waurn Ponds
print("Test 1: Tarneit to Waurn Ponds")
print("=" * 60)
payload = {
    "origin": "Tarneit",
    "destination": "Waurn Ponds",
    "time": "14:00"
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

# Test 2: Tarneit to Geelong
print("Test 2: Tarneit to Geelong")
print("=" * 60)
payload = {
    "origin": "Tarneit",
    "destination": "Geelong",
    "time": "now"
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

# Test 3: Check available stations
print("Test 3: Available stations")
print("=" * 60)
response = requests.get("http://localhost:5001/api/stations")
stations = response.json()
print(f"Total stations: {len(stations)}")
print(f"Sample stations: {[s['name'] for s in stations[:5]]}")
