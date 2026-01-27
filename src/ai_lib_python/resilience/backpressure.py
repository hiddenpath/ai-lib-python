"""
Backpressure control using semaphores.

Limits concurrent operations to prevent overload.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

T = TypeVar("T")


@dataclass
class BackpressureConfig:
    """Configuration for backpressure control.

    Attributes:
        max_concurrent: Maximum concurrent operations
        queue_timeout: Timeout waiting for permit (None = wait forever)
    """

    max_concurrent: int = 10
    queue_timeout: float | None = None

    @classmethod
    def from_env(cls) -> BackpressureConfig:
        """Create configuration from environment variables."""
        max_concurrent = int(os.getenv("AI_LIB_MAX_INFLIGHT", "10"))
        timeout_str = os.getenv("AI_LIB_QUEUE_TIMEOUT")
        queue_timeout = float(timeout_str) if timeout_str else None

        return cls(
            max_concurrent=max_concurrent,
            queue_timeout=queue_timeout,
        )

    @classmethod
    def unlimited(cls) -> BackpressureConfig:
        """Create config with no limit."""
        return cls(max_concurrent=0)


class BackpressureError(Exception):
    """Raised when backpressure limit is exceeded."""

    def __init__(self, message: str = "Backpressure limit exceeded") -> None:
        super().__init__(message)


class Backpressure:
    """Backpressure control using semaphores.

    Limits the number of concurrent operations to prevent
    overwhelming downstream services.

    Example:
        >>> bp = Backpressure(BackpressureConfig(max_concurrent=5))
        >>> async with bp.acquire():
        ...     await make_request()

        >>> # Or with execute
        >>> result = await bp.execute(async_operation)
    """

    def __init__(self, config: BackpressureConfig | None = None) -> None:
        """Initialize backpressure control.

        Args:
            config: Backpressure configuration
        """
        self._config = config or BackpressureConfig()

        # Create semaphore if limiting is enabled
        if self._config.max_concurrent > 0:
            self._semaphore: asyncio.Semaphore | None = asyncio.Semaphore(
                self._config.max_concurrent
            )
        else:
            self._semaphore = None

        # Statistics
        self._current_inflight = 0
        self._peak_inflight = 0
        self._total_acquired = 0
        self._total_rejected = 0

    @property
    def current_inflight(self) -> int:
        """Get current number of in-flight operations."""
        return self._current_inflight

    @property
    def available_permits(self) -> int:
        """Get number of available permits."""
        if self._semaphore is None:
            return float("inf")  # type: ignore
        return self._config.max_concurrent - self._current_inflight

    @property
    def is_limited(self) -> bool:
        """Check if backpressure limiting is enabled."""
        return self._semaphore is not None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        """Acquire a permit for an operation.

        Yields:
            None when permit acquired

        Raises:
            BackpressureError: If timeout exceeded
            asyncio.TimeoutError: If timeout exceeded
        """
        if self._semaphore is None:
            # No limiting
            self._current_inflight += 1
            self._peak_inflight = max(self._peak_inflight, self._current_inflight)
            self._total_acquired += 1
            try:
                yield
            finally:
                self._current_inflight -= 1
            return

        try:
            if self._config.queue_timeout is not None:
                # Wait with timeout
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self._config.queue_timeout,
                )
            else:
                # Wait indefinitely
                await self._semaphore.acquire()

            self._current_inflight += 1
            self._peak_inflight = max(self._peak_inflight, self._current_inflight)
            self._total_acquired += 1

            try:
                yield
            finally:
                self._current_inflight -= 1
                self._semaphore.release()

        except asyncio.TimeoutError:
            self._total_rejected += 1
            raise BackpressureError("Timeout waiting for permit") from None

    async def try_acquire(self) -> bool:
        """Try to acquire a permit without waiting.

        Returns:
            True if permit acquired, False otherwise
        """
        if self._semaphore is None:
            self._current_inflight += 1
            self._peak_inflight = max(self._peak_inflight, self._current_inflight)
            self._total_acquired += 1
            return True

        # Try to acquire without waiting
        acquired = self._semaphore.locked() is False
        if acquired:
            await self._semaphore.acquire()
            self._current_inflight += 1
            self._peak_inflight = max(self._peak_inflight, self._current_inflight)
            self._total_acquired += 1

        return acquired

    def release(self) -> None:
        """Release a permit (if using try_acquire)."""
        self._current_inflight -= 1
        if self._semaphore is not None:
            self._semaphore.release()

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        """Execute an operation with backpressure control.

        Args:
            operation: Async operation to execute

        Returns:
            Operation result

        Raises:
            BackpressureError: If timeout exceeded
        """
        async with self.acquire():
            return await operation()

    def get_stats(self) -> dict[str, int]:
        """Get backpressure statistics.

        Returns:
            Dict with statistics
        """
        return {
            "current_inflight": self._current_inflight,
            "peak_inflight": self._peak_inflight,
            "total_acquired": self._total_acquired,
            "total_rejected": self._total_rejected,
            "max_concurrent": self._config.max_concurrent,
        }

    def __repr__(self) -> str:
        if self._semaphore is None:
            return "Backpressure(unlimited)"
        return (
            f"Backpressure("
            f"inflight={self._current_inflight}/{self._config.max_concurrent})"
        )
