"""
Retry policy with exponential backoff and jitter.

Implements retry strategies aligned with AI-Protocol retry_policy specification.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from ai_lib_python.errors import ErrorClass, RemoteError, is_retryable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


class JitterStrategy(str, Enum):
    """Jitter strategy for retry delays."""

    NONE = "none"
    FULL = "full"
    EQUAL = "equal"


@dataclass
class RetryConfig:
    """Configuration for retry policy.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries)
        min_delay_ms: Minimum delay between retries in milliseconds
        max_delay_ms: Maximum delay between retries in milliseconds
        jitter: Jitter strategy (none, full, equal)
        retry_on_status: HTTP status codes to retry on
        retry_on_error_class: Error classes to retry on
    """

    max_retries: int = 3
    min_delay_ms: int = 1000
    max_delay_ms: int = 60000
    jitter: JitterStrategy = JitterStrategy.FULL
    retry_on_status: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    retry_on_error_class: set[ErrorClass] = field(
        default_factory=lambda: {
            ErrorClass.RATE_LIMITED,
            ErrorClass.TIMEOUT,
            ErrorClass.SERVER_ERROR,
            ErrorClass.OVERLOADED,
        }
    )
    exponential_base: float = 2.0

    @classmethod
    def from_protocol(cls, retry_policy: dict[str, Any] | None) -> RetryConfig:
        """Create config from protocol retry_policy.

        Args:
            retry_policy: Protocol retry_policy configuration

        Returns:
            RetryConfig instance
        """
        if not retry_policy:
            return cls()

        jitter_str = retry_policy.get("jitter", "full")
        jitter = JitterStrategy(jitter_str) if jitter_str in ("none", "full", "equal") else JitterStrategy.FULL

        retry_on_status = set(retry_policy.get("retry_on_http_status", [429, 500]))

        return cls(
            max_retries=retry_policy.get("max_retries", 3),
            min_delay_ms=retry_policy.get("min_delay_ms", 1000),
            max_delay_ms=retry_policy.get("max_delay_ms", 60000),
            jitter=jitter,
            retry_on_status=retry_on_status,
        )

    @classmethod
    def no_retry(cls) -> RetryConfig:
        """Create a config that disables retries."""
        return cls(max_retries=0)


@dataclass
class RetryResult:
    """Result of a retry operation.

    Attributes:
        success: Whether the operation succeeded
        value: The result value (if success)
        error: The last error (if failed)
        attempts: Number of attempts made
        total_delay_ms: Total delay from retries in milliseconds
    """

    success: bool
    value: Any = None
    error: Exception | None = None
    attempts: int = 0
    total_delay_ms: float = 0.0


class RetryPolicy:
    """Retry policy with exponential backoff and jitter.

    Implements exponential backoff algorithm with configurable jitter
    to prevent thundering herd problems.

    Example:
        >>> policy = RetryPolicy(RetryConfig(max_retries=3))
        >>> result = await policy.execute(async_operation)
        >>> if result.success:
        ...     print(result.value)
        ... else:
        ...     print(f"Failed after {result.attempts} attempts")
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize retry policy.

        Args:
            config: Retry configuration
        """
        self._config = config or RetryConfig()

    def calculate_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Calculate delay for a retry attempt.

        Args:
            attempt: Current attempt number (0-based)
            retry_after: Optional retry-after hint from server

        Returns:
            Delay in seconds
        """
        # If server provided retry-after, respect it
        if retry_after is not None and retry_after > 0:
            return retry_after

        # Calculate base exponential delay
        base_delay_ms = self._config.min_delay_ms * (
            self._config.exponential_base ** attempt
        )

        # Cap at max delay
        base_delay_ms = min(base_delay_ms, self._config.max_delay_ms)

        # Apply jitter
        if self._config.jitter == JitterStrategy.FULL:
            # Full jitter: random between 0 and base_delay
            delay_ms = random.uniform(0, base_delay_ms)
        elif self._config.jitter == JitterStrategy.EQUAL:
            # Equal jitter: base/2 + random(0, base/2)
            delay_ms = base_delay_ms / 2 + random.uniform(0, base_delay_ms / 2)
        else:
            # No jitter
            delay_ms = base_delay_ms

        return delay_ms / 1000.0  # Convert to seconds

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if an error should trigger a retry.

        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry
        """
        # Check max retries
        if attempt >= self._config.max_retries:
            return False

        # Check if error is retryable
        if isinstance(error, RemoteError):
            # Check error class
            if error.error_class in self._config.retry_on_error_class:
                return True

            # Check HTTP status
            if error.status_code in self._config.retry_on_status:
                return True

            # Check explicit retryable flag
            return error.retryable

        # For other errors, check if retryable by class
        if hasattr(error, "error_class"):
            return is_retryable(error.error_class)

        # Default: don't retry unknown errors
        return False

    def get_retry_after(self, error: Exception) -> float | None:
        """Get retry-after hint from error.

        Args:
            error: The exception

        Returns:
            Retry-after in seconds, or None
        """
        if isinstance(error, RemoteError):
            return error.retry_after
        return None

    async def execute(
        self,
        operation: Callable[[], Awaitable[T]],
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ) -> RetryResult:
        """Execute an operation with retry.

        Args:
            operation: Async operation to execute
            on_retry: Optional callback called before each retry

        Returns:
            RetryResult with success status and value/error
        """
        last_error: Exception | None = None
        total_delay = 0.0
        attempt = 0

        while True:
            try:
                result = await operation()
                return RetryResult(
                    success=True,
                    value=result,
                    attempts=attempt + 1,
                    total_delay_ms=total_delay * 1000,
                )
            except Exception as e:
                last_error = e
                attempt += 1

                if not self.should_retry(e, attempt - 1):
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempt,
                        total_delay_ms=total_delay * 1000,
                    )

                # Calculate delay
                retry_after = self.get_retry_after(e)
                delay = self.calculate_delay(attempt - 1, retry_after)
                total_delay += delay

                # Callback before retry
                if on_retry:
                    on_retry(attempt, e, delay)

                # Wait before retry
                await asyncio.sleep(delay)

        # Should never reach here
        return RetryResult(
            success=False,
            error=last_error,
            attempts=attempt,
            total_delay_ms=total_delay * 1000,
        )


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    """Execute an operation with retry, raising on failure.

    Args:
        operation: Async operation to execute
        config: Retry configuration
        on_retry: Optional callback called before each retry

    Returns:
        Operation result

    Raises:
        The last exception if all retries fail
    """
    policy = RetryPolicy(config)
    result = await policy.execute(operation, on_retry)

    if result.success:
        return result.value
    else:
        raise result.error  # type: ignore
