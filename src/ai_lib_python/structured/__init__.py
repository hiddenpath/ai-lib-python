"""
Structured output module for ai-lib-python.

Provides JSON mode and schema-based output validation.
"""

from ai_lib_python.structured.json_mode import (
    JsonMode,
    JsonModeConfig,
    StructuredOutput,
)
from ai_lib_python.structured.schema import (
    SchemaGenerator,
    json_schema_from_pydantic,
    json_schema_from_type,
)
from ai_lib_python.structured.validator import (
    OutputValidator,
    ValidationError,
    ValidationResult,
)

__all__ = [
    "JsonMode",
    "JsonModeConfig",
    "OutputValidator",
    "SchemaGenerator",
    "StructuredOutput",
    "ValidationError",
    "ValidationResult",
    "json_schema_from_pydantic",
    "json_schema_from_type",
]
