"""错误体系：提供与 AI-Protocol 规范对齐的结构化错误类型。

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
from ai_lib_python.errors.standard_codes import (
    STANDARD_ERROR_CODES,
    StandardErrorCode,
    from_error_class,
    from_http_status,
    from_name,
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
    "STANDARD_ERROR_CODES",
    "StandardErrorCode",
    "from_error_class",
    "from_http_status",
    "from_name",
]
