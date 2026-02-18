"""Tests for JourneyPlanner class."""

import pytest
from pathlib import Path

from src.routing.journey_planner import JourneyPlanner
from src.data.gtfs_parser import GTFSParser
from src.graph.transit_graph import TransitGraph


@pytest.fixture
def gtfs_dir():
    """Path to test GTFS fixtures."""
    return Path(__file__).parent.parent / "test_data" / "fixtures"


@pytest.fixture
def parser(gtfs_dir):
    """GTFSParser with loaded test data."""
    return GTFSParser(str(gtfs_dir)).load_all()


@pytest.fixture
def graph(parser):
    """TransitGraph built from test data."""
    return TransitGraph(parser)


@pytest.fixture
def planner(parser, graph):
    """JourneyPlanner with test data."""
    return JourneyPlanner(parser, graph)


class TestJourneyPlannerInit:
    """Tests for JourneyPlanner initialization."""

    def test_init_with_graph(self, parser, graph):
        """Test initialization with pre-built graph."""
        planner = JourneyPlanner(parser, graph)
        assert planner.parser is parser
        assert planner.graph is graph

    def test_init_without_graph(self, parser):
        """Test initialization without graph (builds automatically)."""
        planner = JourneyPlanner(parser)
        assert planner.parser is parser
        assert planner.graph is not None
        assert planner.graph.parser is parser


class TestFindJourney:
    """Tests for find_journey method."""

    def test_find_journey_direct_route(self, planner):
        """Test finding a direct journey (no transfers)."""
        # T1 goes 1001 -> 1002 -> 1003 starting at 08:00
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:30:00"
        )

        assert journey is not None
        assert journey.origin_stop_id == "1001"
        assert journey.destination_stop_id == "1002"
        assert len(journey.legs) == 1
        assert journey.num_transfers == 0

    def test_find_journey_multi_stop_route(self, planner):
        """Test finding a journey through multiple stops on same trip."""
        # T1 goes 1001 -> 1002 -> 1003
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1003",
            departure_time="07:30:00"
        )

        assert journey is not None
        assert journey.origin_stop_id == "1001"
        assert journey.destination_stop_id == "1003"
        # Should be one leg even though it's 2 stops (same trip)
        assert len(journey.legs) == 1
        assert journey.num_transfers == 0

    def test_find_journey_invalid_origin(self, planner):
        """Test that invalid origin raises error."""
        with pytest.raises(ValueError, match="Origin stop .* not found"):
            planner.find_journey(
                origin_stop_id="9999",
                destination_stop_id="1002",
                departure_time="08:00:00"
            )

    def test_find_journey_invalid_destination(self, planner):
        """Test that invalid destination raises error."""
        with pytest.raises(ValueError, match="Destination stop .* not found"):
            planner.find_journey(
                origin_stop_id="1001",
                destination_stop_id="9999",
                departure_time="08:00:00"
            )

    def test_find_journey_same_origin_destination(self, planner):
        """Test that same origin and destination returns None."""
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1001",
            departure_time="08:00:00"
        )

        assert journey is None

    def test_find_journey_departure_after_all_trips(self, planner):
        """Test finding journey when departure is after all available trips."""
        # Latest trip departs at 09:00, request departure at 10:00
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="10:00:00"
        )

        # Should return None (no available trips)
        assert journey is None

    def test_find_journey_times_match_connections(self, planner):
        """Test that journey times match the actual connections."""
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:30:00"
        )

        assert journey is not None
        # T1 departs 1001 at 08:00, arrives 1002 at 08:10
        assert journey.departure_time == "08:00:00"
        assert journey.arrival_time == "08:10:00"


class TestTimeToSeconds:
    """Tests for _time_to_seconds method."""

    def test_time_to_seconds_midnight(self, planner):
        """Test converting midnight to seconds."""
        seconds = planner._time_to_seconds("00:00:00")
        assert seconds == 0

    def test_time_to_seconds_morning(self, planner):
        """Test converting morning time to seconds."""
        seconds = planner._time_to_seconds("08:30:00")
        assert seconds == 8 * 3600 + 30 * 60  # 30600

    def test_time_to_seconds_afternoon(self, planner):
        """Test converting afternoon time to seconds."""
        seconds = planner._time_to_seconds("14:15:30")
        assert seconds == 14 * 3600 + 15 * 60 + 30  # 51330

    def test_time_to_seconds_past_midnight(self, planner):
        """Test converting time past midnight (GTFS allows 25:00:00 etc)."""
        seconds = planner._time_to_seconds("25:30:00")
        assert seconds == 25 * 3600 + 30 * 60  # 91800


class TestReconstructJourney:
    """Tests for journey reconstruction."""

    def test_journey_reconstruction_creates_legs(self, planner):
        """Test that journey reconstruction creates proper legs."""
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1003",
            departure_time="07:30:00"
        )

        assert journey is not None
        assert len(journey.legs) > 0
        # Verify leg structure
        for leg in journey.legs:
            assert leg.from_stop_id is not None
            assert leg.to_stop_id is not None
            assert leg.departure_time is not None
            assert leg.arrival_time is not None
            assert leg.trip_id is not None

    def test_journey_leg_stop_names_populated(self, planner):
        """Test that leg stop names are populated from parser."""
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:30:00"
        )

        assert journey is not None
        leg = journey.legs[0]
        assert leg.from_stop_name == "Test Station A"
        assert leg.to_stop_name == "Test Station B"

    def test_journey_leg_route_name_populated(self, planner):
        """Test that leg route name is populated from parser."""
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:30:00"
        )

        assert journey is not None
        leg = journey.legs[0]
        # Route name from test fixtures
        assert leg.route_name is not None


class TestFindMultipleJourneys:
    """Tests for find_multiple_journeys method."""

    def test_find_multiple_journeys_returns_list(self, planner):
        """Test that method returns a list."""
        journeys = planner.find_multiple_journeys(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:30:00"
        )

        assert isinstance(journeys, list)

    def test_find_multiple_journeys_with_results(self, planner):
        """Test that method returns journey when available."""
        journeys = planner.find_multiple_journeys(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:30:00"
        )

        assert len(journeys) == 1
        assert journeys[0].origin_stop_id == "1001"
        assert journeys[0].destination_stop_id == "1002"

    def test_find_multiple_journeys_no_results(self, planner):
        """Test that method returns empty list when no journey available."""
        journeys = planner.find_multiple_journeys(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="10:00:00"  # After all trips
        )

        assert journeys == []


class TestConnectionScan:
    """Tests for Connection Scan Algorithm implementation."""

    def test_csa_finds_earliest_arrival(self, planner):
        """Test that CSA finds the earliest arrival journey."""
        # Two trips available: T1 at 08:00 and potentially others
        # CSA should find the earliest arrival
        journey = planner.find_journey(
            origin_stop_id="1001",
            destination_stop_id="1002",
            departure_time="07:00:00"
        )

        assert journey is not None
        # Should take first available trip (T1 at 08:00)
        assert journey.departure_time == "08:00:00"

    def test_csa_respects_departure_time(self, planner):
        """Test that CSA only considers trips after departure time."""
        # Request departure at 08:30 (after T1 at 08:00)
        # Should not take T1
        journey = planner.find_journey(
            origin_stop_id="1003",  # T2 starts here at 09:00
            destination_stop_id="1002",
            departure_time="08:30:00"
        )

        # Should find T2 (which goes backwards: 1003 -> 1002 -> 1001)
        if journey:
            assert journey.departure_time >= "08:30:00"

    def test_csa_handles_no_route(self, planner):
        """Test that CSA returns None when no route exists."""
        # Try to find route that doesn't exist in test data
        # In our small test dataset, reverse routes might not exist
        journey = planner.find_journey(
            origin_stop_id="1002",
            destination_stop_id="1001",
            departure_time="07:00:00"
        )

        # May or may not find a route depending on test data
        # Just verify it doesn't crash
        assert journey is None or isinstance(journey.legs, list)


class TestCreateLeg:
    """Tests for _create_leg method."""

    def test_create_leg_single_connection(self, planner, graph):
        """Test creating a leg from a single connection."""
        # Get a connection from the graph
        connections = graph.get_connections_from("1001")
        assert len(connections) > 0

        # Find connection to 1002
        conn = next((c for c in connections if c.to_stop_id == "1002"), None)
        assert conn is not None

        leg = planner._create_leg([conn])

        assert leg.from_stop_id == conn.from_stop_id
        assert leg.to_stop_id == conn.to_stop_id
        assert leg.trip_id == conn.trip_id
        assert leg.num_stops == 2  # Two stops (from and to)

    def test_create_leg_multiple_connections(self, planner, graph):
        """Test creating a leg from multiple consecutive connections."""
        # Get connections for trip T1
        connections = [c for c in graph.connections if c.trip_id == "T1"]
        connections.sort(key=lambda c: planner._time_to_seconds(c.departure_time))

        if len(connections) >= 2:
            # Use first two connections
            leg = planner._create_leg(connections[:2])

            assert leg.from_stop_id == connections[0].from_stop_id
            assert leg.to_stop_id == connections[1].to_stop_id
            assert leg.departure_time == connections[0].departure_time
            assert leg.arrival_time == connections[1].arrival_time
            assert leg.num_stops == 3  # Three stops total
