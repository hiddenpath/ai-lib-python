"""错误基类：提供分层错误体系和结构化错误上下文。

Base error classes for ai-lib-python.

Provides a layered error hierarchy:
- AiLibError: Base class for all library errors
- ProtocolError: Protocol loading/validation errors
- TransportError: HTTP/network errors
- PipelineError: Stream processing errors
- ValidationError: Request/response validation errors
- RuntimeError: General runtime errors
- RemoteError: Remote API errors with classification
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_lib_python.errors.classification import ErrorClass
    from ai_lib_python.errors.standard_codes import StandardErrorCode


@dataclass
class ErrorContext:
    """Structured error context for diagnostics.

    Provides actionable information for debugging and error handling.
    """

    field_path: str | None = None
    """Path to the problematic field (e.g., 'messages[0].content')"""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional details about the error"""

    source: str | None = None
    """Error source (e.g., 'protocol', 'transport', 'pipeline')"""

    hint: str | None = None
    """Actionable hint for resolving the error"""

    def __str__(self) -> str:
        parts = []
        if self.source:
            parts.append(f"[{self.source}]")
        if self.field_path:
            parts.append(f"at '{self.field_path}'")
        if self.hint:
            parts.append(f"(hint: {self.hint})")
        return " ".join(parts)


class AiLibError(Exception):
    """Base class for all ai-lib-python errors.

    All errors from this library inherit from this class, making it easy
    to catch all library errors with a single except clause.

    Attributes:
        message: Human-readable error message
        context: Optional structured error context
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
    ) -> None:
        self.message = message
        self.context = context or ErrorContext()
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the full error message."""
        ctx_str = str(self.context)
        if ctx_str:
            return f"{self.message} {ctx_str}"
        return self.message

    def with_hint(self, hint: str) -> AiLibError:
        """Add a hint to this error."""
        self.context.hint = hint
        return self


class ProtocolError(AiLibError):
    """Error during protocol loading or parsing.

    Raised when:
    - Protocol file not found
    - Invalid YAML/JSON syntax
    - Schema validation failure
    - Unsupported protocol version
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        *,
        protocol_path: str | None = None,
        version: str | None = None,
    ) -> None:
        ctx = context or ErrorContext(source="protocol")
        if protocol_path:
            ctx.details["protocol_path"] = protocol_path
        if version:
            ctx.details["version"] = version
        super().__init__(message, ctx)
        self.protocol_path = protocol_path
        self.version = version


class TransportError(AiLibError):
    """Error during HTTP transport.

    Raised when:
    - Network connection failure
    - Timeout
    - SSL/TLS errors
    - Proxy errors
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        *,
        url: str | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        ctx = context or ErrorContext(source="transport")
        if url:
            ctx.details["url"] = url
        if status_code:
            ctx.details["status_code"] = status_code
        super().__init__(message, ctx)
        self.url = url
        self.status_code = status_code
        self.__cause__ = cause


class PipelineError(AiLibError):
    """Error during pipeline processing.

    Raised when:
    - Decoder fails to parse stream
    - JSONPath evaluation error
    - Event mapping error
    - Accumulator state error
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        *,
        operator: str | None = None,
    ) -> None:
        ctx = context or ErrorContext(source="pipeline")
        if operator:
            ctx.details["operator"] = operator
        super().__init__(message, ctx)
        self.operator = operator


class ValidationError(AiLibError):
    """Validation error for requests or responses.

    Raised when:
    - Invalid request parameters
    - Missing required fields
    - Type mismatch
    - Capability mismatch (e.g., tools not supported)
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        *,
        field: str | None = None,
        expected: Any = None,
        actual: Any = None,
    ) -> None:
        ctx = context or ErrorContext(source="validation")
        if field:
            ctx.field_path = field
        if expected is not None:
            ctx.details["expected"] = expected
        if actual is not None:
            ctx.details["actual"] = actual
        super().__init__(message, ctx)
        self.field = field
        self.expected = expected
        self.actual = actual


class RuntimeError(AiLibError):
    """General runtime error.

    Raised for unexpected runtime conditions that don't fit other categories.
    """

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
    ) -> None:
        ctx = context or ErrorContext(source="runtime")
        super().__init__(message, ctx)


class RemoteError(AiLibError):
    """Error from remote API.

    Represents errors returned by AI provider APIs, with structured
    classification for retry and fallback decisions.

    Attributes:
        status_code: HTTP status code
        error_class: Standardized error classification
        retryable: Whether the error is retryable
        fallbackable: Whether fallback to another model is appropriate
        raw_error: Raw error response from the API
        retry_after: Suggested retry delay in seconds (from header)
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_class: ErrorClass,
        retryable: bool = False,
        fallbackable: bool = False,
        raw_error: dict[str, Any] | None = None,
        retry_after: float | None = None,
        request_id: str | None = None,
    ) -> None:
        ctx = ErrorContext(source="remote")
        ctx.details["status_code"] = status_code
        ctx.details["error_class"] = error_class.value
        ctx.details["retryable"] = retryable
        ctx.details["fallbackable"] = fallbackable
        if request_id:
            ctx.details["request_id"] = request_id

        super().__init__(message, ctx)

        self.status_code = status_code
        self.error_class = error_class
        self.retryable = retryable
        self.fallbackable = fallbackable
        self.raw_error = raw_error or {}
        self.retry_after = retry_after
        self.request_id = request_id

    @property
    def standard_code(self) -> StandardErrorCode:
        """Return the AI-Protocol V2 StandardErrorCode for this error."""
        return self.error_class.standard_code

    @classmethod
    def from_response(
        cls,
        status_code: int,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        provider_classification: dict[str, Any] | None = None,
    ) -> RemoteError:
        """Create RemoteError from HTTP response.

        Args:
            status_code: HTTP status code
            body: Response body (parsed JSON)
            headers: Response headers
            provider_classification: Provider's error classification config

        Returns:
            RemoteError with appropriate classification
        """
        from ai_lib_python.errors.classification import (
            classify_http_error,
            extract_error_message,
            is_fallbackable,
            is_retryable,
        )

        error_class = classify_http_error(status_code, body, provider_classification)
        message = extract_error_message(body) or f"HTTP {status_code}"

        # Extract retry-after header
        retry_after = None
        if headers:
            retry_after_str = headers.get("retry-after") or headers.get("Retry-After")
            if retry_after_str:
                with contextlib.suppress(ValueError):
                    retry_after = float(retry_after_str)

        # Extract request ID
        request_id = None
        if headers:
            request_id = (
                headers.get("x-request-id")
                or headers.get("request-id")
                or headers.get("X-Request-Id")
            )
        if body and "request_id" in body:
            request_id = body["request_id"]

        return cls(
            message=message,
            status_code=status_code,
            error_class=error_class,
            retryable=is_retryable(error_class),
            fallbackable=is_fallbackable(error_class),
            raw_error=body,
            retry_after=retry_after,
            request_id=request_id,
        )
