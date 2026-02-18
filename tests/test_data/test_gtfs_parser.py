"""
Unit tests for GTFS Parser.
"""

import pytest
from pathlib import Path
from src.data.gtfs_parser import GTFSParser
from src.data.models import Stop, Route, Trip, StopTime


class TestGTFSParserInit:
    """Test GTFSParser initialization."""

    def test_init_with_valid_directory(self, gtfs_dir):
        """Test initialization with valid GTFS directory."""
        parser = GTFSParser(str(gtfs_dir))

        assert parser.gtfs_dir == gtfs_dir
        assert isinstance(parser.stops, dict)
        assert isinstance(parser.routes, dict)
        assert isinstance(parser.trips, dict)
        assert isinstance(parser.stop_times, dict)

    def test_init_with_invalid_directory(self):
        """Test initialization with non-existent directory."""
        with pytest.raises(FileNotFoundError, match="GTFS directory not found"):
            GTFSParser("/nonexistent/directory")


class TestLoadStops:
    """Test loading stops.txt."""

    def test_load_stops_success(self, gtfs_dir):
        """Test successful loading of stops."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()

        assert len(parser.stops) == 3
        assert "1001" in parser.stops
        assert "1002" in parser.stops
        assert "1003" in parser.stops

    def test_load_stops_data_correctness(self, gtfs_dir):
        """Test loaded stop data is correct."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()

        stop = parser.stops["1001"]
        assert stop.stop_id == "1001"
        assert stop.stop_name == "Test Station A"
        assert stop.stop_lat == -37.8136
        assert stop.stop_lon == 144.9631
        assert isinstance(stop, Stop)

    def test_load_stops_missing_file(self, tmp_path):
        """Test error when stops.txt is missing."""
        parser = GTFSParser(str(tmp_path))

        with pytest.raises(FileNotFoundError, match="Required file not found"):
            parser.load_stops()


class TestLoadRoutes:
    """Test loading routes.txt."""

    def test_load_routes_success(self, gtfs_dir):
        """Test successful loading of routes."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_routes()

        assert len(parser.routes) == 2
        assert "R1" in parser.routes
        assert "R2" in parser.routes

    def test_load_routes_data_correctness(self, gtfs_dir):
        """Test loaded route data is correct."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_routes()

        route = parser.routes["R1"]
        assert route.route_id == "R1"
        assert route.route_short_name == "1"
        assert route.route_long_name == "Test Route 1"
        assert route.route_type == "1"
        assert isinstance(route, Route)


class TestLoadTrips:
    """Test loading trips.txt."""

    def test_load_trips_success(self, gtfs_dir):
        """Test successful loading of trips."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_trips()

        assert len(parser.trips) == 2
        assert "T1" in parser.trips
        assert "T2" in parser.trips

    def test_load_trips_data_correctness(self, gtfs_dir):
        """Test loaded trip data is correct."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_trips()

        trip = parser.trips["T1"]
        assert trip.trip_id == "T1"
        assert trip.route_id == "R1"
        assert trip.service_id == "SVC1"
        assert isinstance(trip, Trip)


class TestLoadStopTimes:
    """Test loading stop_times.txt."""

    def test_load_stop_times_success(self, gtfs_dir):
        """Test successful loading of stop times."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stop_times()

        assert len(parser.stop_times) == 2
        assert "T1" in parser.stop_times
        assert "T2" in parser.stop_times

    def test_load_stop_times_sorted_by_sequence(self, gtfs_dir):
        """Test that stop times are sorted by sequence."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stop_times()

        stop_times = parser.stop_times["T1"]
        assert len(stop_times) == 3

        # Check sorted by sequence
        sequences = [st.stop_sequence for st in stop_times]
        assert sequences == [1, 2, 3]

    def test_load_stop_times_data_correctness(self, gtfs_dir):
        """Test loaded stop time data is correct."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stop_times()

        stop_times = parser.stop_times["T1"]
        first_st = stop_times[0]

        assert first_st.trip_id == "T1"
        assert first_st.stop_id == "1001"
        assert first_st.stop_sequence == 1
        assert first_st.arrival_time == "08:00:00"
        assert first_st.departure_time == "08:00:00"
        assert isinstance(first_st, StopTime)


class TestLoadAgencies:
    """Test loading agency.txt."""

    def test_load_agencies_success(self, gtfs_dir):
        """Test successful loading of agencies."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_agencies()

        assert len(parser.agencies) == 1
        assert "AGENCY1" in parser.agencies

    def test_load_agencies_missing_file(self, tmp_path):
        """Test graceful handling of missing agency.txt."""
        parser = GTFSParser(str(tmp_path))
        parser.load_agencies()  # Should not raise

        assert len(parser.agencies) == 0


class TestLoadCalendar:
    """Test loading calendar.txt."""

    def test_load_calendar_success(self, gtfs_dir):
        """Test successful loading of calendar."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_calendar()

        assert len(parser.calendars) == 1
        assert "SVC1" in parser.calendars

    def test_load_calendar_missing_file(self, tmp_path):
        """Test graceful handling of missing calendar.txt."""
        parser = GTFSParser(str(tmp_path))
        parser.load_calendar()  # Should not raise

        assert len(parser.calendars) == 0


class TestLoadAll:
    """Test loading all GTFS files."""

    def test_load_all_success(self, gtfs_dir):
        """Test loading all GTFS files at once."""
        parser = GTFSParser(str(gtfs_dir))
        result = parser.load_all()

        # Check all data loaded
        assert len(parser.stops) == 3
        assert len(parser.routes) == 2
        assert len(parser.trips) == 2
        assert len(parser.stop_times) == 2
        assert len(parser.agencies) == 1
        assert len(parser.calendars) == 1

        # Check method chaining
        assert result is parser


class TestGetMethods:
    """Test getter methods."""

    @pytest.fixture
    def loaded_parser(self, gtfs_dir):
        """Create a parser with data loaded."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_all()
        return parser

    def test_get_stop_existing(self, loaded_parser):
        """Test getting an existing stop."""
        stop = loaded_parser.get_stop("1001")

        assert stop is not None
        assert stop.stop_id == "1001"
        assert stop.stop_name == "Test Station A"

    def test_get_stop_nonexistent(self, loaded_parser):
        """Test getting a non-existent stop."""
        stop = loaded_parser.get_stop("9999")

        assert stop is None

    def test_get_route_existing(self, loaded_parser):
        """Test getting an existing route."""
        route = loaded_parser.get_route("R1")

        assert route is not None
        assert route.route_id == "R1"

    def test_get_route_nonexistent(self, loaded_parser):
        """Test getting a non-existent route."""
        route = loaded_parser.get_route("R999")

        assert route is None

    def test_get_trip_existing(self, loaded_parser):
        """Test getting an existing trip."""
        trip = loaded_parser.get_trip("T1")

        assert trip is not None
        assert trip.trip_id == "T1"

    def test_get_trip_nonexistent(self, loaded_parser):
        """Test getting a non-existent trip."""
        trip = loaded_parser.get_trip("T999")

        assert trip is None

    def test_get_trip_stop_times_existing(self, loaded_parser):
        """Test getting stop times for existing trip."""
        stop_times = loaded_parser.get_trip_stop_times("T1")

        assert len(stop_times) == 3
        assert all(isinstance(st, StopTime) for st in stop_times)
        assert stop_times[0].stop_sequence == 1

    def test_get_trip_stop_times_nonexistent(self, loaded_parser):
        """Test getting stop times for non-existent trip."""
        stop_times = loaded_parser.get_trip_stop_times("T999")

        assert stop_times == []
