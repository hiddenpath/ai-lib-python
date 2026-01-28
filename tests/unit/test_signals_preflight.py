"""Tests for signals and preflight modules."""

import pytest

from ai_lib_python.resilience import (
    CircuitBreakerSnapshot,
    InflightSnapshot,
    PreflightChecker,
    PreflightConfig,
    PreflightError,
    PreflightResult,
    RateLimiterSnapshot,
    SignalsSnapshot,
)


class TestInflightSnapshot:
    """Tests for InflightSnapshot."""

    def test_utilization(self) -> None:
        """Test utilization calculation."""
        snapshot = InflightSnapshot(max_concurrent=10, available=3, in_use=7)
        assert snapshot.utilization == 0.7

    def test_zero_max(self) -> None:
        """Test utilization with zero max."""
        snapshot = InflightSnapshot(max_concurrent=0, available=0, in_use=0)
        assert snapshot.utilization == 0.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        snapshot = InflightSnapshot(max_concurrent=10, available=5, in_use=5)
        d = snapshot.to_dict()
        assert d["max_concurrent"] == 10
        assert d["in_use"] == 5
        assert d["utilization"] == 0.5


class TestRateLimiterSnapshot:
    """Tests for RateLimiterSnapshot."""

    def test_utilization(self) -> None:
        """Test utilization calculation."""
        snapshot = RateLimiterSnapshot(
            tokens_available=50.0,
            max_tokens=100.0,
            refill_rate=10.0,
        )
        assert snapshot.utilization == 0.5

    def test_is_throttled(self) -> None:
        """Test throttled state."""
        snapshot = RateLimiterSnapshot(
            tokens_available=0.0,
            max_tokens=100.0,
            refill_rate=10.0,
            is_throttled=True,
        )
        assert snapshot.is_throttled is True


class TestCircuitBreakerSnapshot:
    """Tests for CircuitBreakerSnapshot."""

    def test_state_checks(self) -> None:
        """Test state checking properties."""
        closed = CircuitBreakerSnapshot(
            state="closed", failure_count=0, failure_threshold=5
        )
        assert closed.is_closed is True
        assert closed.is_open is False
        assert closed.is_half_open is False

        open_state = CircuitBreakerSnapshot(
            state="open", failure_count=5, failure_threshold=5
        )
        assert open_state.is_open is True

        half_open = CircuitBreakerSnapshot(
            state="half_open", failure_count=5, failure_threshold=5
        )
        assert half_open.is_half_open is True


class TestSignalsSnapshot:
    """Tests for SignalsSnapshot."""

    def test_is_healthy_all_good(self) -> None:
        """Test healthy state with all components good."""
        snapshot = SignalsSnapshot(
            inflight=InflightSnapshot(max_concurrent=10, available=5, in_use=5),
            rate_limiter=RateLimiterSnapshot(
                tokens_available=50.0, max_tokens=100.0, refill_rate=10.0
            ),
            circuit_breaker=CircuitBreakerSnapshot(
                state="closed", failure_count=0, failure_threshold=5
            ),
        )
        assert snapshot.is_healthy is True

    def test_is_healthy_circuit_open(self) -> None:
        """Test unhealthy state with circuit open."""
        snapshot = SignalsSnapshot(
            circuit_breaker=CircuitBreakerSnapshot(
                state="open", failure_count=5, failure_threshold=5
            ),
        )
        assert snapshot.is_healthy is False

    def test_is_healthy_rate_limited(self) -> None:
        """Test unhealthy state when throttled."""
        snapshot = SignalsSnapshot(
            rate_limiter=RateLimiterSnapshot(
                tokens_available=0.0,
                max_tokens=100.0,
                refill_rate=10.0,
                is_throttled=True,
            ),
        )
        assert snapshot.is_healthy is False

    def test_is_healthy_no_capacity(self) -> None:
        """Test unhealthy state with no capacity."""
        snapshot = SignalsSnapshot(
            inflight=InflightSnapshot(max_concurrent=10, available=0, in_use=10),
        )
        assert snapshot.is_healthy is False

    def test_health_score(self) -> None:
        """Test health score calculation."""
        # Perfect health
        snapshot = SignalsSnapshot(
            inflight=InflightSnapshot(max_concurrent=10, available=10, in_use=0),
            rate_limiter=RateLimiterSnapshot(
                tokens_available=100.0, max_tokens=100.0, refill_rate=10.0
            ),
            circuit_breaker=CircuitBreakerSnapshot(
                state="closed", failure_count=0, failure_threshold=5
            ),
        )
        assert snapshot.health_score == 1.0

    def test_health_score_degraded(self) -> None:
        """Test health score with degradation."""
        snapshot = SignalsSnapshot(
            circuit_breaker=CircuitBreakerSnapshot(
                state="half_open", failure_count=5, failure_threshold=5
            ),
        )
        assert snapshot.health_score == 0.5

    def test_empty_snapshot(self) -> None:
        """Test empty snapshot."""
        snapshot = SignalsSnapshot()
        assert snapshot.is_healthy is True
        assert snapshot.health_score == 1.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        snapshot = SignalsSnapshot(
            provider="openai",
            model="gpt-4o",
        )
        d = snapshot.to_dict()
        assert d["provider"] == "openai"
        assert d["model"] == "gpt-4o"
        assert d["is_healthy"] is True


class TestPreflightConfig:
    """Tests for PreflightConfig."""

    def test_default_values(self) -> None:
        """Test default configuration."""
        config = PreflightConfig()
        assert config.check_rate_limiter is True
        assert config.check_circuit_breaker is True
        assert config.check_backpressure is True
        assert config.fail_fast is True


class TestPreflightResult:
    """Tests for PreflightResult."""

    def test_default_passed(self) -> None:
        """Test default result is passed."""
        result = PreflightResult()
        assert result.passed is True
        assert result.errors == []

    def test_with_errors(self) -> None:
        """Test result with errors."""
        error = PreflightError("Test error", "test_component")
        result = PreflightResult(passed=False, errors=[error])
        assert result.passed is False
        assert len(result.errors) == 1


class TestPreflightChecker:
    """Tests for PreflightChecker."""

    @pytest.mark.asyncio
    async def test_check_no_components(self) -> None:
        """Test check with no components configured."""
        checker = PreflightChecker()
        result = await checker.check()
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_get_signals(self) -> None:
        """Test getting signals snapshot."""
        checker = PreflightChecker(provider="openai", model="gpt-4o")
        signals = checker.get_signals()
        assert signals.provider == "openai"
        assert signals.model == "gpt-4o"

    def test_on_success(self) -> None:
        """Test success reporting."""
        # Should not raise
        checker = PreflightChecker()
        checker.on_success()

    def test_on_failure(self) -> None:
        """Test failure reporting."""
        # Should not raise
        checker = PreflightChecker()
        checker.on_failure()
