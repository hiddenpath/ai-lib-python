"""
Protocol validator using JSON Schema.

Validates manifests against the AI-Protocol JSON Schema specification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_lib_python.errors import ProtocolError

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


@dataclass
class ValidationResult:
    """Result of schema validation."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


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
