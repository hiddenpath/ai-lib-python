"""
Distributed tracing for ai-lib-python.

Provides span creation, context propagation, and OpenTelemetry integration.
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

# Context variable for current span
_current_span: ContextVar[Span | None] = ContextVar("current_span", default=None)


class SpanKind(str, Enum):
    """Kind of span."""

    CLIENT = "CLIENT"
    SERVER = "SERVER"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"
    INTERNAL = "INTERNAL"


class SpanStatus(str, Enum):
    """Status of a span."""

    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanContext:
    """Context for distributed tracing.

    Attributes:
        trace_id: 128-bit trace identifier
        span_id: 64-bit span identifier
        trace_flags: Trace flags (e.g., sampled)
        trace_state: W3C trace state
    """

    trace_id: str
    span_id: str
    trace_flags: int = 1  # 1 = sampled
    trace_state: str = ""

    @classmethod
    def generate(cls, parent: SpanContext | None = None) -> SpanContext:
        """Generate a new span context.

        Args:
            parent: Parent span context (reuses trace_id)

        Returns:
            New SpanContext
        """
        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]

        return cls(trace_id=trace_id, span_id=span_id)

    def to_w3c_traceparent(self) -> str:
        """Export as W3C traceparent header.

        Returns:
            traceparent header value
        """
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}"

    @classmethod
    def from_w3c_traceparent(cls, header: str) -> SpanContext | None:
        """Parse W3C traceparent header.

        Args:
            header: traceparent header value

        Returns:
            SpanContext or None if invalid
        """
        try:
            parts = header.split("-")
            if len(parts) != 4 or parts[0] != "00":
                return None
            return cls(
                trace_id=parts[1],
                span_id=parts[2],
                trace_flags=int(parts[3], 16),
            )
        except (ValueError, IndexError):
            return None


@dataclass
class SpanEvent:
    """Event within a span.

    Attributes:
        name: Event name
        timestamp: Event timestamp
        attributes: Event attributes
    """

    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A span representing a unit of work.

    Attributes:
        name: Span name
        context: Span context with trace/span IDs
        parent_context: Parent span context
        kind: Span kind
        status: Span status
        start_time: Start timestamp
        end_time: End timestamp
        attributes: Span attributes
        events: Span events
    """

    name: str
    context: SpanContext
    parent_context: SpanContext | None = None
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any) -> Span:
        """Set a span attribute.

        Args:
            key: Attribute key
            value: Attribute value

        Returns:
            Self for chaining
        """
        self.attributes[key] = value
        return self

    def set_attributes(self, attributes: dict[str, Any]) -> Span:
        """Set multiple attributes.

        Args:
            attributes: Attributes to set

        Returns:
            Self for chaining
        """
        self.attributes.update(attributes)
        return self

    def add_event(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> Span:
        """Add an event to the span.

        Args:
            name: Event name
            attributes: Event attributes

        Returns:
            Self for chaining
        """
        self.events.append(SpanEvent(name=name, attributes=attributes or {}))
        return self

    def set_status(self, status: SpanStatus, message: str = "") -> Span:
        """Set span status.

        Args:
            status: Status code
            message: Status message

        Returns:
            Self for chaining
        """
        self.status = status
        self.status_message = message
        return self

    def record_exception(self, exception: Exception) -> Span:
        """Record an exception.

        Args:
            exception: The exception

        Returns:
            Self for chaining
        """
        self.set_status(SpanStatus.ERROR, str(exception))
        self.add_event(
            "exception",
            {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            },
        )
        return self

    def end(self) -> None:
        """End the span."""
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000

    @property
    def trace_id(self) -> str:
        """Get trace ID."""
        return self.context.trace_id

    @property
    def span_id(self) -> str:
        """Get span ID."""
        return self.context.span_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.parent_context.span_id if self.parent_context else None,
            "kind": self.kind.value,
            "status": self.status.value,
            "status_message": self.status_message,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
        }


class Tracer:
    """Tracer for creating spans.

    Example:
        >>> tracer = Tracer("ai_lib_python")
        >>> with tracer.start_span("request") as span:
        ...     span.set_attribute("model", "gpt-4o")
        ...     # do work
    """

    def __init__(
        self,
        name: str,
        exporter: SpanExporter | None = None,
    ) -> None:
        """Initialize tracer.

        Args:
            name: Tracer name
            exporter: Span exporter
        """
        self._name = name
        self._exporter = exporter

    @property
    def name(self) -> str:
        """Get tracer name."""
        return self._name

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: SpanContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Create and start a new span.

        Args:
            name: Span name
            kind: Span kind
            parent: Parent span context
            attributes: Initial attributes

        Returns:
            New Span
        """
        # Get parent from current context if not specified
        if parent is None:
            current = _current_span.get()
            if current:
                parent = current.context

        context = SpanContext.generate(parent)
        span = Span(
            name=name,
            context=context,
            parent_context=parent,
            kind=kind,
            attributes=attributes or {},
        )

        return span

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[Span]:
        """Context manager for creating spans.

        Args:
            name: Span name
            kind: Span kind
            attributes: Initial attributes

        Yields:
            Active span
        """
        span = self.start_span(name, kind=kind, attributes=attributes)
        token = _current_span.set(span)

        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.end()
            _current_span.reset(token)

            # Export span
            if self._exporter:
                self._exporter.export(span)

    def set_exporter(self, exporter: SpanExporter) -> None:
        """Set span exporter.

        Args:
            exporter: Span exporter
        """
        self._exporter = exporter


class SpanExporter:
    """Base class for span exporters."""

    def export(self, span: Span) -> None:
        """Export a span.

        Args:
            span: Span to export
        """
        raise NotImplementedError

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass


class InMemoryExporter(SpanExporter):
    """In-memory span exporter for testing."""

    def __init__(self) -> None:
        """Initialize exporter."""
        self._spans: list[Span] = []

    def export(self, span: Span) -> None:
        """Export span to memory."""
        self._spans.append(span)

    def get_spans(self) -> list[Span]:
        """Get all exported spans."""
        return list(self._spans)

    def clear(self) -> None:
        """Clear all spans."""
        self._spans.clear()


class ConsoleExporter(SpanExporter):
    """Console span exporter for debugging."""

    def export(self, span: Span) -> None:
        """Export span to console."""
        import json

        print(json.dumps(span.to_dict(), indent=2, default=str))


def get_current_span() -> Span | None:
    """Get the current active span.

    Returns:
        Current span or None
    """
    return _current_span.get()


def get_current_trace_id() -> str | None:
    """Get the current trace ID.

    Returns:
        Trace ID or None
    """
    span = _current_span.get()
    return span.trace_id if span else None


def get_current_span_id() -> str | None:
    """Get the current span ID.

    Returns:
        Span ID or None
    """
    span = _current_span.get()
    return span.span_id if span else None


# Global tracer
_global_tracer: Tracer | None = None


def get_tracer(name: str = "ai_lib_python") -> Tracer:
    """Get or create a tracer.

    Args:
        name: Tracer name

    Returns:
        Tracer instance
    """
    global _global_tracer
    if _global_tracer is None or _global_tracer.name != name:
        _global_tracer = Tracer(name)
    return _global_tracer


def set_tracer(tracer: Tracer) -> None:
    """Set the global tracer.

    Args:
        tracer: Tracer instance
    """
    global _global_tracer
    _global_tracer = tracer
