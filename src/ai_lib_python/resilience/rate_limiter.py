"""
Rate limiter using token bucket algorithm.

Provides both static and adaptive rate limiting based on provider response headers.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter.

    Attributes:
        requests_per_second: Maximum requests per second (0 = unlimited)
        burst_size: Maximum burst size (tokens in bucket)
        initial_tokens: Initial tokens in bucket
    """

    requests_per_second: float = 0.0
    burst_size: int | None = None
    initial_tokens: int | None = None

    @classmethod
    def from_rps(cls, rps: float, burst_multiplier: float = 1.5) -> RateLimiterConfig:
        """Create config from requests per second.

        Args:
            rps: Requests per second
            burst_multiplier: Multiplier for burst size

        Returns:
            RateLimiterConfig instance
        """
        burst = int(rps * burst_multiplier) if rps > 0 else None
        return cls(
            requests_per_second=rps,
            burst_size=burst,
            initial_tokens=burst,
        )

    @classmethod
    def from_rpm(cls, rpm: float, burst_multiplier: float = 1.5) -> RateLimiterConfig:
        """Create config from requests per minute.

        Args:
            rpm: Requests per minute
            burst_multiplier: Multiplier for burst size

        Returns:
            RateLimiterConfig instance
        """
        return cls.from_rps(rpm / 60.0, burst_multiplier)

    @classmethod
    def unlimited(cls) -> RateLimiterConfig:
        """Create an unlimited rate limiter config."""
        return cls(requests_per_second=0.0)


class RateLimiter:
    """Token bucket rate limiter.

    Implements the token bucket algorithm for rate limiting:
    - Tokens are added at a fixed rate
    - Requests consume tokens
    - If no tokens available, requests wait

    Example:
        >>> limiter = RateLimiter(RateLimiterConfig.from_rps(10))
        >>> await limiter.acquire()  # Wait if needed
        >>> # Make request
    """

    def __init__(self, config: RateLimiterConfig | None = None) -> None:
        """Initialize rate limiter.

        Args:
            config: Rate limiter configuration
        """
        self._config = config or RateLimiterConfig()
        self._lock = asyncio.Lock()

        # Token bucket state
        self._tokens = float(
            self._config.initial_tokens
            if self._config.initial_tokens is not None
            else (self._config.burst_size or 1)
        )
        self._max_tokens = float(self._config.burst_size or 1)
        self._last_refill = time.monotonic()

        # Rate (tokens per second)
        self._rate = self._config.requests_per_second

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        if self._rate <= 0:
            return

        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        # Add tokens based on elapsed time
        new_tokens = elapsed * self._rate
        self._tokens = min(self._tokens + new_tokens, self._max_tokens)

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Wait time in seconds (0 if no wait)
        """
        if self._rate <= 0:
            return 0.0  # Unlimited

        async with self._lock:
            self._refill()

            wait_time = 0.0

            if self._tokens < tokens:
                # Calculate wait time
                deficit = tokens - self._tokens
                wait_time = deficit / self._rate

                # Wait for tokens
                await asyncio.sleep(wait_time)
                self._refill()

            # Consume tokens
            self._tokens -= tokens
            return wait_time

    async def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False if would need to wait
        """
        if self._rate <= 0:
            return True  # Unlimited

        async with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get estimated wait time without acquiring.

        Args:
            tokens: Number of tokens needed

        Returns:
            Estimated wait time in seconds
        """
        if self._rate <= 0:
            return 0.0

        self._refill()

        if self._tokens >= tokens:
            return 0.0

        deficit = tokens - self._tokens
        return deficit / self._rate

    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        self._refill()
        return self._tokens

    @property
    def is_limited(self) -> bool:
        """Check if rate limiting is enabled."""
        return self._rate > 0


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on server responses.

    Monitors rate limit headers from API responses and adjusts
    the rate limit dynamically.

    Example:
        >>> limiter = AdaptiveRateLimiter()
        >>> await limiter.acquire()
        >>> response = await make_request()
        >>> limiter.update_from_headers(response.headers)
    """

    def __init__(
        self,
        config: RateLimiterConfig | None = None,
        header_config: dict[str, str] | None = None,
    ) -> None:
        """Initialize adaptive rate limiter.

        Args:
            config: Base rate limiter configuration
            header_config: Mapping of header names for rate limit info
        """
        super().__init__(config)
        self._header_config = header_config or {}

        # Adaptive state
        self._server_limit: int | None = None
        self._server_remaining: int | None = None
        self._server_reset: float | None = None

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """Update rate limit state from response headers.

        Args:
            headers: Response headers
        """
        # Extract limit
        limit_header = self._header_config.get(
            "requests_limit", "x-ratelimit-limit-requests"
        )
        if limit_header in headers:
            try:
                self._server_limit = int(headers[limit_header])
            except ValueError:
                pass

        # Extract remaining
        remaining_header = self._header_config.get(
            "requests_remaining", "x-ratelimit-remaining-requests"
        )
        if remaining_header in headers:
            try:
                self._server_remaining = int(headers[remaining_header])
                # Update tokens to match server state
                if self._server_remaining is not None:
                    self._tokens = float(self._server_remaining)
            except ValueError:
                pass

        # Extract reset time
        reset_header = self._header_config.get("requests_reset")
        if reset_header and reset_header in headers:
            try:
                # May be seconds or timestamp
                reset_value = headers[reset_header]
                if "s" in reset_value or "m" in reset_value:
                    # Parse duration like "1s" or "1m"
                    reset_value = reset_value.rstrip("sm")
                    self._server_reset = float(reset_value)
                else:
                    self._server_reset = float(reset_value)
            except ValueError:
                pass

        # Adjust rate based on server limit
        if (
            self._server_limit is not None
            and self._server_reset is not None
            and self._server_reset > 0
        ):
            self._rate = self._server_limit / self._server_reset
            self._max_tokens = float(self._server_limit)

    def get_server_state(self) -> dict[str, Any]:
        """Get current server-reported rate limit state.

        Returns:
            Dict with limit, remaining, and reset values
        """
        return {
            "limit": self._server_limit,
            "remaining": self._server_remaining,
            "reset": self._server_reset,
        }
