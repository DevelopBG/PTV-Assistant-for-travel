"""
Unit tests for GTFS Realtime Feed Fetcher

Tests cover:
- Initialization
- Feed fetching
- Error handling
- Different transport modes
- API authentication
"""

import pytest
import requests
from google.transit import gtfs_realtime_pb2
from src.realtime.feed_fetcher import GTFSRealtimeFetcher


class TestGTFSRealtimeFetcherInit:
    """Test GTFSRealtimeFetcher initialization."""

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        fetcher = GTFSRealtimeFetcher(api_key="test-key-123")
        assert fetcher.api_key == "test-key-123"
        assert fetcher.timeout == 30

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        fetcher = GTFSRealtimeFetcher(api_key="test-key", timeout=60)
        assert fetcher.timeout == 60

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError, match="API key is required"):
            GTFSRealtimeFetcher(api_key="")

    def test_init_with_none_api_key(self):
        """Test initialization fails with None API key."""
        with pytest.raises(ValueError, match="API key is required"):
            GTFSRealtimeFetcher(api_key=None)


class TestFetchFeed:
    """Test feed fetching functionality."""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance for testing."""
        return GTFSRealtimeFetcher(api_key="test-api-key")

    @pytest.fixture
    def mock_feed(self):
        """Create a mock GTFS Realtime feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = 1234567890

        # Add a test entity
        entity = feed.entity.add()
        entity.id = "test-entity-1"
        trip_update = entity.trip_update
        trip_update.trip.trip_id = "test-trip-123"
        trip_update.trip.route_id = "test-route"

        return feed

    def test_fetch_feed_success(self, fetcher, mock_feed, requests_mock):
        """Test successful feed fetch."""
        url = "https://test.example.com/feed"
        requests_mock.get(url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_feed(url)

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert result.header.gtfs_realtime_version == "2.0"
        assert len(result.entity) == 1
        assert result.entity[0].id == "test-entity-1"

    def test_fetch_feed_with_correct_headers(self, fetcher, mock_feed, requests_mock):
        """Test that fetch sends correct authentication headers."""
        url = "https://test.example.com/feed"
        adapter = requests_mock.get(url, content=mock_feed.SerializeToString())

        fetcher.fetch_feed(url)

        assert adapter.last_request.headers['KeyID'] == "test-api-key"

    def test_fetch_feed_http_error(self, fetcher, requests_mock):
        """Test handling of HTTP errors."""
        url = "https://test.example.com/feed"
        requests_mock.get(url, status_code=404, text="Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.fetch_feed(url)

    def test_fetch_feed_timeout(self, fetcher, requests_mock):
        """Test handling of timeout errors."""
        url = "https://test.example.com/feed"
        requests_mock.get(url, exc=requests.exceptions.Timeout)

        with pytest.raises(requests.exceptions.Timeout):
            fetcher.fetch_feed(url)

    def test_fetch_feed_connection_error(self, fetcher, requests_mock):
        """Test handling of connection errors."""
        url = "https://test.example.com/feed"
        requests_mock.get(url, exc=requests.exceptions.ConnectionError)

        with pytest.raises(requests.exceptions.ConnectionError):
            fetcher.fetch_feed(url)

    def test_fetch_feed_invalid_protobuf(self, fetcher, requests_mock):
        """Test handling of invalid protobuf data."""
        url = "https://test.example.com/feed"
        requests_mock.get(url, content=b"invalid protobuf data")

        with pytest.raises(ValueError, match="Invalid protobuf data"):
            fetcher.fetch_feed(url)

    def test_fetch_feed_empty_response(self, fetcher, requests_mock):
        """Test handling of empty response - creates empty valid feed."""
        url = "https://test.example.com/feed"
        requests_mock.get(url, content=b"")

        # Empty bytes is actually a valid (empty) protobuf message
        result = fetcher.fetch_feed(url)
        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert len(result.entity) == 0


class TestFetchTripUpdates:
    """Test trip updates fetching."""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance for testing."""
        return GTFSRealtimeFetcher(api_key="test-api-key")

    @pytest.fixture
    def mock_feed(self):
        """Create a mock feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        return feed

    def test_fetch_trip_updates_metro(self, fetcher, mock_feed, requests_mock):
        """Test fetching metro trip updates."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['metro']['trip_updates']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_trip_updates('metro')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_trip_updates_vline(self, fetcher, mock_feed, requests_mock):
        """Test fetching V/Line trip updates."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['vline']['trip_updates']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_trip_updates('vline')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_trip_updates_tram(self, fetcher, mock_feed, requests_mock):
        """Test fetching tram trip updates."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['tram']['trip_updates']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_trip_updates('tram')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_trip_updates_bus(self, fetcher, mock_feed, requests_mock):
        """Test fetching bus trip updates."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['bus']['trip_updates']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_trip_updates('bus')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_trip_updates_invalid_mode(self, fetcher):
        """Test error on invalid transport mode."""
        with pytest.raises(ValueError, match="Unknown mode: invalid"):
            fetcher.fetch_trip_updates('invalid')


class TestFetchVehiclePositions:
    """Test vehicle positions fetching."""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance for testing."""
        return GTFSRealtimeFetcher(api_key="test-api-key")

    @pytest.fixture
    def mock_feed(self):
        """Create a mock feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        return feed

    def test_fetch_vehicle_positions_metro(self, fetcher, mock_feed, requests_mock):
        """Test fetching metro vehicle positions."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['metro']['vehicle_positions']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_vehicle_positions('metro')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_vehicle_positions_vline(self, fetcher, mock_feed, requests_mock):
        """Test fetching V/Line vehicle positions."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['vline']['vehicle_positions']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_vehicle_positions('vline')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_vehicle_positions_tram(self, fetcher, mock_feed, requests_mock):
        """Test fetching tram vehicle positions."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['tram']['vehicle_positions']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_vehicle_positions('tram')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_vehicle_positions_bus(self, fetcher, mock_feed, requests_mock):
        """Test fetching bus vehicle positions."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['bus']['vehicle_positions']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_vehicle_positions('bus')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_vehicle_positions_invalid_mode(self, fetcher):
        """Test error on invalid transport mode."""
        with pytest.raises(ValueError, match="Unknown mode"):
            fetcher.fetch_vehicle_positions('ferry')


class TestFetchServiceAlerts:
    """Test service alerts fetching."""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance for testing."""
        return GTFSRealtimeFetcher(api_key="test-api-key")

    @pytest.fixture
    def mock_feed(self):
        """Create a mock feed."""
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        return feed

    def test_fetch_service_alerts_metro(self, fetcher, mock_feed, requests_mock):
        """Test fetching metro service alerts."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['metro']['service_alerts']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_service_alerts('metro')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_service_alerts_vline(self, fetcher, mock_feed, requests_mock):
        """Test fetching V/Line service alerts."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['vline']['service_alerts']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_service_alerts('vline')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)

    def test_fetch_service_alerts_tram(self, fetcher, mock_feed, requests_mock):
        """Test fetching tram service alerts."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['tram']['service_alerts']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_service_alerts('tram')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_service_alerts_bus(self, fetcher, mock_feed, requests_mock):
        """Test fetching bus service alerts (URL exists even though not available)."""
        expected_url = GTFSRealtimeFetcher.FEED_URLS['bus']['service_alerts']
        requests_mock.get(expected_url, content=mock_feed.SerializeToString())

        result = fetcher.fetch_service_alerts('bus')

        assert isinstance(result, gtfs_realtime_pb2.FeedMessage)
        assert requests_mock.last_request.url == expected_url

    def test_fetch_service_alerts_invalid_mode(self, fetcher):
        """Test error on invalid transport mode."""
        with pytest.raises(ValueError, match="Unknown mode"):
            fetcher.fetch_service_alerts('ferry')


class TestFeedURLs:
    """Test feed URL configuration."""

    def test_feed_urls_structure(self):
        """Test that FEED_URLS has the expected structure for all 4 modes."""
        urls = GTFSRealtimeFetcher.FEED_URLS

        # All 4 modes should be present
        assert 'metro' in urls
        assert 'vline' in urls
        assert 'tram' in urls
        assert 'bus' in urls

        for mode in ['metro', 'vline', 'tram', 'bus']:
            assert 'trip_updates' in urls[mode]
            assert 'vehicle_positions' in urls[mode]
            assert 'service_alerts' in urls[mode]

    def test_feed_urls_are_valid(self):
        """Test that all feed URLs are properly formatted."""
        urls = GTFSRealtimeFetcher.FEED_URLS

        for mode, feeds in urls.items():
            for feed_type, url in feeds.items():
                assert url.startswith('https://')
                assert 'api.opendata.transport.vic.gov.au' in url
                assert mode in url
                assert feed_type.replace('_', '-') in url

    def test_feed_urls_count(self):
        """Test that we have exactly 4 modes configured."""
        urls = GTFSRealtimeFetcher.FEED_URLS
        assert len(urls) == 4

    def test_each_mode_has_three_feeds(self):
        """Test that each mode has all 3 feed types."""
        urls = GTFSRealtimeFetcher.FEED_URLS
        for mode in urls:
            assert len(urls[mode]) == 3, f"Mode {mode} should have 3 feed types"
