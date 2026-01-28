"""
Protocol layer - Protocol loading, validation, and manifest models.

This module handles:
- Loading protocol manifests from various sources
- Validating manifests against JSON Schema
- Protocol version validation
- Strict streaming validation
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
from ai_lib_python.protocol.validator import (
    SUPPORTED_PROTOCOL_VERSIONS,
    ProtocolValidator,
    ValidationResult,
    validate_manifest,
    validate_manifest_or_raise,
    validate_protocol_version,
    validate_streaming_config,
)

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
    "SUPPORTED_PROTOCOL_VERSIONS",
    "ServiceConfig",
    "StreamingConfig",
    "ToolUseConfig",
    "ToolingConfig",
    # Validation functions
    "ValidationResult",
    "validate_manifest",
    "validate_manifest_or_raise",
    "validate_protocol_version",
    "validate_streaming_config",
]
