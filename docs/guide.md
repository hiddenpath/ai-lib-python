# ai-lib-python User Guide

**Official Python Runtime for AI-Protocol**

This guide covers advanced usage patterns and best practices for using ai-lib-python, the official Python runtime for the AI-Protocol specification.

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Basic Usage](#basic-usage)
3. [Streaming Responses](#streaming-responses)
4. [Tool Calling](#tool-calling)
5. [Multimodal Messages](#multimodal-messages)
6. [Resilience Patterns](#resilience-patterns)
7. [Error Handling](#error-handling)
8. [Protocol Configuration](#protocol-configuration)
9. [Best Practices](#best-practices)

## Installation and Setup

### Requirements

- Python 3.10 or higher
- An API key from at least one supported provider

### Installation

```bash
# Basic installation
pip install ai-lib-python

# Full installation with all optional dependencies
pip install ai-lib-python[full]

# Development installation
pip install ai-lib-python[dev]
```

### Environment Variables

Set your API keys as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

## Basic Usage

### Creating a Client

```python
from ai_lib_python import AiClient

# Simple creation
client = await AiClient.create("openai/gpt-4o")

# With explicit API key
client = await AiClient.create(
    "openai/gpt-4o",
    api_key="sk-...",
)

# With custom base URL (for proxies or compatible APIs)
client = await AiClient.create(
    "openai/gpt-4o",
    base_url="https://my-proxy.example.com/v1",
)

# Using the builder for advanced configuration
client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .api_key("sk-...")
    .timeout(60.0)
    .build()
)
```

### Making Chat Requests

```python
# Fluent API
response = await (
    client.chat()
    .system("You are a helpful assistant.")
    .user("Hello!")
    .temperature(0.7)
    .max_tokens(1000)
    .execute()
)

print(response.content)
print(response.finish_reason)
print(response.usage)  # Token usage stats
```

### Using Message Objects

```python
from ai_lib_python import Message

messages = [
    Message.system("You are a Python tutor."),
    Message.user("Explain list comprehensions."),
    Message.assistant("List comprehensions are..."),
    Message.user("Can you give an example?"),
]

response = await client.chat().messages(messages).execute()
```

### Context Manager

Always properly close clients to release resources:

```python
# Option 1: Async context manager
async with await AiClient.create("openai/gpt-4o") as client:
    response = await client.chat().user("Hello!").execute()

# Option 2: Manual close
client = await AiClient.create("openai/gpt-4o")
try:
    response = await client.chat().user("Hello!").execute()
finally:
    await client.close()
```

## Streaming Responses

Streaming allows you to display responses as they're generated.

### Basic Streaming

```python
async for event in client.chat().user("Tell me a story.").stream():
    if event.is_content_delta:
        print(event.as_content_delta.content, end="", flush=True)
```

### Event Types

```python
async for event in client.chat().user("...").stream():
    match event.event_type:
        case "PartialContentDelta":
            # Text content chunk
            print(event.as_content_delta.content, end="")
            
        case "ThinkingDelta":
            # Chain-of-thought (if enabled)
            print(f"[Thinking: {event.as_thinking_delta.content}]")
            
        case "ToolCallStarted":
            # Tool call beginning
            data = event.as_tool_call_started
            print(f"Calling tool: {data.function_name}")
            
        case "PartialToolCall":
            # Tool call argument chunk
            data = event.as_partial_tool_call
            print(f"  Args: {data.arguments_delta}", end="")
            
        case "ToolCallEnded":
            # Tool call complete
            data = event.as_tool_call_ended
            print(f"Tool {data.tool_call_id} complete")
            
        case "Metadata":
            # Usage statistics
            data = event.as_metadata
            if data.usage:
                print(f"Usage: {data.usage}")
                
        case "StreamEnd":
            # Stream finished
            data = event.as_stream_end
            print(f"\n[Done: {data.finish_reason}]")
            
        case "StreamError":
            # Error occurred
            data = event.as_stream_error
            print(f"[Error: {data.message}]")
```

### Streaming with Statistics

```python
stream_iter, stats = await (
    client.chat()
    .user("Hello!")
    .stream_with_stats()
)

async for event in stream_iter:
    if event.is_content_delta:
        print(event.as_content_delta.content, end="")

print(f"\nTime to first token: {stats.time_to_first_token_ms:.0f}ms")
print(f"Total latency: {stats.latency_ms:.0f}ms")
```

## Tool Calling

### Defining Tools

```python
from ai_lib_python import ToolDefinition

# Method 1: From function schema
calculator = ToolDefinition.from_function(
    name="calculate",
    description="Perform mathematical calculations",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression to evaluate",
            },
        },
        "required": ["expression"],
    },
)

# Method 2: Direct construction
weather_tool = ToolDefinition(
    type="function",
    function=FunctionDefinition(
        name="get_weather",
        description="Get weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    ),
)
```

### Using Tools

```python
# Make request with tools
response = await (
    client.chat()
    .user("What's the weather in Tokyo?")
    .tools([weather_tool, calculator])
    .tool_choice("auto")  # auto, none, required, or specific
    .execute()
)

# Handle tool calls
if response.tool_calls:
    for tool_call in response.tool_calls:
        # Execute the tool
        result = execute_tool(tool_call.function_name, tool_call.arguments)
        
        # Continue conversation with result
        messages = [
            Message.user("What's the weather in Tokyo?"),
            Message.assistant_with_tool_calls(response.tool_calls),
            Message.tool_result(tool_call.id, result),
        ]
        
        final = await client.chat().messages(messages).execute()
```

## Multimodal Messages

### Images from URL

```python
message = Message.user_with_image(
    text="What's in this image?",
    image_url="https://example.com/image.jpg",
)

response = await client.chat().messages([message]).execute()
```

### Images from Base64

```python
import base64

with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

message = Message(
    role=MessageRole.USER,
    content=[
        ContentBlock.text("Describe this image:"),
        ContentBlock.image_base64(image_data, "image/jpeg"),
    ],
)

response = await client.chat().messages([message]).execute()
```

### Multiple Images

```python
message = Message(
    role=MessageRole.USER,
    content=[
        ContentBlock.text("Compare these images:"),
        ContentBlock.image_url("https://example.com/image1.jpg"),
        ContentBlock.image_url("https://example.com/image2.jpg"),
    ],
)
```

## Resilience Patterns

### Production-Ready Configuration

The simplest way to enable all resilience patterns:

```python
client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .production_ready()
    .build()
)
```

This enables:
- Retry with exponential backoff (3 retries)
- Rate limiting (10 RPS)
- Circuit breaker (5 failures)
- Backpressure (10 concurrent)

### Custom Retry Configuration

```python
from ai_lib_python.resilience import RetryConfig, JitterStrategy

client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .with_retry(RetryConfig(
        max_retries=5,
        min_delay_ms=1000,
        max_delay_ms=30000,
        jitter=JitterStrategy.FULL,  # NONE, FULL, or EQUAL
    ))
    .build()
)
```

### Custom Rate Limiting

```python
from ai_lib_python.resilience import RateLimiterConfig

# From requests per second
config = RateLimiterConfig.from_rps(10)

# From requests per minute
config = RateLimiterConfig.from_rpm(600)

client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .with_rate_limit(config)
    .build()
)
```

### Circuit Breaker

```python
from ai_lib_python.resilience import CircuitBreakerConfig

client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .with_circuit_breaker(CircuitBreakerConfig(
        failure_threshold=5,    # Open after 5 failures
        cooldown_seconds=30,    # Wait before testing
        success_threshold=2,    # Close after 2 successes
    ))
    .build()
)

# Check circuit state
print(client.circuit_state)  # "closed", "open", or "half_open"
```

### Fallback Chains

```python
from ai_lib_python.resilience import FallbackChain

chain = FallbackChain()

# Add targets (higher weight = higher priority)
chain.add_target("primary", call_openai, weight=2.0)
chain.add_target("secondary", call_anthropic, weight=1.0)

result = await chain.execute()
if result.success:
    print(f"Success via {result.target_used}: {result.value}")
```

### Monitoring Resilience

```python
# Check current state
print(f"Circuit: {client.circuit_state}")
print(f"In-flight: {client.current_inflight}")

# Get detailed stats
stats = client.get_resilience_stats()
print(stats)

# Reset after issues
client.reset_resilience()
```

## Error Handling

### Error Hierarchy

```python
from ai_lib_python.errors import (
    AiLibError,      # Base class
    ProtocolError,   # Protocol loading/validation
    TransportError,  # Network/HTTP errors
    RemoteError,     # API errors from provider
    PipelineError,   # Stream processing errors
    ValidationError, # Data validation errors
)
```

### Handling Errors

```python
from ai_lib_python.errors import RemoteError, ErrorClass

try:
    response = await client.chat().user("Hello").execute()
except RemoteError as e:
    print(f"API Error: {e.message}")
    print(f"Status: {e.status_code}")
    print(f"Class: {e.error_class}")  # e.g., RATE_LIMITED
    
    if e.retryable:
        print("This error is retryable")
    if e.retry_after:
        print(f"Retry after: {e.retry_after}s")
        
except TransportError as e:
    print(f"Network error: {e}")
    
except AiLibError as e:
    print(f"General error: {e}")
```

### Error Classes

```python
from ai_lib_python.errors import ErrorClass, is_retryable, is_fallbackable

# Standard error classes
ErrorClass.INVALID_REQUEST      # Bad request format
ErrorClass.AUTHENTICATION       # Auth failure
ErrorClass.RATE_LIMITED         # Too many requests
ErrorClass.QUOTA_EXCEEDED       # Billing/quota issue
ErrorClass.NOT_FOUND            # Resource not found
ErrorClass.CONTENT_POLICY       # Content filtered
ErrorClass.CONTEXT_LENGTH       # Too many tokens
ErrorClass.SERVER_ERROR         # Provider error
ErrorClass.TIMEOUT              # Request timeout
ErrorClass.OVERLOADED           # Service overloaded
ErrorClass.UNAVAILABLE          # Service down
ErrorClass.MODEL_NOT_AVAILABLE  # Model unavailable

# Check if error should trigger retry/fallback
if is_retryable(error.error_class):
    # Retry the request
    pass
    
if is_fallbackable(error.error_class):
    # Try fallback provider
    pass
```

## Protocol Configuration

### Loading Protocols

```python
from ai_lib_python.protocol import ProtocolLoader

loader = ProtocolLoader()

# Load by provider ID
manifest = await loader.load_provider("openai")

# Load by model ID
manifest = await loader.load_model("openai/gpt-4o")

# Register custom protocol
loader.register_provider({
    "id": "custom",
    "endpoint": {"base_url": "https://api.custom.com"},
    # ... rest of manifest
})
```

### Custom Protocol Directory

```python
# Via environment variable
export AI_PROTOCOL_PATH="/path/to/protocols"

# Via code
loader = ProtocolLoader(base_path="/path/to/protocols")
```

### Hot Reload (Development)

```python
loader = ProtocolLoader(hot_reload=True)

# Or via client builder
client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .hot_reload(True)
    .build()
)
```

## Best Practices

### 1. Always Close Clients

```python
# Preferred: context manager
async with await AiClient.create("...") as client:
    ...

# Alternative: manual close
client = await AiClient.create("...")
try:
    ...
finally:
    await client.close()
```

### 2. Reuse Clients

Create clients once and reuse them:

```python
# Bad: Creating new client for each request
async def handle_request(prompt):
    client = await AiClient.create("openai/gpt-4o")
    response = await client.chat().user(prompt).execute()
    await client.close()
    return response

# Good: Reuse client
class ChatService:
    def __init__(self):
        self.client = None
    
    async def start(self):
        self.client = await AiClient.create("openai/gpt-4o")
    
    async def stop(self):
        await self.client.close()
    
    async def chat(self, prompt):
        return await self.client.chat().user(prompt).execute()
```

### 3. Use Production-Ready Mode

For production deployments, always enable resilience:

```python
client = await (
    AiClient.builder()
    .model("openai/gpt-4o")
    .production_ready()
    .build()
)
```

### 4. Set Reasonable Timeouts

```python
client = await AiClient.create("openai/gpt-4o", timeout=60.0)
```

### 5. Handle Streaming Errors

```python
try:
    async for event in client.chat().user("...").stream():
        if event.is_stream_error:
            # Handle error gracefully
            logger.error(f"Stream error: {event.as_stream_error.message}")
            break
        if event.is_content_delta:
            yield event.as_content_delta.content
except TransportError as e:
    # Handle connection issues
    logger.error(f"Connection error: {e}")
```

### 6. Log Request Statistics

```python
response, stats = await (
    client.chat()
    .user("Hello!")
    .execute_with_stats()
)

logger.info(
    "Request completed",
    extra={
        "model": stats.model,
        "latency_ms": stats.latency_ms,
        "input_tokens": stats.input_tokens,
        "output_tokens": stats.output_tokens,
    }
)
```

### 7. Use Type Hints

The library is fully typed. Enable strict type checking:

```python
# pyproject.toml
[tool.mypy]
strict = true

# Or mypy.ini
[mypy]
strict = true
```
