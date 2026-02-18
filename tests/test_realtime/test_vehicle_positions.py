"""
Unit tests for Vehicle Position Parser - Phase 8

Tests cover:
- VehiclePosition dataclass functionality
- VehiclePositionParser parsing
- Filtering by route, trip, and proximity
- Summary generation
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock
from google.transit import gtfs_realtime_pb2

from src.realtime.models import (
    VehiclePosition,
    VehiclePositionSummary,
    VehicleStopStatus,
    CongestionLevel,
    OccupancyStatus
)
from src.realtime.vehicle_positions import VehiclePositionParser


# ============== VehiclePosition Dataclass Tests ==============

class TestVehiclePosition:
    """Test VehiclePosition dataclass functionality."""

    @pytest.fixture
    def sample_position(self):
        """Create a sample vehicle position."""
        return VehiclePosition(
            vehicle_id="train-001",
            latitude=-37.8136,
            longitude=144.9631,
            timestamp=1704067200,
            trip_id="trip-123",
            route_id="route-456",
            direction_id=0,
            label="Train 001",
            bearing=45.0,
            speed=16.67,  # 60 km/h in m/s
            stop_id="stop-789",
            current_status=VehicleStopStatus.IN_TRANSIT_TO,
            occupancy_status=OccupancyStatus.MANY_SEATS_AVAILABLE
        )

    def test_vehicle_position_creation(self, sample_position):
        """Test basic VehiclePosition creation."""
        assert sample_position.vehicle_id == "train-001"
        assert sample_position.latitude == -37.8136
        assert sample_position.longitude == 144.9631
        assert sample_position.trip_id == "trip-123"

    def test_get_speed_kmh(self, sample_position):
        """Test speed conversion to km/h."""
        speed_kmh = sample_position.get_speed_kmh()
        assert speed_kmh == pytest.approx(60.0, rel=0.1)

    def test_get_speed_kmh_none(self):
        """Test speed conversion when speed is None."""
        position = VehiclePosition(
            vehicle_id="v1",
            latitude=-37.8,
            longitude=144.9,
            timestamp=0,
            speed=None
        )
        assert position.get_speed_kmh() is None

    def test_get_status_display(self, sample_position):
        """Test status display string."""
        display = sample_position.get_status_display()
        assert "In Transit To" in display
        assert "stop-789" in display

    def test_get_status_display_unknown(self):
        """Test status display when status is None."""
        position = VehiclePosition(
            vehicle_id="v1",
            latitude=-37.8,
            longitude=144.9,
            timestamp=0
        )
        assert position.get_status_display() == "Unknown"

    def test_get_status_display_no_stop(self):
        """Test status display when no stop ID."""
        position = VehiclePosition(
            vehicle_id="v1",
            latitude=-37.8,
            longitude=144.9,
            timestamp=0,
            current_status=VehicleStopStatus.STOPPED_AT
        )
        display = position.get_status_display()
        assert "Stopped At" in display

    def test_get_occupancy_display(self, sample_position):
        """Test occupancy display string."""
        display = sample_position.get_occupancy_display()
        assert "Many Seats Available" in display

    def test_get_occupancy_display_unknown(self):
        """Test occupancy display when status is None."""
        position = VehiclePosition(
            vehicle_id="v1",
            latitude=-37.8,
            longitude=144.9,
            timestamp=0
        )
        assert position.get_occupancy_display() == "Unknown"

    def test_has_location_valid(self, sample_position):
        """Test has_location with valid coordinates."""
        assert sample_position.has_location() is True

    def test_has_location_invalid_lat(self):
        """Test has_location with invalid latitude."""
        position = VehiclePosition(
            vehicle_id="v1",
            latitude=100.0,  # Invalid
            longitude=144.9,
            timestamp=0
        )
        assert position.has_location() is False

    def test_has_location_invalid_lon(self):
        """Test has_location with invalid longitude."""
        position = VehiclePosition(
            vehicle_id="v1",
            latitude=-37.8,
            longitude=200.0,  # Invalid
            timestamp=0
        )
        assert position.has_location() is False


class TestVehiclePositionSummary:
    """Test VehiclePositionSummary dataclass."""

    def test_summary_creation(self):
        """Test basic summary creation."""
        summary = VehiclePositionSummary(
            total_vehicles=10,
            vehicles_with_trip=8,
            vehicles_in_transit=6,
            vehicles_at_stop=2,
            average_speed_kmh=45.5,
            timestamp=1704067200,
            mode="vline"
        )
        assert summary.total_vehicles == 10
        assert summary.vehicles_with_trip == 8
        assert summary.average_speed_kmh == 45.5


# ============== VehiclePositionParser Tests ==============

class TestVehiclePositionParser:
    """Test VehiclePositionParser functionality."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return VehiclePositionParser()

    @pytest.fixture
    def mock_feed(self):
        """Create a mock GTFS Realtime vehicle position feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1704067200

        # Vehicle 1: Complete data
        entity1 = feed.entity.add()
        entity1.id = "entity-1"
        vp1 = entity1.vehicle
        vp1.position.latitude = -37.8136
        vp1.position.longitude = 144.9631
        vp1.position.bearing = 90.0
        vp1.position.speed = 20.0
        vp1.trip.trip_id = "trip-001"
        vp1.trip.route_id = "route-A"
        vp1.trip.direction_id = 0
        vp1.vehicle.id = "vehicle-001"
        vp1.vehicle.label = "Train 001"
        vp1.stop_id = "stop-001"
        vp1.current_status = gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO
        vp1.timestamp = 1704067200

        # Vehicle 2: Minimal data
        entity2 = feed.entity.add()
        entity2.id = "entity-2"
        vp2 = entity2.vehicle
        vp2.position.latitude = -37.8200
        vp2.position.longitude = 144.9700
        vp2.trip.trip_id = "trip-002"
        vp2.trip.route_id = "route-A"
        vp2.vehicle.id = "vehicle-002"
        vp2.current_status = gtfs_realtime_pb2.VehiclePosition.STOPPED_AT
        vp2.timestamp = 1704067100

        # Vehicle 3: Different route
        entity3 = feed.entity.add()
        entity3.id = "entity-3"
        vp3 = entity3.vehicle
        vp3.position.latitude = -37.8300
        vp3.position.longitude = 144.9800
        vp3.trip.trip_id = "trip-003"
        vp3.trip.route_id = "route-B"
        vp3.vehicle.id = "vehicle-003"
        vp3.timestamp = 1704067150

        return feed

    @pytest.fixture
    def mock_feed_with_occupancy(self):
        """Create a feed with occupancy data."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "entity-occupancy"
        vp = entity.vehicle
        vp.position.latitude = -37.8136
        vp.position.longitude = 144.9631
        vp.vehicle.id = "vehicle-occ"
        vp.occupancy_status = gtfs_realtime_pb2.VehiclePosition.MANY_SEATS_AVAILABLE
        vp.congestion_level = gtfs_realtime_pb2.VehiclePosition.RUNNING_SMOOTHLY
        vp.timestamp = 1704067200

        return feed

    def test_parse_feed_basic(self, parser, mock_feed):
        """Test basic feed parsing."""
        positions = parser.parse_feed(mock_feed)
        assert len(positions) == 3

    def test_parse_feed_vehicle_data(self, parser, mock_feed):
        """Test that vehicle data is correctly parsed."""
        positions = parser.parse_feed(mock_feed)

        # Find vehicle-001
        v1 = next(p for p in positions if p.vehicle_id == "vehicle-001")
        assert v1.latitude == pytest.approx(-37.8136, rel=1e-5)
        assert v1.longitude == pytest.approx(144.9631, rel=1e-5)
        assert v1.trip_id == "trip-001"
        assert v1.route_id == "route-A"
        assert v1.label == "Train 001"
        assert v1.bearing == pytest.approx(90.0, rel=1e-5)
        assert v1.current_status == VehicleStopStatus.IN_TRANSIT_TO

    def test_parse_feed_occupancy(self, parser, mock_feed_with_occupancy):
        """Test parsing of occupancy data."""
        positions = parser.parse_feed(mock_feed_with_occupancy)
        assert len(positions) == 1

        v = positions[0]
        assert v.occupancy_status == OccupancyStatus.MANY_SEATS_AVAILABLE
        assert v.congestion_level == CongestionLevel.RUNNING_SMOOTHLY

    def test_parse_feed_empty(self, parser):
        """Test parsing empty feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        positions = parser.parse_feed(feed)
        assert len(positions) == 0

    def test_parse_feed_no_position(self, parser):
        """Test parsing entity without position data."""
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.id = "no-position"
        # No vehicle.position set

        positions = parser.parse_feed(feed)
        assert len(positions) == 0

    def test_get_vehicles_for_route(self, parser, mock_feed):
        """Test filtering vehicles by route."""
        positions = parser.parse_feed(mock_feed)
        route_a_vehicles = parser.get_vehicles_for_route("route-A", positions)

        assert len(route_a_vehicles) == 2
        assert all(v.route_id == "route-A" for v in route_a_vehicles)

    def test_get_vehicles_for_route_empty(self, parser, mock_feed):
        """Test filtering by non-existent route."""
        positions = parser.parse_feed(mock_feed)
        vehicles = parser.get_vehicles_for_route("route-NONE", positions)

        assert len(vehicles) == 0

    def test_get_vehicles_for_trip(self, parser, mock_feed):
        """Test filtering vehicles by trip."""
        positions = parser.parse_feed(mock_feed)
        trip_vehicles = parser.get_vehicles_for_trip("trip-001", positions)

        assert len(trip_vehicles) == 1
        assert trip_vehicles[0].trip_id == "trip-001"

    def test_get_vehicle_by_id(self, parser, mock_feed):
        """Test getting single vehicle by ID."""
        positions = parser.parse_feed(mock_feed)
        vehicle = parser.get_vehicle_by_id("vehicle-002", positions)

        assert vehicle is not None
        assert vehicle.vehicle_id == "vehicle-002"

    def test_get_vehicle_by_id_not_found(self, parser, mock_feed):
        """Test getting non-existent vehicle."""
        positions = parser.parse_feed(mock_feed)
        vehicle = parser.get_vehicle_by_id("vehicle-999", positions)

        assert vehicle is None

    def test_get_vehicles_near_stop(self, parser, mock_feed):
        """Test finding vehicles near a location."""
        positions = parser.parse_feed(mock_feed)

        # Use coordinates near vehicle-001
        nearby = parser.get_vehicles_near_stop(
            stop_lat=-37.8136,
            stop_lon=144.9631,
            radius_km=5.0,
            positions=positions
        )

        assert len(nearby) >= 1
        # First vehicle should be closest
        assert nearby[0].vehicle_id == "vehicle-001"

    def test_get_vehicles_near_stop_sorted_by_distance(self, parser, mock_feed):
        """Test that nearby vehicles are sorted by distance."""
        positions = parser.parse_feed(mock_feed)

        # Use coordinates between vehicles
        nearby = parser.get_vehicles_near_stop(
            stop_lat=-37.8150,
            stop_lon=144.9650,
            radius_km=10.0,
            positions=positions
        )

        # Should be sorted by distance (closest first)
        assert len(nearby) >= 2

    def test_get_vehicles_near_stop_radius_filter(self, parser, mock_feed):
        """Test that radius correctly filters vehicles."""
        positions = parser.parse_feed(mock_feed)

        # Very small radius - should only get closest
        nearby = parser.get_vehicles_near_stop(
            stop_lat=-37.8136,
            stop_lon=144.9631,
            radius_km=0.1,
            positions=positions
        )

        # Only the vehicle at exact location should be within 100m
        assert len(nearby) <= 1

    def test_get_summary(self, parser, mock_feed):
        """Test summary generation."""
        positions = parser.parse_feed(mock_feed)
        summary = parser.get_summary(positions, mode="vline")

        assert summary.total_vehicles == 3
        assert summary.vehicles_with_trip == 3
        assert summary.mode == "vline"

    def test_get_summary_with_status_counts(self, parser, mock_feed):
        """Test summary counts vehicles by status."""
        positions = parser.parse_feed(mock_feed)
        summary = parser.get_summary(positions)

        # Mock feed has 1 IN_TRANSIT_TO, 1 STOPPED_AT
        assert summary.vehicles_in_transit == 1
        assert summary.vehicles_at_stop == 1

    def test_get_summary_average_speed(self, parser, mock_feed):
        """Test average speed calculation."""
        positions = parser.parse_feed(mock_feed)
        summary = parser.get_summary(positions)

        # Only vehicle-001 has speed data (20.0 m/s = 72 km/h)
        if summary.average_speed_kmh:
            assert summary.average_speed_kmh == pytest.approx(72.0, rel=0.1)

    def test_clear_cache(self, parser):
        """Test cache clearing."""
        parser._cache["vline"] = []
        parser.clear_cache()
        assert len(parser._cache) == 0


class TestVehiclePositionParserWithFetcher:
    """Test VehiclePositionParser with mocked fetcher."""

    @pytest.fixture
    def mock_fetcher(self):
        """Create a mock fetcher."""
        fetcher = Mock()
        return fetcher

    @pytest.fixture
    def mock_feed(self):
        """Create a simple mock feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"

        entity = feed.entity.add()
        entity.id = "entity-1"
        vp = entity.vehicle
        vp.position.latitude = -37.8136
        vp.position.longitude = 144.9631
        vp.vehicle.id = "vehicle-001"
        vp.timestamp = 1704067200

        return feed

    def test_fetch_positions(self, mock_fetcher, mock_feed):
        """Test fetching positions through fetcher."""
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        parser = VehiclePositionParser(fetcher=mock_fetcher)
        positions = parser.fetch_positions(mode="vline")

        assert len(positions) == 1
        mock_fetcher.fetch_vehicle_positions.assert_called_once_with(mode="vline")

    def test_fetch_positions_caches_result(self, mock_fetcher, mock_feed):
        """Test that fetch_positions caches results."""
        mock_fetcher.fetch_vehicle_positions.return_value = mock_feed

        parser = VehiclePositionParser(fetcher=mock_fetcher)
        parser.fetch_positions(mode="vline")

        assert "vline" in parser._cache
        assert len(parser._cache["vline"]) == 1

    def test_fetch_positions_no_fetcher(self):
        """Test fetch_positions without fetcher raises error."""
        parser = VehiclePositionParser()

        with pytest.raises(ValueError, match="Fetcher not available"):
            parser.fetch_positions(mode="vline")

    def test_fetch_positions_fetcher_error(self, mock_fetcher):
        """Test handling of fetcher errors."""
        mock_fetcher.fetch_vehicle_positions.side_effect = Exception("Network error")

        parser = VehiclePositionParser(fetcher=mock_fetcher)

        with pytest.raises(Exception, match="Network error"):
            parser.fetch_positions(mode="vline")


class TestHaversineDistance:
    """Test distance calculation."""

    @pytest.fixture
    def parser(self):
        return VehiclePositionParser()

    def test_haversine_same_point(self, parser):
        """Test distance between same point is zero."""
        distance = parser._haversine_distance(
            -37.8136, 144.9631,
            -37.8136, 144.9631
        )
        assert distance == pytest.approx(0.0, abs=0.001)

    def test_haversine_known_distance(self, parser):
        """Test distance calculation with known points."""
        # Melbourne CBD to St Kilda (~5.5km)
        distance = parser._haversine_distance(
            -37.8136, 144.9631,  # Melbourne CBD
            -37.8674, 144.9743   # St Kilda
        )
        assert 5.0 < distance < 7.0

    def test_haversine_large_distance(self, parser):
        """Test distance calculation for larger distance."""
        # Melbourne to Sydney (~715km)
        distance = parser._haversine_distance(
            -37.8136, 144.9631,  # Melbourne
            -33.8688, 151.2093   # Sydney
        )
        assert 700 < distance < 730


# ============== Edge Cases and Error Handling ==============

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def parser(self):
        return VehiclePositionParser()

    def test_parse_entity_with_trip_update_not_vehicle(self, parser):
        """Test that trip updates (not vehicles) are skipped."""
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.id = "trip-update-entity"
        # This is a trip update, not a vehicle position
        entity.trip_update.trip.trip_id = "some-trip"

        positions = parser.parse_feed(feed)
        assert len(positions) == 0

    def test_get_methods_with_empty_cache(self, parser):
        """Test get methods with no cached data."""
        assert parser.get_vehicles_for_route("route-A") == []
        assert parser.get_vehicles_for_trip("trip-1") == []
        assert parser.get_vehicle_by_id("v1") is None
        assert parser.get_vehicles_near_stop(-37.8, 144.9) == []

    def test_vehicle_with_only_entity_id(self, parser):
        """Test parsing vehicle that only has entity ID (no vehicle descriptor)."""
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.id = "entity-only-id"
        vp = entity.vehicle
        vp.position.latitude = -37.8
        vp.position.longitude = 144.9

        positions = parser.parse_feed(feed)
        assert len(positions) == 1
        assert positions[0].vehicle_id == "entity-only-id"

    def test_summary_empty_positions(self, parser):
        """Test summary with no positions."""
        summary = parser.get_summary([])
        assert summary.total_vehicles == 0
        assert summary.average_speed_kmh is None

    def test_near_stop_with_invalid_positions(self, parser):
        """Test near stop filtering excludes invalid locations."""
        positions = [
            VehiclePosition(
                vehicle_id="v1",
                latitude=100.0,  # Invalid
                longitude=144.9,
                timestamp=0
            ),
            VehiclePosition(
                vehicle_id="v2",
                latitude=-37.8,
                longitude=144.9,
                timestamp=0
            )
        ]

        nearby = parser.get_vehicles_near_stop(
            stop_lat=-37.8,
            stop_lon=144.9,
            radius_km=10.0,
            positions=positions
        )

        # Only v2 should be included (v1 has invalid lat)
        assert len(nearby) == 1
        assert nearby[0].vehicle_id == "v2"
