"""
Streaming events based on AI-Protocol standard_schema.

Provides a unified event model for streaming responses across all providers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PartialContentDelta(BaseModel):
    """Partial content delta event (text streaming)."""

    model_config = ConfigDict(extra="allow")

    content: str = Field(description="Partial content text")
    sequence_id: int | None = Field(default=None, description="Sequence identifier")


class ThinkingDelta(BaseModel):
    """Thinking delta event (reasoning process)."""

    model_config = ConfigDict(extra="allow")

    thinking: str = Field(description="Thinking/reasoning text")
    tool_consideration: str | None = Field(
        default=None, description="Tool consideration notes"
    )


class ToolCallStarted(BaseModel):
    """Tool call started event."""

    model_config = ConfigDict(extra="allow")

    tool_call_id: str = Field(description="Unique tool call identifier")
    tool_name: str = Field(description="Name of the tool being called")
    index: int | None = Field(default=None, description="Tool call index")


class PartialToolCall(BaseModel):
    """Partial tool call event (arguments streaming)."""

    model_config = ConfigDict(extra="allow")

    tool_call_id: str = Field(description="Tool call identifier")
    arguments: str = Field(description="Partial JSON arguments string")
    index: int | None = Field(default=None, description="Tool call index")
    is_complete: bool | None = Field(
        default=None, description="Whether arguments are complete"
    )


class ToolCallEnded(BaseModel):
    """Tool call ended event."""

    model_config = ConfigDict(extra="allow")

    tool_call_id: str = Field(description="Tool call identifier")
    index: int | None = Field(default=None, description="Tool call index")


class Metadata(BaseModel):
    """Metadata event (usage, finish reason, etc.)."""

    model_config = ConfigDict(extra="allow")

    usage: dict[str, Any] | None = Field(default=None, description="Token usage info")
    finish_reason: str | None = Field(default=None, description="Finish reason")
    stop_reason: str | None = Field(default=None, description="Stop reason (provider-specific)")


class FinalCandidate(BaseModel):
    """Final candidate event (for multi-candidate scenarios)."""

    model_config = ConfigDict(extra="allow")

    candidate_index: int = Field(description="Candidate index (0-based)")
    finish_reason: str = Field(description="Finish reason for this candidate")


class StreamEnd(BaseModel):
    """Stream end event."""

    model_config = ConfigDict(extra="allow")

    finish_reason: str | None = Field(default=None, description="Final finish reason")


class StreamError(BaseModel):
    """Stream error event."""

    model_config = ConfigDict(extra="allow")

    error: Any = Field(description="Error payload")
    event_id: str | None = Field(default=None, description="Event identifier")


class StreamingEvent(BaseModel):
    """Unified streaming event container.

    This is a discriminated union of all streaming event types.
    Use pattern matching to handle different event types:

    Example:
        >>> async for event in stream:
        ...     match event.event_type:
        ...         case "PartialContentDelta":
        ...             print(event.data.content, end="")
        ...         case "ToolCallStarted":
        ...             print(f"Tool: {event.data.tool_name}")
        ...         case "StreamEnd":
        ...             print("Done!")

    Or use the typed accessor properties:
        >>> if event.is_content_delta:
        ...     print(event.as_content_delta.content)
    """

    model_config = ConfigDict(extra="allow")

    event_type: str = Field(description="Event type discriminator")
    data: (
        PartialContentDelta
        | ThinkingDelta
        | ToolCallStarted
        | PartialToolCall
        | ToolCallEnded
        | Metadata
        | FinalCandidate
        | StreamEnd
        | StreamError
    ) = Field(description="Event data")

    # Factory methods for creating events
    @classmethod
    def content_delta(cls, content: str, sequence_id: int | None = None) -> StreamingEvent:
        """Create a partial content delta event."""
        return cls(
            event_type="PartialContentDelta",
            data=PartialContentDelta(content=content, sequence_id=sequence_id),
        )

    @classmethod
    def thinking_delta(
        cls, thinking: str, tool_consideration: str | None = None
    ) -> StreamingEvent:
        """Create a thinking delta event."""
        return cls(
            event_type="ThinkingDelta",
            data=ThinkingDelta(thinking=thinking, tool_consideration=tool_consideration),
        )

    @classmethod
    def tool_call_started(
        cls, tool_call_id: str, tool_name: str, index: int | None = None
    ) -> StreamingEvent:
        """Create a tool call started event."""
        return cls(
            event_type="ToolCallStarted",
            data=ToolCallStarted(
                tool_call_id=tool_call_id, tool_name=tool_name, index=index
            ),
        )

    @classmethod
    def partial_tool_call(
        cls,
        tool_call_id: str,
        arguments: str,
        index: int | None = None,
        is_complete: bool | None = None,
    ) -> StreamingEvent:
        """Create a partial tool call event."""
        return cls(
            event_type="PartialToolCall",
            data=PartialToolCall(
                tool_call_id=tool_call_id,
                arguments=arguments,
                index=index,
                is_complete=is_complete,
            ),
        )

    @classmethod
    def tool_call_ended(
        cls, tool_call_id: str, index: int | None = None
    ) -> StreamingEvent:
        """Create a tool call ended event."""
        return cls(
            event_type="ToolCallEnded",
            data=ToolCallEnded(tool_call_id=tool_call_id, index=index),
        )

    @classmethod
    def metadata(
        cls,
        usage: dict[str, Any] | None = None,
        finish_reason: str | None = None,
        stop_reason: str | None = None,
    ) -> StreamingEvent:
        """Create a metadata event."""
        return cls(
            event_type="Metadata",
            data=Metadata(usage=usage, finish_reason=finish_reason, stop_reason=stop_reason),
        )

    @classmethod
    def final_candidate(cls, candidate_index: int, finish_reason: str) -> StreamingEvent:
        """Create a final candidate event."""
        return cls(
            event_type="FinalCandidate",
            data=FinalCandidate(candidate_index=candidate_index, finish_reason=finish_reason),
        )

    @classmethod
    def stream_end(cls, finish_reason: str | None = None) -> StreamingEvent:
        """Create a stream end event."""
        return cls(
            event_type="StreamEnd",
            data=StreamEnd(finish_reason=finish_reason),
        )

    @classmethod
    def stream_error(cls, error: Any, event_id: str | None = None) -> StreamingEvent:
        """Create a stream error event."""
        return cls(
            event_type="StreamError",
            data=StreamError(error=error, event_id=event_id),
        )

    # Type checking properties
    @property
    def is_content_delta(self) -> bool:
        """Check if this is a content delta event."""
        return self.event_type == "PartialContentDelta"

    @property
    def is_thinking_delta(self) -> bool:
        """Check if this is a thinking delta event."""
        return self.event_type == "ThinkingDelta"

    @property
    def is_tool_call_started(self) -> bool:
        """Check if this is a tool call started event."""
        return self.event_type == "ToolCallStarted"

    @property
    def is_partial_tool_call(self) -> bool:
        """Check if this is a partial tool call event."""
        return self.event_type == "PartialToolCall"

    @property
    def is_tool_call_ended(self) -> bool:
        """Check if this is a tool call ended event."""
        return self.event_type == "ToolCallEnded"

    @property
    def is_metadata(self) -> bool:
        """Check if this is a metadata event."""
        return self.event_type == "Metadata"

    @property
    def is_final_candidate(self) -> bool:
        """Check if this is a final candidate event."""
        return self.event_type == "FinalCandidate"

    @property
    def is_stream_end(self) -> bool:
        """Check if this is a stream end event."""
        return self.event_type == "StreamEnd"

    @property
    def is_stream_error(self) -> bool:
        """Check if this is a stream error event."""
        return self.event_type == "StreamError"

    # Typed accessors
    @property
    def as_content_delta(self) -> PartialContentDelta:
        """Get data as PartialContentDelta. Raises if wrong type."""
        if not isinstance(self.data, PartialContentDelta):
            raise TypeError(f"Event is {self.event_type}, not PartialContentDelta")
        return self.data

    @property
    def as_thinking_delta(self) -> ThinkingDelta:
        """Get data as ThinkingDelta. Raises if wrong type."""
        if not isinstance(self.data, ThinkingDelta):
            raise TypeError(f"Event is {self.event_type}, not ThinkingDelta")
        return self.data

    @property
    def as_tool_call_started(self) -> ToolCallStarted:
        """Get data as ToolCallStarted. Raises if wrong type."""
        if not isinstance(self.data, ToolCallStarted):
            raise TypeError(f"Event is {self.event_type}, not ToolCallStarted")
        return self.data

    @property
    def as_partial_tool_call(self) -> PartialToolCall:
        """Get data as PartialToolCall. Raises if wrong type."""
        if not isinstance(self.data, PartialToolCall):
            raise TypeError(f"Event is {self.event_type}, not PartialToolCall")
        return self.data

    @property
    def as_tool_call_ended(self) -> ToolCallEnded:
        """Get data as ToolCallEnded. Raises if wrong type."""
        if not isinstance(self.data, ToolCallEnded):
            raise TypeError(f"Event is {self.event_type}, not ToolCallEnded")
        return self.data

    @property
    def as_metadata(self) -> Metadata:
        """Get data as Metadata. Raises if wrong type."""
        if not isinstance(self.data, Metadata):
            raise TypeError(f"Event is {self.event_type}, not Metadata")
        return self.data

    @property
    def as_final_candidate(self) -> FinalCandidate:
        """Get data as FinalCandidate. Raises if wrong type."""
        if not isinstance(self.data, FinalCandidate):
            raise TypeError(f"Event is {self.event_type}, not FinalCandidate")
        return self.data

    @property
    def as_stream_end(self) -> StreamEnd:
        """Get data as StreamEnd. Raises if wrong type."""
        if not isinstance(self.data, StreamEnd):
            raise TypeError(f"Event is {self.event_type}, not StreamEnd")
        return self.data

    @property
    def as_stream_error(self) -> StreamError:
        """Get data as StreamError. Raises if wrong type."""
        if not isinstance(self.data, StreamError):
            raise TypeError(f"Event is {self.event_type}, not StreamError")
        return self.data
