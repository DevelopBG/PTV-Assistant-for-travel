"""
Tests for stops endpoint.
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


class TestStopSearch:
    """Tests for /api/v1/stops/search endpoint."""

    def test_search_returns_200(self, client):
        """Test search endpoint returns 200 OK."""
        response = client.get("/api/v1/stops/search?query=Test")
        assert response.status_code == 200

    def test_search_returns_results(self, client):
        """Test search returns matching stops."""
        # Use full name for better fuzzy match score
        response = client.get("/api/v1/stops/search?query=Test Station")
        data = response.json()
        assert data["success"] is True
        assert data["count"] > 0
        assert len(data["stops"]) > 0

    def test_search_includes_stop_details(self, client):
        """Test search results include stop details."""
        response = client.get("/api/v1/stops/search?query=Station")
        data = response.json()
        stop = data["stops"][0]
        assert "stop_id" in stop
        assert "stop_name" in stop

    def test_search_includes_match_score(self, client):
        """Test fuzzy search includes match score."""
        response = client.get("/api/v1/stops/search?query=Test&fuzzy=true")
        data = response.json()
        if data["stops"]:
            stop = data["stops"][0]
            assert "match_score" in stop
            assert stop["match_score"] > 0

    def test_search_respects_limit(self, client):
        """Test search respects limit parameter."""
        response = client.get("/api/v1/stops/search?query=Test&limit=2")
        data = response.json()
        assert len(data["stops"]) <= 2

    def test_search_exact_match(self, client):
        """Test exact match search."""
        response = client.get("/api/v1/stops/search?query=Test Station A&fuzzy=false")
        data = response.json()
        assert data["success"] is True

    def test_search_no_results(self, client):
        """Test search with no results."""
        response = client.get("/api/v1/stops/search?query=NonexistentStopXYZ123")
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 0
        assert len(data["stops"]) == 0

    def test_search_query_too_short(self, client):
        """Test search with query too short."""
        response = client.get("/api/v1/stops/search?query=T")
        assert response.status_code == 422  # Validation error

    def test_search_missing_query(self, client):
        """Test search without query parameter."""
        response = client.get("/api/v1/stops/search")
        assert response.status_code == 422  # Validation error


class TestGetStopById:
    """Tests for /api/v1/stops/{stop_id} endpoint."""

    def test_get_stop_returns_200(self, client):
        """Test get stop returns 200 for valid ID."""
        response = client.get("/api/v1/stops/1001")  # Test Station A
        assert response.status_code == 200

    def test_get_stop_returns_details(self, client):
        """Test get stop returns stop details."""
        response = client.get("/api/v1/stops/1001")
        data = response.json()
        assert data["stop_id"] == "1001"
        assert "stop_name" in data
        assert "Test Station A" in data["stop_name"]

    def test_get_stop_not_found(self, client):
        """Test get stop returns 404 for invalid ID."""
        response = client.get("/api/v1/stops/invalid_stop_id_999")
        assert response.status_code == 404
