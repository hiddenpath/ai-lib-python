"""
ai-lib-python: Protocol Runtime for AI-Protocol

A Pythonic implementation for unified AI model interaction.
Core principle: All logic is operators, all configuration is protocol.
"""

from ai_lib_python.client import AiClient, AiClientBuilder, CallStats, ChatResponse
from ai_lib_python.errors import AiLibError, ProtocolError, TransportError
from ai_lib_python.types.events import StreamingEvent
from ai_lib_python.types.message import (
    ContentBlock,
    Message,
    MessageContent,
    MessageRole,
)
from ai_lib_python.types.tool import ToolCall, ToolDefinition

__version__ = "0.2.0-dev"

__all__ = [
    # Client
    "AiClient",
    "AiClientBuilder",
    # Errors
    "AiLibError",
    "CallStats",
    "ChatResponse",
    "ContentBlock",
    # Types - Message
    "Message",
    "MessageContent",
    "MessageRole",
    "ProtocolError",
    # Types - Events
    "StreamingEvent",
    "ToolCall",
    # Types - Tool
    "ToolDefinition",
    "TransportError",
    # Version
    "__version__",
]
