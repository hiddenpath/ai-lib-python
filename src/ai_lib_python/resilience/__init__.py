"""
Resilience layer - Retry, rate limiting, circuit breaker, and backpressure.

This module provides production-ready resilience patterns:
- RetryPolicy: Exponential backoff with jitter
- RateLimiter: Token bucket algorithm with adaptive mode
- CircuitBreaker: Closed/Open/Half-Open state machine
- Backpressure: Semaphore-based concurrency control
- FallbackChain: Multi-model degradation
- ResilientExecutor: Unified executor combining all patterns
"""

from ai_lib_python.resilience.backpressure import Backpressure, BackpressureConfig
from ai_lib_python.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    CircuitStats,
)
from ai_lib_python.resilience.executor import (
    ExecutionStats,
    ResilientConfig,
    ResilientExecutor,
)
from ai_lib_python.resilience.fallback import (
    FallbackChain,
    FallbackConfig,
    FallbackResult,
    FallbackTarget,
    MultiFallback,
)
from ai_lib_python.resilience.rate_limiter import (
    AdaptiveRateLimiter,
    RateLimiter,
    RateLimiterConfig,
)
from ai_lib_python.resilience.retry import (
    JitterStrategy,
    RetryConfig,
    RetryPolicy,
    RetryResult,
    with_retry,
)

__all__ = [
    # Rate limiting
    "AdaptiveRateLimiter",
    # Backpressure
    "Backpressure",
    "BackpressureConfig",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
    "CircuitStats",
    # Executor
    "ExecutionStats",
    # Fallback
    "FallbackChain",
    "FallbackConfig",
    "FallbackResult",
    "FallbackTarget",
    # Retry
    "JitterStrategy",
    "MultiFallback",
    "RateLimiter",
    "RateLimiterConfig",
    "ResilientConfig",
    "ResilientExecutor",
    "RetryConfig",
    "RetryPolicy",
    "RetryResult",
    "with_retry",
]
