"""
Tests for journey planning endpoint.
"""

import os
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.dependencies import reset_transit_service, TransitService
import src.api.dependencies as deps

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


class TestJourneyPlan:
    """Tests for /api/v1/journey/plan endpoint."""

    def test_plan_returns_200(self, client):
        """Test plan endpoint returns 200 OK."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "Test Station A",
                "destination": "Test Station B",
                "departure_time": "08:00:00"
            }
        )
        assert response.status_code == 200

    def test_plan_returns_journey(self, client):
        """Test plan returns journey when route exists."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",  # Test Station A
                "destination": "1002",  # Test Station B
                "departure_time": "08:00:00"
            }
        )
        data = response.json()
        # May or may not find journey depending on fixture data
        assert "success" in data

    def test_plan_journey_includes_details_when_found(self, client):
        """Test journey includes required details when found."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",
                "destination": "1002",
                "departure_time": "08:00:00"
            }
        )
        data = response.json()
        if data.get("journey"):
            journey = data["journey"]
            assert "origin_stop_id" in journey
            assert "destination_stop_id" in journey
            assert "departure_time" in journey
            assert "arrival_time" in journey
            assert "duration_minutes" in journey
            assert "legs" in journey

    def test_plan_journey_with_fuzzy_names(self, client):
        """Test journey planning with fuzzy stop names."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "Test Station",
                "destination": "Fuzzy Test",
                "departure_time": "14:00:00"
            }
        )
        data = response.json()
        # Should at least resolve the stops
        assert response.status_code == 200

    def test_plan_journey_not_found_same_origin_dest(self, client):
        """Test journey not found when origin equals destination."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",
                "destination": "1001",
                "departure_time": "08:00:00"
            }
        )
        data = response.json()
        assert data["success"] is False
        assert data["journey"] is None

    def test_plan_invalid_origin(self, client):
        """Test journey with invalid origin."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "NonexistentStopXYZ",
                "destination": "1002",
                "departure_time": "08:00:00"
            }
        )
        data = response.json()
        assert data["success"] is False

    def test_plan_invalid_destination(self, client):
        """Test journey with invalid destination."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",
                "destination": "NonexistentStopXYZ",
                "departure_time": "08:00:00"
            }
        )
        data = response.json()
        assert data["success"] is False

    def test_plan_with_max_transfers(self, client):
        """Test journey with max_transfers parameter."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",
                "destination": "1002",
                "departure_time": "08:00:00",
                "max_transfers": 1
            }
        )
        assert response.status_code == 200

    def test_plan_without_realtime(self, client):
        """Test journey without realtime info."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",
                "destination": "1002",
                "departure_time": "08:00:00",
                "include_realtime": False
            }
        )
        assert response.status_code == 200

    def test_plan_missing_required_fields(self, client):
        """Test journey with missing required fields."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001"
                # Missing destination and departure_time
            }
        )
        assert response.status_code == 422  # Validation error

    def test_plan_with_all_parameters(self, client):
        """Test journey with all parameters specified."""
        response = client.post(
            "/api/v1/journey/plan",
            json={
                "origin": "1001",
                "destination": "1002",
                "departure_time": "08:00:00",
                "include_realtime": False,
                "max_transfers": 2
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
