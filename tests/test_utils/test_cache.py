"""
Tests for the TTL-based caching utility.
"""

import time
import pytest
import threading
from unittest.mock import MagicMock

from src.utils.cache import (
    TTLCache,
    CacheEntry,
    make_cache_key,
    cached,
    get_search_cache,
    get_journey_cache,
    reset_caches,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_not_expired(self):
        """Test entry is not expired when within TTL."""
        entry = CacheEntry(value="test", expires_at=time.time() + 100)
        assert not entry.is_expired()

    def test_cache_entry_expired(self):
        """Test entry is expired when past TTL."""
        entry = CacheEntry(value="test", expires_at=time.time() - 1)
        assert entry.is_expired()

    def test_cache_entry_stores_created_at(self):
        """Test entry records creation time."""
        before = time.time()
        entry = CacheEntry(value="test", expires_at=time.time() + 100)
        after = time.time()
        assert before <= entry.created_at <= after


class TestTTLCache:
    """Tests for TTLCache class."""

    def test_get_set_basic(self):
        """Test basic get/set operations."""
        cache = TTLCache(default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        """Test get returns None for missing key."""
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_get_expired_key(self):
        """Test get returns None for expired key."""
        cache = TTLCache(default_ttl=0.01)  # Very short TTL
        cache.set("key1", "value1")
        time.sleep(0.02)  # Wait for expiration
        assert cache.get("key1") is None

    def test_set_with_custom_ttl(self):
        """Test set with custom TTL."""
        cache = TTLCache(default_ttl=60)
        cache.set("key1", "value1", ttl=0.01)
        time.sleep(0.02)
        assert cache.get("key1") is None

    def test_delete_existing_key(self):
        """Test delete returns True for existing key."""
        cache = TTLCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing_key(self):
        """Test delete returns False for missing key."""
        cache = TTLCache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test clear removes all entries."""
        cache = TTLCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_max_size_eviction(self):
        """Test oldest entries are evicted when max size reached."""
        cache = TTLCache(max_size=5, default_ttl=60)

        # Add entries up to max size
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
            time.sleep(0.001)  # Ensure different creation times

        # Add one more to trigger eviction
        cache.set("key_new", "value_new")

        # Newest should exist
        assert cache.get("key_new") == "value_new"

        # At least some old entries should be evicted
        stats = cache.stats()
        assert stats['size'] <= 5

    def test_stats(self):
        """Test cache statistics."""
        cache = TTLCache(max_size=100, default_ttl=60)

        # Generate some hits and misses
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        stats = cache.stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 2/3
        assert stats['size'] == 1
        assert stats['max_size'] == 100

    def test_thread_safety(self):
        """Test cache is thread-safe."""
        cache = TTLCache(max_size=1000, default_ttl=60)
        errors = []

        def writer():
            try:
                for i in range(100):
                    cache.set(f"key_{threading.current_thread().name}_{i}", i)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(100):
                    cache.get(f"key_reader_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, name=f"writer_{i}"))
            threads.append(threading.Thread(target=reader, name=f"reader_{i}"))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_cleanup_expired(self):
        """Test automatic cleanup of expired entries."""
        cache = TTLCache(default_ttl=0.01, cleanup_interval=0.01)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        time.sleep(0.03)  # Wait for expiration and cleanup

        # Trigger cleanup by accessing cache
        cache.get("any_key")

        # Both entries should be cleaned up
        stats = cache.stats()
        assert stats['size'] == 0


class TestMakeCacheKey:
    """Tests for make_cache_key function."""

    def test_same_args_same_key(self):
        """Test same arguments produce same key."""
        key1 = make_cache_key("arg1", "arg2", kwarg1="value1")
        key2 = make_cache_key("arg1", "arg2", kwarg1="value1")
        assert key1 == key2

    def test_different_args_different_key(self):
        """Test different arguments produce different keys."""
        key1 = make_cache_key("arg1")
        key2 = make_cache_key("arg2")
        assert key1 != key2

    def test_order_matters_for_args(self):
        """Test argument order affects key."""
        key1 = make_cache_key("a", "b")
        key2 = make_cache_key("b", "a")
        assert key1 != key2

    def test_handles_complex_types(self):
        """Test key generation with complex types."""
        key = make_cache_key(
            [1, 2, 3],
            {"nested": "dict"},
            value={"list": [1, 2]}
        )
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_caches_function_result(self):
        """Test decorator caches function results."""
        cache = TTLCache(default_ttl=60)
        call_count = 0

        @cached(cache, key_prefix="test")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Only called once

    def test_different_args_not_cached(self):
        """Test different arguments are not cached together."""
        cache = TTLCache(default_ttl=60)

        @cached(cache, key_prefix="test")
        def add(x, y):
            return x + y

        result1 = add(1, 2)
        result2 = add(3, 4)

        assert result1 == 3
        assert result2 == 7

    def test_custom_ttl(self):
        """Test decorator with custom TTL."""
        cache = TTLCache(default_ttl=60)

        @cached(cache, key_prefix="test", ttl=0.01)
        def get_value():
            return "value"

        result1 = get_value()
        time.sleep(0.02)
        # Force re-execution by checking cache is expired
        stats_before = cache.stats()

        result2 = get_value()

        assert result1 == "value"
        assert result2 == "value"


class TestGlobalCaches:
    """Tests for global cache instances."""

    def teardown_method(self):
        """Reset caches after each test."""
        reset_caches()

    def test_get_search_cache(self):
        """Test get_search_cache returns singleton."""
        cache1 = get_search_cache()
        cache2 = get_search_cache()
        assert cache1 is cache2

    def test_get_journey_cache(self):
        """Test get_journey_cache returns singleton."""
        cache1 = get_journey_cache()
        cache2 = get_journey_cache()
        assert cache1 is cache2

    def test_search_cache_config(self):
        """Test search cache has correct configuration."""
        cache = get_search_cache()
        stats = cache.stats()
        assert stats['default_ttl'] == 300.0  # 5 minutes
        assert stats['max_size'] == 500

    def test_journey_cache_config(self):
        """Test journey cache has correct configuration."""
        cache = get_journey_cache()
        stats = cache.stats()
        assert stats['default_ttl'] == 60.0  # 1 minute
        assert stats['max_size'] == 200

    def test_reset_caches(self):
        """Test reset_caches clears all caches."""
        search_cache = get_search_cache()
        journey_cache = get_journey_cache()

        search_cache.set("key1", "value1")
        journey_cache.set("key2", "value2")

        reset_caches()

        # Get new instances
        new_search = get_search_cache()
        new_journey = get_journey_cache()

        assert new_search.get("key1") is None
        assert new_journey.get("key2") is None
