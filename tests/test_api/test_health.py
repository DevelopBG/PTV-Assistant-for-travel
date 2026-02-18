"""
Tests for health check endpoint.
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


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_version(self, client):
        """Test health endpoint includes API version."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_includes_gtfs_loaded_flag(self, client):
        """Test health endpoint includes GTFS loaded flag."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "gtfs_loaded" in data
        assert data["gtfs_loaded"] is True

    def test_health_includes_counts(self, client):
        """Test health endpoint includes data counts."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "stops_count" in data
        assert "routes_count" in data
        assert "trips_count" in data
        assert data["stops_count"] > 0

    def test_health_includes_timestamp(self, client):
        """Test health endpoint includes timestamp."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "timestamp" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_200(self, client):
        """Test root endpoint returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_api_info(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data
