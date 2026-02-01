# ai-lib-python

**Official Python Runtime for AI-Protocol** - The canonical Pythonic implementation for unified AI model interaction.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://github.com/hiddenpath/ai-lib-python/actions/workflows/ci.yml/badge.svg)](https://github.com/hiddenpath/ai-lib-python/actions)
[![PyPI](https://img.shields.io/pypi/v/ai-lib-python.svg)](https://pypi.org/project/ai-lib-python/)

## Overview

`ai-lib-python` is the **official Python runtime** for the [AI-Protocol](https://github.com/hiddenpath/ai-protocol) specification. As the canonical Python implementation maintained by the AI-Protocol team, it embodies the core design principle:

> **All logic is operators, all configuration is protocol.**

Unlike traditional adapter libraries that hardcode provider-specific logic, `ai-lib-python` is a **protocol-driven runtime** that executes AI-Protocol specifications.

## Features

- **Protocol-Driven**: All behavior is driven by YAML/JSON protocol files
- **Unified Interface**: Single API for all AI providers (OpenAI, Anthropic, Gemini, DeepSeek, etc.)
- **Streaming First**: Native async streaming with Python's `async for`
- **Type Safe**: Full type hints with Pydantic v2 models
- **Production Ready**: Built-in retry, rate limiting, circuit breaker, and fallback
- **Extensible**: Easy to add new providers via protocol configuration
- **Multimodal**: Support for text, images (base64/URL), and audio

## Installation

```bash
pip install ai-lib-python
```

With optional features:

```bash
# Full installation with keyring and hot-reload support
pip install ai-lib-python[full]

# For Jupyter notebook integration
pip install ai-lib-python[jupyter]

# For development
pip install ai-lib-python[dev]
```

## Quick Start

### Basic Usage

```python
import asyncio
from ai_lib_python import AiClient, Message

async def main():
    # Create client with model
    client = await AiClient.create("openai/gpt-4o")
    
    # Simple chat completion
    response = await (
        client.chat()
        .user("Hello! What's 2+2?")
        .execute()
    )
    print(response.content)
    # Output: 2+2 equals 4.
    
    await client.close()

asyncio.run(main())
```

### Streaming

```python
async def stream_example():
    client = await AiClient.create("anthropic/claude-3-5-sonnet")
    
    async for event in (
        client.chat()
        .system("You are a helpful assistant.")
        .user("Tell me a short story.")
        .stream()
    ):
        if event.is_content_delta:
            print(event.as_content_delta.content, end="", flush=True)
    
    print()  # Newline at end
    await client.close()
```

### With Messages List

```python
from ai_lib_python import Message

messages = [
    Message.system("You are a Python expert."),
    Message.user("How do I read a file in Python?"),
]

response = await (
    client.chat()
    .messages(messages)
    .temperature(0.7)
    .max_tokens(1024)
    .execute()
)
```

### Tool Calling (Function Calling)

```python
from ai_lib_python import ToolDefinition

# Define a tool
weather_tool = ToolDefinition.from_function(
    name="get_weather",
    description="Get current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
        },
        "required": ["location"]
    }
)

# Use tool in request
response = await (
    client.chat()
    .user("What's the weather in Tokyo?")
    .tools([weather_tool])
    .execute()
)

# Check for tool calls
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"Call {tool_call.function_name}: {tool_call.arguments}")
```

### Multimodal (Images)

```python
from ai_lib_python import Message, ContentBlock

# Image from URL
message = Message.user_with_image(
    "What's in this image?",
    image_url="https://example.com/image.jpg"
)

# Image from base64
with open("photo.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

message = Message(
    role=MessageRole.USER,
    content=[
        ContentBlock.text("Describe this image:"),
        ContentBlock.image_base64(image_data, "image/jpeg"),
    ]
)

response = await client.chat().messages([message]).execute()
```

### Production-Ready Configuration

```python
from ai_lib_python import AiClient

# Enable all resilience patterns
client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .production_ready()  # Enables retry, rate limit, circuit breaker
    .with_fallbacks(["anthropic/claude-3-5-sonnet"])
    .build()
)

# Check resilience status
print(f"Circuit state: {client.circuit_state}")
print(f"In-flight requests: {client.current_inflight}")
print(client.get_resilience_stats())
```

### Custom Resilience Configuration

```python
from ai_lib_python import AiClient
from ai_lib_python.resilience import (
    RetryConfig,
    RateLimiterConfig,
    CircuitBreakerConfig,
)

client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .with_retry(RetryConfig(
        max_retries=5,
        min_delay_ms=1000,
        max_delay_ms=30000,
    ))
    .with_rate_limit(RateLimiterConfig.from_rps(10))
    .with_circuit_breaker(CircuitBreakerConfig(
        failure_threshold=5,
        cooldown_seconds=30,
    ))
    .max_inflight(20)
    .build()
)
```

### Context Manager

```python
async with await AiClient.create("openai/gpt-4o") as client:
    response = await client.chat().user("Hello!").execute()
    print(response.content)
# Client automatically closed
```

## Supported Providers

| Provider | Models | Streaming | Tools | Vision |
|----------|--------|-----------|-------|--------|
| OpenAI | GPT-4o, GPT-4, GPT-3.5 | ✅ | ✅ | ✅ |
| Anthropic | Claude 3.5, Claude 3 | ✅ | ✅ | ✅ |
| Google | Gemini Pro, Gemini Flash | ✅ | ✅ | ✅ |
| DeepSeek | DeepSeek Chat, Coder | ✅ | ✅ | ❌ |
| Qwen | Qwen2.5, Qwen-Max | ✅ | ✅ | ✅ |
| Groq | Llama, Mixtral | ✅ | ✅ | ❌ |
| Mistral | Mistral Large, Medium | ✅ | ✅ | ❌ |

## API Reference

### Core Classes

- **`AiClient`**: Main entry point for AI model interaction
- **`Message`**: Represents a chat message with role and content
- **`ContentBlock`**: Content blocks for multimodal messages
- **`ToolDefinition`**: Tool/function definition for function calling
- **`StreamingEvent`**: Events from streaming responses

### Resilience Classes

- **`RetryPolicy`**: Exponential backoff with jitter
- **`RateLimiter`**: Token bucket rate limiting
- **`CircuitBreaker`**: Circuit breaker pattern
- **`Backpressure`**: Concurrency limiting
- **`FallbackChain`**: Multi-target failover

### Error Classes

- **`AiLibError`**: Base error class
- **`ProtocolError`**: Protocol loading/validation errors
- **`TransportError`**: HTTP transport errors
- **`RemoteError`**: API errors from providers

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AiClient                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ ChatRequest │  │  Resilience │  │    Protocol         │  │
│  │   Builder   │  │  Executor   │  │    Loader           │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼───────────────────┼──────────────┘
          │                │                   │
          ▼                ▼                   ▼
┌─────────────────┐ ┌──────────────┐ ┌─────────────────────┐
│   HttpTransport │ │   Pipeline   │ │  ProtocolManifest   │
│   (httpx)       │ │   (decode→   │ │  (YAML/JSON)        │
│                 │ │   select→    │ │                     │
│                 │ │   map)       │ │                     │
└─────────────────┘ └──────────────┘ └─────────────────────┘
```

## Development

```bash
# Clone the repository
git clone https://github.com/hiddenpath/ai-lib-python.git
cd ai-lib-python

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/ai_lib_python

# Type checking
mypy src

# Linting
ruff check src tests

# Format code
ruff format src tests
```

## Project Structure

```
ai-lib-python/
├── src/ai_lib_python/
│   ├── __init__.py         # Package exports
│   ├── types/              # Type definitions
│   │   ├── message.py      # Message, ContentBlock
│   │   ├── tool.py         # ToolDefinition, ToolCall
│   │   └── events.py       # StreamingEvent types
│   ├── protocol/           # Protocol layer
│   │   ├── manifest.py     # ProtocolManifest models
│   │   ├── loader.py       # Protocol loading
│   │   └── validator.py    # Schema validation
│   ├── transport/          # HTTP transport
│   │   ├── http.py         # HttpTransport
│   │   └── auth.py         # API key resolution
│   ├── pipeline/           # Stream processing
│   │   ├── decode.py       # SSE/NDJSON decoders
│   │   ├── select.py       # JSONPath selectors
│   │   ├── accumulate.py   # Tool call accumulator
│   │   └── event_map.py    # Event mappers
│   ├── resilience/         # Resilience patterns
│   │   ├── retry.py        # RetryPolicy
│   │   ├── rate_limiter.py # RateLimiter
│   │   ├── circuit_breaker.py
│   │   ├── backpressure.py
│   │   ├── fallback.py     # FallbackChain
│   │   └── executor.py     # ResilientExecutor
│   ├── client/             # User API
│   │   ├── core.py         # AiClient
│   │   ├── builder.py      # Builders
│   │   └── response.py     # ChatResponse
│   └── errors/             # Error hierarchy
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation
├── examples/               # Example scripts
└── pyproject.toml
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `GOOGLE_API_KEY` | Google AI API key | - |
| `AI_PROTOCOL_PATH` | Custom protocol directory | - |
| `AI_HTTP_TIMEOUT_SECS` | HTTP timeout | 60 |
| `AI_LIB_MAX_INFLIGHT` | Max concurrent requests | 10 |

## Related Projects

- [AI-Protocol](https://github.com/hiddenpath/ai-protocol) - Protocol specification
- [ai-lib-rust](https://github.com/hiddenpath/ai-lib-rust) - Rust runtime implementation

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under either of:

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT License ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.
