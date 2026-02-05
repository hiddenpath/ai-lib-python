"""
Production-ready example: Handling concurrent requests.

This example demonstrates how to handle multiple concurrent AI requests
efficiently with proper resource management and error handling.

Key features:
- Concurrent request processing
- Max inflight limits
- Batching strategies
- Error isolation
- Performance optimization
"""

import asyncio
import os
import time

from ai_lib_python.client import AiClient
from ai_lib_python.types.message import Message


# Configuration
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "sk-your-openai-key")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "sk-ant-your-anthropic-key")


async def fetch_simple_response(client: AiClient, prompt: str, request_id: int) -> tuple[int, str, float]:
    """Fetch a simple response from the AI model.

    Args:
        client: AiClient instance
        prompt: User prompt
        request_id: Request identifier

    Returns:
        Tuple of (request_id, response_content, latency_ms)
    """
    start_time = time.perf_counter()

    try:
        response = await client.chat().messages([Message.user(prompt)]).execute()

        latency_ms = (time.perf_counter() - start_time) * 1000
        return (request_id, response.content, latency_ms)

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"Request {request_id} failed: {e}")
        return (request_id, f"ERROR: {e}", latency_ms)


async def stream_response(client: AiClient, prompt: str, request_id: int) -> tuple[int, str, float]:
    """Fetch and stream a response from the AI model.

    Args:
        client: AiClient instance
        prompt: User prompt
        request_id: Request identifier

    Returns:
        Tuple of (request_id, full_content, latency_ms)
    """
    start_time = time.perf_counter()
    content_parts = []

    try:
        async for event in client.chat().messages([Message.user(prompt)]).stream():
            if event.is_content_delta:
                content_parts.append(event.as_content_delta.content)

        latency_ms = (time.perf_counter() - start_time) * 1000
        full_content = "".join(content_parts)
        return (request_id, full_content, latency_ms)

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"Stream request {request_id} failed: {e}")
        return (request_id, f"ERROR: {e}", latency_ms)


async def example_concurrent_requests() -> None:
    """Example: Process multiple requests concurrently."""
    print("=== Example 1: Concurrent Requests ===\n")

    # Create client with max inflight limit
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .max_inflight(5)  # Limit to 5 concurrent requests
        .timeout(30.0)
        .build()
    )

    # Define prompts for multiple requests
    prompts = [
        f"What is the capital of country {i}?" for i in range(10)
    ]

    print(f"Processing {len(prompts)} requests concurrently (max_inflight=5)...\n")

    # Create tasks (they'll be limited by max_inflight internally)
    tasks = [
        fetch_simple_response(client, prompt, i)
        for i, prompt in enumerate(prompts)
    ]

    # Wait for all to complete
    start_time = time.perf_counter()
    results = await asyncio.gather(*tasks)
    total_time = (time.perf_counter() - start_time) * 1000

    # Report results
    successes = sum(1 for _, content, _ in results if not content.startswith("ERROR"))
    avg_latency = sum(latency for _, _, latency in results) / len(results)

    print(f"\nResults:")
    print(f"  Total time: {total_time:.0f}ms")
    print(f"  Per-request avg: {total_time / len(prompts):.0f}ms")
    print(f"  Successes: {successes}/{len(prompts)}")
    print(f"  Avg latency: {avg_latency:.0f}ms")

    # Show some responses
    print(f"\nSample responses:")
    for req_id, content, latency in results[:3]:
        print(f"  [{req_id}] ({latency:.0f}ms): {content[:80]}...")


async def example_mixed_operations() -> None:
    """Example: Mix of streaming and non-streaming requests."""
    print("\n=== Example 2: Mixed Streaming/Non-Streaming ===\n")

    # Create client
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .max_inflight(3)
        .build()
    )

    # Mix streaming and non-streaming tasks
    tasks = [
        fetch_simple_response(client, "Short response 1", 0),
        stream_response(client, "Stream this response", 1),
        fetch_simple_response(client, "Short response 2", 2),
        stream_response(client, "Stream another response", 3),
        fetch_simple_response(client, "Short response 3", 4),
    ]

    print("Processing mixed requests (3 streaming, 2 non-streaming)...\n")

    start_time = time.perf_counter()
    results = await asyncio.gather(*tasks)
    total_time = (time.perf_counter() - start_time) * 1000

    print(f"\nCompleted in {total_time:.0f}ms")
    for req_id, content, latency in results:
        mode = "STREAM" if "Stream" in ["Stream this", "Stream another"][req_id % 5 < 2 or req_id == 1 or req_id == 3] else "CHUNK"
        print(f"  [{req_id}] ({mode}, {latency:.0f}ms): {content[:60]}...")


async def example_batch_processing() -> None:
    """Example: Process requests in batches."""
    print("\n=== Example 3: Batch Processing ===\n")

    client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .max_inflight(3)
        .timeout(20.0)
        .build()
    )

    # Process 15 requests in batches of 5
    all_prompts = [f"Generate a short fact about topic {i}" for i in range(15)]
    batch_size = 5

    print(f"Processing {len(all_prompts)} requests in batches of {batch_size}...\n")

    all_results = []
    total_start = time.perf_counter()

    for batch_num in range(0, len(all_prompts), batch_size):
        batch = all_prompts[batch_num:batch_num + batch_size]
        batch_start = time.perf_counter()

        # Process batch
        tasks = [
            fetch_simple_response(client, prompt, batch_num + i)
            for i, prompt in enumerate(batch)
        ]

        results = await asyncio.gather(*tasks)
        all_results.extend(results)

        batch_time = (time.perf_counter() - batch_start) * 1000
        print(f"Batch {batch_num // batch_size + 1} completed in {batch_time:.0f}ms")

    total_time = (time.perf_counter() - total_start) * 1000

    print(f"\nTotal processing time: {total_time:.0f}ms")
    print(f"Average per batch: {total_time / max(1, len(all_prompts) // batch_size):.0f}ms")


async def example_multi_provider() -> None:
    """Example: Concurrent requests to multiple providers."""
    print("\n=== Example 4: Multi-Provider Concurrent ===\n")

    # Create clients for different providers
    openai_client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .max_inflight(2)
        .build()
    )

    anthropic_client = await (
        AiClient.builder()
        .model("anthropic/claude-3-5-haiku")
        .api_key(ANTHROPIC_KEY)
        .max_inflight(2)
        .build()
    )

    # Distribute requests across providers
    tasks = [
        fetch_simple_response(openai_client, "OpenAI response 1", 0),
        fetch_simple_response(anthropic_client, "Anthropic response 1", 1),
        fetch_simple_response(openai_client, "OpenAI response 2", 2),
        fetch_simple_response(anthropic_client, "Anthropic response 2", 3),
    ]

    print("Processing requests across multiple providers...\n")

    start_time = time.perf_counter()
    results = await asyncio.gather(*tasks)
    total_time = (time.perf_counter() - start_time) * 1000

    print(f"\nCompleted in {total_time:.0f}ms")
    for req_id, content, latency in results:
        provider = "OpenAI" if req_id % 2 == 0 else "Anthropic"
        print(f"  [{req_id}] {provider} ({latency:.0f}ms): {content[:60]}...")


async def example_error_isolation() -> None:
    """Example: Error isolation in concurrent processing."""
    print("\n=== Example 5: Error Isolation ===\n")

    # Create client
    client = await (
        AiClient.builder()
        .model("openai/gpt-4o-mini")
        .api_key(OPENAI_KEY)
        .max_inflight(3)
        .retry(max_attempts=2, backoff=0.1)
        .build()
    )

    # Mix of potentially failing requests
    tasks = [
        fetch_simple_response(client, "Normal request 1", 0),
        fetch_simple_response(client, "Normal request 2", 1),
        fetch_simple_response(client, "Normal request 3", 2),
    ]

    print("Processing requests with error handling...\n")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results handling both successes and failures
    successful = []
    failed = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Request {i} raised exception: {result}")
            failed.append(i)
        else:
            req_id, content, latency = result
            if content.startswith("ERROR"):
                print(f"Request {req_id} failed: {content}")
                failed.append(req_id)
            else:
                print(f"Request {req_id} succeeded: {content[:50]}...")
                successful.append(req_id)

    print(f"\nSummary: {len(successful)} succeeded, {len(failed)} failed")


async def main() -> None:
    """Run all examples."""
    print("Production-Ready Concurrent Request Handling\n")
    print("=" * 60)
    print()

    # Run examples (note: some require actual API keys)
    try:
        await example_concurrent_requests()
    except Exception as e:
        print(f"Example 1 failed: {e}")
        print("(Set OPENAI_API_KEY to run with real API calls)\n")

    try:
        await example_mixed_operations()
    except Exception as e:
        print(f"Example 2 failed: {e}\n")

    try:
        await example_batch_processing()
    except Exception as e:
        print(f"Example 3 failed: {e}\n")

    try:
        await example_multi_provider()
    except Exception as e:
        print(f"Example 4 failed: {e}\n")

    try:
        await example_error_isolation()
    except Exception as e:
        print(f"Example 5 failed: {e}\n")

    print("\n" + "=" * 60)
    print("Note: These examples work best with actual API keys")
    print("Without keys, they demonstrate the patterns for concurrent processing")


if __name__ == "__main__":
    asyncio.run(main())
