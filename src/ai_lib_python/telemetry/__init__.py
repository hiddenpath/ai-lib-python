"""
Telemetry module for ai-lib-python.

Provides structured logging, metrics collection, distributed tracing,
and health monitoring.
"""

from ai_lib_python.telemetry.health import (
    AggregatedHealth,
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    ProviderHealthTracker,
    get_health_checker,
    get_health_tracker,
)
from ai_lib_python.telemetry.logger import (
    AiLibLogger,
    LogContext,
    LogLevel,
    SensitiveDataMasker,
    clear_log_context,
    get_log_context,
    get_logger,
    set_log_context,
)
from ai_lib_python.telemetry.metrics import (
    HistogramBuckets,
    MetricLabels,
    MetricsCollector,
    MetricSnapshot,
    get_metrics_collector,
    set_metrics_collector,
)
from ai_lib_python.telemetry.tracer import (
    ConsoleExporter,
    InMemoryExporter,
    Span,
    SpanContext,
    SpanExporter,
    SpanKind,
    SpanStatus,
    Tracer,
    get_current_span,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    set_tracer,
)

__all__ = [
    # Health
    "AggregatedHealth",
    # Logger
    "AiLibLogger",
    # Tracer
    "ConsoleExporter",
    "HealthCheckResult",
    "HealthChecker",
    "HealthStatus",
    "HistogramBuckets",
    "InMemoryExporter",
    "LogContext",
    "LogLevel",
    # Metrics
    "MetricLabels",
    "MetricSnapshot",
    "MetricsCollector",
    "ProviderHealthTracker",
    "SensitiveDataMasker",
    "Span",
    "SpanContext",
    "SpanExporter",
    "SpanKind",
    "SpanStatus",
    "Tracer",
    "clear_log_context",
    "get_current_span",
    "get_current_span_id",
    "get_current_trace_id",
    "get_health_checker",
    "get_health_tracker",
    "get_log_context",
    "get_logger",
    "get_metrics_collector",
    "get_tracer",
    "set_log_context",
    "set_metrics_collector",
    "set_tracer",
]
