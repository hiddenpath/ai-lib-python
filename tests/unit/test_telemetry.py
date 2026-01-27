"""Tests for telemetry module."""

import pytest

from ai_lib_python.telemetry import (
    AiLibLogger,
    HealthCheckResult,
    HealthChecker,
    HealthStatus,
    InMemoryExporter,
    LogContext,
    LogLevel,
    MetricLabels,
    MetricsCollector,
    MetricSnapshot,
    ProviderHealthTracker,
    SensitiveDataMasker,
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    Tracer,
    get_log_context,
    get_logger,
    set_log_context,
)


class TestLogContext:
    """Tests for LogContext."""

    def test_empty_context(self) -> None:
        """Test empty context."""
        ctx = LogContext()
        assert ctx.to_dict() == {}

    def test_context_with_fields(self) -> None:
        """Test context with fields."""
        ctx = LogContext(
            request_id="req-123",
            trace_id="trace-456",
            provider="openai",
            model="gpt-4o",
        )
        result = ctx.to_dict()
        assert result["request_id"] == "req-123"
        assert result["trace_id"] == "trace-456"
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"

    def test_context_with_extra(self) -> None:
        """Test context with extra fields."""
        ctx = LogContext(request_id="req-123")
        new_ctx = ctx.with_extra(latency_ms=100, tokens=50)
        result = new_ctx.to_dict()
        assert result["request_id"] == "req-123"
        assert result["latency_ms"] == 100
        assert result["tokens"] == 50


class TestSensitiveDataMasker:
    """Tests for SensitiveDataMasker."""

    def test_mask_api_key(self) -> None:
        """Test masking API keys."""
        masker = SensitiveDataMasker()
        text = "Using API key sk-1234567890abcdefghijklmnop"
        masked = masker.mask(text)
        assert "sk-1234567890" not in masked
        assert "REDACTED" in masked

    def test_mask_bearer_token(self) -> None:
        """Test masking bearer tokens."""
        masker = SensitiveDataMasker()
        text = "Authorization: Bearer secret-token-123"
        masked = masker.mask(text)
        assert "secret-token-123" not in masked
        assert "REDACTED" in masked

    def test_mask_dict(self) -> None:
        """Test masking dictionary."""
        masker = SensitiveDataMasker()
        data = {
            "api_key": "secret-key",
            "message": "Hello",
            "nested": {"token": "secret-token"},
        }
        masked = masker.mask_dict(data)
        assert masked["api_key"] == "***REDACTED***"
        assert masked["message"] == "Hello"
        assert masked["nested"]["token"] == "***REDACTED***"


class TestAiLibLogger:
    """Tests for AiLibLogger."""

    def test_get_logger(self) -> None:
        """Test getting a logger."""
        logger = get_logger("test")
        assert logger is not None

    def test_configure_log_level(self) -> None:
        """Test configuring log level."""
        AiLibLogger.configure(level=LogLevel.DEBUG)
        logger = get_logger("test.debug")
        # Should not raise
        logger.debug("Debug message")
        logger.info("Info message")


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_record_request(self) -> None:
        """Test recording a request."""
        collector = MetricsCollector()
        labels = MetricLabels(provider="openai", model="gpt-4o")

        collector.record_request(
            labels=labels,
            latency=0.5,
            status="success",
            tokens_in=100,
            tokens_out=50,
        )

        snapshot = collector.get_snapshot()
        assert snapshot.total_requests == 1
        assert snapshot.successful_requests == 1
        assert snapshot.total_tokens_in == 100
        assert snapshot.total_tokens_out == 50

    def test_record_error(self) -> None:
        """Test recording an error."""
        collector = MetricsCollector()
        labels = MetricLabels(provider="openai", model="gpt-4o")

        collector.record_request(
            labels=labels,
            latency=0.1,
            status="error",
        )

        snapshot = collector.get_snapshot()
        assert snapshot.total_requests == 1
        assert snapshot.failed_requests == 1
        assert snapshot.error_rate == 1.0

    def test_latency_percentiles(self) -> None:
        """Test latency percentile calculation."""
        collector = MetricsCollector()
        labels = MetricLabels(provider="openai")

        # Record multiple requests with different latencies
        for latency in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            collector.record_request(labels=labels, latency=latency)

        snapshot = collector.get_snapshot()
        assert snapshot.latency_p50_ms > 0
        assert snapshot.latency_p90_ms > 0

    def test_record_retry(self) -> None:
        """Test recording retries."""
        collector = MetricsCollector()
        labels = MetricLabels(provider="openai")

        collector.record_retry(labels, attempt=1)
        collector.record_retry(labels, attempt=2)

        snapshot = collector.get_snapshot()
        assert snapshot.retry_count == 2

    def test_prometheus_export(self) -> None:
        """Test Prometheus format export."""
        collector = MetricsCollector()
        labels = MetricLabels(provider="openai", model="gpt-4o")

        collector.record_request(labels=labels, latency=0.5, status="success")

        prometheus_output = collector.to_prometheus()
        assert "ailib_requests_total" in prometheus_output
        assert "provider=openai" in prometheus_output

    def test_filter_by_labels(self) -> None:
        """Test filtering metrics by labels."""
        collector = MetricsCollector()

        # Record for different providers
        collector.record_request(
            MetricLabels(provider="openai"), latency=0.1, status="success"
        )
        collector.record_request(
            MetricLabels(provider="anthropic"), latency=0.2, status="success"
        )

        # Get filtered snapshot
        openai_snapshot = collector.get_snapshot(MetricLabels(provider="openai"))
        assert openai_snapshot.total_requests == 1


class TestMetricSnapshot:
    """Tests for MetricSnapshot."""

    def test_error_rate_calculation(self) -> None:
        """Test error rate calculation."""
        snapshot = MetricSnapshot(
            total_requests=100,
            successful_requests=90,
            failed_requests=10,
        )
        assert snapshot.error_rate == 0.1

    def test_error_rate_zero_requests(self) -> None:
        """Test error rate with zero requests."""
        snapshot = MetricSnapshot()
        assert snapshot.error_rate == 0.0


class TestSpanContext:
    """Tests for SpanContext."""

    def test_generate_new_context(self) -> None:
        """Test generating new span context."""
        ctx = SpanContext.generate()
        assert ctx.trace_id is not None
        assert ctx.span_id is not None
        assert len(ctx.trace_id) == 32  # UUID hex without dashes

    def test_generate_child_context(self) -> None:
        """Test generating child span context."""
        parent = SpanContext.generate()
        child = SpanContext.generate(parent)
        assert child.trace_id == parent.trace_id
        assert child.span_id != parent.span_id

    def test_w3c_traceparent(self) -> None:
        """Test W3C traceparent conversion."""
        ctx = SpanContext(trace_id="abc123" * 5 + "ab", span_id="def456" * 2 + "de")
        traceparent = ctx.to_w3c_traceparent()
        assert traceparent.startswith("00-")

        # Parse back
        parsed = SpanContext.from_w3c_traceparent(traceparent)
        assert parsed is not None
        assert parsed.trace_id == ctx.trace_id


class TestSpan:
    """Tests for Span."""

    def test_span_creation(self) -> None:
        """Test creating a span."""
        ctx = SpanContext.generate()
        span = Span(name="test-span", context=ctx)

        assert span.name == "test-span"
        assert span.status == SpanStatus.UNSET
        assert span.start_time > 0

    def test_set_attributes(self) -> None:
        """Test setting span attributes."""
        span = Span(name="test", context=SpanContext.generate())
        span.set_attribute("key1", "value1")
        span.set_attributes({"key2": "value2", "key3": 123})

        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == "value2"
        assert span.attributes["key3"] == 123

    def test_add_event(self) -> None:
        """Test adding events to span."""
        span = Span(name="test", context=SpanContext.generate())
        span.add_event("event1", {"detail": "value"})

        assert len(span.events) == 1
        assert span.events[0].name == "event1"
        assert span.events[0].attributes["detail"] == "value"

    def test_record_exception(self) -> None:
        """Test recording exception."""
        span = Span(name="test", context=SpanContext.generate())
        span.record_exception(ValueError("test error"))

        assert span.status == SpanStatus.ERROR
        assert len(span.events) == 1
        assert span.events[0].name == "exception"

    def test_span_duration(self) -> None:
        """Test span duration calculation."""
        span = Span(name="test", context=SpanContext.generate())
        import time

        time.sleep(0.01)  # 10ms
        span.end()

        assert span.duration_ms >= 10


class TestTracer:
    """Tests for Tracer."""

    def test_start_span(self) -> None:
        """Test starting a span."""
        tracer = Tracer("test-tracer")
        span = tracer.start_span("test-operation")

        assert span.name == "test-operation"
        assert span.context is not None

    def test_span_context_manager(self) -> None:
        """Test span context manager."""
        exporter = InMemoryExporter()
        tracer = Tracer("test-tracer", exporter=exporter)

        with tracer.span("test-operation") as span:
            span.set_attribute("test", "value")

        assert len(exporter.get_spans()) == 1
        exported = exporter.get_spans()[0]
        assert exported.name == "test-operation"
        assert exported.status == SpanStatus.OK
        assert exported.end_time is not None

    def test_span_exception_handling(self) -> None:
        """Test span exception handling."""
        exporter = InMemoryExporter()
        tracer = Tracer("test-tracer", exporter=exporter)

        with pytest.raises(ValueError):
            with tracer.span("failing-operation"):
                raise ValueError("test error")

        assert len(exporter.get_spans()) == 1
        exported = exporter.get_spans()[0]
        assert exported.status == SpanStatus.ERROR

    def test_nested_spans(self) -> None:
        """Test nested spans share trace ID."""
        exporter = InMemoryExporter()
        tracer = Tracer("test-tracer", exporter=exporter)

        with tracer.span("parent") as parent:
            with tracer.span("child") as child:
                assert child.parent_context is not None
                assert child.parent_context.span_id == parent.context.span_id
                assert child.trace_id == parent.trace_id


class TestHealthChecker:
    """Tests for HealthChecker."""

    @pytest.mark.asyncio
    async def test_register_and_check(self) -> None:
        """Test registering and running a health check."""
        checker = HealthChecker()

        async def healthy_check() -> HealthCheckResult:
            return HealthCheckResult(
                name="test",
                status=HealthStatus.HEALTHY,
                message="All good",
            )

        checker.register("test", healthy_check)
        result = await checker.check("test")

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_check_all(self) -> None:
        """Test checking all health checks."""
        checker = HealthChecker()

        async def healthy_check() -> HealthCheckResult:
            return HealthCheckResult(name="healthy", status=HealthStatus.HEALTHY)

        async def degraded_check() -> HealthCheckResult:
            return HealthCheckResult(name="degraded", status=HealthStatus.DEGRADED)

        checker.register("healthy", healthy_check)
        checker.register("degraded", degraded_check)

        health = await checker.check_all()
        assert health.status == HealthStatus.DEGRADED  # Worst of all
        assert len(health.checks) == 2


class TestProviderHealthTracker:
    """Tests for ProviderHealthTracker."""

    def test_record_success(self) -> None:
        """Test recording successful requests."""
        tracker = ProviderHealthTracker()
        tracker.record_success("openai")
        tracker.record_success("openai")

        status = tracker.get_status("openai")
        assert status == HealthStatus.HEALTHY

    def test_record_failures(self) -> None:
        """Test recording failed requests."""
        tracker = ProviderHealthTracker(
            window_size=10,
            unhealthy_threshold=0.5,
        )

        # Record 6 failures, 4 successes = 60% error rate
        for _ in range(6):
            tracker.record_failure("openai", "error")
        for _ in range(4):
            tracker.record_success("openai")

        status = tracker.get_status("openai")
        assert status == HealthStatus.UNHEALTHY

    def test_error_rate(self) -> None:
        """Test error rate calculation."""
        tracker = ProviderHealthTracker()

        tracker.record_success("openai")
        tracker.record_failure("openai", "error")

        error_rate = tracker.get_error_rate("openai")
        assert error_rate == 0.5

    def test_unknown_provider(self) -> None:
        """Test unknown provider status."""
        tracker = ProviderHealthTracker()
        status = tracker.get_status("unknown")
        assert status == HealthStatus.UNKNOWN
