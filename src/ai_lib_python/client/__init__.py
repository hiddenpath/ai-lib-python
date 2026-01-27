"""
Client layer - User-facing API.

This module provides:
- AiClient: Main entry point for AI model interaction
- ChatBuilder: Fluent API for building chat requests
- Response types and utilities
"""

from ai_lib_python.client.builder import AiClientBuilder, ChatRequestBuilder
from ai_lib_python.client.core import AiClient
from ai_lib_python.client.response import CallStats, ChatResponse

__all__ = [
    "AiClient",
    "AiClientBuilder",
    "CallStats",
    "ChatRequestBuilder",
    "ChatResponse",
]
