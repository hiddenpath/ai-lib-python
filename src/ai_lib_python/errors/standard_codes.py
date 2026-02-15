"""V2 标准错误码：定义 13 个规范错误码及其重试/回退语义。

AI-Protocol V2 standard error codes.

Defines the standard error code system with code strings (E1001, etc.),
HTTP status mappings, and conversion utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_lib_python.errors.classification import ErrorClass


@dataclass(frozen=True)
class StandardErrorCode:
    """AI-Protocol V2 standard error code.

    Each code has a unique identifier (E1001, etc.), name, category,
    retry/fallback semantics, and HTTP status when applicable.
    """

    code: str
    """Unique code identifier (e.g., 'E1001')."""

    name: str
    """Human-readable name (e.g., 'invalid_request')."""

    category: str
    """Error category: 'client', 'rate', 'server', 'operational', or 'unknown'."""

    http_status: int | None
    """Typical HTTP status code, or None for N/A (e.g., cancelled)."""

    retryable: bool
    """Whether the error is typically retryable with backoff."""

    fallbackable: bool
    """Whether fallback to another model/provider is appropriate."""

    description: str
    """Brief description of the error."""


# Standard error code instances per AI-Protocol V2
E1001 = StandardErrorCode(
    code="E1001",
    name="invalid_request",
    category="client",
    http_status=400,
    retryable=False,
    fallbackable=False,
    description="Malformed request body, invalid parameters, or unsupported operation.",
)
E1002 = StandardErrorCode(
    code="E1002",
    name="authentication",
    category="client",
    http_status=401,
    retryable=False,
    fallbackable=True,
    description="Missing or invalid credentials (API key/token).",
)
E1003 = StandardErrorCode(
    code="E1003",
    name="permission_denied",
    category="client",
    http_status=403,
    retryable=False,
    fallbackable=False,
    description="Caller is authenticated but not permitted to access the resource.",
)
E1004 = StandardErrorCode(
    code="E1004",
    name="not_found",
    category="client",
    http_status=404,
    retryable=False,
    fallbackable=False,
    description="Requested resource not found.",
)
E1005 = StandardErrorCode(
    code="E1005",
    name="request_too_large",
    category="client",
    http_status=413,
    retryable=False,
    fallbackable=False,
    description="Payload too large (e.g., context too long, request too big).",
)
E2001 = StandardErrorCode(
    code="E2001",
    name="rate_limited",
    category="rate",
    http_status=429,
    retryable=True,
    fallbackable=True,
    description="Throttled due to request/token limits; typically retryable with backoff.",
)
E2002 = StandardErrorCode(
    code="E2002",
    name="quota_exhausted",
    category="rate",
    http_status=429,
    retryable=False,
    fallbackable=True,
    description="Account quota/billing/spend limit exceeded.",
)
E3001 = StandardErrorCode(
    code="E3001",
    name="server_error",
    category="server",
    http_status=500,
    retryable=True,
    fallbackable=True,
    description="Transient server-side failure (5xx).",
)
E3002 = StandardErrorCode(
    code="E3002",
    name="overloaded",
    category="server",
    http_status=503,
    retryable=True,
    fallbackable=True,
    description="Service overloaded or temporarily unavailable.",
)
E3003 = StandardErrorCode(
    code="E3003",
    name="timeout",
    category="server",
    http_status=504,
    retryable=True,
    fallbackable=True,
    description="Request timed out or deadline exceeded.",
)
E4001 = StandardErrorCode(
    code="E4001",
    name="conflict",
    category="operational",
    http_status=409,
    retryable=True,
    fallbackable=False,
    description="Request conflict (often safe to retry depending on semantics).",
)
E4002 = StandardErrorCode(
    code="E4002",
    name="cancelled",
    category="operational",
    http_status=None,
    retryable=False,
    fallbackable=False,
    description="Request was cancelled by client or upstream.",
)
E9999 = StandardErrorCode(
    code="E9999",
    name="unknown",
    category="unknown",
    http_status=None,
    retryable=False,
    fallbackable=False,
    description="Unknown or provider-specific classification.",
)

STANDARD_ERROR_CODES: dict[str, StandardErrorCode] = {
    E1001.code: E1001,
    E1002.code: E1002,
    E1003.code: E1003,
    E1004.code: E1004,
    E1005.code: E1005,
    E2001.code: E2001,
    E2002.code: E2002,
    E3001.code: E3001,
    E3002.code: E3002,
    E3003.code: E3003,
    E4001.code: E4001,
    E4002.code: E4002,
    E9999.code: E9999,
}

_NAME_TO_CODE: dict[str, StandardErrorCode] = {
    sec.name: sec for sec in STANDARD_ERROR_CODES.values()
}

_HTTP_STATUS_TO_CODE: dict[int, StandardErrorCode] = {
    400: E1001,
    401: E1002,
    403: E1003,
    404: E1004,
    408: E3003,
    409: E4001,
    413: E1005,
    422: E1001,
    429: E2001,  # Default 429 to rate_limited; quota_exhausted needs body context
    499: E4002,
    500: E3001,
    502: E3001,
    503: E3002,
    504: E3003,
    529: E3002,  # Anthropic-specific overloaded status
}


_CLASS_TO_CODE: dict[str, StandardErrorCode] | None = None


def _get_class_to_code() -> dict[str, StandardErrorCode]:
    """Lazily build and cache the ErrorClass -> StandardErrorCode mapping."""
    global _CLASS_TO_CODE
    if _CLASS_TO_CODE is None:
        _CLASS_TO_CODE = {
            "invalid_request": E1001,
            "authentication": E1002,
            "permission_denied": E1003,
            "not_found": E1004,
            "request_too_large": E1005,
            "rate_limited": E2001,
            "quota_exhausted": E2002,
            "server_error": E3001,
            "overloaded": E3002,
            "timeout": E3003,
            "conflict": E4001,
            "cancelled": E4002,
            "other": E9999,
        }
    return _CLASS_TO_CODE


def from_error_class(error_class: ErrorClass) -> StandardErrorCode:
    """Get the StandardErrorCode for an ErrorClass.

    Args:
        error_class: The ErrorClass enum value.

    Returns:
        The corresponding StandardErrorCode instance.
    """
    mapping = _get_class_to_code()
    return mapping.get(error_class.value, E9999)


def from_http_status(status_code: int) -> StandardErrorCode:
    """Get the StandardErrorCode for an HTTP status code.

    Uses default mappings. For 429, returns rate_limited (E2001);
    use classify_http_error with body for quota_exhausted detection.

    Args:
        status_code: HTTP status code (e.g., 400, 500).

    Returns:
        The corresponding StandardErrorCode instance.
    """
    if status_code in _HTTP_STATUS_TO_CODE:
        return _HTTP_STATUS_TO_CODE[status_code]
    if 400 <= status_code < 500:
        return E1001
    if 500 <= status_code < 600:
        return E3001
    return E9999


def from_name(name: str) -> StandardErrorCode:
    """Get the StandardErrorCode by name.

    Args:
        name: Error name (e.g., 'invalid_request', 'rate_limited').

    Returns:
        The StandardErrorCode instance.

    Raises:
        KeyError: If the name is not a valid standard error name.
    """
    code = _NAME_TO_CODE.get(name)
    if code is None:
        raise KeyError(f"Unknown standard error name: {name!r}")
    return code
