"""
Unit tests for Stop Index.
"""

import pytest
from src.data.gtfs_parser import GTFSParser
from src.data.stop_index import StopIndex
from src.data.models import Stop


class TestStopIndexInit:
    """Test StopIndex initialization."""

    def test_init_with_parser(self, gtfs_dir):
        """Test initialization with GTFSParser."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()

        index = StopIndex(parser)

        assert index.parser is parser
        assert len(index.stops) == 3


class TestFindStopExact:
    """Test exact stop name matching."""

    @pytest.fixture
    def stop_index(self, gtfs_dir):
        """Create a StopIndex with test data."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()
        return StopIndex(parser)

    def test_find_exact_match_case_insensitive(self, stop_index):
        """Test exact match is case-insensitive."""
        stop = stop_index.find_stop_exact("Test Station A")

        assert stop is not None
        assert stop.stop_name == "Test Station A"
        assert stop.stop_id == "1001"

    def test_find_exact_match_lowercase(self, stop_index):
        """Test exact match with lowercase input."""
        stop = stop_index.find_stop_exact("test station a")

        assert stop is not None
        assert stop.stop_name == "Test Station A"

    def test_find_exact_match_uppercase(self, stop_index):
        """Test exact match with uppercase input."""
        stop = stop_index.find_stop_exact("TEST STATION A")

        assert stop is not None
        assert stop.stop_name == "Test Station A"

    def test_find_exact_no_match(self, stop_index):
        """Test returns None when no exact match."""
        stop = stop_index.find_stop_exact("Nonexistent Station")

        assert stop is None


class TestFindStopFuzzy:
    """Test fuzzy stop name matching."""

    @pytest.fixture
    def stop_index(self, gtfs_dir):
        """Create a StopIndex with test data."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()
        return StopIndex(parser)

    def test_find_fuzzy_typo(self, stop_index):
        """Test fuzzy match with typo."""
        matches = stop_index.find_stop_fuzzy("Test Station A", limit=3)

        assert len(matches) > 0
        stop, score = matches[0]
        assert stop.stop_name == "Test Station A"
        assert score > 90  # High score for exact match

    def test_find_fuzzy_partial_match(self, stop_index):
        """Test fuzzy match with partial name."""
        matches = stop_index.find_stop_fuzzy("Station A", limit=3)

        assert len(matches) > 0
        # Should find Test Station A
        stop_names = [stop.stop_name for stop, score in matches]
        assert "Test Station A" in stop_names

    def test_find_fuzzy_limit(self, stop_index):
        """Test fuzzy match respects limit parameter."""
        matches = stop_index.find_stop_fuzzy("Station", limit=2)

        assert len(matches) <= 2

    def test_find_fuzzy_min_score(self, stop_index):
        """Test fuzzy match respects min_score parameter."""
        matches = stop_index.find_stop_fuzzy("XYZ Random", limit=5, min_score=90)

        # Should have no high-quality matches for random string
        assert len(matches) == 0

    def test_find_fuzzy_returns_tuples(self, stop_index):
        """Test fuzzy match returns (Stop, score) tuples."""
        matches = stop_index.find_stop_fuzzy("Test Station", limit=2)

        assert len(matches) > 0
        for item in matches:
            assert isinstance(item, tuple)
            assert len(item) == 2
            stop, score = item
            assert isinstance(stop, Stop)
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100

    def test_find_fuzzy_sorted_by_score(self, stop_index):
        """Test fuzzy matches are sorted by score descending."""
        matches = stop_index.find_stop_fuzzy("Test", limit=3)

        if len(matches) > 1:
            scores = [score for stop, score in matches]
            assert scores == sorted(scores, reverse=True)

    def test_find_fuzzy_empty_index(self):
        """Test fuzzy match with empty index."""
        parser = GTFSParser.__new__(GTFSParser)
        parser.stops = {}
        index = StopIndex(parser)

        matches = index.find_stop_fuzzy("Any Station")

        assert matches == []


class TestFindStop:
    """Test combined find_stop method."""

    @pytest.fixture
    def stop_index(self, gtfs_dir):
        """Create a StopIndex with test data."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()
        return StopIndex(parser)

    def test_find_exact_match(self, stop_index):
        """Test finds exact match first."""
        stop = stop_index.find_stop("Test Station A")

        assert stop is not None
        assert stop.stop_name == "Test Station A"
        assert stop.stop_id == "1001"

    def test_find_fuzzy_fallback(self, stop_index):
        """Test falls back to fuzzy matching."""
        stop = stop_index.find_stop("Station A")

        assert stop is not None
        # Should find Test Station A via fuzzy matching

    def test_find_no_fuzzy(self, stop_index):
        """Test with fuzzy=False only does exact matching."""
        stop = stop_index.find_stop("Station A", fuzzy=False)

        assert stop is None  # No exact match

    def test_find_no_match(self, stop_index):
        """Test returns None when no match found."""
        stop = stop_index.find_stop("Completely Different Station XYZ")

        assert stop is None


class TestFindStopsByIds:
    """Test finding multiple stops by IDs."""

    @pytest.fixture
    def stop_index(self, gtfs_dir):
        """Create a StopIndex with test data."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()
        return StopIndex(parser)

    def test_find_multiple_stops(self, stop_index):
        """Test finding multiple stops by IDs."""
        stops = stop_index.find_stops_by_ids(["1001", "1002"])

        assert len(stops) == 2
        assert stops[0].stop_id == "1001"
        assert stops[1].stop_id == "1002"

    def test_find_with_invalid_ids(self, stop_index):
        """Test finding stops with some invalid IDs."""
        stops = stop_index.find_stops_by_ids(["1001", "9999", "1002"])

        # Should only return valid stops
        assert len(stops) == 2
        assert all(stop.stop_id in ["1001", "1002"] for stop in stops)

    def test_find_empty_list(self, stop_index):
        """Test finding stops with empty list."""
        stops = stop_index.find_stops_by_ids([])

        assert stops == []


class TestGetAllStops:
    """Test getting all stops."""

    @pytest.fixture
    def stop_index(self, gtfs_dir):
        """Create a StopIndex with test data."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()
        return StopIndex(parser)

    def test_get_all_stops(self, stop_index):
        """Test getting all stops."""
        all_stops = stop_index.get_all_stops()

        assert len(all_stops) == 3
        assert all(isinstance(stop, Stop) for stop in all_stops)


class TestGetStopCount:
    """Test getting stop count."""

    @pytest.fixture
    def stop_index(self, gtfs_dir):
        """Create a StopIndex with test data."""
        parser = GTFSParser(str(gtfs_dir))
        parser.load_stops()
        return StopIndex(parser)

    def test_get_stop_count(self, stop_index):
        """Test getting stop count."""
        count = stop_index.get_stop_count()

        assert count == 3

    def test_get_stop_count_empty(self):
        """Test getting count from empty index."""
        parser = GTFSParser.__new__(GTFSParser)
        parser.stops = {}
        index = StopIndex(parser)

        count = index.get_stop_count()

        assert count == 0
