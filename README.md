# ai-lib-python

**Protocol Runtime for AI-Protocol** - A Pythonic implementation for unified AI model interaction.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)

## Overview

`ai-lib-python` is the Python runtime implementation for the [AI-Protocol](https://github.com/hiddenpath/ai-protocol) specification. It embodies the core design principle:

> **All logic is operators, all configuration is protocol.**

Unlike traditional adapter libraries that hardcode provider-specific logic, `ai-lib-python` is a **protocol-driven runtime** that executes AI-Protocol specifications.

## Features

- **Protocol-Driven**: All behavior is driven by YAML/JSON protocol files
- **Unified Interface**: Single API for all AI providers (OpenAI, Anthropic, Gemini, DeepSeek, etc.)
- **Streaming First**: Native async streaming with Python's `async for`
- **Type Safe**: Full type hints with Pydantic v2 models
- **Resilient**: Built-in retry, rate limiting, and circuit breaker support
- **Extensible**: Easy to add new providers via protocol configuration

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
```

## Quick Start

```python
from ai_lib_python import Message
from ai_lib_python.protocol import ProtocolLoader

# Load protocol manifest
loader = ProtocolLoader()
manifest = await loader.load_provider("openai")

# Create messages
messages = [
    Message.system("You are a helpful assistant."),
    Message.user("Hello!"),
]
```

## Supported Providers

- OpenAI (GPT-4o, GPT-4, GPT-3.5)
- Anthropic (Claude 3.5, Claude 3)
- Google (Gemini Pro, Gemini Flash)
- DeepSeek
- Qwen (通义千问)
- Groq
- Mistral
- And more...

## Documentation

See the [AI_LIB_PYTHON_PROPOSAL.md](AI_LIB_PYTHON_PROPOSAL.md) for the full project specification.

## Development

```bash
# Clone the repository
git clone https://github.com/hiddenpath/ai-lib-python.git
cd ai-lib-python

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src

# Linting
ruff check src tests
```

## Project Structure

```
ai-lib-python/
├── src/ai_lib_python/
│   ├── types/          # Type definitions (Message, Tool, Event)
│   ├── protocol/       # Protocol loading and validation
│   ├── transport/      # HTTP transport layer
│   ├── pipeline/       # Stream processing operators
│   ├── resilience/     # Retry, rate limiting, circuit breaker
│   ├── client/         # User-facing API
│   └── errors/         # Error hierarchy
├── tests/
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
└── pyproject.toml
```

## Related Projects

- [AI-Protocol](https://github.com/hiddenpath/ai-protocol) - Protocol specification
- [ai-lib-rust](https://github.com/hiddenpath/ai-lib-rust) - Rust runtime implementation

## License

This project is licensed under either of:

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT License ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.
