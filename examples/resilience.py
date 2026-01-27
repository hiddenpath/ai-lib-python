#!/usr/bin/env python3
"""
Resilience patterns example.

This example demonstrates how to use the built-in resilience patterns:
- Retry with exponential backoff
- Rate limiting
- Circuit breaker
- Fallback chains

Usage:
    export OPENAI_API_KEY="your-api-key"
    export ANTHROPIC_API_KEY="your-api-key"
    python examples/resilience.py
"""

import asyncio

from ai_lib_python import AiClient
from ai_lib_python.resilience import (
    CircuitBreakerConfig,
    FallbackChain,
    RateLimiterConfig,
    RetryConfig,
)


async def production_ready_client() -> None:
    """Create a production-ready client with all resilience patterns."""
    print("Creating production-ready client...")
    print()

    # Use production_ready() for sensible defaults
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o")
        .production_ready()  # Enables all resilience patterns
        .build()
    )

    try:
        # Check resilience status
        print(f"Resilience enabled: {client.is_resilient}")
        print(f"Circuit state: {client.circuit_state}")
        print(f"Current in-flight: {client.current_inflight}")
        print()

        # Make a request
        response = await client.chat().user("Hello!").execute()
        print(f"Response: {response.content}")
        print()

        # Check stats after request
        stats = client.get_resilience_stats()
        print("Resilience stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    finally:
        await client.close()


async def custom_resilience_config() -> None:
    """Create a client with custom resilience configuration."""
    print("\n" + "=" * 50)
    print("Creating client with custom resilience config...")
    print()

    client = await (
        AiClient.builder()
        .model("openai/gpt-4o")
        .with_retry(
            RetryConfig(
                max_retries=5,
                min_delay_ms=500,
                max_delay_ms=10000,
                # retry_on_status={429, 500, 502, 503}
            )
        )
        .with_rate_limit(
            RateLimiterConfig.from_rps(10)  # 10 requests per second
        )
        .with_circuit_breaker(
            CircuitBreakerConfig(
                failure_threshold=3,  # Open after 3 failures
                cooldown_seconds=30,  # Wait 30s before half-open
                success_threshold=2,  # Close after 2 successes
            )
        )
        .max_inflight(20)  # Max 20 concurrent requests
        .build()
    )

    try:
        print("Configuration:")
        stats = client.get_resilience_stats()
        if "backpressure" in stats:
            print(f"  Max concurrent: {stats['backpressure']['max_concurrent']}")
        if "circuit_breaker" in stats:
            print(f"  Circuit state: {stats['circuit_breaker']['state']}")
        print()

        # Make requests
        for i in range(3):
            response = await client.chat().user(f"Count: {i + 1}").execute()
            print(f"Request {i + 1}: {response.content[:50]}...")

    finally:
        await client.close()


async def fallback_chain_example() -> None:
    """Demonstrate fallback chain for multi-model failover."""
    print("\n" + "=" * 50)
    print("Demonstrating fallback chain...")
    print()

    # Create a fallback chain
    chain = FallbackChain()

    # Add targets with priorities (weight)
    async def call_openai() -> str:
        client = await AiClient.create("openai/gpt-4o")
        try:
            response = await client.chat().user("Say 'Hello from OpenAI'").execute()
            return f"OpenAI: {response.content}"
        finally:
            await client.close()

    async def call_anthropic() -> str:
        client = await AiClient.create("anthropic/claude-3-5-sonnet")
        try:
            response = await client.chat().user("Say 'Hello from Anthropic'").execute()
            return f"Anthropic: {response.content}"
        finally:
            await client.close()

    chain.add_target("openai", call_openai, weight=2.0)  # Higher priority
    chain.add_target("anthropic", call_anthropic, weight=1.0)  # Fallback

    print(f"Targets: {chain.get_targets()}")
    print()

    # Execute with fallback
    result = await chain.execute(
        on_fallback=lambda from_t, to_t, err: print(f"Falling back from {from_t} to {to_t}: {err}")
    )

    if result.success:
        print(f"Success from {result.target_used}: {result.value}")
    else:
        print(f"All targets failed: {result.errors}")


async def concurrent_requests() -> None:
    """Demonstrate concurrent request handling with backpressure."""
    print("\n" + "=" * 50)
    print("Demonstrating concurrent requests with backpressure...")
    print()

    # Create client with limited concurrency
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o")
        .max_inflight(3)  # Only 3 concurrent requests
        .build()
    )

    try:
        # Create multiple concurrent tasks
        async def make_request(idx: int) -> str:
            response = await client.chat().user(f"Request {idx}: Say hello").execute()
            return f"Request {idx}: {response.content[:30]}..."

        print("Starting 5 concurrent requests (max 3 in-flight)...")
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        for result in results:
            print(f"  {result}")

        print()
        stats = client.get_resilience_stats()
        if "backpressure" in stats:
            print(f"Peak in-flight: {stats['backpressure']['peak_inflight']}")

    finally:
        await client.close()


async def main() -> None:
    """Run resilience examples."""
    await production_ready_client()
    await custom_resilience_config()
    # Uncomment if you have API keys for both providers:
    # await fallback_chain_example()
    await concurrent_requests()


if __name__ == "__main__":
    asyncio.run(main())
