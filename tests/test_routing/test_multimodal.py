"""Tests for multi-modal routing features."""

import pytest
from src.routing.models import Leg, Journey


class TestLegModeSupport:
    """Tests for mode support in Leg dataclass."""

    def test_leg_with_route_type(self):
        """Test creating a leg with route_type."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=2  # Regional train
        )

        assert leg.route_type == 2
        assert leg.is_transfer is False

    def test_leg_get_mode_name_regional_train(self):
        """Test getting mode name for regional train."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=2
        )

        assert leg.get_mode_name() == "Regional Train"

    def test_leg_get_mode_name_metro(self):
        """Test getting mode name for metro."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=1
        )

        assert leg.get_mode_name() == "Metro"

    def test_leg_get_mode_name_tram(self):
        """Test getting mode name for tram."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=0
        )

        assert leg.get_mode_name() == "Tram"

    def test_leg_get_mode_name_bus(self):
        """Test getting mode name for bus."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=3
        )

        assert leg.get_mode_name() == "Bus"

    def test_leg_get_mode_name_ptv_bus(self):
        """Test getting mode name for PTV bus (route_type=700)."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=700
        )

        assert leg.get_mode_name() == "Bus"

    def test_leg_get_mode_name_walking_transfer(self):
        """Test getting mode name for walking transfer."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:05:00",
            trip_id="WALK",
            route_id="",
            is_transfer=True
        )

        assert leg.get_mode_name() == "Walking"

    def test_leg_get_mode_name_unknown(self):
        """Test getting mode name for unknown route type."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=99  # Unknown type
        )

        assert leg.get_mode_name() == "Unknown"


class TestJourneyMultiModal:
    """Tests for multi-modal journey features."""

    def test_journey_get_modes_used_single_mode(self):
        """Test getting modes used with single mode."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=2  # Regional train
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1002",
            destination_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            legs=[leg]
        )

        modes = journey.get_modes_used()
        assert len(modes) == 1
        assert modes[0] == "Regional Train"

    def test_journey_get_modes_used_multi_modal(self):
        """Test getting modes used with multiple modes."""
        leg1 = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=2  # Regional train
        )

        leg2 = Leg(
            from_stop_id="1002",
            from_stop_name="Stop B",
            to_stop_id="1003",
            to_stop_name="Stop C",
            departure_time="08:15:00",
            arrival_time="08:25:00",
            trip_id="T2",
            route_id="R2",
            route_type=3  # Bus
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1003",
            destination_stop_name="Stop C",
            departure_time="08:00:00",
            arrival_time="08:25:00",
            legs=[leg1, leg2]
        )

        modes = journey.get_modes_used()
        assert len(modes) == 2
        assert "Regional Train" in modes
        assert "Bus" in modes

    def test_journey_get_modes_used_ignores_walking(self):
        """Test that walking transfers are excluded from modes list."""
        leg1 = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=2  # Regional train
        )

        # Walking transfer
        leg2 = Leg(
            from_stop_id="1002",
            from_stop_name="Stop B",
            to_stop_id="1003",
            to_stop_name="Stop C Platform",
            departure_time="08:10:00",
            arrival_time="08:15:00",
            trip_id="WALK",
            route_id="",
            is_transfer=True
        )

        leg3 = Leg(
            from_stop_id="1003",
            from_stop_name="Stop C Platform",
            to_stop_id="1004",
            to_stop_name="Stop D",
            departure_time="08:15:00",
            arrival_time="08:25:00",
            trip_id="T3",
            route_id="R3",
            route_type=0  # Tram
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1004",
            destination_stop_name="Stop D",
            departure_time="08:00:00",
            arrival_time="08:25:00",
            legs=[leg1, leg2, leg3]
        )

        modes = journey.get_modes_used()
        assert len(modes) == 2
        assert "Regional Train" in modes
        assert "Tram" in modes
        assert "Walking" not in modes

    def test_journey_is_multi_modal_false(self):
        """Test is_multi_modal returns False for single mode."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=2
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1002",
            destination_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            legs=[leg]
        )

        assert journey.is_multi_modal() is False

    def test_journey_is_multi_modal_true(self):
        """Test is_multi_modal returns True for multiple modes."""
        leg1 = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_type=1  # Metro
        )

        leg2 = Leg(
            from_stop_id="1002",
            from_stop_name="Stop B",
            to_stop_id="1003",
            to_stop_name="Stop C",
            departure_time="08:15:00",
            arrival_time="08:25:00",
            trip_id="T2",
            route_id="R2",
            route_type=0  # Tram
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1003",
            destination_stop_name="Stop C",
            departure_time="08:00:00",
            arrival_time="08:25:00",
            legs=[leg1, leg2]
        )

        assert journey.is_multi_modal() is True

    def test_journey_format_summary_shows_mode(self):
        """Test that journey summary includes mode information."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Test Station A",
            to_stop_id="1002",
            to_stop_name="Test Station B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_name="Test Route",
            route_type=2,  # Regional train
            num_stops=2
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Test Station A",
            destination_stop_id="1002",
            destination_stop_name="Test Station B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            legs=[leg]
        )

        summary = journey.format_summary()

        # Check that mode is included in summary
        assert "Mode: Regional Train" in summary
        assert "Test Station A → Test Station B" in summary
        assert "08:00:00" in summary
        assert "08:10:00" in summary


class TestConnectionModeSupport:
    """Tests for mode support in Connection dataclass."""

    def test_connection_with_route_type(self):
        """Test creating connection with route_type."""
        from src.graph.transit_graph import Connection

        conn = Connection(
            from_stop_id="1001",
            to_stop_id="1002",
            trip_id="T1",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            travel_time_seconds=600,
            route_id="R1",
            route_type=2
        )

        assert conn.route_type == 2
        assert conn.is_transfer is False

    def test_connection_get_mode_name(self):
        """Test getting mode name from connection."""
        from src.graph.transit_graph import Connection

        conn = Connection(
            from_stop_id="1001",
            to_stop_id="1002",
            trip_id="T1",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            travel_time_seconds=600,
            route_id="R1",
            route_type=2
        )

        assert conn.get_mode_name() == "Regional Train"

    def test_connection_walking_transfer(self):
        """Test walking transfer connection."""
        from src.graph.transit_graph import Connection

        conn = Connection(
            from_stop_id="1001",
            to_stop_id="1002",
            trip_id="WALK",
            departure_time="08:10:00",
            arrival_time="08:15:00",
            travel_time_seconds=300,
            route_id="",
            is_transfer=True
        )

        assert conn.is_transfer is True
        assert conn.get_mode_name() == "Walking"
