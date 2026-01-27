"""
Error classification based on AI-Protocol error_handling specification.

Provides 13 standard error classes aligned with the protocol specification.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorClass(str, Enum):
    """Standard error classification.

    Based on AI-Protocol error_handling.error_classes specification.
    """

    INVALID_REQUEST = "invalid_request"
    """Malformed request body, invalid parameters, or unsupported operation."""

    AUTHENTICATION = "authentication"
    """Missing/invalid credentials (API key/token)."""

    PERMISSION_DENIED = "permission_denied"
    """Caller is authenticated but not permitted to access the resource."""

    NOT_FOUND = "not_found"
    """Requested resource not found."""

    QUOTA_EXHAUSTED = "quota_exhausted"
    """Account quota/billing/spend limit exceeded."""

    RATE_LIMITED = "rate_limited"
    """Throttled due to request/token limits; typically retryable with backoff."""

    REQUEST_TOO_LARGE = "request_too_large"
    """Payload too large (e.g., context too long, request too big)."""

    TIMEOUT = "timeout"
    """Request timed out or deadline exceeded."""

    CONFLICT = "conflict"
    """Request conflict (often safe to retry depending on semantics)."""

    CANCELLED = "cancelled"
    """Request was cancelled by client or upstream."""

    SERVER_ERROR = "server_error"
    """Transient server-side failure (5xx)."""

    OVERLOADED = "overloaded"
    """Service overloaded / temporarily unavailable."""

    OTHER = "other"
    """Unknown or provider-specific classification."""


# Default retryable error classes
_RETRYABLE_CLASSES: set[ErrorClass] = {
    ErrorClass.RATE_LIMITED,
    ErrorClass.TIMEOUT,
    ErrorClass.CONFLICT,
    ErrorClass.SERVER_ERROR,
    ErrorClass.OVERLOADED,
}

# Default fallbackable error classes
_FALLBACKABLE_CLASSES: set[ErrorClass] = {
    ErrorClass.RATE_LIMITED,
    ErrorClass.TIMEOUT,
    ErrorClass.SERVER_ERROR,
    ErrorClass.OVERLOADED,
    ErrorClass.QUOTA_EXHAUSTED,
}

# Default HTTP status to error class mapping
_DEFAULT_STATUS_MAPPING: dict[int, ErrorClass] = {
    400: ErrorClass.INVALID_REQUEST,
    401: ErrorClass.AUTHENTICATION,
    403: ErrorClass.PERMISSION_DENIED,
    404: ErrorClass.NOT_FOUND,
    408: ErrorClass.TIMEOUT,
    409: ErrorClass.CONFLICT,
    413: ErrorClass.REQUEST_TOO_LARGE,
    422: ErrorClass.INVALID_REQUEST,
    429: ErrorClass.RATE_LIMITED,
    499: ErrorClass.CANCELLED,
    500: ErrorClass.SERVER_ERROR,
    502: ErrorClass.SERVER_ERROR,
    503: ErrorClass.OVERLOADED,
    504: ErrorClass.TIMEOUT,
}


def classify_http_error(
    status_code: int,
    body: dict[str, Any] | None = None,
    provider_classification: dict[str, Any] | None = None,
) -> ErrorClass:
    """Classify an HTTP error into a standard error class.

    Args:
        status_code: HTTP status code
        body: Response body (parsed JSON)
        provider_classification: Provider's error_classification config

    Returns:
        ErrorClass representing the error type
    """
    # Try provider-specific classification first
    if provider_classification:
        by_status = provider_classification.get("by_http_status", {})
        status_str = str(status_code)
        if status_str in by_status:
            try:
                return ErrorClass(by_status[status_str])
            except ValueError:
                pass

    # Check for quota exhaustion hints in body (429 may be quota or rate limit)
    if status_code == 429 and body:
        error_msg = extract_error_message(body) or ""
        error_type = body.get("error", {}).get("type", "") if isinstance(body.get("error"), dict) else ""

        # Common patterns indicating quota exhaustion
        quota_patterns = ["quota", "billing", "spend", "limit exceeded", "plan"]
        msg_lower = error_msg.lower()
        type_lower = error_type.lower()

        for pattern in quota_patterns:
            if pattern in msg_lower or pattern in type_lower:
                return ErrorClass.QUOTA_EXHAUSTED

    # Default mapping
    if status_code in _DEFAULT_STATUS_MAPPING:
        return _DEFAULT_STATUS_MAPPING[status_code]

    # Generic classification by status code range
    if 400 <= status_code < 500:
        return ErrorClass.INVALID_REQUEST
    if 500 <= status_code < 600:
        return ErrorClass.SERVER_ERROR

    return ErrorClass.OTHER


def is_retryable(error_class: ErrorClass) -> bool:
    """Check if an error class is retryable by default.

    Args:
        error_class: The error class to check

    Returns:
        True if the error is typically retryable
    """
    return error_class in _RETRYABLE_CLASSES


def is_fallbackable(error_class: ErrorClass) -> bool:
    """Check if an error class supports fallback to another model.

    Args:
        error_class: The error class to check

    Returns:
        True if fallback to another model is appropriate
    """
    return error_class in _FALLBACKABLE_CLASSES


def extract_error_message(body: dict[str, Any] | None) -> str | None:
    """Extract error message from response body.

    Supports multiple error envelope formats:
    - OpenAI style: {"error": {"message": "..."}}
    - Anthropic style: {"error": {"message": "..."}, "type": "error"}
    - Google style: {"error": {"message": "..."}}
    - Simple: {"message": "..."}

    Args:
        body: Response body (parsed JSON)

    Returns:
        Error message if found, None otherwise
    """
    if not body:
        return None

    # OpenAI/Anthropic/Google style
    if "error" in body:
        error = body["error"]
        if isinstance(error, dict):
            return error.get("message")
        if isinstance(error, str):
            return error

    # Simple message field
    if "message" in body:
        return body["message"]

    # Detail field (common in some APIs)
    if "detail" in body:
        detail = body["detail"]
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            return str(detail[0])

    return None
