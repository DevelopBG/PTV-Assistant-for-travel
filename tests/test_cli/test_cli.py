"""
Tests for CLI interface.
"""

import pytest
from io import StringIO
import sys
import os

from src.cli.main import main, create_parser, TransitCLI


# Path to test fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data", "fixtures")


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_create_parser_returns_parser(self):
        """Test create_parser returns ArgumentParser."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "ptv"

    def test_parser_has_search_command(self):
        """Test parser has search subcommand."""
        parser = create_parser()
        args = parser.parse_args(["search", "Tarneit"])
        assert args.command == "search"
        assert args.query == "Tarneit"

    def test_parser_has_plan_command(self):
        """Test parser has plan subcommand."""
        parser = create_parser()
        args = parser.parse_args(["plan", "Tarneit", "Waurn Ponds", "08:00:00"])
        assert args.command == "plan"
        assert args.origin == "Tarneit"
        assert args.destination == "Waurn Ponds"
        assert args.time == "08:00:00"

    def test_search_default_limit(self):
        """Test search command default limit."""
        parser = create_parser()
        args = parser.parse_args(["search", "Tarneit"])
        assert args.limit == 5

    def test_search_custom_limit(self):
        """Test search command custom limit."""
        parser = create_parser()
        args = parser.parse_args(["search", "Tarneit", "-l", "10"])
        assert args.limit == 10

    def test_search_exact_flag(self):
        """Test search command exact flag."""
        parser = create_parser()
        args = parser.parse_args(["search", "Tarneit", "--exact"])
        assert args.exact is True

    def test_plan_realtime_flag(self):
        """Test plan command realtime flag."""
        parser = create_parser()
        args = parser.parse_args(["plan", "A", "B", "08:00:00", "-r"])
        assert args.realtime is True

    def test_plan_max_transfers(self):
        """Test plan command max transfers."""
        parser = create_parser()
        args = parser.parse_args(["plan", "A", "B", "08:00:00", "-t", "2"])
        assert args.max_transfers == 2

    def test_verbose_flag(self):
        """Test verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["-v", "search", "Tarneit"])
        assert args.verbose is True

    def test_data_dir_option(self):
        """Test data directory option."""
        parser = create_parser()
        args = parser.parse_args(["-d", "/custom/path", "search", "Tarneit"])
        assert args.data_dir == "/custom/path"


class TestTransitCLI:
    """Tests for TransitCLI class."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance with test fixtures."""
        cli = TransitCLI(gtfs_dir=FIXTURES_DIR)
        cli.load()
        return cli

    def test_cli_loads_data(self, cli):
        """Test CLI loads GTFS data."""
        assert cli.parser is not None
        assert cli.stop_index is not None
        assert cli.graph is not None
        assert cli.planner is not None

    def test_cli_load_returns_self(self):
        """Test load returns self for chaining."""
        cli = TransitCLI(gtfs_dir=FIXTURES_DIR)
        result = cli.load()
        assert result is cli

    def test_resolve_stop_by_id(self, cli):
        """Test resolving stop by ID."""
        stop = cli._resolve_stop("1001")
        assert stop is not None
        assert stop.stop_id == "1001"

    def test_resolve_stop_by_name(self, cli):
        """Test resolving stop by name."""
        stop = cli._resolve_stop("Test Station A")
        assert stop is not None

    def test_resolve_stop_not_found(self, cli):
        """Test resolving non-existent stop."""
        stop = cli._resolve_stop("NonexistentStopXYZ123")
        assert stop is None


class TestMainFunction:
    """Tests for main CLI entry point."""

    def test_main_no_command_shows_help(self, capsys):
        """Test main with no command shows help."""
        result = main([])
        assert result == 0

    def test_main_invalid_data_dir(self):
        """Test main with invalid data directory."""
        result = main(["-d", "/nonexistent/path", "search", "test"])
        assert result == 1

    def test_main_search_with_fixtures(self, capsys):
        """Test main search command with fixtures."""
        result = main(["-d", FIXTURES_DIR, "search", "Test"])
        captured = capsys.readouterr()
        assert result == 0
        assert "Searching for" in captured.out

    def test_main_plan_with_fixtures(self, capsys):
        """Test main plan command with fixtures."""
        result = main(["-d", FIXTURES_DIR, "plan", "1001", "1002", "08:00:00"])
        captured = capsys.readouterr()
        assert result == 0
        assert "Planning journey" in captured.out


class TestSearchStopsOutput:
    """Tests for search_stops output formatting."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance with test fixtures."""
        cli = TransitCLI(gtfs_dir=FIXTURES_DIR)
        cli.load()
        return cli

    def test_search_stops_fuzzy_results(self, cli, capsys):
        """Test search_stops with fuzzy results."""
        cli.search_stops("Test Station", limit=5, fuzzy=True)
        captured = capsys.readouterr()
        assert "Searching for:" in captured.out
        assert "Found" in captured.out
        assert "stop(s)" in captured.out

    def test_search_stops_fuzzy_no_results(self, cli, capsys):
        """Test search_stops with no fuzzy results."""
        cli.search_stops("NonexistentStopXYZ123", limit=5, fuzzy=True)
        captured = capsys.readouterr()
        assert "No stops found" in captured.out

    def test_search_stops_exact_match(self, cli, capsys):
        """Test search_stops with exact match."""
        cli.search_stops("Test Station A", limit=5, fuzzy=False)
        captured = capsys.readouterr()
        assert "Searching for:" in captured.out
        assert "Found 1 stop" in captured.out

    def test_search_stops_exact_no_match(self, cli, capsys):
        """Test search_stops with no exact match."""
        cli.search_stops("NonexistentStop", limit=5, fuzzy=False)
        captured = capsys.readouterr()
        assert "No exact match found" in captured.out

    def test_search_stops_not_loaded(self, capsys):
        """Test search_stops when data not loaded."""
        cli = TransitCLI(gtfs_dir=FIXTURES_DIR)
        # Don't call load()
        cli.search_stops("Test", limit=5, fuzzy=True)
        captured = capsys.readouterr()
        assert "Error: GTFS data not loaded" in captured.out


class TestPlanJourneyOutput:
    """Tests for plan_journey output formatting."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance with test fixtures."""
        cli = TransitCLI(gtfs_dir=FIXTURES_DIR)
        cli.load()
        return cli

    def test_plan_journey_displays_route(self, cli, capsys):
        """Test plan_journey displays journey route."""
        cli.plan_journey("1001", "1002", "08:00:00")
        captured = capsys.readouterr()
        assert "Planning journey:" in captured.out
        assert "From:" in captured.out
        assert "To:" in captured.out

    def test_plan_journey_not_loaded(self, capsys):
        """Test plan_journey when data not loaded."""
        cli = TransitCLI(gtfs_dir=FIXTURES_DIR)
        # Don't call load()
        cli.plan_journey("1001", "1002", "08:00:00")
        captured = capsys.readouterr()
        assert "Error: GTFS data not loaded" in captured.out

    def test_plan_journey_origin_not_found(self, cli, capsys):
        """Test plan_journey with invalid origin."""
        cli.plan_journey("NonexistentOrigin123", "1002", "08:00:00")
        captured = capsys.readouterr()
        assert "Error: Origin stop not found" in captured.out

    def test_plan_journey_destination_not_found(self, cli, capsys):
        """Test plan_journey with invalid destination."""
        cli.plan_journey("1001", "NonexistentDest123", "08:00:00")
        captured = capsys.readouterr()
        assert "Error: Destination stop not found" in captured.out

    def test_plan_journey_same_origin_dest(self, cli, capsys):
        """Test plan_journey with same origin and destination."""
        cli.plan_journey("1001", "1001", "08:00:00")
        captured = capsys.readouterr()
        # Should show error from planner
        assert "Planning journey:" in captured.out

    def test_plan_journey_no_route(self, cli, capsys):
        """Test plan_journey when no route found."""
        # Use a stop that has no connections
        cli.plan_journey("1001", "1003", "03:00:00")
        captured = capsys.readouterr()
        # Either shows "No journey found" or error message
        assert "Planning journey:" in captured.out


class TestMainVerboseMode:
    """Tests for verbose mode."""

    def test_main_verbose_search(self, capsys):
        """Test main with verbose flag."""
        result = main(["-v", "-d", FIXTURES_DIR, "search", "Test"])
        assert result == 0

    def test_main_verbose_plan(self, capsys):
        """Test main plan with verbose flag."""
        result = main(["-v", "-d", FIXTURES_DIR, "plan", "1001", "1002", "08:00:00"])
        assert result == 0


class TestSearchExactMode:
    """Tests for exact search mode."""

    def test_main_search_exact(self, capsys):
        """Test main search with exact flag."""
        result = main(["-d", FIXTURES_DIR, "search", "Test Station A", "--exact"])
        captured = capsys.readouterr()
        assert result == 0
        assert "Searching for" in captured.out
