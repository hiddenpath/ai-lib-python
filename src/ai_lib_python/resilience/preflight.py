"""
Preflight checks and unified request gating.

Provides unified preflight validation before request execution.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ai_lib_python.errors import AiLibError
from ai_lib_python.resilience.signals import SignalsSnapshot

if TYPE_CHECKING:
    from ai_lib_python.resilience.backpressure import BackpressureController
    from ai_lib_python.resilience.circuit_breaker import CircuitBreaker
    from ai_lib_python.resilience.rate_limiter import RateLimiter


class PreflightError(AiLibError):
    """Error raised when preflight check fails."""

    def __init__(
        self,
        message: str,
        component: str,
        retryable: bool = True,
        retry_after_ms: int | None = None,
    ) -> None:
        """Initialize preflight error.

        Args:
            message: Error message
            component: Component that failed (rate_limiter, circuit_breaker, backpressure)
            retryable: Whether the request can be retried
            retry_after_ms: Suggested retry delay in milliseconds
        """
        super().__init__(message)
        self.component = component
        self.retryable = retryable
        self.retry_after_ms = retry_after_ms


@dataclass
class PreflightResult:
    """Result of preflight checks.

    Attributes:
        passed: Whether all checks passed
        permit: Backpressure permit (if acquired)
        signals: Current signals snapshot
        errors: List of failed checks
    """

    passed: bool = True
    permit: Any = None
    signals: SignalsSnapshot | None = None
    errors: list[PreflightError] = field(default_factory=list)

    def release_permit(self) -> None:
        """Release the backpressure permit if held."""
        if self.permit is not None:
            # Permit is typically an asyncio.Semaphore release
            try:
                self.permit.release()
            except (ValueError, RuntimeError):
                pass
            self.permit = None


@dataclass
class PreflightConfig:
    """Configuration for preflight checks.

    Attributes:
        check_rate_limiter: Whether to check rate limiter
        check_circuit_breaker: Whether to check circuit breaker
        check_backpressure: Whether to check backpressure
        fail_fast: Whether to fail immediately on first failure
        timeout_ms: Timeout for acquiring permits
    """

    check_rate_limiter: bool = True
    check_circuit_breaker: bool = True
    check_backpressure: bool = True
    fail_fast: bool = True
    timeout_ms: float = 30000.0


class PreflightChecker:
    """Unified preflight checker for requests.

    Performs rate limiter, circuit breaker, and backpressure checks
    before allowing a request to proceed.

    Example:
        >>> checker = PreflightChecker(
        ...     rate_limiter=rate_limiter,
        ...     circuit_breaker=circuit_breaker,
        ...     backpressure=backpressure_controller,
        ... )
        >>>
        >>> result = await checker.check()
        >>> if result.passed:
        ...     try:
        ...         response = await make_request()
        ...     finally:
        ...         result.release_permit()
        >>> else:
        ...     for error in result.errors:
        ...         print(f"Failed: {error.component}: {error}")
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        backpressure: BackpressureController | None = None,
        config: PreflightConfig | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize preflight checker.

        Args:
            rate_limiter: Optional rate limiter
            circuit_breaker: Optional circuit breaker
            backpressure: Optional backpressure controller
            config: Preflight configuration
            provider: Provider identifier for signals
            model: Model identifier for signals
        """
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._backpressure = backpressure
        self._config = config or PreflightConfig()
        self._provider = provider
        self._model = model

    async def check(self) -> PreflightResult:
        """Perform all preflight checks.

        Returns:
            PreflightResult with check status and permit
        """
        result = PreflightResult()
        errors: list[PreflightError] = []

        # 1. Check circuit breaker (fast fail)
        if self._config.check_circuit_breaker and self._circuit_breaker:
            try:
                if not self._circuit_breaker.allow():
                    cooldown = None
                    if self._circuit_breaker._last_failure:
                        import time

                        elapsed = time.time() - self._circuit_breaker._last_failure
                        remaining = (
                            self._circuit_breaker.config.cooldown_seconds - elapsed
                        )
                        if remaining > 0:
                            cooldown = int(remaining * 1000)

                    error = PreflightError(
                        "Circuit breaker is open",
                        "circuit_breaker",
                        retryable=True,
                        retry_after_ms=cooldown,
                    )
                    errors.append(error)
                    if self._config.fail_fast:
                        result.passed = False
                        result.errors = errors
                        return result
            except Exception as e:
                errors.append(
                    PreflightError(f"Circuit breaker check failed: {e}", "circuit_breaker")
                )
                if self._config.fail_fast:
                    result.passed = False
                    result.errors = errors
                    return result

        # 2. Check rate limiter
        if self._config.check_rate_limiter and self._rate_limiter:
            try:
                allowed = await self._rate_limiter.acquire()
                if not allowed:
                    error = PreflightError(
                        "Rate limit exceeded",
                        "rate_limiter",
                        retryable=True,
                        retry_after_ms=1000,  # Default 1s retry
                    )
                    errors.append(error)
                    if self._config.fail_fast:
                        result.passed = False
                        result.errors = errors
                        return result
            except Exception as e:
                errors.append(
                    PreflightError(f"Rate limiter check failed: {e}", "rate_limiter")
                )
                if self._config.fail_fast:
                    result.passed = False
                    result.errors = errors
                    return result

        # 3. Acquire backpressure permit
        if self._config.check_backpressure and self._backpressure:
            try:
                timeout = self._config.timeout_ms / 1000.0
                permit = await asyncio.wait_for(
                    self._backpressure.acquire(),
                    timeout=timeout,
                )
                if permit:
                    result.permit = permit
                else:
                    error = PreflightError(
                        "Backpressure limit reached",
                        "backpressure",
                        retryable=True,
                        retry_after_ms=100,
                    )
                    errors.append(error)
                    if self._config.fail_fast:
                        result.passed = False
                        result.errors = errors
                        return result
            except asyncio.TimeoutError:
                error = PreflightError(
                    "Backpressure permit timeout",
                    "backpressure",
                    retryable=True,
                    retry_after_ms=100,
                )
                errors.append(error)
                if self._config.fail_fast:
                    result.passed = False
                    result.errors = errors
                    return result
            except Exception as e:
                errors.append(
                    PreflightError(f"Backpressure check failed: {e}", "backpressure")
                )
                if self._config.fail_fast:
                    result.passed = False
                    result.errors = errors
                    return result

        # Generate signals snapshot
        result.signals = self.get_signals()
        result.errors = errors
        result.passed = len(errors) == 0

        return result

    def get_signals(self) -> SignalsSnapshot:
        """Get current signals snapshot.

        Returns:
            SignalsSnapshot with current state
        """
        inflight = None
        if self._backpressure:
            max_concurrent = self._backpressure.max_concurrent
            in_use = max_concurrent - self._backpressure.available
            inflight = (max_concurrent, in_use)

        return SignalsSnapshot.from_components(
            inflight=inflight,
            rate_limiter=self._rate_limiter,
            circuit_breaker=self._circuit_breaker,
            provider=self._provider,
            model=self._model,
        )

    def on_success(self) -> None:
        """Report successful request completion."""
        if self._circuit_breaker:
            self._circuit_breaker.on_success()

    def on_failure(self) -> None:
        """Report request failure."""
        if self._circuit_breaker:
            self._circuit_breaker.on_failure()

    async def update_rate_limits(self, headers: dict[str, str]) -> None:
        """Update rate limiter state from response headers.

        Args:
            headers: Response headers
        """
        if not self._rate_limiter:
            return

        # Common header patterns
        remaining_headers = [
            "x-ratelimit-remaining",
            "x-ratelimit-remaining-requests",
            "ratelimit-remaining",
        ]
        reset_headers = [
            "x-ratelimit-reset",
            "x-ratelimit-reset-requests",
            "ratelimit-reset",
            "retry-after",
        ]

        # Try to extract remaining count
        remaining = None
        for header in remaining_headers:
            value = headers.get(header) or headers.get(header.title())
            if value:
                try:
                    remaining = int(value)
                    break
                except ValueError:
                    continue

        # Try to extract reset time
        reset_after = None
        for header in reset_headers:
            value = headers.get(header) or headers.get(header.title())
            if value:
                try:
                    val = float(value)
                    # Check if it's an epoch timestamp or seconds
                    if val > 1_000_000_000:
                        import time

                        reset_after = val - time.time()
                    else:
                        reset_after = val
                    break
                except ValueError:
                    continue

        # Update rate limiter if we have useful info
        if remaining is not None or reset_after is not None:
            await self._rate_limiter.update_budget(remaining, reset_after)


class PreflightContext:
    """Context manager for preflight checks.

    Automatically releases permits on exit.

    Example:
        >>> async with PreflightContext(checker) as ctx:
        ...     if ctx.passed:
        ...         response = await make_request()
        ...         ctx.on_success()
        ...     else:
        ...         print(f"Preflight failed: {ctx.errors}")
    """

    def __init__(self, checker: PreflightChecker) -> None:
        """Initialize context.

        Args:
            checker: PreflightChecker instance
        """
        self._checker = checker
        self._result: PreflightResult | None = None

    async def __aenter__(self) -> PreflightContext:
        """Enter context and perform checks."""
        self._result = await self._checker.check()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context and release permit."""
        if self._result:
            self._result.release_permit()

            # Report outcome
            if exc_val is not None:
                self._checker.on_failure()
            elif self._result.passed:
                # Success is reported explicitly by caller
                pass

    @property
    def passed(self) -> bool:
        """Check if preflight passed."""
        return self._result.passed if self._result else False

    @property
    def signals(self) -> SignalsSnapshot | None:
        """Get signals snapshot."""
        return self._result.signals if self._result else None

    @property
    def errors(self) -> list[PreflightError]:
        """Get list of errors."""
        return self._result.errors if self._result else []

    def on_success(self) -> None:
        """Report successful completion."""
        self._checker.on_success()

    def on_failure(self) -> None:
        """Report failure."""
        self._checker.on_failure()
