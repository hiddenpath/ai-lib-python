#!/usr/bin/env python3
"""
Streaming response example.

This example demonstrates how to stream responses token by token
for real-time output.

Usage:
    export ANTHROPIC_API_KEY="your-api-key"
    python examples/streaming.py
"""

import asyncio

from ai_lib_python import AiClient


async def main() -> None:
    """Run streaming example."""
    client = await AiClient.create("anthropic/claude-3-5-sonnet")

    try:
        print("Streaming response:\n")
        print("-" * 50)

        # Stream tokens as they arrive
        async for event in (
            client.chat()
            .system("You are a creative storyteller.")
            .user("Tell me a very short story about a robot learning to paint.")
            .max_tokens(500)
            .stream()
        ):
            # Check event type and handle accordingly
            if event.is_content_delta:
                # Print content as it arrives
                print(event.as_content_delta.content, end="", flush=True)
            elif event.is_stream_end:
                # Stream finished
                end_data = event.as_stream_end
                print(f"\n\n[Stream ended: {end_data.finish_reason}]")
            elif event.is_stream_error:
                # Error occurred
                error_data = event.as_stream_error
                print(f"\n\n[Error: {error_data.message}]")

        print("-" * 50)

        # Example with stats
        print("\n\nStreaming with statistics:")
        print("-" * 50)

        stream_iter, stats = await (
            client.chat()
            .user("Count from 1 to 5.")
            .stream_with_stats()
        )

        async for event in stream_iter:
            if event.is_content_delta:
                print(event.as_content_delta.content, end="", flush=True)

        print(f"\n\nTime to first token: {stats.time_to_first_token_ms:.0f}ms")
        print(f"Total latency: {stats.latency_ms:.0f}ms")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
