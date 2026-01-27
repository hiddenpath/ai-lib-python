#!/usr/bin/env python3
"""
Multimodal (images) example.

This example demonstrates how to send images to AI models
for vision-based tasks.

Usage:
    export OPENAI_API_KEY="your-api-key"
    python examples/multimodal.py
"""

import asyncio
import base64
from pathlib import Path

from ai_lib_python import AiClient, ContentBlock, Message, MessageRole


async def analyze_image_from_url() -> None:
    """Analyze an image from a URL."""
    client = await AiClient.create("openai/gpt-4o")

    try:
        print("Analyzing image from URL...")
        print()

        # Use helper method for image URL
        message = Message.user_with_image(
            text="What do you see in this image? Describe it briefly.",
            image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png",
        )

        response = await client.chat().messages([message]).max_tokens(200).execute()
        print(f"Description: {response.content}")

    finally:
        await client.close()


async def analyze_image_from_file(image_path: str) -> None:
    """Analyze an image from a local file."""
    client = await AiClient.create("anthropic/claude-3-5-sonnet")

    try:
        # Read and encode image
        path = Path(image_path)
        if not path.exists():
            print(f"Image file not found: {image_path}")
            return

        with path.open("rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # Determine media type from extension
        suffix = path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/jpeg")

        print(f"Analyzing image from file: {image_path}")
        print()

        # Create message with image content block
        message = Message(
            role=MessageRole.USER,
            content=[
                ContentBlock.text("Analyze this image in detail:"),
                ContentBlock.image_base64(image_data, media_type),
            ],
        )

        response = await client.chat().messages([message]).max_tokens(500).execute()
        print(f"Analysis: {response.content}")

    finally:
        await client.close()


async def compare_images() -> None:
    """Compare multiple images."""
    client = await AiClient.create("openai/gpt-4o")

    try:
        print("Comparing multiple images...")
        print()

        # Message with multiple images
        message = Message(
            role=MessageRole.USER,
            content=[
                ContentBlock.text("Compare these two images and describe the differences:"),
                ContentBlock.image_url(
                    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Camponotus_flavomarginatus_ant.jpg/320px-Camponotus_flavomarginatus_ant.jpg"
                ),
                ContentBlock.image_url(
                    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Honeybee_landing_on_milkthistle02.jpg/320px-Honeybee_landing_on_milkthistle02.jpg"
                ),
            ],
        )

        response = await client.chat().messages([message]).max_tokens(300).execute()
        print(f"Comparison: {response.content}")

    finally:
        await client.close()


async def main() -> None:
    """Run multimodal examples."""
    # Example 1: URL-based image
    await analyze_image_from_url()
    print("\n" + "=" * 50 + "\n")

    # Example 2: Multiple images comparison
    await compare_images()

    # Example 3: Local file (uncomment to use)
    # await analyze_image_from_file("path/to/your/image.jpg")


if __name__ == "__main__":
    asyncio.run(main())
