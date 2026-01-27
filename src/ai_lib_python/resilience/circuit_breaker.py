"""
Circuit breaker for fault isolation.

Implements the circuit breaker pattern with three states:
- Closed: Normal operation, requests pass through
- Open: Circuit tripped, requests fail fast
- Half-Open: Testing if service recovered
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker.

    Attributes:
        failure_threshold: Number of failures to trip the circuit
        success_threshold: Number of successes in half-open to close
        cooldown_seconds: Time to wait before testing (half-open)
        timeout_seconds: Optional timeout for operations
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    cooldown_seconds: float = 30.0
    timeout_seconds: float | None = None
    half_open_max_concurrent: int = 1

    @classmethod
    def default(cls) -> CircuitBreakerConfig:
        """Create default configuration."""
        return cls()

    @classmethod
    def from_env(cls) -> CircuitBreakerConfig:
        """Create configuration from environment variables."""
        import os

        failure_threshold = int(
            os.getenv("AI_LIB_BREAKER_FAILURE_THRESHOLD", "5")
        )
        cooldown_seconds = float(
            os.getenv("AI_LIB_BREAKER_COOLDOWN_SECS", "30")
        )

        return cls(
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
        )


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        time_until_retry: float | None = None,
    ) -> None:
        super().__init__(message)
        self.time_until_retry = time_until_retry


@dataclass
class CircuitStats:
    """Statistics for circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None


class CircuitBreaker:
    """Circuit breaker for fault isolation.

    Prevents cascading failures by failing fast when a service is unhealthy.

    Example:
        >>> breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        >>> try:
        ...     result = await breaker.execute(async_operation)
        ... except CircuitOpenError:
        ...     print("Service unavailable")
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

        # Failure tracking
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._opened_at: float | None = None

        # Half-open state management
        self._half_open_semaphore = asyncio.Semaphore(
            self._config.half_open_max_concurrent
        )

        # Statistics
        self._stats = CircuitStats()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing)."""
        return self._state == CircuitState.HALF_OPEN

    def _check_state_transition(self) -> None:
        """Check if state should transition."""
        now = time.monotonic()

        if self._state == CircuitState.OPEN and self._opened_at is not None:
            # Check if cooldown has passed
            elapsed = now - self._opened_at
            if elapsed >= self._config.cooldown_seconds:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state.

        Args:
            new_state: Target state
        """
        if new_state == self._state:
            return

        self._state = new_state
        self._stats.state_changes += 1

        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._opened_at = None

    def _record_success(self) -> None:
        """Record a successful operation."""
        self._stats.successful_requests += 1
        self._stats.last_success_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = max(0, self._failure_count - 1)

    def _record_failure(self) -> None:
        """Record a failed operation."""
        now = time.monotonic()
        self._stats.failed_requests += 1
        self._stats.last_failure_time = now
        self._last_failure_time = now

        if self._state == CircuitState.HALF_OPEN:
            # Single failure in half-open trips back to open
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self._config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def get_time_until_retry(self) -> float | None:
        """Get time until circuit will transition to half-open.

        Returns:
            Seconds until retry, or None if not open
        """
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return None

        elapsed = time.monotonic() - self._opened_at
        remaining = self._config.cooldown_seconds - elapsed
        return max(0, remaining)

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        fallback: Callable[[], Awaitable[T]] | None = None,
    ) -> T:
        """Execute an operation through the circuit breaker.

        Args:
            operation: Async operation to execute
            fallback: Optional fallback if circuit is open

        Returns:
            Operation result

        Raises:
            CircuitOpenError: If circuit is open and no fallback
        """
        async with self._lock:
            self._check_state_transition()
            self._stats.total_requests += 1

            if self._state == CircuitState.OPEN:
                self._stats.rejected_requests += 1
                if fallback:
                    return await fallback()
                raise CircuitOpenError(
                    time_until_retry=self.get_time_until_retry()
                )

        # Execute operation
        try:
            if self._state == CircuitState.HALF_OPEN:
                # Limit concurrent requests in half-open state
                async with self._half_open_semaphore:
                    result = await self._execute_with_timeout(operation)
            else:
                result = await self._execute_with_timeout(operation)

            async with self._lock:
                self._record_success()

            return result

        except Exception:
            async with self._lock:
                self._record_failure()
            raise

    async def _execute_with_timeout(
        self, operation: Callable[[], Awaitable[T]]
    ) -> T:
        """Execute operation with optional timeout.

        Args:
            operation: Async operation

        Returns:
            Operation result
        """
        if self._config.timeout_seconds:
            return await asyncio.wait_for(
                operation(),
                timeout=self._config.timeout_seconds,
            )
        return await operation()

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None

    def get_stats(self) -> CircuitStats:
        """Get circuit breaker statistics.

        Returns:
            CircuitStats with current statistics
        """
        return CircuitStats(
            total_requests=self._stats.total_requests,
            successful_requests=self._stats.successful_requests,
            failed_requests=self._stats.failed_requests,
            rejected_requests=self._stats.rejected_requests,
            state_changes=self._stats.state_changes,
            last_failure_time=self._stats.last_failure_time,
            last_success_time=self._stats.last_success_time,
        )

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(state={self._state.value}, "
            f"failures={self._failure_count}/{self._config.failure_threshold})"
        )
