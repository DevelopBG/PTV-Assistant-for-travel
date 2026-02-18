"""Tests for routing data models."""

import pytest
from src.routing.models import Leg, Journey


class TestLeg:
    """Tests for Leg dataclass."""

    def test_leg_creation(self):
        """Test creating a Leg."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            route_name="Route 1",
            num_stops=2
        )

        assert leg.from_stop_id == "1001"
        assert leg.to_stop_id == "1002"
        assert leg.trip_id == "T1"
        assert leg.num_stops == 2

    def test_leg_duration_seconds(self):
        """Test duration calculation in seconds."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        assert leg.duration_seconds == 600  # 10 minutes

    def test_leg_duration_minutes(self):
        """Test duration calculation in minutes."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:45:00",
            trip_id="T1",
            route_id="R1"
        )

        assert leg.duration_minutes == 45

    def test_leg_format_duration_minutes_only(self):
        """Test duration formatting for trips under 1 hour."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:45:00",
            trip_id="T1",
            route_id="R1"
        )

        assert leg.format_duration() == "45m"

    def test_leg_format_duration_hours_and_minutes(self):
        """Test duration formatting for trips over 1 hour."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="09:30:00",
            trip_id="T1",
            route_id="R1"
        )

        assert leg.format_duration() == "1h 30m"

    def test_leg_format_duration_hours_only(self):
        """Test duration formatting for exact hours."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="10:00:00",
            trip_id="T1",
            route_id="R1"
        )

        assert leg.format_duration() == "2h"

    def test_leg_num_stops_conversion(self):
        """Test that num_stops is converted to int."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1",
            num_stops="5"  # String
        )

        assert isinstance(leg.num_stops, int)
        assert leg.num_stops == 5


class TestJourney:
    """Tests for Journey dataclass."""

    def test_journey_creation_single_leg(self):
        """Test creating a journey with single leg."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
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

        assert journey.origin_stop_id == "1001"
        assert journey.destination_stop_id == "1002"
        assert len(journey.legs) == 1
        assert journey.num_transfers == 0

    def test_journey_creation_multiple_legs(self):
        """Test creating a journey with multiple legs (transfers)."""
        leg1 = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        leg2 = Leg(
            from_stop_id="1002",
            from_stop_name="Stop B",
            to_stop_id="1003",
            to_stop_name="Stop C",
            departure_time="08:15:00",
            arrival_time="08:25:00",
            trip_id="T2",
            route_id="R2"
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

        assert len(journey.legs) == 2
        assert journey.num_transfers == 1

    def test_journey_empty_legs_raises_error(self):
        """Test that journey with no legs raises error."""
        with pytest.raises(ValueError, match="must have at least one leg"):
            Journey(
                origin_stop_id="1001",
                origin_stop_name="Stop A",
                destination_stop_id="1002",
                destination_stop_name="Stop B",
                departure_time="08:00:00",
                arrival_time="08:10:00",
                legs=[]
            )

    def test_journey_discontinuous_legs_raises_error(self):
        """Test that discontinuous legs raise error."""
        leg1 = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        # Leg 2 starts at wrong stop (should start at 1002)
        leg2 = Leg(
            from_stop_id="1003",
            from_stop_name="Stop C",
            to_stop_id="1004",
            to_stop_name="Stop D",
            departure_time="08:15:00",
            arrival_time="08:25:00",
            trip_id="T2",
            route_id="R2"
        )

        with pytest.raises(ValueError, match="Discontinuous journey"):
            Journey(
                origin_stop_id="1001",
                origin_stop_name="Stop A",
                destination_stop_id="1004",
                destination_stop_name="Stop D",
                departure_time="08:00:00",
                arrival_time="08:25:00",
                legs=[leg1, leg2]
            )

    def test_journey_duration_seconds(self):
        """Test journey duration calculation."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1002",
            destination_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:30:00",
            legs=[leg]
        )

        assert journey.duration_seconds == 1800  # 30 minutes

    def test_journey_duration_minutes(self):
        """Test journey duration in minutes."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1002",
            destination_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="09:15:00",
            legs=[leg]
        )

        assert journey.duration_minutes == 75

    def test_journey_format_duration(self):
        """Test journey duration formatting."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        journey = Journey(
            origin_stop_id="1001",
            origin_stop_name="Stop A",
            destination_stop_id="1002",
            destination_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="09:45:00",
            legs=[leg]
        )

        assert journey.format_duration() == "1h 45m"

    def test_journey_get_transfer_wait_times_no_transfers(self):
        """Test getting transfer wait times with no transfers."""
        leg = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
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

        assert journey.get_transfer_wait_times() == []

    def test_journey_get_transfer_wait_times_with_transfer(self):
        """Test getting transfer wait times with one transfer."""
        leg1 = Leg(
            from_stop_id="1001",
            from_stop_name="Stop A",
            to_stop_id="1002",
            to_stop_name="Stop B",
            departure_time="08:00:00",
            arrival_time="08:10:00",
            trip_id="T1",
            route_id="R1"
        )

        leg2 = Leg(
            from_stop_id="1002",
            from_stop_name="Stop B",
            to_stop_id="1003",
            to_stop_name="Stop C",
            departure_time="08:15:00",  # 5 minute wait
            arrival_time="08:25:00",
            trip_id="T2",
            route_id="R2"
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

        wait_times = journey.get_transfer_wait_times()
        assert len(wait_times) == 1
        assert wait_times[0] == 300  # 5 minutes in seconds

    def test_journey_format_summary(self):
        """Test journey summary formatting."""
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

        assert "Test Station A → Test Station B" in summary
        assert "08:00:00" in summary
        assert "08:10:00" in summary
        assert "Transfers: 0" in summary
        assert "Test Route" in summary
