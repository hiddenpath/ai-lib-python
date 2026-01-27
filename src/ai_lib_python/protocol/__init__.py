"""
Protocol layer - Protocol loading, validation, and manifest models.

This module handles:
- Loading protocol manifests from various sources
- Validating manifests against JSON Schema
- Typed manifest models for runtime use
"""

from ai_lib_python.protocol.loader import ProtocolLoader
from ai_lib_python.protocol.manifest import (
    AccumulatorConfig,
    AuthConfig,
    AvailabilityConfig,
    CandidateConfig,
    CapabilitiesConfig,
    DecoderConfig,
    EndpointConfig,
    ErrorClassification,
    EventMapRule,
    HealthCheckConfig,
    ProtocolManifest,
    RateLimitHeaders,
    RetryPolicy,
    ServiceConfig,
    StreamingConfig,
    ToolingConfig,
    ToolUseConfig,
)
from ai_lib_python.protocol.validator import ProtocolValidator

__all__ = [
    "AccumulatorConfig",
    "AuthConfig",
    "AvailabilityConfig",
    "CandidateConfig",
    "CapabilitiesConfig",
    "DecoderConfig",
    "EndpointConfig",
    "ErrorClassification",
    "EventMapRule",
    "HealthCheckConfig",
    # Loader and validator
    "ProtocolLoader",
    # Manifest models
    "ProtocolManifest",
    "ProtocolValidator",
    "RateLimitHeaders",
    "RetryPolicy",
    "ServiceConfig",
    "StreamingConfig",
    "ToolUseConfig",
    "ToolingConfig",
]
