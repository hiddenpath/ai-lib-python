"""
Guardrails module for content filtering and safety checks.

This module provides a flexible framework for filtering and validating
both user inputs and AI model outputs to ensure safety and compliance.

Core principle: All logic is operators, all configuration is protocol.
"""

from ai_lib_python.guardrails.base import Guardrail, GuardrailViolation, GuardrailResult
from ai_lib_python.guardrails.filters import (
    KeywordFilter,
    RegexFilter,
    LengthFilter,
    ProfanityFilter,
    UrlFilter,
    EmailFilter,
)
from ai_lib_python.guardrails.validators import ContentValidator

__all__ = [
    # Base classes
    "Guardrail",
    "GuardrailViolation",
    "GuardrailResult",
    # Filters
    "KeywordFilter",
    "RegexFilter",
    "LengthFilter",
    "ProfanityFilter",
    "UrlFilter",
    "EmailFilter",
    # Validators
    "ContentValidator",
]
