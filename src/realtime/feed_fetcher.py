"""
GTFS Realtime Feed Fetcher

Fetches and parses GTFS Realtime protobuf feeds from PTV API.
Supports trip updates, vehicle positions, and service alerts.

Documentation: https://opendata.transport.vic.gov.au/dataset/gtfs-realtime
License: Creative Commons Attribution 4.0
"""

import requests
from google.transit import gtfs_realtime_pb2
from typing import Optional
import logging
import time
import threading
from collections import deque

# Import cache utilities with relative import
from ..utils.cache import TTLCache

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter to ensure we don't exceed API limits.
    PTV allows 24 requests per minute per feed type.
    """

    def __init__(self, max_calls: int = 24, period: float = 60.0):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self._calls = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """
        Acquire permission to make a call. Blocks if rate limit would be exceeded.
        """
        with self._lock:
            now = time.time()

            # Remove calls outside the current period
            while self._calls and self._calls[0] < now - self.period:
                self._calls.popleft()

            # If at limit, wait until oldest call expires
            if len(self._calls) >= self.max_calls:
                sleep_time = self.period - (now - self._calls[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    # Remove expired calls after sleeping
                    now = time.time()
                    while self._calls and self._calls[0] < now - self.period:
                        self._calls.popleft()

            # Record this call
            self._calls.append(now)


class GTFSRealtimeFetcher:
    """Fetches GTFS Realtime feeds from PTV API."""

    # PTV GTFS Realtime feed URLs
    # Supports: metro, vline, tram, bus
    # Note: Service alerts only available for metro and tram
    FEED_URLS = {
        'metro': {
            'trip_updates': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/metro/trip-updates',
            'vehicle_positions': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/metro/vehicle-positions',
            'service_alerts': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/metro/service-alerts',
        },
        'vline': {
            'trip_updates': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/vline/trip-updates',
            'vehicle_positions': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/vline/vehicle-positions',
            'service_alerts': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/vline/service-alerts',
        },
        'tram': {
            'trip_updates': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/tram/trip-updates',
            'vehicle_positions': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/tram/vehicle-positions',
            'service_alerts': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/tram/service-alerts',
        },
        'bus': {
            'trip_updates': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/bus/trip-updates',
            'vehicle_positions': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/bus/vehicle-positions',
            'service_alerts': 'https://api.opendata.transport.vic.gov.au/opendata/public-transport/gtfs/realtime/v1/bus/service-alerts',
        }
    }

    def __init__(self, api_key: str, timeout: int = 30, enable_cache: bool = True, enable_rate_limiting: bool = True):
        """
        Initialize the GTFS Realtime fetcher.

        Args:
            api_key: PTV API subscription key
            timeout: Request timeout in seconds (default: 30)
            enable_cache: Enable 30-second TTL caching (default: True)
            enable_rate_limiting: Enable rate limiting at 24 calls/min (default: True)
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.timeout = timeout

        # Initialize 30-second TTL cache per architecture spec
        self._cache_enabled = enable_cache
        if enable_cache:
            self._cache = TTLCache(
                default_ttl=30.0,  # 30 seconds as per ARCHITECTURE.md
                max_size=128,      # Cache up to 128 feed responses
                cleanup_interval=30.0
            )
        else:
            self._cache = None

        # Initialize rate limiter (24 calls per minute per PTV spec)
        self._rate_limit_enabled = enable_rate_limiting
        if enable_rate_limiting:
            self._rate_limiter = RateLimiter(max_calls=24, period=60.0)
        else:
            self._rate_limiter = None

    def fetch_feed(self, url: str) -> gtfs_realtime_pb2.FeedMessage:
        """
        Fetch and parse a GTFS Realtime feed from the given URL.
        Uses 30-second TTL cache and rate limiting as per ARCHITECTURE.md.

        Args:
            url: The URL of the GTFS Realtime feed

        Returns:
            Parsed FeedMessage protobuf object

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails
            ValueError: If the response cannot be parsed as protobuf
        """
        # Check cache first
        if self._cache_enabled and self._cache is not None:
            cached_feed = self._cache.get(url)
            if cached_feed is not None:
                logger.debug(f"Cache hit for {url}")
                return cached_feed

        # Apply rate limiting before making request
        if self._rate_limit_enabled and self._rate_limiter is not None:
            self._rate_limiter.acquire()

        try:
            headers = {
                'KeyID': self.api_key
            }

            logger.debug(f"Fetching GTFS Realtime feed from: {url}")
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Parse the protobuf feed
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            logger.info(f"Successfully fetched feed with {len(feed.entity)} entities")

            # Cache the result
            if self._cache_enabled and self._cache is not None:
                self._cache.set(url, feed)
                logger.debug(f"Cached feed for {url} (30s TTL)")

            return feed

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text[:200]}")
            raise

        except Exception as e:
            logger.error(f"Failed to parse protobuf: {e}")
            raise ValueError(f"Invalid protobuf data: {e}") from e

    def fetch_trip_updates(self, mode: str = 'metro') -> gtfs_realtime_pb2.FeedMessage:
        """
        Fetch trip updates for the specified transport mode.

        Args:
            mode: Transport mode ('metro', 'vline', 'tram', or 'bus')

        Returns:
            FeedMessage containing trip updates
        """
        if mode not in self.FEED_URLS:
            raise ValueError(f"Unknown mode: {mode}. Must be one of {list(self.FEED_URLS.keys())}")

        url = self.FEED_URLS[mode]['trip_updates']
        return self.fetch_feed(url)

    def fetch_vehicle_positions(self, mode: str = 'metro') -> gtfs_realtime_pb2.FeedMessage:
        """
        Fetch vehicle positions for the specified transport mode.

        Args:
            mode: Transport mode ('metro', 'vline', 'tram', or 'bus')

        Returns:
            FeedMessage containing vehicle positions
        """
        if mode not in self.FEED_URLS:
            raise ValueError(f"Unknown mode: {mode}. Must be one of {list(self.FEED_URLS.keys())}")

        url = self.FEED_URLS[mode]['vehicle_positions']
        return self.fetch_feed(url)

    def fetch_service_alerts(self, mode: str = 'metro') -> gtfs_realtime_pb2.FeedMessage:
        """
        Fetch service alerts for the specified transport mode.

        Args:
            mode: Transport mode ('metro', 'vline', 'tram', or 'bus')
                  Note: Service alerts only available for 'metro' and 'tram'.

        Returns:
            FeedMessage containing service alerts
        """
        if mode not in self.FEED_URLS:
            raise ValueError(f"Unknown mode: {mode}. Must be one of {list(self.FEED_URLS.keys())}")

        url = self.FEED_URLS[mode]['service_alerts']
        return self.fetch_feed(url)

    def clear_cache(self) -> None:
        """Clear the feed cache."""
        if self._cache is not None:
            self._cache.clear()
            logger.info("Feed cache cleared")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats or empty dict if caching disabled
        """
        if self._cache is not None:
            return self._cache.stats()
        return {}
