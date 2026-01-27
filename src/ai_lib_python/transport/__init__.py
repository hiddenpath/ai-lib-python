"""
Transport layer - HTTP client for API communication.

Provides httpx-based transport with:
- Async streaming support
- Proxy configuration
- Timeout management
- API key resolution
"""

from ai_lib_python.transport.auth import resolve_api_key
from ai_lib_python.transport.http import HttpTransport

__all__ = [
    "HttpTransport",
    "resolve_api_key",
]
