"""
Resilience signals and snapshots.

Provides unified runtime state aggregation for orchestration decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_lib_python.resilience.circuit_breaker import CircuitBreaker
    from ai_lib_python.resilience.rate_limiter import RateLimiter


@dataclass
class InflightSnapshot:
    """Snapshot of in-flight request state.

    Attributes:
        max_concurrent: Maximum allowed concurrent requests
        available: Available slots
        in_use: Currently in use slots
    """

    max_concurrent: int
    available: int
    in_use: int

    @property
    def utilization(self) -> float:
        """Get utilization ratio (0.0 to 1.0)."""
        if self.max_concurrent == 0:
            return 0.0
        return self.in_use / self.max_concurrent

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_concurrent": self.max_concurrent,
            "available": self.available,
            "in_use": self.in_use,
            "utilization": self.utilization,
        }


@dataclass
class RateLimiterSnapshot:
    """Snapshot of rate limiter state.

    Attributes:
        tokens_available: Available tokens
        max_tokens: Maximum tokens (bucket capacity)
        refill_rate: Token refill rate per second
        is_throttled: Whether currently throttled
    """

    tokens_available: float
    max_tokens: float
    refill_rate: float
    is_throttled: bool = False

    @property
    def utilization(self) -> float:
        """Get utilization ratio (0.0 to 1.0)."""
        if self.max_tokens == 0:
            return 0.0
        return 1.0 - (self.tokens_available / self.max_tokens)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tokens_available": self.tokens_available,
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
            "is_throttled": self.is_throttled,
            "utilization": self.utilization,
        }


@dataclass
class CircuitBreakerSnapshot:
    """Snapshot of circuit breaker state.

    Attributes:
        state: Current state (closed, open, half_open)
        failure_count: Current failure count
        failure_threshold: Threshold for opening
        success_count: Successes in half-open state
        last_failure_time: Time of last failure
        cooldown_remaining_ms: Remaining cooldown in milliseconds
    """

    state: str
    failure_count: int
    failure_threshold: int
    success_count: int = 0
    last_failure_time: float | None = None
    cooldown_remaining_ms: float | None = None

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == "open"

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == "closed"

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == "half_open"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "cooldown_remaining_ms": self.cooldown_remaining_ms,
            "is_open": self.is_open,
        }


@dataclass
class SignalsSnapshot:
    """Unified snapshot of all resilience signals.

    This provides a lightweight, provider-agnostic view of runtime state
    for orchestration decisions. Applications can use these signals to
    implement custom selection/scoring strategies.

    Attributes:
        inflight: In-flight request state
        rate_limiter: Rate limiter state
        circuit_breaker: Circuit breaker state
        timestamp: Snapshot timestamp
        provider: Provider identifier
        model: Model identifier
    """

    inflight: InflightSnapshot | None = None
    rate_limiter: RateLimiterSnapshot | None = None
    circuit_breaker: CircuitBreakerSnapshot | None = None
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    provider: str | None = None
    model: str | None = None

    @property
    def is_healthy(self) -> bool:
        """Check if all signals indicate healthy state.

        Returns:
            True if:
            - Circuit breaker is not open
            - Rate limiter is not throttled
            - In-flight has available capacity
        """
        if self.circuit_breaker and self.circuit_breaker.is_open:
            return False
        if self.rate_limiter and self.rate_limiter.is_throttled:
            return False
        return not (self.inflight and self.inflight.available <= 0)

    @property
    def health_score(self) -> float:
        """Calculate a health score (0.0 to 1.0).

        Higher is better. Considers all available signals.
        """
        scores: list[float] = []

        # Circuit breaker contribution
        if self.circuit_breaker:
            if self.circuit_breaker.is_closed:
                scores.append(1.0)
            elif self.circuit_breaker.is_half_open:
                scores.append(0.5)
            else:
                scores.append(0.0)

        # Rate limiter contribution
        if self.rate_limiter:
            if self.rate_limiter.is_throttled:
                scores.append(0.0)
            else:
                scores.append(1.0 - self.rate_limiter.utilization)

        # In-flight contribution
        if self.inflight:
            scores.append(1.0 - self.inflight.utilization)

        if not scores:
            return 1.0

        return sum(scores) / len(scores)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "inflight": self.inflight.to_dict() if self.inflight else None,
            "rate_limiter": self.rate_limiter.to_dict() if self.rate_limiter else None,
            "circuit_breaker": (
                self.circuit_breaker.to_dict() if self.circuit_breaker else None
            ),
            "timestamp": self.timestamp,
            "provider": self.provider,
            "model": self.model,
            "is_healthy": self.is_healthy,
            "health_score": self.health_score,
        }

    @classmethod
    def from_components(
        cls,
        inflight: tuple[int, int] | None = None,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> SignalsSnapshot:
        """Create snapshot from resilience components.

        Args:
            inflight: Tuple of (max_concurrent, in_use)
            rate_limiter: RateLimiter instance
            circuit_breaker: CircuitBreaker instance
            provider: Provider identifier
            model: Model identifier

        Returns:
            SignalsSnapshot instance
        """
        inflight_snap = None
        if inflight:
            max_concurrent, in_use = inflight
            inflight_snap = InflightSnapshot(
                max_concurrent=max_concurrent,
                available=max_concurrent - in_use,
                in_use=in_use,
            )

        rate_snap = None
        if rate_limiter:
            rate_snap = RateLimiterSnapshot(
                tokens_available=rate_limiter.available_tokens,
                max_tokens=rate_limiter.config.bucket_size,
                refill_rate=rate_limiter.config.refill_rate,
                is_throttled=rate_limiter.available_tokens <= 0,
            )

        breaker_snap = None
        if circuit_breaker:
            import time

            cooldown = None
            if circuit_breaker.state.value == "open" and circuit_breaker._last_failure:
                elapsed = time.time() - circuit_breaker._last_failure
                remaining = circuit_breaker.config.cooldown_seconds - elapsed
                if remaining > 0:
                    cooldown = remaining * 1000

            breaker_snap = CircuitBreakerSnapshot(
                state=circuit_breaker.state.value,
                failure_count=circuit_breaker._failure_count,
                failure_threshold=circuit_breaker.config.failure_threshold,
                success_count=circuit_breaker._success_count,
                last_failure_time=circuit_breaker._last_failure,
                cooldown_remaining_ms=cooldown,
            )

        return cls(
            inflight=inflight_snap,
            rate_limiter=rate_snap,
            circuit_breaker=breaker_snap,
            provider=provider,
            model=model,
        )
