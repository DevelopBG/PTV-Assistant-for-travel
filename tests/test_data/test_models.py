"""
Unit tests for GTFS data models.
"""

import pytest
from src.data.models import (
    Stop, Route, Trip, StopTime, Agency, Calendar, CalendarDate, Transfer
)


class TestStop:
    """Test Stop dataclass."""

    def test_stop_creation(self):
        """Test creating a Stop instance."""
        stop = Stop(
            stop_id="123",
            stop_name="Test Station",
            stop_lat="-37.8136",
            stop_lon="144.9631"
        )

        assert stop.stop_id == "123"
        assert stop.stop_name == "Test Station"
        assert stop.stop_lat == -37.8136
        assert stop.stop_lon == 144.9631

    def test_stop_with_optional_fields(self):
        """Test Stop with all optional fields."""
        stop = Stop(
            stop_id="123",
            stop_name="Test Station",
            stop_lat="-37.8136",
            stop_lon="144.9631",
            location_type="0",
            parent_station="parent_123",
            wheelchair_boarding="1",
            stop_url="http://example.com",
            level_id="L1",
            platform_code="1"
        )

        assert stop.location_type == "0"
        assert stop.parent_station == "parent_123"
        assert stop.wheelchair_boarding == "1"
        assert stop.stop_url == "http://example.com"
        assert stop.level_id == "L1"
        assert stop.platform_code == "1"

    def test_stop_lat_lon_conversion(self):
        """Test that lat/lon are converted to float."""
        stop = Stop(
            stop_id="123",
            stop_name="Test",
            stop_lat="-37.8136",
            stop_lon="144.9631"
        )

        assert isinstance(stop.stop_lat, float)
        assert isinstance(stop.stop_lon, float)


class TestRoute:
    """Test Route dataclass."""

    def test_route_creation(self):
        """Test creating a Route instance."""
        route = Route(
            route_id="R1",
            route_short_name="1",
            route_long_name="Test Route",
            route_type="1"
        )

        assert route.route_id == "R1"
        assert route.route_short_name == "1"
        assert route.route_long_name == "Test Route"
        assert route.route_type == "1"

    def test_route_with_optional_fields(self):
        """Test Route with optional fields."""
        route = Route(
            route_id="R1",
            route_short_name="1",
            route_long_name="Test Route",
            route_type="1",
            agency_id="AGENCY1",
            route_desc="Description",
            route_url="http://example.com",
            route_color="FF0000",
            route_text_color="FFFFFF"
        )

        assert route.agency_id == "AGENCY1"
        assert route.route_desc == "Description"
        assert route.route_url == "http://example.com"
        assert route.route_color == "FF0000"
        assert route.route_text_color == "FFFFFF"


class TestTrip:
    """Test Trip dataclass."""

    def test_trip_creation(self):
        """Test creating a Trip instance."""
        trip = Trip(
            trip_id="T1",
            route_id="R1",
            service_id="SVC1"
        )

        assert trip.trip_id == "T1"
        assert trip.route_id == "R1"
        assert trip.service_id == "SVC1"

    def test_trip_with_optional_fields(self):
        """Test Trip with optional fields."""
        trip = Trip(
            trip_id="T1",
            route_id="R1",
            service_id="SVC1",
            trip_headsign="Destination",
            trip_short_name="Short",
            direction_id="0",
            block_id="B1",
            shape_id="S1",
            wheelchair_accessible="1",
            bikes_allowed="1"
        )

        assert trip.trip_headsign == "Destination"
        assert trip.trip_short_name == "Short"
        assert trip.direction_id == "0"
        assert trip.block_id == "B1"
        assert trip.shape_id == "S1"
        assert trip.wheelchair_accessible == "1"
        assert trip.bikes_allowed == "1"


class TestStopTime:
    """Test StopTime dataclass."""

    def test_stop_time_creation(self):
        """Test creating a StopTime instance."""
        st = StopTime(
            trip_id="T1",
            stop_id="S1",
            stop_sequence="1",
            arrival_time="08:00:00",
            departure_time="08:00:00"
        )

        assert st.trip_id == "T1"
        assert st.stop_id == "S1"
        assert st.stop_sequence == 1
        assert st.arrival_time == "08:00:00"
        assert st.departure_time == "08:00:00"

    def test_stop_time_sequence_conversion(self):
        """Test that stop_sequence is converted to int."""
        st = StopTime(
            trip_id="T1",
            stop_id="S1",
            stop_sequence="5",
            arrival_time="08:00:00",
            departure_time="08:00:00"
        )

        assert isinstance(st.stop_sequence, int)
        assert st.stop_sequence == 5

    def test_stop_time_with_optional_fields(self):
        """Test StopTime with optional fields."""
        st = StopTime(
            trip_id="T1",
            stop_id="S1",
            stop_sequence="1",
            arrival_time="08:00:00",
            departure_time="08:00:00",
            stop_headsign="Destination",
            pickup_type="0",
            drop_off_type="0",
            shape_dist_traveled="100",
            timepoint="1"
        )

        assert st.stop_headsign == "Destination"
        assert st.pickup_type == "0"
        assert st.drop_off_type == "0"
        assert st.shape_dist_traveled == "100"
        assert st.timepoint == "1"


class TestAgency:
    """Test Agency dataclass."""

    def test_agency_creation(self):
        """Test creating an Agency instance."""
        agency = Agency(
            agency_id="A1",
            agency_name="Test Agency",
            agency_url="http://test.com",
            agency_timezone="Australia/Melbourne"
        )

        assert agency.agency_id == "A1"
        assert agency.agency_name == "Test Agency"
        assert agency.agency_url == "http://test.com"
        assert agency.agency_timezone == "Australia/Melbourne"


class TestCalendar:
    """Test Calendar dataclass."""

    def test_calendar_creation(self):
        """Test creating a Calendar instance."""
        calendar = Calendar(
            service_id="SVC1",
            monday="1",
            tuesday="1",
            wednesday="1",
            thursday="1",
            friday="1",
            saturday="0",
            sunday="0",
            start_date="20260101",
            end_date="20261231"
        )

        assert calendar.service_id == "SVC1"
        assert calendar.monday == "1"
        assert calendar.saturday == "0"
        assert calendar.start_date == "20260101"


class TestCalendarDate:
    """Test CalendarDate dataclass."""

    def test_calendar_date_creation(self):
        """Test creating a CalendarDate instance."""
        cal_date = CalendarDate(
            service_id="SVC1",
            date="20260101",
            exception_type="1"
        )

        assert cal_date.service_id == "SVC1"
        assert cal_date.date == "20260101"
        assert cal_date.exception_type == "1"


class TestTransfer:
    """Test Transfer dataclass."""

    def test_transfer_creation(self):
        """Test creating a Transfer instance."""
        transfer = Transfer(
            from_stop_id="S1",
            to_stop_id="S2"
        )

        assert transfer.from_stop_id == "S1"
        assert transfer.to_stop_id == "S2"
        assert transfer.transfer_type == "0"

    def test_transfer_with_time(self):
        """Test Transfer with min_transfer_time."""
        transfer = Transfer(
            from_stop_id="S1",
            to_stop_id="S2",
            transfer_type="2",
            min_transfer_time="120"
        )

        assert transfer.transfer_type == "2"
        assert transfer.min_transfer_time == "120"
