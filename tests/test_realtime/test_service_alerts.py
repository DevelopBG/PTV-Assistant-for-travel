"""
Unit tests for Service Alert Parser - Phase 9

Tests cover:
- ServiceAlert dataclass functionality
- InformedEntity and ActivePeriod dataclasses
- ServiceAlertParser parsing
- Filtering by route, stop, trip, severity, effect
- Active period checking
- Summary generation
- Error handling
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
from google.transit import gtfs_realtime_pb2

from src.realtime.models import (
    ServiceAlert,
    ServiceAlertSummary,
    InformedEntity,
    ActivePeriod,
    AlertCause,
    AlertEffect,
    AlertSeverity,
)
from src.realtime.service_alerts import ServiceAlertParser


# ============== InformedEntity Tests ==============

class TestInformedEntity:
    """Test InformedEntity dataclass functionality."""

    def test_informed_entity_creation(self):
        """Test basic InformedEntity creation."""
        entity = InformedEntity(
            agency_id="agency-1",
            route_id="route-A",
            route_type=1,
            stop_id="stop-001",
            trip_id="trip-123",
            direction_id=0
        )
        assert entity.agency_id == "agency-1"
        assert entity.route_id == "route-A"
        assert entity.stop_id == "stop-001"

    def test_affects_route_true(self):
        """Test affects_route returns True for matching route."""
        entity = InformedEntity(route_id="route-A")
        assert entity.affects_route("route-A") is True

    def test_affects_route_false(self):
        """Test affects_route returns False for non-matching route."""
        entity = InformedEntity(route_id="route-A")
        assert entity.affects_route("route-B") is False

    def test_affects_stop_true(self):
        """Test affects_stop returns True for matching stop."""
        entity = InformedEntity(stop_id="stop-001")
        assert entity.affects_stop("stop-001") is True

    def test_affects_stop_false(self):
        """Test affects_stop returns False for non-matching stop."""
        entity = InformedEntity(stop_id="stop-001")
        assert entity.affects_stop("stop-002") is False

    def test_affects_trip_true(self):
        """Test affects_trip returns True for matching trip."""
        entity = InformedEntity(trip_id="trip-123")
        assert entity.affects_trip("trip-123") is True

    def test_affects_trip_false(self):
        """Test affects_trip returns False for non-matching trip."""
        entity = InformedEntity(trip_id="trip-123")
        assert entity.affects_trip("trip-456") is False

    def test_get_description_route(self):
        """Test get_description with route."""
        entity = InformedEntity(route_id="route-A")
        assert entity.get_description() == "Route route-A"

    def test_get_description_stop(self):
        """Test get_description with stop."""
        entity = InformedEntity(stop_id="stop-001")
        assert entity.get_description() == "Stop stop-001"

    def test_get_description_trip(self):
        """Test get_description with trip."""
        entity = InformedEntity(trip_id="trip-123")
        assert entity.get_description() == "Trip trip-123"

    def test_get_description_multiple(self):
        """Test get_description with multiple entities."""
        entity = InformedEntity(route_id="route-A", stop_id="stop-001")
        desc = entity.get_description()
        assert "Route route-A" in desc
        assert "Stop stop-001" in desc

    def test_get_description_agency_only(self):
        """Test get_description with only agency."""
        entity = InformedEntity(agency_id="agency-1")
        assert entity.get_description() == "Agency agency-1"

    def test_get_description_empty(self):
        """Test get_description with no entities."""
        entity = InformedEntity()
        assert entity.get_description() == "Entire network"


# ============== ActivePeriod Tests ==============

class TestActivePeriod:
    """Test ActivePeriod dataclass functionality."""

    def test_active_period_creation(self):
        """Test basic ActivePeriod creation."""
        period = ActivePeriod(start=1704067200, end=1704153600)
        assert period.start == 1704067200
        assert period.end == 1704153600

    def test_is_active_within_period(self):
        """Test is_active returns True within period."""
        period = ActivePeriod(start=1000, end=2000)
        assert period.is_active(1500) is True

    def test_is_active_before_start(self):
        """Test is_active returns False before start."""
        period = ActivePeriod(start=1000, end=2000)
        assert period.is_active(500) is False

    def test_is_active_after_end(self):
        """Test is_active returns False after end."""
        period = ActivePeriod(start=1000, end=2000)
        assert period.is_active(2500) is False

    def test_is_active_at_start(self):
        """Test is_active returns True at exact start."""
        period = ActivePeriod(start=1000, end=2000)
        assert period.is_active(1000) is True

    def test_is_active_at_end(self):
        """Test is_active returns True at exact end."""
        period = ActivePeriod(start=1000, end=2000)
        assert period.is_active(2000) is True

    def test_is_active_no_start(self):
        """Test is_active when start is None (already active)."""
        period = ActivePeriod(start=None, end=2000)
        assert period.is_active(500) is True

    def test_is_active_no_end(self):
        """Test is_active when end is None (no end time)."""
        period = ActivePeriod(start=1000, end=None)
        assert period.is_active(5000) is True

    def test_is_active_start_zero(self):
        """Test is_active when start is 0 (already active)."""
        period = ActivePeriod(start=0, end=2000)
        assert period.is_active(500) is True

    def test_is_active_end_zero(self):
        """Test is_active when end is 0 (no end time)."""
        period = ActivePeriod(start=1000, end=0)
        assert period.is_active(5000) is True


# ============== ServiceAlert Tests ==============

class TestServiceAlert:
    """Test ServiceAlert dataclass functionality."""

    @pytest.fixture
    def sample_alert(self):
        """Create a sample service alert."""
        return ServiceAlert(
            alert_id="alert-001",
            cause=AlertCause.MAINTENANCE,
            effect=AlertEffect.REDUCED_SERVICE,
            severity=AlertSeverity.WARNING,
            header_text="Track maintenance",
            description_text="Reduced service due to track maintenance",
            url="https://ptv.vic.gov.au/alerts/001",
            active_periods=[ActivePeriod(start=1000, end=2000)],
            informed_entities=[
                InformedEntity(route_id="route-A"),
                InformedEntity(stop_id="stop-001")
            ],
            timestamp=1704067200
        )

    def test_service_alert_creation(self, sample_alert):
        """Test basic ServiceAlert creation."""
        assert sample_alert.alert_id == "alert-001"
        assert sample_alert.cause == AlertCause.MAINTENANCE
        assert sample_alert.effect == AlertEffect.REDUCED_SERVICE
        assert sample_alert.severity == AlertSeverity.WARNING
        assert sample_alert.header_text == "Track maintenance"

    def test_is_active_within_period(self, sample_alert):
        """Test is_active within active period."""
        assert sample_alert.is_active(1500) is True

    def test_is_active_outside_period(self, sample_alert):
        """Test is_active outside active period."""
        assert sample_alert.is_active(500) is False

    def test_is_active_no_periods(self):
        """Test is_active when no periods defined (always active)."""
        alert = ServiceAlert(alert_id="a1", active_periods=[])
        assert alert.is_active(1500) is True

    def test_is_active_multiple_periods(self):
        """Test is_active with multiple active periods."""
        alert = ServiceAlert(
            alert_id="a1",
            active_periods=[
                ActivePeriod(start=1000, end=2000),
                ActivePeriod(start=3000, end=4000)
            ]
        )
        assert alert.is_active(1500) is True
        assert alert.is_active(3500) is True
        assert alert.is_active(2500) is False

    def test_affects_route_true(self, sample_alert):
        """Test affects_route returns True for affected route."""
        assert sample_alert.affects_route("route-A") is True

    def test_affects_route_false(self, sample_alert):
        """Test affects_route returns False for unaffected route."""
        assert sample_alert.affects_route("route-B") is False

    def test_affects_stop_true(self, sample_alert):
        """Test affects_stop returns True for affected stop."""
        assert sample_alert.affects_stop("stop-001") is True

    def test_affects_stop_false(self, sample_alert):
        """Test affects_stop returns False for unaffected stop."""
        assert sample_alert.affects_stop("stop-002") is False

    def test_affects_trip_true(self):
        """Test affects_trip returns True for affected trip."""
        alert = ServiceAlert(
            alert_id="a1",
            informed_entities=[InformedEntity(trip_id="trip-123")]
        )
        assert alert.affects_trip("trip-123") is True

    def test_affects_trip_false(self, sample_alert):
        """Test affects_trip returns False for unaffected trip."""
        assert sample_alert.affects_trip("trip-123") is False

    def test_get_cause_display(self, sample_alert):
        """Test get_cause_display returns human-readable string."""
        assert sample_alert.get_cause_display() == "Maintenance"

    def test_get_effect_display(self, sample_alert):
        """Test get_effect_display returns human-readable string."""
        assert sample_alert.get_effect_display() == "Reduced Service"

    def test_get_severity_display(self, sample_alert):
        """Test get_severity_display returns human-readable string."""
        assert sample_alert.get_severity_display() == "Warning"

    def test_get_affected_routes(self, sample_alert):
        """Test get_affected_routes returns list of route IDs."""
        routes = sample_alert.get_affected_routes()
        assert "route-A" in routes
        assert len(routes) == 1

    def test_get_affected_stops(self, sample_alert):
        """Test get_affected_stops returns list of stop IDs."""
        stops = sample_alert.get_affected_stops()
        assert "stop-001" in stops
        assert len(stops) == 1

    def test_get_summary_with_header(self, sample_alert):
        """Test get_summary returns header text."""
        assert sample_alert.get_summary() == "Track maintenance"

    def test_get_summary_without_header(self):
        """Test get_summary without header text."""
        alert = ServiceAlert(
            alert_id="a1",
            cause=AlertCause.WEATHER,
            effect=AlertEffect.SIGNIFICANT_DELAYS
        )
        summary = alert.get_summary()
        assert "Significant Delays" in summary
        assert "Weather" in summary


class TestServiceAlertSummary:
    """Test ServiceAlertSummary dataclass."""

    def test_summary_creation(self):
        """Test basic summary creation."""
        summary = ServiceAlertSummary(
            total_alerts=5,
            by_severity={"WARNING": 3, "SEVERE": 2},
            by_effect={"NO_SERVICE": 1, "REDUCED_SERVICE": 4},
            affected_routes=["route-A", "route-B"],
            affected_stops=["stop-001"],
            timestamp=1704067200,
            mode="metro"
        )
        assert summary.total_alerts == 5
        assert summary.by_severity["WARNING"] == 3
        assert "route-A" in summary.affected_routes


# ============== ServiceAlertParser Tests ==============

class TestServiceAlertParser:
    """Test ServiceAlertParser functionality."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return ServiceAlertParser()

    @pytest.fixture
    def mock_feed(self):
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
        period.end = 2000

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

        # Alert 2: Minimal data
        entity2 = feed.entity.add()
        entity2.id = "alert-002"
        alert2 = entity2.alert
        informed3 = alert2.informed_entity.add()
        informed3.route_id = "route-B"

        # Alert 3: With trip
        entity3 = feed.entity.add()
        entity3.id = "alert-003"
        alert3 = entity3.alert
        alert3.cause = gtfs_realtime_pb2.Alert.ACCIDENT
        alert3.effect = gtfs_realtime_pb2.Alert.NO_SERVICE
        informed4 = alert3.informed_entity.add()
        informed4.trip.trip_id = "trip-123"

        return feed

    def test_parser_creation(self, parser):
        """Test parser creation without fetcher."""
        assert parser.fetcher is None
        assert parser._cache == {}

    def test_parser_with_fetcher(self):
        """Test parser creation with fetcher."""
        mock_fetcher = Mock()
        parser = ServiceAlertParser(fetcher=mock_fetcher)
        assert parser.fetcher is mock_fetcher

    def test_parse_feed(self, parser, mock_feed):
        """Test parsing a complete feed."""
        alerts = parser.parse_feed(mock_feed)
        assert len(alerts) == 3

    def test_parse_feed_alert_ids(self, parser, mock_feed):
        """Test parsed alerts have correct IDs."""
        alerts = parser.parse_feed(mock_feed)
        alert_ids = [a.alert_id for a in alerts]
        assert "alert-001" in alert_ids
        assert "alert-002" in alert_ids
        assert "alert-003" in alert_ids

    def test_parse_feed_cause_effect(self, parser, mock_feed):
        """Test parsed alerts have correct cause and effect."""
        alerts = parser.parse_feed(mock_feed)
        alert1 = next(a for a in alerts if a.alert_id == "alert-001")
        assert alert1.cause == AlertCause.MAINTENANCE
        assert alert1.effect == AlertEffect.REDUCED_SERVICE

    def test_parse_feed_active_periods(self, parser, mock_feed):
        """Test parsed alerts have correct active periods."""
        alerts = parser.parse_feed(mock_feed)
        alert1 = next(a for a in alerts if a.alert_id == "alert-001")
        assert len(alert1.active_periods) == 1
        assert alert1.active_periods[0].start == 1000
        assert alert1.active_periods[0].end == 2000

    def test_parse_feed_informed_entities(self, parser, mock_feed):
        """Test parsed alerts have correct informed entities."""
        alerts = parser.parse_feed(mock_feed)
        alert1 = next(a for a in alerts if a.alert_id == "alert-001")
        assert len(alert1.informed_entities) == 2
        assert any(e.route_id == "route-A" for e in alert1.informed_entities)
        assert any(e.stop_id == "stop-001" for e in alert1.informed_entities)

    def test_parse_feed_text(self, parser, mock_feed):
        """Test parsed alerts have correct text."""
        alerts = parser.parse_feed(mock_feed)
        alert1 = next(a for a in alerts if a.alert_id == "alert-001")
        assert alert1.header_text == "Track maintenance"
        assert alert1.description_text == "Reduced service due to track maintenance"

    def test_parse_feed_empty(self, parser):
        """Test parsing empty feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        alerts = parser.parse_feed(feed)
        assert alerts == []

    def test_parse_feed_non_alert_entities(self, parser):
        """Test parsing feed with non-alert entities."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        # Add a vehicle position entity (not an alert)
        entity = feed.entity.add()
        entity.id = "vehicle-1"
        entity.vehicle.position.latitude = -37.8

        alerts = parser.parse_feed(feed)
        assert alerts == []

    def test_fetch_alerts_no_fetcher(self, parser):
        """Test fetch_alerts raises error without fetcher."""
        with pytest.raises(ValueError, match="Fetcher not available"):
            parser.fetch_alerts()

    def test_fetch_alerts_success(self, mock_feed):
        """Test fetch_alerts with working fetcher."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_feed
        parser = ServiceAlertParser(fetcher=mock_fetcher)

        alerts = parser.fetch_alerts(mode="metro")
        assert len(alerts) == 3
        mock_fetcher.fetch_service_alerts.assert_called_once_with(mode="metro")

    def test_fetch_alerts_caches_result(self, mock_feed):
        """Test fetch_alerts caches the result."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_feed
        parser = ServiceAlertParser(fetcher=mock_fetcher)

        parser.fetch_alerts(mode="metro")
        assert "metro" in parser._cache
        assert len(parser._cache["metro"]) == 3

    def test_get_alerts_for_route(self, parser, mock_feed):
        """Test filtering alerts by route."""
        alerts = parser.parse_feed(mock_feed)
        route_alerts = parser.get_alerts_for_route("route-A", alerts)
        assert len(route_alerts) == 1
        assert route_alerts[0].alert_id == "alert-001"

    def test_get_alerts_for_route_none_found(self, parser, mock_feed):
        """Test filtering alerts by route when none match."""
        alerts = parser.parse_feed(mock_feed)
        route_alerts = parser.get_alerts_for_route("route-X", alerts)
        assert route_alerts == []

    def test_get_alerts_for_stop(self, parser, mock_feed):
        """Test filtering alerts by stop."""
        alerts = parser.parse_feed(mock_feed)
        stop_alerts = parser.get_alerts_for_stop("stop-001", alerts)
        assert len(stop_alerts) == 1
        assert stop_alerts[0].alert_id == "alert-001"

    def test_get_alerts_for_trip(self, parser, mock_feed):
        """Test filtering alerts by trip."""
        alerts = parser.parse_feed(mock_feed)
        trip_alerts = parser.get_alerts_for_trip("trip-123", alerts)
        assert len(trip_alerts) == 1
        assert trip_alerts[0].alert_id == "alert-003"

    def test_get_active_alerts(self, parser, mock_feed):
        """Test filtering active alerts."""
        alerts = parser.parse_feed(mock_feed)
        # Alert 1 has period 1000-2000, others have no period (always active)
        active_alerts = parser.get_active_alerts(alerts, current_time=1500)
        assert len(active_alerts) == 3  # All are active at 1500

    def test_get_active_alerts_time_filter(self, parser, mock_feed):
        """Test filtering active alerts excludes expired ones."""
        alerts = parser.parse_feed(mock_feed)
        # At time 500, alert-001 should not be active (starts at 1000)
        active_alerts = parser.get_active_alerts(alerts, current_time=500)
        alert_ids = [a.alert_id for a in active_alerts]
        assert "alert-001" not in alert_ids
        assert "alert-002" in alert_ids  # No period = always active
        assert "alert-003" in alert_ids  # No period = always active

    def test_get_alert_by_id(self, parser, mock_feed):
        """Test getting alert by ID."""
        alerts = parser.parse_feed(mock_feed)
        alert = parser.get_alert_by_id("alert-002", alerts)
        assert alert is not None
        assert alert.alert_id == "alert-002"

    def test_get_alert_by_id_not_found(self, parser, mock_feed):
        """Test getting alert by ID when not found."""
        alerts = parser.parse_feed(mock_feed)
        alert = parser.get_alert_by_id("alert-999", alerts)
        assert alert is None

    def test_get_alerts_by_severity(self, parser):
        """Test filtering alerts by severity."""
        alerts = [
            ServiceAlert(alert_id="a1", severity=AlertSeverity.WARNING),
            ServiceAlert(alert_id="a2", severity=AlertSeverity.SEVERE),
            ServiceAlert(alert_id="a3", severity=AlertSeverity.WARNING),
        ]
        warning_alerts = parser.get_alerts_by_severity(AlertSeverity.WARNING, alerts)
        assert len(warning_alerts) == 2

    def test_get_alerts_by_effect(self, parser):
        """Test filtering alerts by effect."""
        alerts = [
            ServiceAlert(alert_id="a1", effect=AlertEffect.NO_SERVICE),
            ServiceAlert(alert_id="a2", effect=AlertEffect.REDUCED_SERVICE),
            ServiceAlert(alert_id="a3", effect=AlertEffect.NO_SERVICE),
        ]
        no_service = parser.get_alerts_by_effect(AlertEffect.NO_SERVICE, alerts)
        assert len(no_service) == 2

    def test_get_summary(self, parser, mock_feed):
        """Test generating summary."""
        alerts = parser.parse_feed(mock_feed)
        summary = parser.get_summary(alerts, mode="metro")

        assert summary.total_alerts == 3
        assert summary.mode == "metro"
        assert "route-A" in summary.affected_routes
        assert "route-B" in summary.affected_routes
        assert "stop-001" in summary.affected_stops

    def test_get_summary_by_severity(self, parser):
        """Test summary counts by severity."""
        alerts = [
            ServiceAlert(alert_id="a1", severity=AlertSeverity.WARNING),
            ServiceAlert(alert_id="a2", severity=AlertSeverity.SEVERE),
            ServiceAlert(alert_id="a3", severity=AlertSeverity.WARNING),
        ]
        summary = parser.get_summary(alerts)
        assert summary.by_severity["WARNING"] == 2
        assert summary.by_severity["SEVERE"] == 1

    def test_get_summary_by_effect(self, parser):
        """Test summary counts by effect."""
        alerts = [
            ServiceAlert(alert_id="a1", effect=AlertEffect.NO_SERVICE),
            ServiceAlert(alert_id="a2", effect=AlertEffect.REDUCED_SERVICE),
        ]
        summary = parser.get_summary(alerts)
        assert summary.by_effect["NO_SERVICE"] == 1
        assert summary.by_effect["REDUCED_SERVICE"] == 1

    def test_clear_cache(self, mock_feed):
        """Test clearing cache."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_feed
        parser = ServiceAlertParser(fetcher=mock_fetcher)

        parser.fetch_alerts(mode="metro")
        assert len(parser._cache) == 1

        parser.clear_cache()
        assert parser._cache == {}

    def test_get_cached_alerts_empty(self, parser):
        """Test _get_cached_alerts returns empty list when cache empty."""
        alerts = parser._get_cached_alerts()
        assert alerts == []

    def test_get_cached_alerts_from_cache(self, mock_feed):
        """Test _get_cached_alerts returns cached alerts."""
        mock_fetcher = Mock()
        mock_fetcher.fetch_service_alerts.return_value = mock_feed
        parser = ServiceAlertParser(fetcher=mock_fetcher)

        parser.fetch_alerts(mode="metro")
        cached = parser._get_cached_alerts()
        assert len(cached) == 3


# ============== Parser Edge Cases ==============

class TestServiceAlertParserEdgeCases:
    """Test edge cases in ServiceAlertParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return ServiceAlertParser()

    def test_parse_alert_with_url(self, parser):
        """Test parsing alert with URL."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "alert-url"
        alert = entity.alert

        url_translation = alert.url.translation.add()
        url_translation.text = "https://ptv.vic.gov.au"
        url_translation.language = "en"

        alerts = parser.parse_feed(feed)
        assert len(alerts) == 1
        assert alerts[0].url == "https://ptv.vic.gov.au"

    def test_parse_alert_with_trip_in_informed_entity(self, parser):
        """Test parsing alert with trip descriptor in informed entity."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "alert-trip"
        alert = entity.alert
        informed = alert.informed_entity.add()
        informed.trip.trip_id = "trip-999"
        informed.trip.direction_id = 1

        alerts = parser.parse_feed(feed)
        assert len(alerts) == 1
        assert alerts[0].informed_entities[0].trip_id == "trip-999"
        assert alerts[0].informed_entities[0].direction_id == 1

    def test_parse_translated_text_no_language(self, parser):
        """Test parsing translated text without language specified."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "alert-nolang"
        alert = entity.alert
        translation = alert.header_text.translation.add()
        translation.text = "No language specified"
        # No language field set

        alerts = parser.parse_feed(feed)
        assert len(alerts) == 1
        assert alerts[0].header_text == "No language specified"

    def test_parse_translated_text_non_english(self, parser):
        """Test parsing translated text with non-English first."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "alert-multi"
        alert = entity.alert
        # Spanish translation
        es_translation = alert.header_text.translation.add()
        es_translation.text = "Servicio reducido"
        es_translation.language = "es"
        # English translation
        en_translation = alert.header_text.translation.add()
        en_translation.text = "Reduced service"
        en_translation.language = "en"

        alerts = parser.parse_feed(feed)
        assert len(alerts) == 1
        # Should prefer English
        assert alerts[0].header_text == "Reduced service"

    def test_parse_translated_text_only_non_english(self, parser):
        """Test parsing translated text with only non-English."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "alert-es"
        alert = entity.alert
        es_translation = alert.header_text.translation.add()
        es_translation.text = "Servicio reducido"
        es_translation.language = "es"

        alerts = parser.parse_feed(feed)
        assert len(alerts) == 1
        # Should fall back to first translation
        assert alerts[0].header_text == "Servicio reducido"

    def test_parse_unknown_cause(self, parser):
        """Test parsing alert with unknown cause value."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "alert-unknown"
        # Add an alert and an informed entity to make it valid
        entity.alert.informed_entity.add().route_id = "test-route"
        # Not setting cause - defaults to UNKNOWN_CAUSE

        alerts = parser.parse_feed(feed)
        assert len(alerts) == 1
        assert alerts[0].cause == AlertCause.UNKNOWN_CAUSE

    def test_parse_all_cause_values(self, parser):
        """Test parsing all cause enum values."""
        cause_map = {
            gtfs_realtime_pb2.Alert.UNKNOWN_CAUSE: AlertCause.UNKNOWN_CAUSE,
            gtfs_realtime_pb2.Alert.OTHER_CAUSE: AlertCause.OTHER_CAUSE,
            gtfs_realtime_pb2.Alert.TECHNICAL_PROBLEM: AlertCause.TECHNICAL_PROBLEM,
            gtfs_realtime_pb2.Alert.STRIKE: AlertCause.STRIKE,
            gtfs_realtime_pb2.Alert.DEMONSTRATION: AlertCause.DEMONSTRATION,
            gtfs_realtime_pb2.Alert.ACCIDENT: AlertCause.ACCIDENT,
            gtfs_realtime_pb2.Alert.HOLIDAY: AlertCause.HOLIDAY,
            gtfs_realtime_pb2.Alert.WEATHER: AlertCause.WEATHER,
            gtfs_realtime_pb2.Alert.MAINTENANCE: AlertCause.MAINTENANCE,
            gtfs_realtime_pb2.Alert.CONSTRUCTION: AlertCause.CONSTRUCTION,
            gtfs_realtime_pb2.Alert.POLICE_ACTIVITY: AlertCause.POLICE_ACTIVITY,
            gtfs_realtime_pb2.Alert.MEDICAL_EMERGENCY: AlertCause.MEDICAL_EMERGENCY,
        }

        for proto_cause, expected in cause_map.items():
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.header.gtfs_realtime_version = "2.0"
            entity = feed.entity.add()
            entity.id = f"alert-{proto_cause}"
            entity.alert.cause = proto_cause

            alerts = parser.parse_feed(feed)
            assert len(alerts) == 1
            assert alerts[0].cause == expected

    def test_parse_all_effect_values(self, parser):
        """Test parsing all effect enum values."""
        effect_map = {
            gtfs_realtime_pb2.Alert.NO_SERVICE: AlertEffect.NO_SERVICE,
            gtfs_realtime_pb2.Alert.REDUCED_SERVICE: AlertEffect.REDUCED_SERVICE,
            gtfs_realtime_pb2.Alert.SIGNIFICANT_DELAYS: AlertEffect.SIGNIFICANT_DELAYS,
            gtfs_realtime_pb2.Alert.DETOUR: AlertEffect.DETOUR,
            gtfs_realtime_pb2.Alert.ADDITIONAL_SERVICE: AlertEffect.ADDITIONAL_SERVICE,
            gtfs_realtime_pb2.Alert.MODIFIED_SERVICE: AlertEffect.MODIFIED_SERVICE,
            gtfs_realtime_pb2.Alert.OTHER_EFFECT: AlertEffect.OTHER_EFFECT,
            gtfs_realtime_pb2.Alert.UNKNOWN_EFFECT: AlertEffect.UNKNOWN_EFFECT,
            gtfs_realtime_pb2.Alert.STOP_MOVED: AlertEffect.STOP_MOVED,
        }

        for proto_effect, expected in effect_map.items():
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.header.gtfs_realtime_version = "2.0"
            entity = feed.entity.add()
            entity.id = f"alert-{proto_effect}"
            entity.alert.effect = proto_effect

            alerts = parser.parse_feed(feed)
            assert len(alerts) == 1
            assert alerts[0].effect == expected

    def test_uses_cache_when_alerts_not_provided(self, parser):
        """Test methods use cache when alerts parameter is None."""
        # Populate cache manually
        cached_alert = ServiceAlert(
            alert_id="cached",
            informed_entities=[InformedEntity(route_id="cached-route")]
        )
        parser._cache["test"] = [cached_alert]

        # Should use cached alerts
        route_alerts = parser.get_alerts_for_route("cached-route")
        assert len(route_alerts) == 1
        assert route_alerts[0].alert_id == "cached"
