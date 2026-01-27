#!/usr/bin/env python3
"""
Tool calling (function calling) example.

This example demonstrates how to define and use tools
that the AI model can call.

Usage:
    export OPENAI_API_KEY="your-api-key"
    python examples/tool_calling.py
"""

import asyncio
import json
from typing import Any

from ai_lib_python import AiClient, Message, ToolDefinition


# Simulated tool implementations
def get_weather(location: str, unit: str = "celsius") -> dict[str, Any]:
    """Simulate getting weather data."""
    # In real app, this would call a weather API
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "Sunny"},
        "London": {"temp": 15, "condition": "Cloudy"},
        "New York": {"temp": 18, "condition": "Partly Cloudy"},
    }
    data = weather_data.get(location, {"temp": 20, "condition": "Unknown"})
    if unit == "fahrenheit":
        data["temp"] = data["temp"] * 9 / 5 + 32
    data["unit"] = unit
    data["location"] = location
    return data


def search_database(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Simulate database search."""
    # In real app, this would query a database
    return [
        {"id": 1, "title": f"Result for: {query}", "score": 0.95},
        {"id": 2, "title": f"Related to: {query}", "score": 0.87},
    ][:limit]


# Define tools
weather_tool = ToolDefinition.from_function(
    name="get_weather",
    description="Get the current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g., 'Tokyo', 'London'",
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit",
            },
        },
        "required": ["location"],
    },
)

search_tool = ToolDefinition.from_function(
    name="search_database",
    description="Search the knowledge database for information",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)


def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Execute a tool by name with given arguments."""
    tools = {
        "get_weather": get_weather,
        "search_database": search_database,
    }
    if name in tools:
        return tools[name](**arguments)
    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    """Run tool calling example."""
    client = await AiClient.create("openai/gpt-4o")

    try:
        # First request: Ask something that requires tools
        print("User: What's the weather like in Tokyo and London?")
        print()

        response = await (
            client.chat()
            .system("You are a helpful assistant with access to weather data.")
            .user("What's the weather like in Tokyo and London?")
            .tools([weather_tool, search_tool])
            .execute()
        )

        # Check if model wants to call tools
        if response.tool_calls:
            print(f"Model wants to call {len(response.tool_calls)} tool(s):")

            # Execute each tool call
            tool_results = []
            for tool_call in response.tool_calls:
                print(f"  - {tool_call.function_name}({tool_call.arguments})")
                result = execute_tool(tool_call.function_name, tool_call.arguments)
                tool_results.append((tool_call, result))
                print(f"    Result: {result}")

            print()

            # Send tool results back to model
            messages = [
                Message.system("You are a helpful assistant with access to weather data."),
                Message.user("What's the weather like in Tokyo and London?"),
                Message.assistant_with_tool_calls(response.tool_calls),
            ]

            # Add tool results
            for tool_call, result in tool_results:
                messages.append(
                    Message.tool_result(tool_call.id, json.dumps(result))
                )

            # Get final response
            final_response = await (
                client.chat()
                .messages(messages)
                .tools([weather_tool, search_tool])
                .execute()
            )

            print(f"Assistant: {final_response.content}")

        else:
            # Model responded without using tools
            print(f"Assistant: {response.content}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
