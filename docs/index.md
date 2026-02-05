# AI-Lib-Python

The Official Python Runtime for **AI-Protocol**.

```bash
pip install ai-lib-python
```

## What is AI-Lib-Python?

AI-Lib-Python is the canonical Pythonic implementation for unified AI model interaction. It provides a **protocol-driven**, **provider-agnostic** interface with built-in resilience patterns.

### Key Features

- 🔄 **Protocol-Driven**: All logic is operators, all configuration is protocol
- 🚀 **Built-in Resilience**: Retries, circuit breakers, backpressure
- 🌐 **Multi-Provider**: Switch between OpenAI, Anthropic, and more
- 📡 **Streaming Support**: Efficient streaming with cancellation
- 🛡️ **Guardrails**: Content filtering and safety checks
- 🔧 **Type-Safe**: Full type hints with MyPy strict mode
- ✅ **Production Ready**: Comprehensive testing (80%+ coverage)

## Quick Start

```python
import asyncio
from ai_lib_python import AiClient

async def main():
    # Create a client
    client = await AiClient.create("openai/gpt-4o", api_key="sk-...")

    # Simple chat
    response = await client.chat().messages([Message.user("Hello!")]).execute()
    print(response.content)

    # Streaming
    async for event in client.chat().messages([Message.user("Stream")]).stream():
        if event.is_content_delta:
            print(event.as_content_delta.content, end="")

asyncio.run(main())
```

## Installation

### Basic Installation

```bash
pip install ai-lib-python
```

### Full Installation (with all optional dependencies)

```bash
pip install ai-lib-python[full]
```

### Development Installation

```bash
pip install ai-lib-python[dev]
```

## Documentation

- [User Guide](guide.md) - Complete usage guide
- [Guardrails](guardrails.md) - Content filtering and safety
- [API Reference](api/client.md) - API documentation

## Resources

- [GitHub Repository](https://github.com/hiddenpath/ai-lib-python)
- [AI-Protocol Specification](https://github.com/hiddenpath/ai-protocol)
- [Issue Tracker](https://github.com/hiddenpath/ai-lib-python/issues)
- [Examples](../examples/)

## License

Copyright © 2026 AI-Protocol Team. Licensed under MIT or Apache-2.0.
