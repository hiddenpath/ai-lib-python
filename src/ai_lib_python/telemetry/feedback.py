"""
User feedback collection system.

Provides typed feedback events and sinks for collecting user feedback,
particularly useful for multi-candidate selection and RLHF.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeedbackType(str, Enum):
    """Types of feedback events."""

    CHOICE_SELECTION = "choice_selection"
    RATING = "rating"
    THUMBS = "thumbs"
    TEXT = "text"
    CORRECTION = "correction"
    REGENERATE = "regenerate"
    STOP = "stop"


@dataclass
class ChoiceSelectionFeedback:
    """Feedback for multi-candidate selection.

    Used when users select one response from multiple candidates.
    Useful for preference learning and A/B testing.

    Attributes:
        request_id: Request identifier (client_request_id)
        chosen_index: Index of the chosen candidate (0-based)
        rejected_indices: Indices of rejected candidates
        latency_to_select_ms: Time from render to selection
        ui_context: Optional UI context (component name, experiment ID)
        candidate_hashes: Content hashes to link choice without storing text
    """

    request_id: str
    chosen_index: int
    rejected_indices: list[int] | None = None
    latency_to_select_ms: float | None = None
    ui_context: dict[str, Any] | None = None
    candidate_hashes: list[str] | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.CHOICE_SELECTION.value,
            "request_id": self.request_id,
            "chosen_index": self.chosen_index,
            "rejected_indices": self.rejected_indices,
            "latency_to_select_ms": self.latency_to_select_ms,
            "ui_context": self.ui_context,
            "candidate_hashes": self.candidate_hashes,
            "timestamp": self.timestamp,
        }


@dataclass
class RatingFeedback:
    """Rating feedback (e.g., 1-5 stars).

    Attributes:
        request_id: Request identifier
        rating: Rating value (typically 1-5)
        max_rating: Maximum possible rating
        category: Optional rating category
        comment: Optional text comment
    """

    request_id: str
    rating: int
    max_rating: int = 5
    category: str | None = None
    comment: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.RATING.value,
            "request_id": self.request_id,
            "rating": self.rating,
            "max_rating": self.max_rating,
            "category": self.category,
            "comment": self.comment,
            "timestamp": self.timestamp,
        }


@dataclass
class ThumbsFeedback:
    """Simple thumbs up/down feedback.

    Attributes:
        request_id: Request identifier
        is_positive: True for thumbs up, False for thumbs down
        reason: Optional reason for the feedback
    """

    request_id: str
    is_positive: bool
    reason: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.THUMBS.value,
            "request_id": self.request_id,
            "is_positive": self.is_positive,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class TextFeedback:
    """Free-form text feedback.

    Attributes:
        request_id: Request identifier
        text: Feedback text
        category: Optional category
    """

    request_id: str
    text: str
    category: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.TEXT.value,
            "request_id": self.request_id,
            "text": self.text,
            "category": self.category,
            "timestamp": self.timestamp,
        }


@dataclass
class CorrectionFeedback:
    """Correction/edit feedback.

    Captures when users edit or correct the AI response.

    Attributes:
        request_id: Request identifier
        original_hash: Hash of original content
        corrected_hash: Hash of corrected content
        edit_distance: Optional edit distance metric
        correction_type: Type of correction (grammar, factual, style, etc.)
    """

    request_id: str
    original_hash: str
    corrected_hash: str
    edit_distance: int | None = None
    correction_type: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.CORRECTION.value,
            "request_id": self.request_id,
            "original_hash": self.original_hash,
            "corrected_hash": self.corrected_hash,
            "edit_distance": self.edit_distance,
            "correction_type": self.correction_type,
            "timestamp": self.timestamp,
        }


@dataclass
class RegenerateFeedback:
    """Regeneration feedback.

    Captures when users request regeneration.

    Attributes:
        request_id: Request identifier
        regeneration_count: Number of regenerations
        reason: Optional reason for regeneration
    """

    request_id: str
    regeneration_count: int = 1
    reason: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.REGENERATE.value,
            "request_id": self.request_id,
            "regeneration_count": self.regeneration_count,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class StopFeedback:
    """Stop generation feedback.

    Captures when users stop generation mid-stream.

    Attributes:
        request_id: Request identifier
        tokens_generated: Tokens generated before stop
        reason: Optional reason for stopping
    """

    request_id: str
    tokens_generated: int | None = None
    reason: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": FeedbackType.STOP.value,
            "request_id": self.request_id,
            "tokens_generated": self.tokens_generated,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


# Union type for all feedback events
FeedbackEvent = (
    ChoiceSelectionFeedback
    | RatingFeedback
    | ThumbsFeedback
    | TextFeedback
    | CorrectionFeedback
    | RegenerateFeedback
    | StopFeedback
)


class FeedbackSink(ABC):
    """Abstract base class for feedback sinks.

    Feedback sinks determine where and how feedback is stored/reported.
    Applications can implement custom sinks for their backend.
    """

    @abstractmethod
    async def report(self, event: FeedbackEvent) -> None:
        """Report a feedback event.

        Args:
            event: Feedback event to report
        """
        raise NotImplementedError

    async def report_batch(self, events: list[FeedbackEvent]) -> None:
        """Report multiple feedback events.

        Default implementation calls report() for each event.
        Override for batch-optimized implementations.

        Args:
            events: List of feedback events
        """
        for event in events:
            await self.report(event)

    async def close(self) -> None:
        """Close the sink and release resources."""
        pass


class NoopFeedbackSink(FeedbackSink):
    """No-op feedback sink that discards all feedback.

    Default sink when no feedback collection is configured.
    """

    async def report(self, event: FeedbackEvent) -> None:
        """Discard feedback event."""
        pass


class InMemoryFeedbackSink(FeedbackSink):
    """In-memory feedback sink for testing and development.

    Stores all feedback in memory for later retrieval.
    """

    def __init__(self, max_events: int = 10000) -> None:
        """Initialize sink.

        Args:
            max_events: Maximum events to store
        """
        self._events: list[FeedbackEvent] = []
        self._max_events = max_events

    async def report(self, event: FeedbackEvent) -> None:
        """Store feedback event in memory."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def get_events(self) -> list[FeedbackEvent]:
        """Get all stored events."""
        return list(self._events)

    def get_events_by_request(self, request_id: str) -> list[FeedbackEvent]:
        """Get events for a specific request."""
        return [e for e in self._events if e.request_id == request_id]

    def get_events_by_type(self, feedback_type: FeedbackType) -> list[FeedbackEvent]:
        """Get events of a specific type."""
        type_map = {
            FeedbackType.CHOICE_SELECTION: ChoiceSelectionFeedback,
            FeedbackType.RATING: RatingFeedback,
            FeedbackType.THUMBS: ThumbsFeedback,
            FeedbackType.TEXT: TextFeedback,
            FeedbackType.CORRECTION: CorrectionFeedback,
            FeedbackType.REGENERATE: RegenerateFeedback,
            FeedbackType.STOP: StopFeedback,
        }
        target_class = type_map.get(feedback_type)
        if target_class:
            return [e for e in self._events if isinstance(e, target_class)]
        return []

    def clear(self) -> None:
        """Clear all stored events."""
        self._events.clear()

    def __len__(self) -> int:
        """Get number of stored events."""
        return len(self._events)


class ConsoleFeedbackSink(FeedbackSink):
    """Console feedback sink for debugging.

    Prints feedback events to console/stdout.
    """

    def __init__(self, prefix: str = "[Feedback]") -> None:
        """Initialize sink.

        Args:
            prefix: Prefix for log messages
        """
        self._prefix = prefix

    async def report(self, event: FeedbackEvent) -> None:
        """Print feedback event to console."""
        print(f"{self._prefix} {event.to_dict()}")


class CompositeFeedbackSink(FeedbackSink):
    """Composite sink that reports to multiple sinks.

    Useful for sending feedback to multiple destinations.
    """

    def __init__(self, sinks: list[FeedbackSink] | None = None) -> None:
        """Initialize composite sink.

        Args:
            sinks: List of sinks to report to
        """
        self._sinks = list(sinks) if sinks else []

    def add_sink(self, sink: FeedbackSink) -> CompositeFeedbackSink:
        """Add a sink.

        Args:
            sink: Sink to add

        Returns:
            Self for chaining
        """
        self._sinks.append(sink)
        return self

    async def report(self, event: FeedbackEvent) -> None:
        """Report to all sinks."""
        for sink in self._sinks:
            try:
                await sink.report(event)
            except Exception:
                pass  # Don't let one sink failure affect others

    async def close(self) -> None:
        """Close all sinks."""
        for sink in self._sinks:
            try:
                await sink.close()
            except Exception:
                pass


# Global feedback sink
_global_sink: FeedbackSink | None = None


def get_feedback_sink() -> FeedbackSink:
    """Get the global feedback sink.

    Returns:
        Global FeedbackSink instance (NoopFeedbackSink if not set)
    """
    global _global_sink
    if _global_sink is None:
        _global_sink = NoopFeedbackSink()
    return _global_sink


def set_feedback_sink(sink: FeedbackSink) -> None:
    """Set the global feedback sink.

    Args:
        sink: FeedbackSink instance
    """
    global _global_sink
    _global_sink = sink


async def report_feedback(event: FeedbackEvent) -> None:
    """Report feedback using the global sink.

    Args:
        event: Feedback event to report
    """
    sink = get_feedback_sink()
    await sink.report(event)
