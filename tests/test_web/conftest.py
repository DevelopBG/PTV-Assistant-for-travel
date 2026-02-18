"""
Pytest fixtures for Flask web application tests.

Provides test fixtures that mock the JourneyPlanner and set up Flask test client.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch


# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope='module')
def flask_app():
    """
    Create Flask application for testing.

    This fixture mocks the GTFSParser and JourneyPlanner initialization to avoid
    loading actual GTFS data during tests.
    """
    # Create mock GTFSParser
    mock_parser = MagicMock()
    mock_parser.load_stops = MagicMock()
    mock_parser.load_routes = MagicMock()
    mock_parser.load_trips = MagicMock()
    mock_parser.load_stop_times = MagicMock()

    # Create mock stops (using GTFS field names: stop_name, stop_lat, stop_lon)
    mock_stop1 = MagicMock()
    mock_stop1.stop_id = '47648'
    mock_stop1.stop_name = 'Tarneit Station'
    mock_stop1.platform_code = 'Platform 1'
    mock_stop1.stop_lat = -37.832
    mock_stop1.stop_lon = 144.694

    mock_stop2 = MagicMock()
    mock_stop2.stop_id = '47641'
    mock_stop2.stop_name = 'Waurn Ponds Station'
    mock_stop2.platform_code = 'Platform 2'
    mock_stop2.stop_lat = -38.216
    mock_stop2.stop_lon = 144.306

    mock_parser.stops = {
        '47648': mock_stop1,
        '47641': mock_stop2
    }

    # Create mock JourneyPlanner
    mock_planner = MagicMock()
    mock_planner.api_key = None
    mock_planner.parser = mock_parser

    # Create mock gtfs_data for backwards compatibility
    mock_planner.gtfs_data = MagicMock()
    mock_planner.gtfs_data.stops = mock_parser.stops

    # Create mock modules
    mock_gtfs_parser_module = MagicMock()
    mock_gtfs_parser_module.GTFSParser = MagicMock(return_value=mock_parser)

    mock_journey_planner_module = MagicMock()
    mock_journey_planner_module.JourneyPlanner = MagicMock(return_value=mock_planner)

    # Inject mocks into sys.modules before importing app
    sys.modules['src.data.gtfs_parser'] = mock_gtfs_parser_module
    sys.modules['src.routing.journey_planner'] = mock_journey_planner_module

    # Now import app - it will use our mocked modules
    import app as flask_app_module
    flask_app_module.planner = mock_planner

    flask_app_module.app.config['TESTING'] = True
    flask_app_module.app.config['DEBUG'] = False

    yield flask_app_module.app

    # Cleanup
    if 'src.data.gtfs_parser' in sys.modules:
        del sys.modules['src.data.gtfs_parser']
    if 'src.routing.journey_planner' in sys.modules:
        del sys.modules['src.routing.journey_planner']


@pytest.fixture
def client(flask_app):
    """Create Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for testing proxy endpoints."""
    with patch('app.requests.get') as mock_get:
        yield mock_get
