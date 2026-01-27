"""
Metrics collection for ai-lib-python.

Provides request metrics, latency tracking, and exporters.
"""

from __future__ import annotations

import statistics
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class MetricType(str, Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricLabels:
    """Labels for a metric.

    Attributes:
        provider: AI provider name
        model: Model name
        endpoint: API endpoint
        status: Request status (success, error, etc.)
        error_class: Error classification
    """

    provider: str | None = None
    model: str | None = None
    endpoint: str | None = None
    status: str | None = None
    error_class: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {k: v for k, v in vars(self).items() if v is not None}

    def to_key(self) -> str:
        """Convert to string key for aggregation."""
        parts = [f"{k}={v}" for k, v in sorted(self.to_dict().items())]
        return ",".join(parts) if parts else "_default_"


@dataclass
class HistogramBuckets:
    """Histogram bucket configuration."""

    boundaries: list[float] = field(
        default_factory=lambda: [
            0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
        ]
    )

    def get_bucket(self, value: float) -> str:
        """Get bucket label for value."""
        for boundary in self.boundaries:
            if value <= boundary:
                return str(boundary)
        return "+Inf"


@dataclass
class MetricSnapshot:
    """Snapshot of current metrics.

    Attributes:
        total_requests: Total request count
        successful_requests: Successful request count
        failed_requests: Failed request count
        total_tokens_in: Total input tokens
        total_tokens_out: Total output tokens
        latency_samples: Latency samples for percentile calculation
        retry_count: Total retry count
        rate_limit_waits: Rate limit wait time sum
        circuit_breaker_opens: Circuit breaker open count
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    latency_samples: list[float] = field(default_factory=list)
    retry_count: int = 0
    rate_limit_waits: float = 0.0
    circuit_breaker_opens: int = 0

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def latency_p50_ms(self) -> float:
        """Get 50th percentile latency."""
        if not self.latency_samples:
            return 0.0
        return statistics.median(self.latency_samples) * 1000

    @property
    def latency_p90_ms(self) -> float:
        """Get 90th percentile latency."""
        if not self.latency_samples:
            return 0.0
        return statistics.quantiles(self.latency_samples, n=10)[-1] * 1000

    @property
    def latency_p99_ms(self) -> float:
        """Get 99th percentile latency."""
        if not self.latency_samples:
            return 0.0
        return statistics.quantiles(self.latency_samples, n=100)[-1] * 1000

    @property
    def avg_latency_ms(self) -> float:
        """Get average latency."""
        if not self.latency_samples:
            return 0.0
        return statistics.mean(self.latency_samples) * 1000


class MetricsCollector:
    """Collects and aggregates metrics.

    Thread-safe metrics collector with support for counters,
    gauges, and histograms.

    Example:
        >>> collector = MetricsCollector()
        >>> collector.record_request(
        ...     labels=MetricLabels(provider="openai", model="gpt-4o"),
        ...     latency=0.5,
        ...     status="success",
        ...     tokens_in=100,
        ...     tokens_out=50,
        ... )
        >>> snapshot = collector.get_snapshot()
        >>> print(f"Total requests: {snapshot.total_requests}")
    """

    def __init__(self, histogram_buckets: HistogramBuckets | None = None) -> None:
        """Initialize collector.

        Args:
            histogram_buckets: Bucket configuration for histograms
        """
        self._lock = threading.Lock()
        self._buckets = histogram_buckets or HistogramBuckets()

        # Counters
        self._request_count: dict[str, int] = defaultdict(int)
        self._success_count: dict[str, int] = defaultdict(int)
        self._error_count: dict[str, int] = defaultdict(int)
        self._tokens_in: dict[str, int] = defaultdict(int)
        self._tokens_out: dict[str, int] = defaultdict(int)
        self._retry_count: dict[str, int] = defaultdict(int)
        self._circuit_opens: dict[str, int] = defaultdict(int)

        # Gauges
        self._inflight: dict[str, int] = defaultdict(int)

        # Histograms (list of samples)
        self._latency_samples: dict[str, list[float]] = defaultdict(list)
        self._rate_limit_wait: dict[str, float] = defaultdict(float)

        # Histogram buckets
        self._latency_buckets: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Callbacks
        self._callbacks: list[Callable[[str, dict[str, Any]], None]] = []

    def record_request(
        self,
        labels: MetricLabels,
        latency: float,
        status: str = "success",
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """Record a completed request.

        Args:
            labels: Metric labels
            latency: Request latency in seconds
            status: Request status
            tokens_in: Input tokens
            tokens_out: Output tokens
        """
        key = labels.to_key()

        with self._lock:
            self._request_count[key] += 1

            if status == "success":
                self._success_count[key] += 1
            else:
                self._error_count[key] += 1

            self._tokens_in[key] += tokens_in
            self._tokens_out[key] += tokens_out

            # Record latency
            self._latency_samples[key].append(latency)

            # Keep only last 1000 samples per key
            if len(self._latency_samples[key]) > 1000:
                self._latency_samples[key] = self._latency_samples[key][-1000:]

            # Update histogram buckets
            bucket = self._buckets.get_bucket(latency)
            self._latency_buckets[key][bucket] += 1

        # Notify callbacks
        self._notify(
            "request",
            {
                "labels": labels.to_dict(),
                "latency": latency,
                "status": status,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            },
        )

    def record_retry(self, labels: MetricLabels, attempt: int) -> None:
        """Record a retry attempt.

        Args:
            labels: Metric labels
            attempt: Retry attempt number
        """
        key = labels.to_key()

        with self._lock:
            self._retry_count[key] += 1

        self._notify("retry", {"labels": labels.to_dict(), "attempt": attempt})

    def record_rate_limit_wait(self, labels: MetricLabels, wait_time: float) -> None:
        """Record rate limit wait time.

        Args:
            labels: Metric labels
            wait_time: Wait time in seconds
        """
        key = labels.to_key()

        with self._lock:
            self._rate_limit_wait[key] += wait_time

        self._notify(
            "rate_limit_wait", {"labels": labels.to_dict(), "wait_time": wait_time}
        )

    def record_circuit_open(self, labels: MetricLabels) -> None:
        """Record circuit breaker opening.

        Args:
            labels: Metric labels
        """
        key = labels.to_key()

        with self._lock:
            self._circuit_opens[key] += 1

        self._notify("circuit_open", {"labels": labels.to_dict()})

    def set_inflight(self, labels: MetricLabels, count: int) -> None:
        """Set current in-flight request count.

        Args:
            labels: Metric labels
            count: In-flight count
        """
        key = labels.to_key()

        with self._lock:
            self._inflight[key] = count

    def get_snapshot(self, labels: MetricLabels | None = None) -> MetricSnapshot:
        """Get current metrics snapshot.

        Args:
            labels: Optional labels to filter by

        Returns:
            MetricSnapshot with current values
        """
        with self._lock:
            if labels:
                key = labels.to_key()
                return MetricSnapshot(
                    total_requests=self._request_count.get(key, 0),
                    successful_requests=self._success_count.get(key, 0),
                    failed_requests=self._error_count.get(key, 0),
                    total_tokens_in=self._tokens_in.get(key, 0),
                    total_tokens_out=self._tokens_out.get(key, 0),
                    latency_samples=list(self._latency_samples.get(key, [])),
                    retry_count=self._retry_count.get(key, 0),
                    rate_limit_waits=self._rate_limit_wait.get(key, 0.0),
                    circuit_breaker_opens=self._circuit_opens.get(key, 0),
                )
            else:
                # Aggregate all
                return MetricSnapshot(
                    total_requests=sum(self._request_count.values()),
                    successful_requests=sum(self._success_count.values()),
                    failed_requests=sum(self._error_count.values()),
                    total_tokens_in=sum(self._tokens_in.values()),
                    total_tokens_out=sum(self._tokens_out.values()),
                    latency_samples=[
                        s for samples in self._latency_samples.values() for s in samples
                    ],
                    retry_count=sum(self._retry_count.values()),
                    rate_limit_waits=sum(self._rate_limit_wait.values()),
                    circuit_breaker_opens=sum(self._circuit_opens.values()),
                )

    def get_all_labels(self) -> list[MetricLabels]:
        """Get all unique label combinations.

        Returns:
            List of MetricLabels
        """
        with self._lock:
            keys = set(self._request_count.keys())
            result = []
            for key in keys:
                if key == "_default_":
                    result.append(MetricLabels())
                else:
                    parts = dict(kv.split("=") for kv in key.split(","))
                    result.append(MetricLabels(**parts))
            return result

    def add_callback(
        self, callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Add a callback for metric events.

        Args:
            callback: Function called with (event_type, data)
        """
        self._callbacks.append(callback)

    def remove_callback(
        self, callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Remove a callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self, event_type: str, data: dict[str, Any]) -> None:
        """Notify all callbacks."""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception:
                pass  # Don't let callback errors affect metrics

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._request_count.clear()
            self._success_count.clear()
            self._error_count.clear()
            self._tokens_in.clear()
            self._tokens_out.clear()
            self._retry_count.clear()
            self._circuit_opens.clear()
            self._inflight.clear()
            self._latency_samples.clear()
            self._rate_limit_wait.clear()
            self._latency_buckets.clear()

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines: list[str] = []

        with self._lock:
            # Request counter
            lines.append("# HELP ailib_requests_total Total number of requests")
            lines.append("# TYPE ailib_requests_total counter")
            for key, count in self._request_count.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_requests_total{labels} {count}")

            # Success counter
            lines.append("# HELP ailib_requests_success_total Successful requests")
            lines.append("# TYPE ailib_requests_success_total counter")
            for key, count in self._success_count.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_requests_success_total{labels} {count}")

            # Error counter
            lines.append("# HELP ailib_requests_error_total Failed requests")
            lines.append("# TYPE ailib_requests_error_total counter")
            for key, count in self._error_count.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_requests_error_total{labels} {count}")

            # Tokens
            lines.append("# HELP ailib_tokens_in_total Total input tokens")
            lines.append("# TYPE ailib_tokens_in_total counter")
            for key, count in self._tokens_in.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_tokens_in_total{labels} {count}")

            lines.append("# HELP ailib_tokens_out_total Total output tokens")
            lines.append("# TYPE ailib_tokens_out_total counter")
            for key, count in self._tokens_out.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_tokens_out_total{labels} {count}")

            # Latency histogram
            lines.append("# HELP ailib_request_duration_seconds Request latency")
            lines.append("# TYPE ailib_request_duration_seconds histogram")
            for key, buckets in self._latency_buckets.items():
                labels_prefix = f"{key}," if key != "_default_" else ""
                cumulative = 0
                for boundary in self._buckets.boundaries:
                    bucket_key = str(boundary)
                    cumulative += buckets.get(bucket_key, 0)
                    lines.append(
                        f'ailib_request_duration_seconds_bucket{{{labels_prefix}le="{boundary}"}} {cumulative}'
                    )
                cumulative += buckets.get("+Inf", 0)
                lines.append(
                    f'ailib_request_duration_seconds_bucket{{{labels_prefix}le="+Inf"}} {cumulative}'
                )

            # Retry counter
            lines.append("# HELP ailib_retries_total Total retry attempts")
            lines.append("# TYPE ailib_retries_total counter")
            for key, count in self._retry_count.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_retries_total{labels} {count}")

            # In-flight gauge
            lines.append("# HELP ailib_inflight_requests Current in-flight requests")
            lines.append("# TYPE ailib_inflight_requests gauge")
            for key, count in self._inflight.items():
                labels = f"{{{key}}}" if key != "_default_" else ""
                lines.append(f"ailib_inflight_requests{labels} {count}")

        return "\n".join(lines)


# Global metrics collector
_global_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector.

    Returns:
        Global MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def set_metrics_collector(collector: MetricsCollector) -> None:
    """Set the global metrics collector.

    Args:
        collector: MetricsCollector instance
    """
    global _global_collector
    _global_collector = collector
