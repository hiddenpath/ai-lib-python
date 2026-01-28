"""
Resilience layer - Retry, rate limiting, circuit breaker, and backpressure.

This module provides production-ready resilience patterns:
- RetryPolicy: Exponential backoff with jitter
- RateLimiter: Token bucket algorithm with adaptive mode
- CircuitBreaker: Closed/Open/Half-Open state machine
- Backpressure: Semaphore-based concurrency control
- FallbackChain: Multi-model degradation
- ResilientExecutor: Unified executor combining all patterns
- SignalsSnapshot: Unified runtime state aggregation
- PreflightChecker: Unified request gating
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
from ai_lib_python.resilience.preflight import (
    PreflightChecker,
    PreflightConfig,
    PreflightContext,
    PreflightError,
    PreflightResult,
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
from ai_lib_python.resilience.signals import (
    CircuitBreakerSnapshot,
    InflightSnapshot,
    RateLimiterSnapshot,
    SignalsSnapshot,
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
    "CircuitBreakerSnapshot",
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
    # Signals
    "InflightSnapshot",
    # Retry
    "JitterStrategy",
    "MultiFallback",
    # Preflight
    "PreflightChecker",
    "PreflightConfig",
    "PreflightContext",
    "PreflightError",
    "PreflightResult",
    "RateLimiter",
    "RateLimiterConfig",
    "RateLimiterSnapshot",
    "ResilientConfig",
    "ResilientExecutor",
    "RetryConfig",
    "RetryPolicy",
    "RetryResult",
    "SignalsSnapshot",
    "with_retry",
]
