"""
Tests for Flask web application routes - Phase 12 Map Visualization.

Tests the new API proxy routes and page rendering endpoints.
"""

import pytest
from unittest.mock import MagicMock
import json


class TestPageRendering:
    """Test that all pages render successfully."""

    def test_index_page_renders(self, client):
        """Test that the index page renders successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Journey Planner' in response.data

    def test_map_page_renders(self, client):
        """Test that the map page renders successfully."""
        response = client.get('/map')
        assert response.status_code == 200
        assert b'map' in response.data.lower()

    def test_stations_page_renders(self, client):
        """Test that the stations page renders successfully."""
        response = client.get('/stations')
        assert response.status_code == 200
        assert b'Stations' in response.data

    def test_live_map_page_renders(self, client):
        """Test that the live vehicle map page renders successfully."""
        response = client.get('/live')
        assert response.status_code == 200
        assert b'Live' in response.data

    def test_dashboard_page_renders(self, client):
        """Test that the dashboard page renders successfully."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data


class TestVehicleProxyEndpoint:
    """Test the /api/vehicles proxy endpoint."""

    def test_vehicles_endpoint_success(self, client, mock_requests_get):
        """Test successful vehicle data fetch from FastAPI backend."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'Found 42 vehicles',
            'mode': 'metro',
            'count': 42,
            'vehicles': [
                {
                    'vehicle_id': '1234',
                    'latitude': -37.8136,
                    'longitude': 144.9631,
                    'speed_kmh': 45.0,
                    'current_status': 'IN_TRANSIT_TO'
                }
            ]
        }
        mock_requests_get.return_value = mock_response

        response = client.get('/api/vehicles?mode=metro')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 42
        assert len(data['vehicles']) == 1

    def test_vehicles_endpoint_default_mode(self, client, mock_requests_get):
        """Test vehicles endpoint uses default mode when not specified."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'vehicles': []
        }
        mock_requests_get.return_value = mock_response

        client.get('/api/vehicles')

        # Verify the request was made with default mode
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert 'mode' in call_args.kwargs.get('params', {})

    def test_vehicles_endpoint_connection_error(self, client, mock_requests_get):
        """Test vehicles endpoint handles connection errors gracefully."""
        import requests
        mock_requests_get.side_effect = requests.exceptions.ConnectionError()

        response = client.get('/api/vehicles?mode=metro')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'connect' in data['error'].lower()

    def test_vehicles_endpoint_timeout(self, client, mock_requests_get):
        """Test vehicles endpoint handles timeout errors gracefully."""
        import requests
        mock_requests_get.side_effect = requests.exceptions.Timeout()

        response = client.get('/api/vehicles?mode=metro')

        assert response.status_code == 504
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'timed out' in data['error'].lower()

    def test_vehicles_endpoint_backend_503(self, client, mock_requests_get):
        """Test vehicles endpoint handles backend 503 errors."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_requests_get.return_value = mock_response

        response = client.get('/api/vehicles?mode=metro')

        assert response.status_code == 503


class TestVehicleSummaryProxyEndpoint:
    """Test the /api/vehicles/summary proxy endpoint."""

    def test_vehicles_summary_endpoint_success(self, client, mock_requests_get):
        """Test successful vehicle summary fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'mode': 'metro',
            'total_vehicles': 42,
            'vehicles_with_trip': 38,
            'vehicles_in_transit': 35,
            'vehicles_at_stop': 7,
            'average_speed_kmh': 45.2
        }
        mock_requests_get.return_value = mock_response

        response = client.get('/api/vehicles/summary?mode=metro')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['total_vehicles'] == 42

    def test_vehicles_summary_connection_error(self, client, mock_requests_get):
        """Test vehicles summary handles connection errors."""
        import requests
        mock_requests_get.side_effect = requests.exceptions.ConnectionError()

        response = client.get('/api/vehicles/summary?mode=metro')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False


class TestAlertsProxyEndpoint:
    """Test the /api/alerts proxy endpoint."""

    def test_alerts_endpoint_success(self, client, mock_requests_get):
        """Test successful alerts fetch from FastAPI backend."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'Found 3 alerts',
            'mode': 'metro',
            'count': 3,
            'alerts': [
                {
                    'alert_id': 'alert_1',
                    'header_text': 'Planned Works',
                    'description_text': 'Track maintenance this weekend',
                    'effect': 'REDUCED_SERVICE'
                }
            ]
        }
        mock_requests_get.return_value = mock_response

        response = client.get('/api/alerts?mode=metro')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['alerts']) == 1

    def test_alerts_endpoint_connection_error(self, client, mock_requests_get):
        """Test alerts endpoint handles connection errors gracefully."""
        import requests
        mock_requests_get.side_effect = requests.exceptions.ConnectionError()

        response = client.get('/api/alerts?mode=metro')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'alerts' in data  # Should return empty alerts list

    def test_alerts_endpoint_default_mode(self, client, mock_requests_get):
        """Test alerts endpoint uses default mode."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'alerts': []
        }
        mock_requests_get.return_value = mock_response

        client.get('/api/alerts')

        mock_requests_get.assert_called_once()


class TestStationsEndpoint:
    """Test the /api/stations endpoint."""

    def test_stations_endpoint_returns_list(self, client):
        """Test that stations endpoint returns a list."""
        response = client.get('/api/stations')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2  # Two mock stations in conftest

    def test_stations_endpoint_sorted_by_name(self, client):
        """Test that stations are sorted by name."""
        response = client.get('/api/stations')

        data = json.loads(response.data)
        names = [s['name'] for s in data]
        assert names == sorted(names)

    def test_stations_endpoint_includes_coordinates(self, client):
        """Test that stations include lat/lon coordinates."""
        response = client.get('/api/stations')

        data = json.loads(response.data)
        for station in data:
            assert 'lat' in station
            assert 'lon' in station
            assert isinstance(station['lat'], float)
            assert isinstance(station['lon'], float)

    def test_stations_endpoint_includes_required_fields(self, client):
        """Test that stations include all required fields."""
        response = client.get('/api/stations')

        data = json.loads(response.data)
        for station in data:
            assert 'id' in station
            assert 'name' in station
            assert 'platform' in station
            assert 'lat' in station
            assert 'lon' in station


class TestNavigationLinks:
    """Test that all pages have consistent navigation."""

    @pytest.mark.parametrize("page,expected_links", [
        ('/', ['/map', '/live', '/dashboard', '/stations']),
        ('/map', ['/', '/live', '/dashboard', '/stations']),
        ('/live', ['/', '/map', '/dashboard', '/stations']),
        ('/dashboard', ['/', '/map', '/live', '/stations']),
        ('/stations', ['/', '/map', '/live', '/dashboard']),
    ])
    def test_page_has_navigation_links(self, client, page, expected_links):
        """Test that each page has navigation links to other pages."""
        response = client.get(page)
        assert response.status_code == 200

        html = response.data.decode('utf-8')
        for link in expected_links:
            assert f'href="{link}"' in html or f"href='{link}'" in html, \
                f"Page {page} missing navigation link to {link}"
