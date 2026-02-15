"""弹性执行器：统一的重试、限流、熔断和背压控制。

Resilient executor combining all resilience patterns.

Provides a unified interface for executing operations with
retry, rate limiting, circuit breaking, and backpressure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from ai_lib_python.resilience.backpressure import Backpressure, BackpressureConfig
from ai_lib_python.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
)
from ai_lib_python.resilience.rate_limiter import RateLimiter, RateLimiterConfig
from ai_lib_python.resilience.retry import RetryConfig, RetryPolicy, RetryResult

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


@dataclass
class ResilientConfig:
    """Combined configuration for all resilience patterns.

    Attributes:
        retry: Retry configuration
        rate_limit: Rate limiter configuration
        circuit_breaker: Circuit breaker configuration
        backpressure: Backpressure configuration
    """

    retry: RetryConfig | None = None
    rate_limit: RateLimiterConfig | None = None
    circuit_breaker: CircuitBreakerConfig | None = None
    backpressure: BackpressureConfig | None = None

    @classmethod
    def default(cls) -> ResilientConfig:
        """Create default configuration with all patterns enabled."""
        return cls(
            retry=RetryConfig(),
            rate_limit=RateLimiterConfig(),
            circuit_breaker=CircuitBreakerConfig(),
            backpressure=BackpressureConfig(),
        )

    @classmethod
    def minimal(cls) -> ResilientConfig:
        """Create minimal configuration with basic retry only."""
        return cls(retry=RetryConfig(max_retries=2))

    @classmethod
    def production(cls) -> ResilientConfig:
        """Create production-grade configuration."""
        return cls(
            retry=RetryConfig(
                max_retries=3,
                min_delay_ms=1000,
                max_delay_ms=30000,
            ),
            rate_limit=RateLimiterConfig.from_rps(10),
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=5,
                cooldown_seconds=30,
            ),
            backpressure=BackpressureConfig(max_concurrent=10),
        )


@dataclass
class ExecutionStats:
    """Statistics from a resilient execution.

    Attributes:
        success: Whether operation succeeded
        retry_result: Result from retry policy
        rate_limit_wait_ms: Time spent waiting for rate limit
        circuit_state: Current circuit breaker state
        inflight_at_start: In-flight count at execution start
    """

    success: bool
    retry_result: RetryResult | None = None
    rate_limit_wait_ms: float = 0.0
    circuit_state: str = "unknown"
    inflight_at_start: int = 0


class ResilientExecutor:
    """Executor combining all resilience patterns.

    Executes operations with:
    1. Backpressure control (concurrency limiting)
    2. Rate limiting
    3. Circuit breaker
    4. Retry with exponential backoff

    Example:
        >>> config = ResilientConfig.production()
        >>> executor = ResilientExecutor(config)
        >>> result = await executor.execute(async_operation)
    """

    def __init__(
        self,
        config: ResilientConfig | None = None,
        name: str = "default",
    ) -> None:
        """Initialize resilient executor.

        Args:
            config: Combined resilience configuration
            name: Identifier for this executor
        """
        self._config = config or ResilientConfig()
        self._name = name

        # Initialize components
        self._retry = (
            RetryPolicy(self._config.retry) if self._config.retry else None
        )
        self._rate_limiter = (
            RateLimiter(self._config.rate_limit)
            if self._config.rate_limit
            else None
        )
        self._circuit_breaker = (
            CircuitBreaker(self._config.circuit_breaker)
            if self._config.circuit_breaker
            else None
        )
        self._backpressure = (
            Backpressure(self._config.backpressure)
            if self._config.backpressure
            else None
        )

    @property
    def name(self) -> str:
        """Get executor name."""
        return self._name

    @property
    def circuit_state(self) -> str:
        """Get current circuit breaker state."""
        if self._circuit_breaker:
            return self._circuit_breaker.state.value
        return "disabled"

    @property
    def current_inflight(self) -> int:
        """Get current in-flight count."""
        if self._backpressure:
            return self._backpressure.current_inflight
        return 0

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ) -> T:
        """Execute an operation with all resilience patterns.

        Args:
            operation: Async operation to execute
            on_retry: Optional callback on retry

        Returns:
            Operation result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Original exception if all retries fail
        """
        # 1. Backpressure control
        if self._backpressure:
            async with self._backpressure.acquire():
                return await self._execute_inner(operation, on_retry)
        else:
            return await self._execute_inner(operation, on_retry)

    async def _execute_inner(
        self,
        operation: Callable[[], Awaitable[T]],
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ) -> T:
        """Execute with rate limiting, circuit breaker, and retry.

        Args:
            operation: Async operation
            on_retry: Retry callback

        Returns:
            Operation result
        """
        # 2. Rate limiting
        if self._rate_limiter:
            await self._rate_limiter.acquire()

        # 3. Circuit breaker + 4. Retry
        if self._circuit_breaker:
            return await self._circuit_breaker.execute(
                lambda: self._execute_with_retry(operation, on_retry)
            )
        else:
            return await self._execute_with_retry(operation, on_retry)

    async def _execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ) -> T:
        """Execute with retry.

        Args:
            operation: Async operation
            on_retry: Retry callback

        Returns:
            Operation result
        """
        if self._retry:
            result = await self._retry.execute(operation, on_retry)
            if result.success:
                return result.value
            raise result.error  # type: ignore
        else:
            return await operation()

    async def execute_with_stats(
        self,
        operation: Callable[[], Awaitable[T]],
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ) -> tuple[T, ExecutionStats]:
        """Execute and return execution statistics.

        Args:
            operation: Async operation
            on_retry: Retry callback

        Returns:
            Tuple of (result, stats)
        """
        stats = ExecutionStats(
            success=False,
            circuit_state=self.circuit_state,
            inflight_at_start=self.current_inflight,
        )

        try:
            # 1. Backpressure
            if self._backpressure:
                async with self._backpressure.acquire():
                    result = await self._execute_inner_with_stats(
                        operation, on_retry, stats
                    )
            else:
                result = await self._execute_inner_with_stats(
                    operation, on_retry, stats
                )

            stats.success = True
            return result, stats

        except Exception:
            stats.success = False
            raise

    async def _execute_inner_with_stats(
        self,
        operation: Callable[[], Awaitable[T]],
        on_retry: Callable[[int, Exception, float], None] | None,
        stats: ExecutionStats,
    ) -> T:
        """Execute with stats collection.

        Args:
            operation: Async operation
            on_retry: Retry callback
            stats: Stats object to populate

        Returns:
            Operation result
        """
        # Rate limiting
        if self._rate_limiter:
            wait_time = await self._rate_limiter.acquire()
            stats.rate_limit_wait_ms = wait_time * 1000

        # Circuit breaker + Retry
        async def inner() -> T:
            if self._retry:
                result = await self._retry.execute(operation, on_retry)
                stats.retry_result = result
                if result.success:
                    return result.value
                raise result.error  # type: ignore
            return await operation()

        if self._circuit_breaker:
            stats.circuit_state = self._circuit_breaker.state.value
            return await self._circuit_breaker.execute(inner)
        else:
            return await inner()

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics from all components.

        Returns:
            Dict with component statistics
        """
        stats: dict[str, Any] = {"name": self._name}

        if self._rate_limiter:
            stats["rate_limiter"] = {
                "available_tokens": self._rate_limiter.available_tokens,
                "is_limited": self._rate_limiter.is_limited,
            }

        if self._circuit_breaker:
            cb_stats = self._circuit_breaker.get_stats()
            stats["circuit_breaker"] = {
                "state": self._circuit_breaker.state.value,
                "total_requests": cb_stats.total_requests,
                "failed_requests": cb_stats.failed_requests,
                "rejected_requests": cb_stats.rejected_requests,
            }

        if self._backpressure:
            stats["backpressure"] = self._backpressure.get_stats()

        return stats

    def reset(self) -> None:
        """Reset all components to initial state."""
        if self._circuit_breaker:
            self._circuit_breaker.reset()
