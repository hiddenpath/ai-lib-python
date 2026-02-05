"""
Production-ready example: Multi-Provider routing and load balancing.

This example demonstrates how to set up robust multi-provider redundancy
with automatic fallback and load balancing.

Key features:
- Fallback configuration
- Load balancing across providers
- Circuit breaking
- Cost optimization
- Performance monitoring
"""

import asyncio
import os
from typing import Any

from ai_lib_python.client import AiClient, AiClientBuilder
from ai_lib_python.routing import (
    ModelInfo,
    ModelCapabilities,
    PricingInfo,
    PerformanceMetrics,
    ModelSelector,
    WeightedSelector,
    CostBasedSelector,
    PerformanceBasedSelector,
)
from ai_lib_python.types.message import Message


# Configuration
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "sk-your-openai-key")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "sk-ant-your-anthropic-key")


# Model configurations
MODELS = {
    "openai/gpt-4o-mini": {
        "provider": "openai",
        "api_key": OPENAI_KEY,
        "capabilities": ModelCapabilities(
            chat=True,
            code=True,
            multimodal=False,
            tools=True,
        ),
        "pricing": PricingInfo(
            per_million_prompt_tokens=0.15,
            per_million_completion_tokens=0.60,
        ),
        "performance": PerformanceMetrics(
            speed_tier=2,  # Fast
            quality_tier=3,  # Good quality
            context_window=128000,
        ),
    },
    "openai/gpt-4o": {
        "provider": "openai",
        "api_key": OPENAI_KEY,
        "capabilities": ModelCapabilities(
            chat=True,
            code=True,
            multimodal=True,
            tools=True,
        ),
        "pricing": PricingInfo(
            per_million_prompt_tokens=2.50,
            per_million_completion_tokens=10.00,
        ),
        "performance": PerformanceMetrics(
            speed_tier=2,
            quality_tier=5,  # Excellent
            context_window=128000,
        ),
    },
    "anthropic/claude-3-5-haiku": {
        "provider": "anthropic",
        "api_key": ANTHROPIC_KEY,
        "capabilities": ModelCapabilities(
            chat=True,
            code=True,
            multimodal=False,
            tools=True,
        ),
        "pricing": PricingInfo(
            per_million_prompt_tokens=0.25,
            per_million_completion_tokens=1.25,
        ),
        "performance": PerformanceMetrics(
            speed_tier=1,  # Very fast
            quality_tier=3,
            context_window=200000,
        ),
    },
    "anthropic/claude-3-5-sonnet": {
        "provider": "anthropic",
        "api_key": ANTHROPIC_KEY,
        "capabilities": ModelCapabilities(
            chat=True,
            code=True,
            multimodal=True,
            tools=True,
        ),
        "pricing": PricingInfo(
            per_million_prompt_tokens=3.00,
            per_million_completion_tokens=15.00,
        ),
        "performance": PerformanceMetrics(
            speed_tier=2,
            quality_tier=5,
            context_window=200000,
        ),
    },
}


def create_model_info(model_id: str, config: dict[str, Any]) -> ModelInfo:
    """Create ModelInfo from configuration."""
    return ModelInfo(
        model_id=model_id,
        provider=config["provider"],
        display_name=model_id,
        capabilities=config["capabilities"],
        pricing=config["pricing"],
        performance=config["performance"],
    )


async def example_simple_fallback() -> None:
    """Example 1: Simple primary with fallback configuration."""
    print("=== Example 1: Simple Fallback ===\n")

    # Build client with primary model and fallback
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .with_fallbacks(["anthropic/claude-3-5-haiku"])
        .api_key_for("anthropic/claude-3-5-haiku", ANTHROPIC_KEY)
        .production_ready()
        .build()
    )

    print("Client configured with:")
    print("  Primary: openai/gpt-4o-mini")
    print("  Fallback: anthropic/claude-3-5-haiku")
    print()

    # Example request
    try:
        response = await client.chat().messages([
            Message.user("Say hello in 5 words or less."),
        ]).execute()

        print(f"Response: {response.content}")
        print(f"Model used: {response.model}")
        print(f"Tokens: {response.total_tokens}")

    except Exception as e:
        print(f"Request failed: {e}")


async def example_cost_optimization() -> None:
    """Example 2: Load balancing for cost optimization."""
    print("\n=== Example 2: Cost-Based Load Balancing ===\n")

    # Build multiple clients for different cost tiers
    low_cost_client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .with_fallbacks(["anthropic/claude-3-5-haiku"])
        .api_key_for("anthropic/claude-3-5-haiku", ANTHROPIC_KEY)
        .build()
    )

    high_quality_client = await (
        AiClient.builder()
        .model("openai/gpt-4o")
        .api_key(OPENAI_KEY)
        .with_fallbacks(["anthropic/claude-3-5-sonnet"])
        .api_key_for("anthropic/claude-3-5-sonnet", ANTHROPIC_KEY)
        .build()
    )

    # Simulate requests with different requirements
    requests = [
        ("Simple greeting", low_cost_client),
        ("Complex reasoning", high_quality_client),
        ("Quick question", low_cost_client),
        ("Detailed analysis", high_quality_client),
    ]

    print("Processing requests with cost-based routing:\n")

    for prompt, client in requests:
        try:
            response = await client.chat().messages([
                Message.user(f"{prompt} - keep it brief."),
            ]).execute()

            print(f"  Prompt: {prompt}")
            print(f"  Model: {response.model}")
            print(f"  Tokens: {response.total_tokens}")
            print(f"  Response: {response.content[:50]}...")
            print()

        except Exception as e:
            print(f"  Failed: {e}\n")


async def example_weighted_selection() -> None:
    """Example 3: Weighted model selection."""
    print("\n=== Example 3: Weighted Model Selection ===\n")

    # Create model selector with weights
    models = [
        create_model_info(model_id, config)
        for model_id, config in MODELS.items()
    ]

    # Weight by speed (50%) and quality (50%)
    selector = WeightedSelector(
        weights={"speed": 0.5, "quality": 0.5}
    )

    # Select model for different use cases
    use_cases = [
        ("Fast response for chatbot", {"speed": 0.7, "quality": 0.3}),
        ("High quality for code review", {"speed": 0.3, "quality": 0.7}),
        ("Balanced for general use", {"speed": 0.5, "quality": 0.5}),
    ]

    for use_case, weights in use_cases:
        # Update weights based on use case
        selector._speed_weight = weights["speed"]
        selector._quality_weight = weights["quality"]

        selected = selector.select(models, {})
        if selected:
            print(f"Use Case: {use_case}")
            print(f"  Selected: {selected.model_id}")
            print(f"  Speed Tier: {selected.performance.speed_tier}")
            print(f"  Quality Tier: {selected.performance.quality_tier}")
            print()


async def example_performance_based() -> None:
    """Example 4: Performance-based routing."""
    print("\n=== Example 4: Performance-Based Routing ===\n")

    models = [
        create_model_info(model_id, config)
        for model_id, config in MODELS.items()
    ]

    selector = PerformanceBasedSelector()

    # Get fastest model
    fastest = selector.select(models, {})
    if fastest:
        print(f"Fastest model: {fastest.model_id}")
        print(f"  Speed tier: {fastest.performance.speed_tier}")
        print()

    # Get highest quality
    selector = PerformanceBasedSelector(prefer_quality=True)
    highest_quality = selector.select(models, {})
    if highest_quality:
        print(f"Highest quality model: {highest_quality.model_id}")
        print(f"  Quality tier: {highest_quality.performance.quality_tier}")
        print()


async def example_multi_region() -> None:
    """Example 5: Multi-region redundancy."""
    print("\n=== Example 5: Multi-Region Redundancy ===\n")

    # Configure clients for different use cases
    # (In production, these might be in different regions)

    # Fast-response tier
    fast_client = await (
        AiClient.builder()
        .model("anthropic/claude-3-5-haiku")
        .api_key(ANTHROPIC_KEY)
        .timeout(10.0)
        .with_fallbacks(["openai/gpt-4o-mini"])
        .api_key_for("openai/gpt-4o-mini", OPENAI_KEY)
        .build()
    )

    # Standard tier
    standard_client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .with_fallbacks(["anthropic/claude-3-5-haiku"])
        .api_key_for("anthropic/claude-3-5-haiku", ANTHROPIC_KEY)
        .build()
    )

    # Premium tier
    premium_client = await (
        AiClient.builder()
        .model("openai/gpt-4o")
        .api_key(OPENAI_KEY)
        .with_fallbacks(["anthropic/claude-3-5-sonnet"])
        .api_key_for("anthropic/claude-3-5-sonnet", ANTHROPIC_KEY)
        .with_fallbacks(["openai/gpt-4o"])
        .api_key_for("openai/gpt-4o", OPENAI_KEY)
        .build()
    )

    tiers = {
        "fast": fast_client,
        "standard": standard_client,
        "premium": premium_client,
    }

    print("Multi-tier configuration:")
    print("  Fast: claude-3-5-haiku -> gpt-4o-mini")
    print("  Standard: gpt-4o-mini -> claude-3-5-haiku") 
    print("  Premium: gpt-4o -> claude-3-5-sonnet -> gpt-4o")
    print()

    # Simulate requests at different tiers
    prompt = "Briefly explain machine learning."

    for tier_name, client in tiers.items():
        try:
            response = await client.chat().messages([
                Message.user(prompt),
            ]).execute()

            print(f"{tier_name.capitalize()} tier:")
            print(f"  Model: {response.model}")
            print(f"  Tokens: {response.total_tokens}")
            print(f"  Response: {response.content[:60]}...")
            print()

        except Exception as e:
            print(f"{tier_name.capitalize()} tier failed: {e}\n")


async def example_circuit_breaker() -> None:
    """Example 6: Circuit breaker with multi-provider."""
    print("\n=== Example 6: Circuit Breaker Integration ===\n")

    # Build client with production-ready settings (includes circuit breaker)
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .with_fallbacks(["anthropic/claude-3-5-haiku"])
        .api_key_for("anthropic/claude-3-5-haiku", ANTHROPIC_KEY)
        .production_ready()  # Enables circuit breaker, retries, etc.
        .build()
    )

    print("Client with circuit breaker enabled:")
    print("  - Automatic circuit opening on failures")
    print("  - Graceful fallback to secondary provider")
    print("  - Automatic circuit recovery")
    print()

    # Simulate a request
    try:
        response = await client.chat().messages([
            Message.user("Test message"),
        ]).execute()

        print(f"Success: {response.content[:50]}...")

    except Exception as e:
        print(f"Request failed after all retries: {e}")


async def main() -> None:
    """Run all examples."""
    print("Production-Ready Multi-Provider Routing\n")
    print("=" * 60)
    print()

    try:
        await example_simple_fallback()
    except Exception as e:
        print(f"Example 1 failed: {e}\n")

    try:
        await example_cost_optimization()
    except Exception as e:
        print(f"Example 2 failed: {e}\n")

    try:
        await example_weighted_selection()
    except Exception as e:
        print(f"Example 3 failed: {e}\n")

    try:
        await example_performance_based()
    except Exception as e:
        print(f"Example 4 failed: {e}\n")

    try:
        await example_multi_region()
    except Exception as e:
        print(f"Example 5 failed: {e}\n")

    try:
        await example_circuit_breaker()
    except Exception as e:
        print(f"Example 6 failed: {e}\n")

    print("\n" + "=" * 60)
    print("Note: Examples require valid API keys for full functionality")
    print("Without keys, they demonstrate the configuration patterns")


if __name__ == "__main__":
    asyncio.run(main())
