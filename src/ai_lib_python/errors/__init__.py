"""
Error hierarchy for ai-lib-python.

Provides structured error types aligned with AI-Protocol error_classification.
"""

from ai_lib_python.errors.base import (
    AiLibError,
    ErrorContext,
    PipelineError,
    ProtocolError,
    RemoteError,
    TransportError,
    ValidationError,
)
from ai_lib_python.errors.base import (
    RuntimeError as AiRuntimeError,
)
from ai_lib_python.errors.classification import (
    ErrorClass,
    classify_http_error,
    is_fallbackable,
    is_retryable,
)

__all__ = [
    # Base errors
    "AiLibError",
    "AiRuntimeError",
    # Classification
    "ErrorClass",
    "ErrorContext",
    "PipelineError",
    "ProtocolError",
    "RemoteError",
    "TransportError",
    "ValidationError",
    "classify_http_error",
    "is_fallbackable",
    "is_retryable",
]
