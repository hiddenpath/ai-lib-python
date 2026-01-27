"""Tests for resilience module."""

import asyncio

import pytest

from ai_lib_python.errors import ErrorClass, RemoteError
from ai_lib_python.resilience import (
    AdaptiveRateLimiter,
    Backpressure,
    BackpressureConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    FallbackChain,
    FallbackConfig,
    JitterStrategy,
    RateLimiter,
    RateLimiterConfig,
    ResilientConfig,
    ResilientExecutor,
    RetryConfig,
    RetryPolicy,
    with_retry,
)


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_default_config(self) -> None:
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.min_delay_ms == 1000
        assert config.max_delay_ms == 60000
        assert config.jitter == JitterStrategy.FULL

    def test_no_retry_config(self) -> None:
        """Test no-retry configuration."""
        config = RetryConfig.no_retry()
        assert config.max_retries == 0

    def test_from_protocol(self) -> None:
        """Test creating config from protocol."""
        protocol_config = {
            "max_retries": 5,
            "min_delay_ms": 2000,
            "jitter": "equal",
        }
        config = RetryConfig.from_protocol(protocol_config)
        assert config.max_retries == 5
        assert config.min_delay_ms == 2000
        assert config.jitter == JitterStrategy.EQUAL

    def test_calculate_delay_exponential(self) -> None:
        """Test exponential backoff calculation."""
        config = RetryConfig(
            min_delay_ms=1000,
            max_delay_ms=60000,
            jitter=JitterStrategy.NONE,
        )
        policy = RetryPolicy(config)

        # Attempt 0: 1000ms
        assert policy.calculate_delay(0) == 1.0
        # Attempt 1: 2000ms
        assert policy.calculate_delay(1) == 2.0
        # Attempt 2: 4000ms
        assert policy.calculate_delay(2) == 4.0

    def test_calculate_delay_respects_max(self) -> None:
        """Test that delay is capped at max."""
        config = RetryConfig(
            min_delay_ms=1000,
            max_delay_ms=5000,
            jitter=JitterStrategy.NONE,
        )
        policy = RetryPolicy(config)

        # Attempt 10: would be huge, but capped at 5000ms
        assert policy.calculate_delay(10) == 5.0

    def test_calculate_delay_respects_retry_after(self) -> None:
        """Test that retry-after hint is respected."""
        policy = RetryPolicy(RetryConfig())
        assert policy.calculate_delay(0, retry_after=10.0) == 10.0

    def test_should_retry_max_retries(self) -> None:
        """Test that max retries is enforced."""
        config = RetryConfig(max_retries=2)
        policy = RetryPolicy(config)

        error = RemoteError(
            "Rate limited",
            status_code=429,
            error_class=ErrorClass.RATE_LIMITED,
        )

        assert policy.should_retry(error, 0) is True
        assert policy.should_retry(error, 1) is True
        assert policy.should_retry(error, 2) is False

    def test_should_retry_error_class(self) -> None:
        """Test retry based on error class."""
        policy = RetryPolicy(RetryConfig())

        # Retryable errors
        rate_limited = RemoteError(
            "Rate limited",
            status_code=429,
            error_class=ErrorClass.RATE_LIMITED,
        )
        assert policy.should_retry(rate_limited, 0) is True

        # Non-retryable errors
        auth_error = RemoteError(
            "Unauthorized",
            status_code=401,
            error_class=ErrorClass.AUTHENTICATION,
        )
        assert policy.should_retry(auth_error, 0) is False

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful execution."""
        policy = RetryPolicy(RetryConfig())

        async def success_op() -> str:
            return "success"

        result = await policy.execute(success_op)
        assert result.success is True
        assert result.value == "success"
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self) -> None:
        """Test execution with retries then success."""
        policy = RetryPolicy(RetryConfig(min_delay_ms=10))
        attempts = [0]

        async def flaky_op() -> str:
            attempts[0] += 1
            if attempts[0] < 3:
                raise RemoteError(
                    "Server error",
                    status_code=500,
                    error_class=ErrorClass.SERVER_ERROR,
                )
            return "success"

        result = await policy.execute(flaky_op)
        assert result.success is True
        assert result.value == "success"
        assert result.attempts == 3

    @pytest.mark.asyncio
    async def test_execute_all_retries_fail(self) -> None:
        """Test execution when all retries fail."""
        policy = RetryPolicy(RetryConfig(max_retries=2, min_delay_ms=10))

        async def always_fail() -> str:
            raise RemoteError(
                "Server error",
                status_code=500,
                error_class=ErrorClass.SERVER_ERROR,
            )

        result = await policy.execute(always_fail)
        assert result.success is False
        assert result.attempts == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_with_retry_function(self) -> None:
        """Test with_retry helper function."""
        async def success_op() -> str:
            return "success"

        result = await with_retry(success_op)
        assert result == "success"


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_unlimited_config(self) -> None:
        """Test unlimited rate limiter."""
        config = RateLimiterConfig.unlimited()
        limiter = RateLimiter(config)
        assert limiter.is_limited is False

    def test_from_rps(self) -> None:
        """Test creating config from RPS."""
        config = RateLimiterConfig.from_rps(10)
        assert config.requests_per_second == 10
        assert config.burst_size == 15  # 10 * 1.5

    def test_from_rpm(self) -> None:
        """Test creating config from RPM."""
        config = RateLimiterConfig.from_rpm(60)
        assert config.requests_per_second == 1.0

    @pytest.mark.asyncio
    async def test_acquire_unlimited(self) -> None:
        """Test acquiring from unlimited limiter."""
        limiter = RateLimiter(RateLimiterConfig.unlimited())
        wait = await limiter.acquire()
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_try_acquire(self) -> None:
        """Test try_acquire without waiting."""
        config = RateLimiterConfig.from_rps(10, burst_multiplier=1.0)
        limiter = RateLimiter(config)

        # Should succeed initially
        assert await limiter.try_acquire() is True

    @pytest.mark.asyncio
    async def test_acquire_waits_when_needed(self) -> None:
        """Test that acquire waits when tokens depleted."""
        config = RateLimiterConfig(
            requests_per_second=100,  # Fast for testing
            burst_size=1,
            initial_tokens=0,  # Start empty
        )
        limiter = RateLimiter(config)

        # Should wait since no tokens
        wait = await limiter.acquire()
        assert wait > 0


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""

    def test_update_from_headers(self) -> None:
        """Test updating from response headers."""
        limiter = AdaptiveRateLimiter()

        headers = {
            "x-ratelimit-limit-requests": "100",
            "x-ratelimit-remaining-requests": "50",
        }
        limiter.update_from_headers(headers)

        state = limiter.get_server_state()
        assert state["limit"] == 100
        assert state["remaining"] == 50


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self) -> None:
        """Test initial state is closed."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self) -> None:
        """Test that success keeps circuit closed."""
        breaker = CircuitBreaker()

        async def success_op() -> str:
            return "success"

        result = await breaker.execute(success_op)
        assert result == "success"
        assert breaker.is_closed is True

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self) -> None:
        """Test that failures open the circuit."""
        config = CircuitBreakerConfig(failure_threshold=3, cooldown_seconds=60)
        breaker = CircuitBreaker(config)

        async def fail_op() -> str:
            raise Exception("error")

        # Cause failures
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute(fail_op)

        assert breaker.is_open is True

    @pytest.mark.asyncio
    async def test_open_circuit_rejects(self) -> None:
        """Test that open circuit rejects requests."""
        config = CircuitBreakerConfig(failure_threshold=1, cooldown_seconds=60)
        breaker = CircuitBreaker(config)

        async def fail_op() -> str:
            raise Exception("error")

        # Trip the circuit
        with pytest.raises(Exception):
            await breaker.execute(fail_op)

        assert breaker.is_open is True

        # Next request should be rejected
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.execute(fail_op)

        assert exc_info.value.time_until_retry is not None

    @pytest.mark.asyncio
    async def test_half_open_after_cooldown(self) -> None:
        """Test transition to half-open after cooldown."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0.1,  # Very short for testing
        )
        breaker = CircuitBreaker(config)

        async def fail_op() -> str:
            raise Exception("error")

        # Trip the circuit
        with pytest.raises(Exception):
            await breaker.execute(fail_op)

        assert breaker.is_open is True

        # Wait for cooldown
        await asyncio.sleep(0.15)

        # Next call should transition to half-open
        async def success_op() -> str:
            return "success"

        result = await breaker.execute(success_op)
        assert result == "success"

    def test_reset(self) -> None:
        """Test resetting the circuit."""
        breaker = CircuitBreaker()
        breaker._failure_count = 10
        breaker._state = CircuitState.OPEN

        breaker.reset()

        assert breaker.is_closed is True
        assert breaker._failure_count == 0

    def test_get_stats(self) -> None:
        """Test getting circuit statistics."""
        breaker = CircuitBreaker()
        stats = breaker.get_stats()

        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0


class TestBackpressure:
    """Tests for Backpressure."""

    def test_unlimited_config(self) -> None:
        """Test unlimited backpressure."""
        config = BackpressureConfig.unlimited()
        bp = Backpressure(config)
        assert bp.is_limited is False

    @pytest.mark.asyncio
    async def test_acquire_release(self) -> None:
        """Test acquiring and releasing permits."""
        config = BackpressureConfig(max_concurrent=2)
        bp = Backpressure(config)

        async with bp.acquire():
            assert bp.current_inflight == 1

        assert bp.current_inflight == 0

    @pytest.mark.asyncio
    async def test_concurrent_limit(self) -> None:
        """Test that concurrent limit is enforced."""
        config = BackpressureConfig(max_concurrent=2, queue_timeout=0.1)
        bp = Backpressure(config)

        acquired = []

        async def acquire_permit(idx: int) -> None:
            async with bp.acquire():
                acquired.append(idx)
                await asyncio.sleep(0.2)

        # Start 3 tasks with only 2 permits
        tasks = [
            asyncio.create_task(acquire_permit(0)),
            asyncio.create_task(acquire_permit(1)),
            asyncio.create_task(acquire_permit(2)),
        ]

        # Wait a bit for tasks to start
        await asyncio.sleep(0.05)

        # Only 2 should be in flight
        assert bp.current_inflight == 2

        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)

    def test_get_stats(self) -> None:
        """Test getting backpressure statistics."""
        bp = Backpressure(BackpressureConfig(max_concurrent=5))
        stats = bp.get_stats()

        assert stats["max_concurrent"] == 5
        assert stats["current_inflight"] == 0


class TestFallbackChain:
    """Tests for FallbackChain."""

    @pytest.mark.asyncio
    async def test_first_target_succeeds(self) -> None:
        """Test when first target succeeds."""
        chain = FallbackChain()

        async def primary() -> str:
            return "primary"

        async def secondary() -> str:
            return "secondary"

        chain.add_target("primary", primary)
        chain.add_target("secondary", secondary)

        result = await chain.execute()
        assert result.success is True
        assert result.value == "primary"
        assert result.target_used == "primary"

    @pytest.mark.asyncio
    async def test_fallback_to_secondary(self) -> None:
        """Test falling back to secondary target."""
        chain = FallbackChain()

        async def primary() -> str:
            raise RemoteError(
                "Server error",
                status_code=500,
                error_class=ErrorClass.SERVER_ERROR,
            )

        async def secondary() -> str:
            return "secondary"

        chain.add_target("primary", primary)
        chain.add_target("secondary", secondary)

        result = await chain.execute()
        assert result.success is True
        assert result.value == "secondary"
        assert result.target_used == "secondary"
        assert "primary" in result.errors

    @pytest.mark.asyncio
    async def test_all_targets_fail(self) -> None:
        """Test when all targets fail."""
        chain = FallbackChain()

        async def fail() -> str:
            raise RemoteError(
                "Error",
                status_code=500,
                error_class=ErrorClass.SERVER_ERROR,
            )

        chain.add_target("target1", fail)
        chain.add_target("target2", fail)

        result = await chain.execute()
        assert result.success is False
        assert len(result.errors) == 2

    def test_target_management(self) -> None:
        """Test adding and removing targets."""
        chain = FallbackChain()

        async def op() -> str:
            return "result"

        chain.add_target("target1", op)
        chain.add_target("target2", op)

        assert chain.get_targets() == ["target1", "target2"]

        chain.remove_target("target1")
        assert chain.get_targets() == ["target2"]

    def test_enable_disable_target(self) -> None:
        """Test enabling and disabling targets."""
        chain = FallbackChain()

        async def op() -> str:
            return "result"

        chain.add_target("target1", op)
        assert chain.get_targets() == ["target1"]

        chain.set_enabled("target1", False)
        assert chain.get_targets() == []

        chain.set_enabled("target1", True)
        assert chain.get_targets() == ["target1"]


class TestResilientExecutor:
    """Tests for ResilientExecutor."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = ResilientConfig.default()
        assert config.retry is not None
        assert config.rate_limit is not None

    def test_production_config(self) -> None:
        """Test production configuration."""
        config = ResilientConfig.production()
        assert config.retry is not None
        assert config.retry.max_retries == 3
        assert config.circuit_breaker is not None

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful execution through executor."""
        config = ResilientConfig.minimal()
        executor = ResilientExecutor(config)

        async def success_op() -> str:
            return "success"

        result = await executor.execute(success_op)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry(self) -> None:
        """Test execution with retry."""
        config = ResilientConfig(
            retry=RetryConfig(max_retries=2, min_delay_ms=10)
        )
        executor = ResilientExecutor(config)

        attempts = [0]

        async def flaky_op() -> str:
            attempts[0] += 1
            if attempts[0] < 2:
                raise RemoteError(
                    "Error",
                    status_code=500,
                    error_class=ErrorClass.SERVER_ERROR,
                )
            return "success"

        result = await executor.execute(flaky_op)
        assert result == "success"
        assert attempts[0] == 2

    @pytest.mark.asyncio
    async def test_execute_with_stats(self) -> None:
        """Test execution with statistics."""
        config = ResilientConfig.minimal()
        executor = ResilientExecutor(config)

        async def success_op() -> str:
            return "success"

        result, stats = await executor.execute_with_stats(success_op)
        assert result == "success"
        assert stats.success is True

    def test_get_stats(self) -> None:
        """Test getting executor statistics."""
        config = ResilientConfig.production()
        executor = ResilientExecutor(config, name="test")

        stats = executor.get_stats()
        assert stats["name"] == "test"
        assert "circuit_breaker" in stats
        assert "backpressure" in stats
