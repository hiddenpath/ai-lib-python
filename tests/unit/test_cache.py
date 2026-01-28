"""Tests for cache module."""

import tempfile
from pathlib import Path

import pytest

from ai_lib_python.cache import (
    CacheConfig,
    CacheKey,
    CacheKeyGenerator,
    CacheManager,
    CacheStats,
    DiskCache,
    MemoryCache,
    NullCache,
)


class TestCacheKey:
    """Tests for CacheKey."""

    def test_basic_key(self) -> None:
        """Test basic cache key."""
        key = CacheKey(key="test:key", model="gpt-4o")
        assert str(key) == "test:key"
        assert key.model == "gpt-4o"

    def test_equality(self) -> None:
        """Test key equality."""
        key1 = CacheKey(key="test")
        key2 = CacheKey(key="test")
        key3 = CacheKey(key="other")

        assert key1 == key2
        assert key1 != key3
        assert key1 == "test"  # Compare with string


class TestCacheKeyGenerator:
    """Tests for CacheKeyGenerator."""

    def test_generate_key(self) -> None:
        """Test key generation."""
        gen = CacheKeyGenerator(prefix="ai")
        key = gen.generate(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert key.key.startswith("ai:")
        assert "gpt-4o" in key.key
        assert key.model == "gpt-4o"

    def test_same_input_same_key(self) -> None:
        """Test deterministic key generation."""
        gen = CacheKeyGenerator()
        messages = [{"role": "user", "content": "Hello"}]

        key1 = gen.generate("gpt-4o", messages)
        key2 = gen.generate("gpt-4o", messages)

        assert key1.key == key2.key

    def test_different_messages_different_key(self) -> None:
        """Test different messages produce different keys."""
        gen = CacheKeyGenerator()

        key1 = gen.generate("gpt-4o", [{"role": "user", "content": "Hello"}])
        key2 = gen.generate("gpt-4o", [{"role": "user", "content": "World"}])

        assert key1.key != key2.key

    def test_generate_for_embedding(self) -> None:
        """Test embedding key generation."""
        gen = CacheKeyGenerator()
        key = gen.generate_for_embedding(
            model="text-embedding-3-small",
            input_text="Hello",
            dimensions=512,
        )
        assert "emb" in key.key
        assert "512" in key.key


class TestCacheStats:
    """Tests for CacheStats."""

    def test_initial_stats(self) -> None:
        """Test initial statistics."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = CacheStats(hits=7, misses=3)
        assert stats.hit_rate == 0.7

    def test_reset(self) -> None:
        """Test stats reset."""
        stats = CacheStats(hits=10, misses=5)
        stats.reset()
        assert stats.hits == 0
        assert stats.misses == 0


class TestMemoryCache:
    """Tests for MemoryCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        """Test basic set and get."""
        cache = MemoryCache()
        await cache.set("key1", {"data": "value"})
        result = await cache.get("key1")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        """Test getting missing key."""
        cache = MemoryCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test deleting key."""
        cache = MemoryCache()
        await cache.set("key1", "value")
        deleted = await cache.delete("key1")
        assert deleted
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        """Test existence check."""
        cache = MemoryCache()
        await cache.set("key1", "value")
        assert await cache.exists("key1")
        assert not await cache.exists("key2")

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing cache."""
        cache = MemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert cache.size == 0

    @pytest.mark.asyncio
    async def test_max_size_eviction(self) -> None:
        """Test eviction when max size reached."""
        cache = MemoryCache(max_size=2)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")  # Should evict one

        assert cache.size == 2


class TestDiskCache:
    """Tests for DiskCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        """Test basic set and get."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(path=tmpdir)
            await cache.set("key1", {"data": "value"})
            result = await cache.get("key1")
            assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_persistence(self) -> None:
        """Test data persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write with first cache instance
            cache1 = DiskCache(path=tmpdir)
            await cache1.set("key1", "value1")

            # Read with second cache instance
            cache2 = DiskCache(path=tmpdir)
            result = await cache2.get("key1")
            assert result == "value1"

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test deleting from disk cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(path=tmpdir)
            await cache.set("key1", "value")
            deleted = await cache.delete("key1")
            assert deleted
            assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing disk cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(path=tmpdir)
            await cache.set("key1", "value1")
            await cache.set("key2", "value2")
            await cache.clear()

            # Should have no JSON files
            json_files = list(Path(tmpdir).glob("*.json"))
            assert len(json_files) == 0


class TestNullCache:
    """Tests for NullCache."""

    @pytest.mark.asyncio
    async def test_always_returns_none(self) -> None:
        """Test null cache always returns None."""
        cache = NullCache()
        await cache.set("key", "value")
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_returns_false(self) -> None:
        """Test delete always returns False."""
        cache = NullCache()
        assert not await cache.delete("key")

    @pytest.mark.asyncio
    async def test_exists_returns_false(self) -> None:
        """Test exists always returns False."""
        cache = NullCache()
        assert not await cache.exists("key")


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = CacheConfig()
        assert config.enabled
        assert config.default_ttl == 3600.0

    def test_disabled_config(self) -> None:
        """Test disabled configuration."""
        config = CacheConfig.disabled()
        assert not config.enabled

    def test_short_ttl(self) -> None:
        """Test short TTL configuration."""
        config = CacheConfig.short_ttl(60.0)
        assert config.default_ttl == 60.0

    def test_long_ttl(self) -> None:
        """Test long TTL configuration."""
        config = CacheConfig.long_ttl()
        assert config.default_ttl == 86400.0


class TestCacheManager:
    """Tests for CacheManager."""

    @pytest.mark.asyncio
    async def test_cache_response(self) -> None:
        """Test caching a response."""
        manager = CacheManager(CacheConfig(default_ttl=3600))
        messages = [{"role": "user", "content": "Hello"}]

        key = await manager.cache_response(
            model="gpt-4o",
            messages=messages,
            response={"content": "Hi there!"},
        )
        assert key is not None

        # Retrieve
        cached = await manager.get_response("gpt-4o", messages)
        assert cached == {"content": "Hi there!"}

    @pytest.mark.asyncio
    async def test_cache_miss(self) -> None:
        """Test cache miss."""
        manager = CacheManager()
        messages = [{"role": "user", "content": "Not cached"}]

        result = await manager.get_response("gpt-4o", messages)
        assert result is None
        assert manager.stats.misses == 1

    @pytest.mark.asyncio
    async def test_cache_hit_stats(self) -> None:
        """Test cache hit updates stats."""
        manager = CacheManager()
        messages = [{"role": "user", "content": "Hello"}]

        await manager.cache_response("gpt-4o", messages, {"response": "Hi"})
        await manager.get_response("gpt-4o", messages)

        assert manager.stats.hits == 1
        assert manager.stats.sets == 1

    @pytest.mark.asyncio
    async def test_invalidate(self) -> None:
        """Test cache invalidation."""
        manager = CacheManager()
        messages = [{"role": "user", "content": "Hello"}]

        await manager.cache_response("gpt-4o", messages, {"response": "Hi"})
        invalidated = await manager.invalidate("gpt-4o", messages)
        assert invalidated

        # Should be gone
        result = await manager.get_response("gpt-4o", messages)
        assert result is None

    @pytest.mark.asyncio
    async def test_disabled_cache(self) -> None:
        """Test disabled cache."""
        manager = CacheManager(CacheConfig.disabled())
        messages = [{"role": "user", "content": "Hello"}]

        await manager.cache_response("gpt-4o", messages, {"response": "Hi"})
        result = await manager.get_response("gpt-4o", messages)

        assert result is None
        assert not manager.enabled
