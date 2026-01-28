"""
Pipeline layer - Stream processing operators.

This module implements the operator pipeline for processing streaming responses:
- Decoder: Parses raw bytes into frames (SSE, JSON Lines)
- Selector: Filters frames using JSONPath expressions
- Accumulator: Accumulates stateful data (tool call arguments)
- EventMapper: Converts frames to unified streaming events
- FanOut: Expands arrays into separate events

The pipeline is constructed dynamically from protocol manifests.
"""

from ai_lib_python.pipeline.accumulate import ToolCallAccumulator
from ai_lib_python.pipeline.base import Decoder, EventMapper, Pipeline, Transform
from ai_lib_python.pipeline.decode import (
    AnthropicSSEDecoder,
    JsonLinesDecoder,
    SSEDecoder,
)
from ai_lib_python.pipeline.event_map import (
    AnthropicEventMapper,
    DefaultEventMapper,
    ProtocolEventMapper,
)
from ai_lib_python.pipeline.fan_out import (
    FanOutTransform,
    ReplicateTransform,
    SplitTransform,
    create_fan_out,
)
from ai_lib_python.pipeline.select import JsonPathSelector, PassThroughSelector

__all__ = [
    # Base abstractions
    "AnthropicEventMapper",
    "AnthropicSSEDecoder",
    "Decoder",
    "DefaultEventMapper",
    "EventMapper",
    # FanOut
    "FanOutTransform",
    # Implementations
    "JsonLinesDecoder",
    "JsonPathSelector",
    "PassThroughSelector",
    "Pipeline",
    "ProtocolEventMapper",
    "ReplicateTransform",
    "SSEDecoder",
    "SplitTransform",
    "ToolCallAccumulator",
    "Transform",
    "create_fan_out",
]
