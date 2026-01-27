"""
Cost estimation for AI API usage.

Provides pricing information and cost estimation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelPricing:
    """Pricing information for a model.

    Attributes:
        model: Model identifier
        input_price_per_1k: Price per 1K input tokens (USD)
        output_price_per_1k: Price per 1K output tokens (USD)
        context_window: Maximum context window size
        max_output_tokens: Maximum output tokens
    """

    model: str
    input_price_per_1k: float
    output_price_per_1k: float
    context_window: int = 128000
    max_output_tokens: int = 4096

    @property
    def input_price_per_token(self) -> float:
        """Price per input token."""
        return self.input_price_per_1k / 1000

    @property
    def output_price_per_token(self) -> float:
        """Price per output token."""
        return self.output_price_per_1k / 1000


@dataclass
class CostEstimate:
    """Cost estimation result.

    Attributes:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        input_cost: Cost for input tokens (USD)
        output_cost: Cost for output tokens (USD)
        total_cost: Total cost (USD)
        model: Model used for estimation
    """

    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    model: str

    @property
    def total_cost(self) -> float:
        """Total cost in USD."""
        return self.input_cost + self.output_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost,
            "model": self.model,
        }


# Pricing data (as of 2026-01 - prices may change)
# Prices in USD per 1K tokens
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o": ModelPricing(
        model="gpt-4o",
        input_price_per_1k=0.0025,
        output_price_per_1k=0.01,
        context_window=128000,
        max_output_tokens=16384,
    ),
    "gpt-4o-mini": ModelPricing(
        model="gpt-4o-mini",
        input_price_per_1k=0.00015,
        output_price_per_1k=0.0006,
        context_window=128000,
        max_output_tokens=16384,
    ),
    "gpt-4-turbo": ModelPricing(
        model="gpt-4-turbo",
        input_price_per_1k=0.01,
        output_price_per_1k=0.03,
        context_window=128000,
        max_output_tokens=4096,
    ),
    "gpt-3.5-turbo": ModelPricing(
        model="gpt-3.5-turbo",
        input_price_per_1k=0.0005,
        output_price_per_1k=0.0015,
        context_window=16385,
        max_output_tokens=4096,
    ),
    "o1": ModelPricing(
        model="o1",
        input_price_per_1k=0.015,
        output_price_per_1k=0.06,
        context_window=200000,
        max_output_tokens=100000,
    ),
    "o1-mini": ModelPricing(
        model="o1-mini",
        input_price_per_1k=0.003,
        output_price_per_1k=0.012,
        context_window=128000,
        max_output_tokens=65536,
    ),
    # Anthropic
    "claude-3-5-sonnet-20241022": ModelPricing(
        model="claude-3-5-sonnet-20241022",
        input_price_per_1k=0.003,
        output_price_per_1k=0.015,
        context_window=200000,
        max_output_tokens=8192,
    ),
    "claude-3-5-haiku-20241022": ModelPricing(
        model="claude-3-5-haiku-20241022",
        input_price_per_1k=0.0008,
        output_price_per_1k=0.004,
        context_window=200000,
        max_output_tokens=8192,
    ),
    "claude-3-opus-20240229": ModelPricing(
        model="claude-3-opus-20240229",
        input_price_per_1k=0.015,
        output_price_per_1k=0.075,
        context_window=200000,
        max_output_tokens=4096,
    ),
    # Google
    "gemini-1.5-pro": ModelPricing(
        model="gemini-1.5-pro",
        input_price_per_1k=0.00125,
        output_price_per_1k=0.005,
        context_window=2097152,
        max_output_tokens=8192,
    ),
    "gemini-1.5-flash": ModelPricing(
        model="gemini-1.5-flash",
        input_price_per_1k=0.000075,
        output_price_per_1k=0.0003,
        context_window=1048576,
        max_output_tokens=8192,
    ),
    # DeepSeek
    "deepseek-chat": ModelPricing(
        model="deepseek-chat",
        input_price_per_1k=0.00014,
        output_price_per_1k=0.00028,
        context_window=64000,
        max_output_tokens=8192,
    ),
    "deepseek-coder": ModelPricing(
        model="deepseek-coder",
        input_price_per_1k=0.00014,
        output_price_per_1k=0.00028,
        context_window=128000,
        max_output_tokens=8192,
    ),
}

# Model aliases
MODEL_ALIASES: dict[str, str] = {
    "gpt-4o-2024-08-06": "gpt-4o",
    "gpt-4o-2024-11-20": "gpt-4o",
    "gpt-4-turbo-preview": "gpt-4-turbo",
    "gpt-4-0125-preview": "gpt-4-turbo",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    "claude-3.5-haiku": "claude-3-5-haiku-20241022",
    "claude-3-opus": "claude-3-opus-20240229",
    "gemini-pro": "gemini-1.5-pro",
    "gemini-flash": "gemini-1.5-flash",
}


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing information for a model.

    Args:
        model: Model identifier

    Returns:
        ModelPricing or None if not found
    """
    # Check direct match
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Check aliases
    if model in MODEL_ALIASES:
        return MODEL_PRICING.get(MODEL_ALIASES[model])

    # Try partial match
    model_lower = model.lower()
    for key in MODEL_PRICING:
        if key in model_lower or model_lower in key:
            return MODEL_PRICING[key]

    return None


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> CostEstimate:
    """Estimate cost for token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier

    Returns:
        CostEstimate with cost breakdown
    """
    pricing = get_model_pricing(model)

    if pricing:
        input_cost = input_tokens * pricing.input_price_per_token
        output_cost = output_tokens * pricing.output_price_per_token
    else:
        # Default pricing estimate (middle-tier pricing)
        input_cost = input_tokens * 0.001 / 1000
        output_cost = output_tokens * 0.002 / 1000

    return CostEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        model=model,
    )


def get_available_models() -> list[str]:
    """Get list of models with pricing information.

    Returns:
        List of model identifiers
    """
    return list(MODEL_PRICING.keys())


def get_model_context_window(model: str) -> int:
    """Get context window size for a model.

    Args:
        model: Model identifier

    Returns:
        Context window size in tokens (default: 128000)
    """
    pricing = get_model_pricing(model)
    return pricing.context_window if pricing else 128000


def get_model_max_output(model: str) -> int:
    """Get maximum output tokens for a model.

    Args:
        model: Model identifier

    Returns:
        Maximum output tokens (default: 4096)
    """
    pricing = get_model_pricing(model)
    return pricing.max_output_tokens if pricing else 4096
