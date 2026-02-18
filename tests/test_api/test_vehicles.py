"""
Tests for vehicle positions API endpoints - Phase 8

Tests cover:
- All vehicle position endpoints
- Error handling and edge cases
- Response format validation
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2

from src.api.main import app
from src.api.dependencies import reset_transit_service, TransitService
import src.api.dependencies as deps
from src.realtime.models import VehiclePosition, VehicleStopStatus, OccupancyStatus


# Path to test fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data", "fixtures")


@pytest.fixture(autouse=True)
def reset_service():
    """Reset transit service and use test fixtures."""
    reset_transit_service()

    # Create and load service with test fixtures
    deps._transit_service = TransitService(gtfs_dir=FIXTURES_DIR)
    deps._transit_service.load()

    yield

    reset_transit_service()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_vehicle_positions():
    """Create mock vehicle positions for testing."""
    return [
        VehiclePosition(
            vehicle_id="vehicle-001",
            latitude=-37.8136,
            longitude=144.9631,
            timestamp=1704067200,
            trip_id="trip-001",
            route_id="route-A",
            direction_id=0,
            label="Train 001",
            bearing=90.0,
            speed=20.0,
            stop_id="1001",
            current_status=VehicleStopStatus.IN_TRANSIT_TO,
            occupancy_status=OccupancyStatus.MANY_SEATS_AVAILABLE
        ),
        VehiclePosition(
            vehicle_id="vehicle-002",
            latitude=-37.8200,
            longitude=144.9700,
            timestamp=1704067100,
            trip_id="trip-002",
            route_id="route-A",
            label="Train 002",
            current_status=VehicleStopStatus.STOPPED_AT
        ),
        VehiclePosition(
            vehicle_id="vehicle-003",
            latitude=-37.8300,
            longitude=144.9800,
            timestamp=1704067150,
            trip_id="trip-003",
            route_id="route-B"
        )
    ]


@pytest.fixture
def mock_feed():
    """Create a mock GTFS Realtime feed."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1704067200

    # Add test vehicle
    entity = feed.entity.add()
    entity.id = "entity-1"
    vp = entity.vehicle
    vp.position.latitude = -37.8136
    vp.position.longitude = 144.9631
    vp.vehicle.id = "vehicle-001"
    vp.trip.trip_id = "trip-001"
    vp.trip.route_id = "route-A"
    vp.timestamp = 1704067200

    return feed


class TestGetAllVehicles:
    """Tests for GET /api/v1/vehicles endpoint."""

    def test_get_vehicles_no_api_key(self, client):
        """Test get vehicles returns 503 when no API key configured."""
        response = client.get("/api/v1/vehicles")
        # Without API key, should return 503
        assert response.status_code == 503
        assert "not available" in response.json()["detail"].lower()

    def test_get_vehicles_with_mock_fetcher(self, client, mock_feed):
        """Test get vehicles with mocked fetcher."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles?mode=vline")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["mode"] == "vline"
        assert data["count"] >= 1
        assert len(data["vehicles"]) >= 1

    def test_get_vehicles_invalid_mode(self, client):
        """Test get vehicles with invalid mode."""
        response = client.get("/api/v1/vehicles?mode=invalid")
        assert response.status_code == 422

    def test_get_vehicles_response_format(self, client, mock_feed):
        """Test vehicle response format."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles")

        data = response.json()
        if data["vehicles"]:
            vehicle = data["vehicles"][0]
            assert "vehicle_id" in vehicle
            assert "latitude" in vehicle
            assert "longitude" in vehicle
            assert "timestamp" in vehicle


class TestGetVehicleSummary:
    """Tests for GET /api/v1/vehicles/summary endpoint."""

    def test_get_summary_no_api_key(self, client):
        """Test summary returns 503 when no API key."""
        response = client.get("/api/v1/vehicles/summary")
        assert response.status_code == 503

    def test_get_summary_with_mock(self, client, mock_feed):
        """Test summary with mocked data."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/summary?mode=vline")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_vehicles" in data
        assert "vehicles_with_trip" in data
        assert "vehicles_in_transit" in data
        assert "vehicles_at_stop" in data


class TestGetVehicleById:
    """Tests for GET /api/v1/vehicles/{vehicle_id} endpoint."""

    def test_get_vehicle_not_found(self, client, mock_feed):
        """Test getting non-existent vehicle returns 404."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/nonexistent-vehicle")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_vehicle_found(self, client, mock_feed):
        """Test getting existing vehicle."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/vehicle-001")

        assert response.status_code == 200
        data = response.json()
        assert data["vehicle_id"] == "vehicle-001"
        assert data["latitude"] == pytest.approx(-37.8136, rel=1e-5)


class TestGetVehiclesForRoute:
    """Tests for GET /api/v1/vehicles/route/{route_id} endpoint."""

    def test_get_vehicles_for_route(self, client, mock_feed):
        """Test getting vehicles for a route."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/route/route-A")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["vehicles"], list)

    def test_get_vehicles_for_nonexistent_route(self, client, mock_feed):
        """Test getting vehicles for route with no vehicles."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/route/nonexistent-route")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0


class TestGetVehiclesNearStop:
    """Tests for GET /api/v1/vehicles/near/{stop_id} endpoint."""

    def test_get_vehicles_near_stop_not_found(self, client, mock_feed):
        """Test getting vehicles near non-existent stop returns 404."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/near/nonexistent-stop")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_vehicles_near_valid_stop(self, client, mock_feed):
        """Test getting vehicles near a valid stop."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            # 1001 is a stop ID in our test fixtures
            response = client.get("/api/v1/vehicles/near/1001?radius_km=5.0")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["vehicles"], list)

    def test_get_vehicles_near_stop_custom_radius(self, client, mock_feed):
        """Test custom radius parameter."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/near/1001?radius_km=0.5")

        assert response.status_code == 200

    def test_get_vehicles_near_stop_invalid_radius(self, client):
        """Test invalid radius parameter."""
        response = client.get("/api/v1/vehicles/near/1001?radius_km=100")
        assert response.status_code == 422  # Validation error


class TestGetVehicleForTrip:
    """Tests for GET /api/v1/vehicles/trip/{trip_id} endpoint."""

    def test_get_vehicle_for_trip(self, client, mock_feed):
        """Test getting vehicle for a trip."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/trip/trip-001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_vehicle_for_nonexistent_trip(self, client, mock_feed):
        """Test getting vehicle for trip with no vehicle."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/trip/nonexistent-trip")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0


class TestVehicleResponseModel:
    """Tests for VehiclePositionResponse model."""

    def test_vehicle_response_includes_speed_kmh(self, client, mock_feed):
        """Test that response includes speed in km/h."""
        # Create feed with speed data
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.id = "speed-test"
        vp = entity.vehicle
        vp.position.latitude = -37.8136
        vp.position.longitude = 144.9631
        vp.position.speed = 20.0  # 72 km/h
        vp.vehicle.id = "speed-vehicle"

        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.return_value = feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles/speed-vehicle")

        assert response.status_code == 200
        data = response.json()
        assert data["speed_kmh"] == pytest.approx(72.0, rel=0.1)


class TestErrorHandling:
    """Tests for error handling in vehicle endpoints."""

    def test_fetcher_error_returns_503(self, client):
        """Test that fetcher errors return 503."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_vehicle_positions.side_effect = Exception("Network error")

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/vehicles")

        assert response.status_code == 503
        assert "Failed to fetch" in response.json()["detail"]

    def test_mode_validation(self, client):
        """Test mode parameter validation for all 4 modes."""
        # Valid modes - all 4 should work
        for mode in ["metro", "vline", "tram", "bus"]:
            # This will fail due to no API key, but shouldn't fail validation
            response = client.get(f"/api/v1/vehicles?mode={mode}")
            assert response.status_code in [200, 503]  # Not 422

        # Invalid mode
        response = client.get("/api/v1/vehicles?mode=ferry")
        assert response.status_code == 422
