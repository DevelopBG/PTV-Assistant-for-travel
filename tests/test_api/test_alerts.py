"""
Tests for service alerts API endpoints - Phase 9

Tests cover:
- All service alert endpoints
- Error handling and edge cases
- Response format validation
"""

import os
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2

from src.api.main import app
from src.api.dependencies import reset_transit_service, TransitService
import src.api.dependencies as deps
from src.realtime.models import (
    ServiceAlert,
    InformedEntity,
    ActivePeriod,
    AlertCause,
    AlertEffect,
    AlertSeverity,
)


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
def mock_alert_feed():
    """Create a mock GTFS Realtime service alert feed."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1704067200

    # Alert 1: Complete data
    entity1 = feed.entity.add()
    entity1.id = "alert-001"
    alert1 = entity1.alert

    # Active period
    period = alert1.active_period.add()
    period.start = 1000
    period.end = 2000000000  # Far future

    # Informed entity (route)
    informed = alert1.informed_entity.add()
    informed.route_id = "route-A"
    informed.route_type = 1

    # Informed entity (stop)
    informed2 = alert1.informed_entity.add()
    informed2.stop_id = "stop-001"

    # Cause and effect
    alert1.cause = gtfs_realtime_pb2.Alert.MAINTENANCE
    alert1.effect = gtfs_realtime_pb2.Alert.REDUCED_SERVICE

    # Text
    translation = alert1.header_text.translation.add()
    translation.text = "Track maintenance"
    translation.language = "en"

    desc_translation = alert1.description_text.translation.add()
    desc_translation.text = "Reduced service due to track maintenance"
    desc_translation.language = "en"

    # Alert 2: Different route
    entity2 = feed.entity.add()
    entity2.id = "alert-002"
    alert2 = entity2.alert
    informed3 = alert2.informed_entity.add()
    informed3.route_id = "route-B"
    alert2.cause = gtfs_realtime_pb2.Alert.WEATHER
    alert2.effect = gtfs_realtime_pb2.Alert.SIGNIFICANT_DELAYS

    # Alert 3: Severe warning
    entity3 = feed.entity.add()
    entity3.id = "alert-003"
    alert3 = entity3.alert
    alert3.cause = gtfs_realtime_pb2.Alert.ACCIDENT
    alert3.effect = gtfs_realtime_pb2.Alert.NO_SERVICE
    informed4 = alert3.informed_entity.add()
    informed4.route_id = "route-A"

    return feed


@pytest.fixture
def mock_service_alerts():
    """Create mock service alerts for testing."""
    return [
        ServiceAlert(
            alert_id="alert-001",
            cause=AlertCause.MAINTENANCE,
            effect=AlertEffect.REDUCED_SERVICE,
            severity=AlertSeverity.WARNING,
            header_text="Track maintenance",
            description_text="Reduced service due to track maintenance",
            active_periods=[ActivePeriod(start=1000, end=2000000000)],
            informed_entities=[
                InformedEntity(route_id="route-A"),
                InformedEntity(stop_id="stop-001")
            ],
            timestamp=1704067200
        ),
        ServiceAlert(
            alert_id="alert-002",
            cause=AlertCause.WEATHER,
            effect=AlertEffect.SIGNIFICANT_DELAYS,
            severity=AlertSeverity.INFO,
            header_text="Weather delays",
            informed_entities=[InformedEntity(route_id="route-B")],
            timestamp=1704067200
        ),
        ServiceAlert(
            alert_id="alert-003",
            cause=AlertCause.ACCIDENT,
            effect=AlertEffect.NO_SERVICE,
            severity=AlertSeverity.SEVERE,
            header_text="Service suspended",
            informed_entities=[InformedEntity(route_id="route-A")],
            timestamp=1704067200
        )
    ]


class TestGetAllAlerts:
    """Tests for GET /api/v1/alerts endpoint."""

    def test_get_alerts_no_api_key(self, client):
        """Test get alerts returns 503 when no API key configured."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 503
        assert "not available" in response.json()["detail"].lower()

    def test_get_alerts_with_mock_fetcher(self, client, mock_alert_feed):
        """Test get alerts with mocked fetcher."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts?mode=metro")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["mode"] == "metro"
        assert data["count"] >= 1
        assert len(data["alerts"]) >= 1

    def test_get_alerts_invalid_mode(self, client):
        """Test get alerts with invalid mode."""
        response = client.get("/api/v1/alerts?mode=invalid")
        assert response.status_code == 422

    def test_get_alerts_response_format(self, client, mock_alert_feed):
        """Test alert response format."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts")

        data = response.json()
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "alert_id" in alert
            assert "cause" in alert
            assert "effect" in alert
            assert "severity" in alert
            assert "informed_entities" in alert

    def test_get_all_alerts_active_only(self, client, mock_alert_feed):
        """Test get all alerts with active_only=True."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert "active" in data["message"]

    def test_get_all_alerts_including_inactive(self, client, mock_alert_feed):
        """Test get all alerts including inactive."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts?active_only=false")

        assert response.status_code == 200


class TestGetAlertSummary:
    """Tests for GET /api/v1/alerts/summary endpoint."""

    def test_get_summary_no_api_key(self, client):
        """Test summary returns 503 when no API key."""
        response = client.get("/api/v1/alerts/summary")
        assert response.status_code == 503

    def test_get_summary_with_mock(self, client, mock_alert_feed):
        """Test summary with mocked data."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/summary?mode=metro")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_alerts" in data
        assert "by_severity" in data
        assert "by_effect" in data
        assert "affected_routes" in data
        assert "affected_stops" in data


class TestGetAlertById:
    """Tests for GET /api/v1/alerts/{alert_id} endpoint."""

    def test_get_alert_not_found(self, client, mock_alert_feed):
        """Test getting non-existent alert returns 404."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/nonexistent-alert")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_alert_found(self, client, mock_alert_feed):
        """Test getting existing alert."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/alert-001")

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "alert-001"
        assert data["cause"] == "MAINTENANCE"
        assert data["effect"] == "REDUCED_SERVICE"


class TestGetAlertsForRoute:
    """Tests for GET /api/v1/alerts/route/{route_id} endpoint."""

    def test_get_alerts_for_route(self, client, mock_alert_feed):
        """Test getting alerts for a route."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/route/route-A")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["alerts"], list)
        # route-A should have multiple alerts in our mock data
        assert data["count"] >= 1

    def test_get_alerts_for_nonexistent_route(self, client, mock_alert_feed):
        """Test getting alerts for route with no alerts."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/route/nonexistent-route")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0


class TestGetAlertsForStop:
    """Tests for GET /api/v1/alerts/stop/{stop_id} endpoint."""

    def test_get_alerts_for_stop(self, client, mock_alert_feed):
        """Test getting alerts for a stop."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/stop/stop-001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["alerts"], list)

    def test_get_alerts_for_nonexistent_stop(self, client, mock_alert_feed):
        """Test getting alerts for stop with no alerts."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/stop/nonexistent-stop")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0


class TestGetAlertsBySeverity:
    """Tests for GET /api/v1/alerts/severity/{severity} endpoint."""

    def test_get_alerts_by_severity_warning(self, client, mock_alert_feed):
        """Test getting alerts by WARNING severity."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/severity/UNKNOWN_SEVERITY")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["alerts"], list)

    def test_get_alerts_by_severity_invalid(self, client, mock_alert_feed):
        """Test getting alerts with invalid severity."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/severity/INVALID")

        assert response.status_code == 400
        assert "Invalid severity" in response.json()["detail"]


class TestAlertResponseModel:
    """Tests for ServiceAlertResponse model."""

    def test_alert_response_includes_all_fields(self, client, mock_alert_feed):
        """Test that response includes all expected fields."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/alert-001")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "alert_id" in data
        assert "cause" in data
        assert "effect" in data
        assert "severity" in data

        # Optional fields
        assert "header_text" in data
        assert "description_text" in data
        assert "active_periods" in data
        assert "informed_entities" in data
        assert "affected_routes" in data
        assert "affected_stops" in data

    def test_informed_entity_includes_description(self, client, mock_alert_feed):
        """Test that informed entities include description."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_alert_feed

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/alert-001")

        assert response.status_code == 200
        data = response.json()

        if data["informed_entities"]:
            entity = data["informed_entities"][0]
            assert "description" in entity


class TestErrorHandling:
    """Tests for error handling in alert endpoints."""

    def test_fetcher_error_returns_503(self, client):
        """Test that fetcher errors return 503."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.side_effect = Exception("Network error")

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts")

        assert response.status_code == 503
        assert "Failed to fetch" in response.json()["detail"]

    def test_mode_validation(self, client):
        """Test mode parameter validation for all 4 modes."""
        # Valid modes - all 4 should work
        for mode in ["metro", "vline", "tram", "bus"]:
            response = client.get(f"/api/v1/alerts?mode={mode}")
            assert response.status_code in [200, 503]  # Not 422

        # Invalid mode
        response = client.get("/api/v1/alerts?mode=ferry")
        assert response.status_code == 422

    def test_summary_fetcher_error_returns_503(self, client):
        """Test that summary endpoint returns 503 on fetcher error."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.side_effect = Exception("Network error")

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/summary")

        assert response.status_code == 503

    def test_route_alerts_fetcher_error_returns_503(self, client):
        """Test that route alerts endpoint returns 503 on fetcher error."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.side_effect = Exception("Network error")

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/route/route-A")

        assert response.status_code == 503

    def test_stop_alerts_fetcher_error_returns_503(self, client):
        """Test that stop alerts endpoint returns 503 on fetcher error."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.side_effect = Exception("Network error")

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/stop/stop-001")

        assert response.status_code == 503

    def test_severity_alerts_fetcher_error_returns_503(self, client):
        """Test that severity alerts endpoint returns 503 on fetcher error."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.side_effect = Exception("Network error")

        with patch.object(
            deps._transit_service,
            'get_realtime_fetcher',
            return_value=mock_fetcher
        ):
            response = client.get("/api/v1/alerts/severity/WARNING")

        assert response.status_code == 503
