"""
TTL-based caching utility for API responses.

Provides thread-safe caching with automatic expiration for
frequently accessed data like stop searches and journey plans.
"""

import time
import threading
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from functools import wraps
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with value and expiration time."""
    value: T
    expires_at: float
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > self.expires_at


class TTLCache(Generic[T]):
    """
    Thread-safe TTL (Time-To-Live) cache.

    Supports automatic expiration of entries and periodic cleanup.
    """

    def __init__(
        self,
        default_ttl: float = 300.0,  # 5 minutes default
        max_size: int = 1000,
        cleanup_interval: float = 60.0
    ):
        """
        Initialize TTL cache.

        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of entries
            cleanup_interval: Interval for automatic cleanup in seconds
        """
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

        # Stats
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            self._maybe_cleanup()

            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        with self._lock:
            self._maybe_cleanup()

            # Evict oldest entries if at capacity
            if len(self._cache) >= self._max_size:
                self._evict_oldest()

            ttl = ttl if ttl is not None else self._default_ttl
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )

    def delete(self, key: str) -> bool:
        """
        Delete a value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def _maybe_cleanup(self) -> None:
        """Perform cleanup if enough time has passed."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now

    def _cleanup_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _evict_oldest(self) -> None:
        """Evict oldest entries to make room."""
        if not self._cache:
            return

        # Sort by creation time and remove oldest 10%
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        evict_count = max(1, len(sorted_keys) // 10)

        for key in sorted_keys[:evict_count]:
            del self._cache[key]

        logger.debug(f"Evicted {evict_count} oldest cache entries")

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'default_ttl': self._default_ttl,
            }


def make_cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Unique cache key string
    """
    # Create a hashable representation of args and kwargs
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_json = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_json.encode()).hexdigest()


def cached(
    cache: TTLCache,
    key_prefix: str = "",
    ttl: Optional[float] = None
) -> Callable:
    """
    Decorator to cache function results.

    Args:
        cache: TTLCache instance to use
        key_prefix: Prefix for cache keys
        ttl: Time-to-live for cached results

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            key = f"{key_prefix}:{make_cache_key(*args, **kwargs)}"

            # Check cache
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {key_prefix}")
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            logger.debug(f"Cache miss for {key_prefix}, cached result")

            return result
        return wrapper
    return decorator


# Global caches for different use cases
_search_cache: Optional[TTLCache] = None
_journey_cache: Optional[TTLCache] = None


def get_search_cache() -> TTLCache:
    """Get the global search results cache."""
    global _search_cache
    if _search_cache is None:
        _search_cache = TTLCache(
            default_ttl=300.0,  # 5 minutes
            max_size=500
        )
    return _search_cache


def get_journey_cache() -> TTLCache:
    """Get the global journey results cache."""
    global _journey_cache
    if _journey_cache is None:
        _journey_cache = TTLCache(
            default_ttl=60.0,  # 1 minute (journey results change with realtime)
            max_size=200
        )
    return _journey_cache


def reset_caches() -> None:
    """Reset all global caches. Used primarily for testing."""
    global _search_cache, _journey_cache
    if _search_cache:
        _search_cache.clear()
    if _journey_cache:
        _journey_cache.clear()
    _search_cache = None
    _journey_cache = None
