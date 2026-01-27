#!/usr/bin/env python3
"""
Multi-provider example.

This example demonstrates how to use ai-lib-python with
different AI providers using the same API.

Usage:
    export OPENAI_API_KEY="your-key"
    export ANTHROPIC_API_KEY="your-key"
    export GOOGLE_API_KEY="your-key"
    python examples/providers.py
"""

import asyncio
import os

from ai_lib_python import AiClient

# Define providers and their models
PROVIDERS = [
    ("openai/gpt-4o", "OPENAI_API_KEY"),
    ("openai/gpt-4o-mini", "OPENAI_API_KEY"),
    ("anthropic/claude-3-5-sonnet-20241022", "ANTHROPIC_API_KEY"),
    ("anthropic/claude-3-5-haiku-20241022", "ANTHROPIC_API_KEY"),
    # ("google/gemini-1.5-pro", "GOOGLE_API_KEY"),
    # ("deepseek/deepseek-chat", "DEEPSEEK_API_KEY"),
]

PROMPT = "What is the meaning of life? Answer in exactly one sentence."


async def test_provider(model: str, env_var: str) -> tuple[str, str | None]:
    """Test a single provider."""
    if not os.getenv(env_var):
        return model, f"Skipped (no {env_var})"

    try:
        client = await AiClient.create(model)
        try:
            response = await (
                client.chat()
                .user(PROMPT)
                .max_tokens(100)
                .temperature(0.7)
                .execute()
            )
            return model, response.content
        finally:
            await client.close()
    except Exception as e:
        return model, f"Error: {e}"


async def main() -> None:
    """Test all providers."""
    print("Testing multiple AI providers with the same API")
    print("=" * 60)
    print(f"Prompt: {PROMPT}")
    print("=" * 60)
    print()

    # Test all providers concurrently
    tasks = [test_provider(model, env_var) for model, env_var in PROVIDERS]
    results = await asyncio.gather(*tasks)

    # Display results
    for model, response in results:
        print(f"[{model}]")
        print(f"  {response}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
