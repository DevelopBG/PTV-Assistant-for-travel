#!/usr/bin/env python3
"""
PTV Journey Planner Web App
Web frontend for the Melbourne public transport journey planner.

Phase 12: Map Visualization with live vehicle tracking and journey visualization.
"""

import sys

# Fix Windows console encoding for emoji/unicode support
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from flask import Flask, render_template, request, jsonify
from src.data.multimodal_parser import MultiModalGTFSParser
from src.data.stop_index import StopIndex
from src.routing.transfer_journey_planner import TransferJourneyPlanner
from src.data.service_manager import get_service_manager
from datetime import datetime
import json
import requests
import os
import subprocess
import time
import atexit
import signal

app = Flask(__name__)

# FastAPI backend URL for vehicle/alerts data
FASTAPI_URL = os.environ.get('FASTAPI_URL', 'http://localhost:8000')

# Global variable to hold the FastAPI process
fastapi_process = None

def start_fastapi_backend():
    """Start the FastAPI backend server in a subprocess."""
    global fastapi_process

    print("\n" + "="*60)
    print("Starting FastAPI Backend Server...")
    print("="*60)

    try:
        # Check if FastAPI is already running
        try:
            response = requests.get(f'{FASTAPI_URL}/api/v1/health', timeout=2)
            if response.status_code == 200:
                print(f"✓ FastAPI backend already running at {FASTAPI_URL}")
                return
        except:
            pass

        # Start FastAPI server
        fastapi_process = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'src.api.main:app', '--port', '8000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )

        # Wait for FastAPI to start (max 10 seconds)
        print("Waiting for FastAPI backend to start...", end="", flush=True)
        for i in range(20):
            time.sleep(0.5)
            try:
                response = requests.get(f'{FASTAPI_URL}/api/v1/health', timeout=1)
                if response.status_code == 200:
                    print(" ✓")
                    print(f"✓ FastAPI backend started at {FASTAPI_URL}")
                    print(f"✓ Swagger UI available at {FASTAPI_URL}/docs")
                    return
            except:
                print(".", end="", flush=True)

        print("\n⚠ FastAPI backend may take longer to start")
        print(f"  Check manually at {FASTAPI_URL}/docs")

    except Exception as e:
        print(f"✗ Failed to start FastAPI backend: {e}")
        print("  You can start it manually with:")
        print("  python -m uvicorn src.api.main:app --reload --port 8000")

def stop_fastapi_backend():
    """Stop the FastAPI backend server."""
    global fastapi_process

    if fastapi_process:
        print("\nStopping FastAPI backend...")
        try:
            # Try graceful termination first
            fastapi_process.terminate()

            # Wait for process to terminate
            try:
                fastapi_process.wait(timeout=5)
                print("✓ FastAPI backend stopped")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                print("⚠ Force stopping FastAPI backend...")
                fastapi_process.kill()
                fastapi_process.wait()
                print("✓ FastAPI backend force stopped")
        except Exception as e:
            print(f"⚠ Error stopping FastAPI: {e}")
            try:
                fastapi_process.kill()
            except:
                pass

# Register cleanup function
atexit.register(stop_fastapi_backend)

# Initialize the multi-modal journey planner with GTFS data
# Loads: Folder 1 = V/Line, Folder 2 = Metro Trains, Folder 3 = Trams
print("="*60)
print("Initializing PTV Journey Planner with Multi-Modal Support")
print("="*60)

parser = None
planner = None
stop_index = None

try:
    # Load all core public transport modes (trains + trams)
    # You can add '4', '5', '6' for buses if needed (slower startup)
    parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
    parser.load_all()

    # Create transfer-aware multi-modal planner
    planner = TransferJourneyPlanner(parser)

    # Create stop index from merged stops
    stop_index = StopIndex(parser)

    print(f"\n✓ Multi-modal system ready!")
    print(f"  Total stops indexed: {len(parser.stops)}")
    print(f"  Modes loaded: {', '.join([parser.get_mode_info(m)['name'] for m in parser.get_loaded_modes()])}")
    print("="*60)

except Exception as e:
    print(f"\n✗ Failed to load multi-modal GTFS data: {e}")
    print("  Journey planning will not be available.")
    print("  Live vehicle tracking and map visualization will still work.")
    print("="*60)


def reload_flask_data():
    """
    Reload Flask parsers and planners after GTFS data update.

    This function is called by the service manager after successful GTFS updates.

    Returns:
        bool: True if reload successful, False otherwise
    """
    global parser, planner, stop_index

    try:
        print("\n🔄 Reloading Flask transit data...")

        # Reload multi-modal parser
        parser = MultiModalGTFSParser(base_gtfs_dir="data/gtfs", modes_to_load=['1', '2', '3'])
        parser.load_all()

        # Rebuild planner and index
        planner = TransferJourneyPlanner(parser)
        stop_index = StopIndex(parser)

        print(f"✓ Flask data reloaded successfully")
        print(f"  Total stops indexed: {len(parser.stops)}")
        print(f"  Modes loaded: {', '.join([parser.get_mode_info(m)['name'] for m in parser.get_loaded_modes()])}")

        return True

    except Exception as e:
        print(f"✗ Flask reload failed: {e}")
        return False


# Register Flask reload callback with service manager
service_manager = get_service_manager()
service_manager.register_reload_callback(reload_flask_data)


@app.route('/')
def index():
    """Main page with multi-modal journey planning form"""
    return render_template('index_multimodal.html')

@app.route('/old')
def index_old():
    """Old single-mode journey planning form (legacy)"""
    return render_template('index.html')

@app.route('/api/stations')
def get_stations():
    """API endpoint to get all available stations"""
    if parser is None:
        return jsonify([])

    stations = []
    for stop in parser.stops.values():
        stations.append({
            'id': stop.stop_id,
            'name': stop.stop_name,
            'platform': stop.platform_code,
            'lat': stop.stop_lat,
            'lon': stop.stop_lon
        })

    # Sort by name
    stations.sort(key=lambda x: x['name'])
    return jsonify(stations)

@app.route('/api/stations/autocomplete')
def autocomplete_stations():
    """
    API endpoint for station name autocomplete/suggestions.

    Query params:
        q: Search query (partial station name)
        limit: Maximum number of results (default: 10)
    """
    if parser is None or stop_index is None:
        return jsonify([])

    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))

    if not query or len(query) < 2:
        return jsonify([])

    # Use fuzzy matching to find similar station names
    matches = stop_index.find_stop_fuzzy(query, limit=limit, min_score=60)

    suggestions = []
    seen_names = set()  # Avoid duplicate names

    for stop, score in matches:
        # Some stops have the same name (different platforms)
        # Only show unique names
        if stop.stop_name not in seen_names:
            suggestions.append({
                'id': stop.stop_id,
                'name': stop.stop_name,
                'score': score
            })
            seen_names.add(stop.stop_name)

    return jsonify(suggestions)

@app.route('/api/plan', methods=['POST'])
def plan_journey_endpoint():
    """API endpoint to plan journeys across all transport modes"""
    print("\n=== Multi-Modal Journey Planning Request ===")

    if planner is None or stop_index is None:
        print("ERROR: GTFS data not loaded")
        return jsonify({'error': 'GTFS data not loaded. Journey planning unavailable.'}), 503

    try:
        data = request.get_json()
        print(f"Request data: {data}")

        origin_name = data.get('origin', '').strip()
        destination_name = data.get('destination', '').strip()
        # Time is optional now - uses current time if not provided
        time_str = data.get('time', '').strip()

        print(f"Origin: '{origin_name}'")
        print(f"Destination: '{destination_name}'")

        if not origin_name or not destination_name:
            print("ERROR: Missing origin or destination")
            return jsonify({'error': 'Origin and destination are required'}), 400

        # Find origin stop using fuzzy matching
        print(f"Searching for origin: {origin_name}")
        origin_matches = stop_index.find_stop_fuzzy(origin_name, limit=5, min_score=50)
        print(f"Origin matches: {[(s.stop_name, score) for s, score in origin_matches]}")

        if not origin_matches:
            origin_stop = stop_index.find_stop_exact(origin_name)
            if not origin_stop:
                print(f"ERROR: Origin station '{origin_name}' not found")
                return jsonify({'error': f'Origin station "{origin_name}" not found'}), 404
        else:
            origin_stop = origin_matches[0][0]

        print(f"✓ Origin found: {origin_stop.stop_name} (ID: {origin_stop.stop_id})")

        # Find destination stop using fuzzy matching
        print(f"Searching for destination: {destination_name}")
        dest_matches = stop_index.find_stop_fuzzy(destination_name, limit=5, min_score=50)
        print(f"Destination matches: {[(s.stop_name, score) for s, score in dest_matches]}")

        if not dest_matches:
            dest_stop = stop_index.find_stop_exact(destination_name)
            if not dest_stop:
                print(f"ERROR: Destination station '{destination_name}' not found")
                return jsonify({'error': f'Destination station "{destination_name}" not found'}), 404
        else:
            dest_stop = dest_matches[0][0]

        print(f"✓ Destination found: {dest_stop.stop_name} (ID: {dest_stop.stop_id})")

        # Parse departure time or use current time
        if not time_str or time_str.lower() == 'now':
            departure_time = None  # Let the planner use current time
            print(f"Using current time for departure")
        else:
            # Handle HH:MM format
            if len(time_str.split(':')) == 2:
                departure_time = f"{time_str}:00"
            else:
                departure_time = time_str
            print(f"Departure time: {departure_time}")

        # Find single best journey using two-tier search
        print(f"Finding best journey from {origin_stop.stop_id} to {dest_stop.stop_id}...")
        journey = planner.find_best_journey(
            origin_stop_id=origin_stop.stop_id,
            destination_stop_id=dest_stop.stop_id,
            departure_time=departure_time,
            max_transfers=4
        )

        # Helper function to convert journey to JSON
        def journey_to_json(journey):
            legs_data = []
            for leg in journey.legs:
                # Get from/to stops for coordinates
                from_stop = parser.get_stop(leg.from_stop_id)
                to_stop = parser.get_stop(leg.to_stop_id)

                leg_data = {
                    'from_stop': leg.from_stop_name,
                    'to_stop': leg.to_stop_name,
                    'from_stop_id': leg.from_stop_id,
                    'to_stop_id': leg.to_stop_id,

                    # Add coordinates for map rendering
                    'from_coords': {
                        'lat': float(from_stop.stop_lat),
                        'lon': float(from_stop.stop_lon),
                        'id': from_stop.stop_id
                    } if from_stop else None,
                    'to_coords': {
                        'lat': float(to_stop.stop_lat),
                        'lon': float(to_stop.stop_lon),
                        'id': to_stop.stop_id
                    } if to_stop else None,

                    'departure_time': leg.departure_time[:5],  # HH:MM
                    'arrival_time': leg.arrival_time[:5],  # HH:MM
                    'route_name': leg.route_name or 'Transfer',
                    'route_id': leg.route_id if hasattr(leg, 'route_id') else None,
                    'trip_id': leg.trip_id if hasattr(leg, 'trip_id') else None,
                    'mode': leg.get_mode_name(),
                    'duration_minutes': leg.duration_minutes,
                    'num_stops': leg.num_stops,
                    'is_transfer': leg.is_transfer,
                    'intermediate_stops': leg.intermediate_stops,

                    # Add intermediate stop coordinates for map
                    'intermediate_coords': leg.intermediate_coords if hasattr(leg, 'intermediate_coords') else []
                }

                # Add transfer-specific info if available
                if leg.is_transfer:
                    if hasattr(leg, 'from_platform') and leg.from_platform:
                        leg_data['from_platform'] = leg.from_platform
                    if hasattr(leg, 'to_platform') and leg.to_platform:
                        leg_data['to_platform'] = leg.to_platform
                    if hasattr(leg, 'transfer_hub_name') and leg.transfer_hub_name:
                        leg_data['transfer_hub_name'] = leg.transfer_hub_name

                legs_data.append(leg_data)

            return {
                'origin': {
                    'id': journey.origin_stop_id,
                    'name': journey.origin_stop_name,
                    'lat': origin_stop.stop_lat,
                    'lon': origin_stop.stop_lon,
                },
                'destination': {
                    'id': journey.destination_stop_id,
                    'name': journey.destination_stop_name,
                    'lat': dest_stop.stop_lat,
                    'lon': dest_stop.stop_lon,
                },
                'departure_time': journey.departure_time[:5],
                'arrival_time': journey.arrival_time[:5],
                'duration_minutes': journey.duration_minutes,
                'num_transfers': journey.num_transfers,
                'modes_used': journey.get_modes_used(),
                'legs': legs_data
            }

        # Build response with single journey
        result = {
            'success': True if journey else False,
            'origin': {
                'id': origin_stop.stop_id,
                'name': origin_stop.stop_name,
                'lat': origin_stop.stop_lat,
                'lon': origin_stop.stop_lon,
            },
            'destination': {
                'id': dest_stop.stop_id,
                'name': dest_stop.stop_name,
                'lat': dest_stop.stop_lat,
                'lon': dest_stop.stop_lon,
            },
            'journey': journey_to_json(journey) if journey else None,
            'has_realtime': bool(os.environ.get('PTV_API_KEY'))
        }

        # Log results
        if journey:
            modes = ' → '.join(journey.get_modes_used())
            print(f"✓ Found route: {journey.duration_minutes}m, {journey.num_transfers} transfers, {modes}")
        else:
            print("✗ No route found")

        print("=== Multi-Modal Journey Planning Success ===\n")
        return jsonify(result)

    except ValueError as e:
        print(f"ERROR: ValueError - {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"ERROR: Unexpected error - {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/map')
def map_page():
    """Map page with interactive journey planning"""
    return render_template('map.html')

@app.route('/stations')
def stations_page():
    """Page showing all available stations"""
    return render_template('stations.html')


@app.route('/live')
def live_map_page():
    """Live vehicle tracking map page"""
    return render_template('live_map.html')


@app.route('/dashboard')
def dashboard_page():
    """Dashboard with overview of vehicles and alerts"""
    return render_template('dashboard.html')


@app.route('/about')
def about_page():
    """About page with API documentation and project information"""
    return render_template('about.html')


@app.route('/api/vehicles')
def get_vehicles():
    """
    Proxy endpoint to get live vehicle positions from FastAPI backend.

    Query params:
        mode: Transport mode (metro, vline, tram, bus)
    """
    mode = request.args.get('mode', 'metro')

    try:
        response = requests.get(
            f'{FASTAPI_URL}/api/v1/vehicles',
            params={'mode': mode},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 503:
            return jsonify({
                'success': False,
                'error': 'Realtime data not available. FastAPI server may not be running or PTV API key not configured.',
                'vehicles': []
            }), 503
        else:
            return jsonify({
                'success': False,
                'error': f'Backend returned status {response.status_code}',
                'vehicles': []
            }), response.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Cannot connect to FastAPI backend. Is it running on port 8000?',
            'vehicles': []
        }), 503
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request to backend timed out',
            'vehicles': []
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'vehicles': []
        }), 500


@app.route('/api/vehicles/summary')
def get_vehicles_summary():
    """
    Proxy endpoint to get vehicle summary statistics from FastAPI backend.

    Query params:
        mode: Transport mode (metro, vline, tram, bus)
    """
    mode = request.args.get('mode', 'metro')

    try:
        response = requests.get(
            f'{FASTAPI_URL}/api/v1/vehicles/summary',
            params={'mode': mode},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'error': f'Backend returned status {response.status_code}'
            }), response.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Cannot connect to FastAPI backend'
        }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/alerts')
def get_alerts():
    """
    Proxy endpoint to get service alerts from FastAPI backend.

    Query params:
        mode: Transport mode (metro, tram - only these have alerts from PTV)
    """
    mode = request.args.get('mode', 'metro')

    try:
        response = requests.get(
            f'{FASTAPI_URL}/api/v1/alerts',
            params={'mode': mode},
            timeout=10
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'error': f'Backend returned status {response.status_code}',
                'alerts': []
            }), response.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Cannot connect to FastAPI backend. Is it running on port 8000?',
            'alerts': []
        }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': []
        }), 500


if __name__ == '__main__':
    # Start FastAPI backend first
    start_fastapi_backend()

    # Use port 5001 by default (5000 is often used by AirPlay on macOS)
    port = int(os.environ.get('FLASK_PORT', 5001))

    print("\n" + "="*60)
    print("Starting Flask Web App...")
    print("="*60)
    print(f"✓ Web interface: http://localhost:{port}")
    print(f"✓ Journey Planner: http://localhost:{port}")
    print(f"✓ About & API Docs: http://localhost:{port}/about")
    print(f"✓ Swagger UI: http://localhost:8000/docs")
    print("="*60)
    print("\nPress CTRL+C to stop both servers\n")

    try:
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        stop_fastapi_backend()
        print("All servers stopped. Goodbye!")