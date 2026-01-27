#!/usr/bin/env python3
"""
Basic chat completion example.

This example demonstrates the simplest way to use ai-lib-python
for chat completions.

Usage:
    export OPENAI_API_KEY="your-api-key"
    python examples/basic_chat.py
"""

import asyncio

from ai_lib_python import AiClient, Message


async def main() -> None:
    """Run basic chat example."""
    # Create client - automatically loads protocol for the model
    client = await AiClient.create("openai/gpt-4o")

    try:
        # Method 1: Fluent API with chained methods
        response = await (
            client.chat()
            .system("You are a helpful assistant.")
            .user("What is the capital of France?")
            .temperature(0.7)
            .execute()
        )
        print(f"Response: {response.content}")
        print(f"Finish reason: {response.finish_reason}")
        print()

        # Method 2: Using Message objects
        messages = [
            Message.system("You are a Python expert."),
            Message.user("Write a one-liner to read a file."),
        ]

        response = await (
            client.chat()
            .messages(messages)
            .max_tokens(100)
            .execute()
        )
        print(f"Python tip: {response.content}")
        print()

        # Method 3: Get response with statistics
        response, stats = await (
            client.chat()
            .user("Hello!")
            .execute_with_stats()
        )
        print(f"Response: {response.content}")
        print(f"Latency: {stats.latency_ms:.0f}ms")
        if stats.input_tokens and stats.output_tokens:
            print(f"Tokens: {stats.input_tokens} in, {stats.output_tokens} out")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
