"""
Cache backend implementations.

Provides memory, disk, and null cache backends.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """A cache entry with metadata.

    Attributes:
        value: Cached value
        created_at: Creation timestamp
        ttl: Time-to-live in seconds
        hits: Number of cache hits
    """

    value: Any
    created_at: float
    ttl: float | None = None
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl

    @property
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return time.time() - self.created_at


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        raise NotImplementedError

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: float | None = None
    ) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Close the backend (cleanup)."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend with TTL support.

    Example:
        >>> cache = MemoryCache(max_size=1000, default_ttl=3600)
        >>> await cache.set("key", {"data": "value"})
        >>> value = await cache.get("key")
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = None,
    ) -> None:
        """Initialize memory cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired:
                del self._cache[key]
                return None

            entry.hits += 1
            return entry.value

    async def set(
        self, key: str, value: Any, ttl: float | None = None
    ) -> None:
        """Set a value in the cache."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_one()

            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self._default_ttl,
            )

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._cache[key]
                return False
            return True

    def _evict_one(self) -> None:
        """Evict one entry (LRU-like based on hits)."""
        if not self._cache:
            return

        # First, remove expired entries
        expired = [k for k, v in self._cache.items() if v.is_expired]
        if expired:
            del self._cache[expired[0]]
            return

        # Otherwise, remove entry with lowest hits
        min_hits_key = min(self._cache.keys(), key=lambda k: self._cache[k].hits)
        del self._cache[min_hits_key]

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class DiskCache(CacheBackend):
    """Disk-based cache backend with TTL support.

    Stores cached values as JSON files on disk.

    Example:
        >>> cache = DiskCache(path="/tmp/ai_cache", default_ttl=86400)
        >>> await cache.set("key", {"data": "value"})
        >>> value = await cache.get("key")
    """

    def __init__(
        self,
        path: str | Path,
        default_ttl: float | None = None,
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB default
    ) -> None:
        """Initialize disk cache.

        Args:
            path: Cache directory path
            default_ttl: Default TTL in seconds
            max_size_bytes: Maximum cache size in bytes
        """
        self._path = Path(path)
        self._default_ttl = default_ttl
        self._max_size_bytes = max_size_bytes
        self._lock = asyncio.Lock()

        # Create cache directory
        self._path.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        """Convert cache key to file path.

        Args:
            key: Cache key

        Returns:
            File path
        """
        # Hash key to create safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self._path / f"{key_hash}.json"

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        path = self._key_to_path(key)

        async with self._lock:
            if not path.exists():
                return None

            try:
                content = path.read_text()
                data = json.loads(content)

                # Check expiry
                if data.get("ttl") is not None:
                    expires_at = data["created_at"] + data["ttl"]
                    if time.time() > expires_at:
                        path.unlink(missing_ok=True)
                        return None

                return data["value"]

            except (json.JSONDecodeError, KeyError, OSError):
                return None

    async def set(
        self, key: str, value: Any, ttl: float | None = None
    ) -> None:
        """Set a value in the cache."""
        path = self._key_to_path(key)

        async with self._lock:
            data = {
                "key": key,
                "value": value,
                "created_at": time.time(),
                "ttl": ttl if ttl is not None else self._default_ttl,
            }

            try:
                path.write_text(json.dumps(data, default=str))
            except OSError:
                # Ignore write errors
                pass

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        path = self._key_to_path(key)

        async with self._lock:
            if path.exists():
                path.unlink(missing_ok=True)
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            for path in self._path.glob("*.json"):
                path.unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        path = self._key_to_path(key)
        return path.exists()

    async def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed
        """
        removed = 0
        now = time.time()

        async with self._lock:
            for path in self._path.glob("*.json"):
                try:
                    content = path.read_text()
                    data = json.loads(content)

                    if data.get("ttl") is not None:
                        expires_at = data["created_at"] + data["ttl"]
                        if now > expires_at:
                            path.unlink(missing_ok=True)
                            removed += 1

                except (json.JSONDecodeError, KeyError, OSError):
                    pass

        return removed

    @property
    def cache_size_bytes(self) -> int:
        """Get total cache size in bytes."""
        total = 0
        for path in self._path.glob("*.json"):
            total += path.stat().st_size
        return total


class NullCache(CacheBackend):
    """Null cache backend that doesn't cache anything.

    Useful for testing or disabling caching.
    """

    async def get(self, key: str) -> Any | None:  # noqa: ARG002
        """Always returns None."""
        return None

    async def set(
        self, key: str, value: Any, ttl: float | None = None
    ) -> None:
        """Does nothing."""
        pass

    async def delete(self, key: str) -> bool:  # noqa: ARG002
        """Always returns False."""
        return False

    async def clear(self) -> None:
        """Does nothing."""
        pass

    async def exists(self, key: str) -> bool:  # noqa: ARG002
        """Always returns False."""
        return False
