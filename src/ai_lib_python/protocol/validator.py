"""
Protocol validator using JSON Schema.

Validates manifests against the AI-Protocol JSON Schema specification.
Also provides protocol version validation and strict streaming validation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_lib_python.errors import ProtocolError

if TYPE_CHECKING:
    from ai_lib_python.protocol.manifest import ProtocolManifest

# Try to import fastjsonschema, fall back to jsonschema
try:
    import fastjsonschema

    _FAST_SCHEMA = True
except ImportError:
    _FAST_SCHEMA = False

try:
    import jsonschema

    _JSON_SCHEMA = True
except ImportError:
    _JSON_SCHEMA = False


# Supported protocol versions
SUPPORTED_PROTOCOL_VERSIONS = ["1.0", "1.1", "1.5", "2.0"]


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid

    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning."""
        self.warnings.append(warning)


class ProtocolValidator:
    """Validates protocol manifests against JSON Schema.

    Uses fastjsonschema for performance if available, falls back to jsonschema.

    Example:
        >>> validator = ProtocolValidator()
        >>> result = validator.validate(manifest_data)
        >>> if not result:
        ...     print("Validation errors:", result.errors)
    """

    def __init__(
        self,
        schema_path: str | Path | None = None,
        offline: bool = False,
    ) -> None:
        """Initialize the validator.

        Args:
            schema_path: Path to custom schema file
            offline: Use embedded schema only (no network)
        """
        self._schema_path = Path(schema_path) if schema_path else None
        self._offline = offline
        self._schema: dict[str, Any] | None = None
        self._compiled_validator: Any = None

    def _load_schema(self) -> dict[str, Any]:
        """Load the JSON Schema."""
        if self._schema is not None:
            return self._schema

        # 1. Try explicit schema path
        if self._schema_path and self._schema_path.exists():
            self._schema = json.loads(self._schema_path.read_text())
            return self._schema

        # 2. Try embedded schema
        embedded_path = Path(__file__).parent / "embedded" / "schema_v1.json"
        if embedded_path.exists():
            self._schema = json.loads(embedded_path.read_text())
            return self._schema

        # 3. Try to load from protocol directory
        if not self._offline:
            from ai_lib_python.protocol.loader import ProtocolLoader

            loader = ProtocolLoader()
            base = loader.base_path
            if base:
                schema_path = base / "schemas" / "v1.json"
                if schema_path.exists():
                    self._schema = json.loads(schema_path.read_text())
                    return self._schema

        # 4. Return minimal schema as fallback
        self._schema = self._get_minimal_schema()
        return self._schema

    def _get_minimal_schema(self) -> dict[str, Any]:
        """Get minimal validation schema as fallback."""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["id", "endpoint"],
            "properties": {
                "id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-_]{1,63}$"},
                "protocol_version": {"type": "string"},
                "endpoint": {
                    "type": "object",
                    "required": ["base_url"],
                    "properties": {
                        "base_url": {"type": "string", "format": "uri"},
                        "protocol": {"type": "string"},
                        "timeout_ms": {"type": "integer", "minimum": 100},
                    },
                },
            },
        }

    def _compile_validator(self) -> None:
        """Compile the validator for performance."""
        schema = self._load_schema()

        if _FAST_SCHEMA:
            try:
                self._compiled_validator = fastjsonschema.compile(schema)
                return
            except Exception:
                pass

        # Fallback to jsonschema (slower but more compatible)
        if _JSON_SCHEMA:
            self._compiled_validator = jsonschema.Draft202012Validator(schema)

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate manifest data against schema.

        Args:
            data: Manifest data to validate

        Returns:
            ValidationResult with valid flag and any errors
        """
        if self._compiled_validator is None:
            self._compile_validator()

        errors: list[str] = []

        if _FAST_SCHEMA and callable(self._compiled_validator):
            try:
                self._compiled_validator(data)
            except fastjsonschema.JsonSchemaValueException as e:
                errors.append(str(e.message))
            except Exception as e:
                errors.append(f"Validation error: {e}")

        elif _JSON_SCHEMA and self._compiled_validator is not None:
            for error in self._compiled_validator.iter_errors(data):
                path = ".".join(str(p) for p in error.absolute_path)
                if path:
                    errors.append(f"{path}: {error.message}")
                else:
                    errors.append(error.message)

        else:
            # No validator available, do minimal checks
            if not isinstance(data, dict):
                errors.append("Manifest must be an object")
            elif "id" not in data:
                errors.append("Missing required field: id")
            elif "endpoint" not in data:
                errors.append("Missing required field: endpoint")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def validate_or_raise(self, data: dict[str, Any]) -> None:
        """Validate manifest data and raise on errors.

        Args:
            data: Manifest data to validate

        Raises:
            ProtocolError: If validation fails
        """
        result = self.validate(data)
        if not result:
            raise ProtocolError(
                f"Schema validation failed: {'; '.join(result.errors)}",
                protocol_path=data.get("id", "unknown"),
            )

    def is_valid(self, data: dict[str, Any]) -> bool:
        """Check if manifest data is valid.

        Args:
            data: Manifest data to validate

        Returns:
            True if valid, False otherwise
        """
        return self.validate(data).valid


def validate_protocol_version(
    manifest: ProtocolManifest | dict[str, Any],
    supported_versions: list[str] | None = None,
) -> ValidationResult:
    """Validate protocol version compatibility.

    Ensures the runtime can handle the protocol version specified.

    Args:
        manifest: Protocol manifest or data dict
        supported_versions: List of supported versions (uses default if None)

    Returns:
        ValidationResult with compatibility status
    """
    result = ValidationResult()
    versions = supported_versions or SUPPORTED_PROTOCOL_VERSIONS

    # Extract version from manifest
    if isinstance(manifest, dict):
        version = manifest.get("protocol_version", "1.0")
    else:
        version = getattr(manifest, "protocol_version", "1.0")

    if not version:
        version = "1.0"

    # Check if version is supported
    if version not in versions:
        result.add_error(
            f"Unsupported protocol version: {version}. "
            f"Runtime supports: {versions}"
        )
    else:
        # Check for version-specific warnings
        if version == "1.0":
            result.add_warning(
                "Protocol version 1.0 is deprecated. Consider upgrading to 1.5+"
            )

    return result


def validate_streaming_config(
    manifest: ProtocolManifest | dict[str, Any],
    strict: bool = False,
) -> ValidationResult:
    """Validate streaming configuration completeness.

    When strict mode is enabled, performs fail-fast checks for streaming
    config to avoid ambiguous runtime behavior.

    Args:
        manifest: Protocol manifest or data dict
        strict: Enable strict validation mode

    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult()

    # Extract streaming config
    if isinstance(manifest, dict):
        streaming = manifest.get("streaming")
        capabilities = manifest.get("capabilities", {})
        tooling = manifest.get("tooling")
    else:
        streaming = getattr(manifest, "streaming", None)
        capabilities = getattr(manifest, "capabilities", None)
        tooling = getattr(manifest, "tooling", None)

    # Check if streaming is claimed as a capability
    supports_streaming = False
    if isinstance(capabilities, dict):
        supports_streaming = capabilities.get("streaming", False)
    elif capabilities is not None:
        supports_streaming = getattr(capabilities, "streaming", False)

    if not supports_streaming and not streaming:
        # No streaming configured, that's fine
        return result

    if supports_streaming and not streaming:
        if strict:
            result.add_error(
                "strict_streaming: manifest.streaming is required when "
                "capabilities.streaming is true"
            )
        else:
            result.add_warning(
                "capabilities.streaming is true but streaming config is missing"
            )
        return result

    if streaming is None:
        return result

    # Validate streaming configuration
    if isinstance(streaming, dict):
        decoder = streaming.get("decoder")
        event_map = streaming.get("event_map", [])
        content_path = streaming.get("content_path")
        tool_call_path = streaming.get("tool_call_path")
    else:
        decoder = getattr(streaming, "decoder", None)
        event_map = getattr(streaming, "event_map", []) or []
        content_path = getattr(streaming, "content_path", None)
        tool_call_path = getattr(streaming, "tool_call_path", None)

    # Check decoder
    if strict:
        if not decoder:
            result.add_error(
                "strict_streaming: streaming.decoder is required for streaming"
            )
        else:
            # Check decoder format
            if isinstance(decoder, dict):
                format_val = decoder.get("format", "")
            else:
                format_val = getattr(decoder, "format", "")

            if not format_val or not str(format_val).strip():
                result.add_error(
                    "strict_streaming: streaming.decoder.format must be non-empty"
                )

    # Check event mapping paths when no explicit event_map
    if not event_map:
        if strict:
            if not content_path or not str(content_path).strip():
                result.add_error(
                    "strict_streaming: streaming.content_path is required "
                    "when streaming.event_map is empty"
                )

            # Check tool_call_path if tools are supported
            supports_tools = False
            if isinstance(capabilities, dict):
                supports_tools = capabilities.get("tools", False)
            elif capabilities is not None:
                supports_tools = getattr(capabilities, "tools", False)

            if tooling is not None:
                supports_tools = True

            if supports_tools and (
                not tool_call_path or not str(tool_call_path).strip()
            ):
                result.add_error(
                    "strict_streaming: streaming.tool_call_path is required "
                    "for tools when streaming.event_map is empty"
                )
        else:
            if not content_path:
                result.add_warning(
                    "streaming.content_path is recommended when event_map is empty"
                )

    return result


def validate_manifest(
    manifest: ProtocolManifest | dict[str, Any],
    strict_streaming: bool | None = None,
    check_version: bool = True,
) -> ValidationResult:
    """Comprehensive manifest validation.

    Performs all validation checks including schema, version compatibility,
    and streaming configuration.

    Args:
        manifest: Protocol manifest to validate
        strict_streaming: Enable strict streaming validation
            (uses AI_LIB_STRICT_STREAMING env var if None)
        check_version: Whether to check protocol version compatibility

    Returns:
        Combined ValidationResult
    """
    result = ValidationResult()

    # Determine strict_streaming setting
    if strict_streaming is None:
        strict_streaming = os.environ.get("AI_LIB_STRICT_STREAMING", "").lower() in (
            "1",
            "true",
            "yes",
        )

    # 1. Validate protocol version
    if check_version:
        version_result = validate_protocol_version(manifest)
        result.errors.extend(version_result.errors)
        result.warnings.extend(version_result.warnings)
        if not version_result.valid:
            result.valid = False

    # 2. Validate streaming configuration
    streaming_result = validate_streaming_config(manifest, strict=strict_streaming)
    result.errors.extend(streaming_result.errors)
    result.warnings.extend(streaming_result.warnings)
    if not streaming_result.valid:
        result.valid = False

    return result


def validate_manifest_or_raise(
    manifest: ProtocolManifest | dict[str, Any],
    strict_streaming: bool | None = None,
) -> None:
    """Validate manifest and raise on errors.

    Args:
        manifest: Protocol manifest to validate
        strict_streaming: Enable strict streaming validation

    Raises:
        ProtocolError: If validation fails
    """
    result = validate_manifest(manifest, strict_streaming=strict_streaming)
    if not result.valid:
        # Get manifest ID for error context
        if isinstance(manifest, dict):
            manifest_id = manifest.get("id", "unknown")
        else:
            manifest_id = getattr(manifest, "id", "unknown")

        raise ProtocolError(
            f"Manifest validation failed: {'; '.join(result.errors)}",
            protocol_path=str(manifest_id),
        )
