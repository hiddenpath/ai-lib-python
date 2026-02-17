# ai-lib-python

**Official Python Runtime for AI-Protocol** - The canonical Pythonic implementation for unified AI model interaction.

[![PyPI Version](https://img.shields.io/pypi/v/ai-lib-python.svg)](https://pypi.org/project/ai-lib-python/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://github.com/hiddenpath/ai-lib-python/actions/workflows/ci.yml/badge.svg)](https://github.com/hiddenpath/ai-lib-python/actions)

## 🎯 Design Philosophy

`ai-lib-python` is the official Python runtime implementation for the [AI-Protocol](https://github.com/hiddenpath/ai-protocol) specification. It embodies the core design principle:

> **一切逻辑皆算子，一切配置皆协议** (All logic is operators, all configuration is protocol)

Unlike traditional adapter libraries that hardcode provider-specific logic, `ai-lib-python` is a **protocol-driven runtime** that executes AI-Protocol specifications. This means:

- **Zero hardcoded provider logic**: All behavior is driven by protocol manifests (YAML/JSON configurations)
- **Operator-based architecture**: Processing is done through composable operators (Decoder → Selector → Accumulator → FanOut → EventMapper)
- **Hot-reloadable**: Protocol configurations can be updated without restarting the application
- **Unified interface**: Developers interact with a single, consistent API regardless of the underlying provider

## 🚀 Quick Start

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

## ✨ Features

- **Protocol-Driven**: All behavior is driven by YAML/JSON protocol files
- **Unified Interface**: Single API for all AI providers (OpenAI, Anthropic, Gemini, DeepSeek, etc.)
- **Streaming First**: Native async streaming with Python's `async for`
- **Type Safe**: Full type hints with Pydantic v2 models
- **Production Ready**: Built-in retry, rate limiting, circuit breaker, and fallback
- **Extensible**: Easy to add new providers via protocol configuration
- **Multimodal**: Support for text, images (base64/URL), and audio
- **Telemetry**: Structured logging, metrics, distributed tracing, and user feedback collection
- **Token Counting**: tiktoken integration and cost estimation
- **Connection Pooling**: Efficient HTTP connection management
- **Request Batching**: Parallel execution with concurrency control
- **Model Routing**: Smart model selection with load balancing strategies
- **Embeddings**: Embedding generation with vector operations
- **Structured Output**: JSON mode with schema validation
- **Response Caching**: Multi-backend caching with TTL support
- **Plugin System**: Extensible hooks and middleware architecture
- **Stream Cancellation**: Cooperative cancellation for streaming operations

## 🔄 V2 Protocol Alignment

Starting with v0.5.0, `ai-lib-python` aligns with the **AI-Protocol V2** specification. V0.7.0 adds full V2 runtime support including V2 manifest parsing, provider drivers, MCP tool bridge, Computer Use abstraction, extended multimodal, and capability registry.

### Standard Error Codes (V2)

All provider errors are classified into 13 standard error codes with unified retry/fallback semantics:

| Code | Name | Retryable | Fallbackable |
|------|------|-----------|--------------|
| E1001 | `invalid_request` | No | No |
| E1002 | `authentication` | No | Yes |
| E1003 | `permission_denied` | No | No |
| E1004 | `not_found` | No | No |
| E1005 | `request_too_large` | No | No |
| E2001 | `rate_limited` | Yes | Yes |
| E2002 | `quota_exhausted` | No | Yes |
| E3001 | `server_error` | Yes | Yes |
| E3002 | `overloaded` | Yes | Yes |
| E3003 | `timeout` | Yes | Yes |
| E4001 | `conflict` | Yes | No |
| E4002 | `cancelled` | No | No |
| E9999 | `unknown` | No | No |

Classification follows a priority pipeline: provider-specific error code → HTTP status override → standard HTTP mapping → `E9999`.

### Compliance Tests

Cross-runtime behavioral consistency is verified by a shared YAML-based test suite from the `ai-protocol` repository:

```bash
# Run compliance tests
pytest tests/compliance/ -v

# With explicit compliance directory
COMPLIANCE_DIR=../ai-protocol/tests/compliance pytest tests/compliance/ -v
```

For details, see [CROSS_RUNTIME.md](https://github.com/hiddenpath/ai-protocol/blob/main/docs/CROSS_RUNTIME.md).

### Testing with ai-protocol-mock

For integration and MCP e2e tests without real API calls, use [ai-protocol-mock](https://github.com/hiddenpath/ai-protocol-mock):

```bash
# Start mock server (from ai-protocol-mock repo)
docker-compose up -d

# Run tests with mock
MOCK_HTTP_URL=http://localhost:4010 MOCK_MCP_URL=http://localhost:4010/mcp pytest tests/ -v
```

Or in code: `AiClient.create("openai/gpt-4o", base_url="http://localhost:4010")`

## 📦 Installation

```bash
pip install ai-lib-python
```

With optional features (V2 capability extras):

```bash
# Full installation with all features
pip install ai-lib-python[full]

# V2 capability extras
pip install ai-lib-python[vision]        # Image processing (Pillow)
pip install ai-lib-python[audio]         # Audio processing (soundfile)
pip install ai-lib-python[embeddings]    # Embedding generation
pip install ai-lib-python[structured]    # Structured output / JSON mode
pip install ai-lib-python[batch]         # Batch processing
pip install ai-lib-python[agentic]       # Agent workflow support

# Infrastructure extras
pip install ai-lib-python[telemetry]     # OpenTelemetry integration
pip install ai-lib-python[tokenizer]     # tiktoken token counting

# For Jupyter notebook integration
pip install ai-lib-python[jupyter]

# For development
pip install ai-lib-python[dev]
```

## 🔧 Configuration

The library automatically looks for protocol manifests in the following locations (in order):

1. Custom path set via `AI_PROTOCOL_PATH` environment variable
2. Common dev paths: `ai-protocol/`, `../ai-protocol/`, `../../ai-protocol/`
3. Last resort: GitHub raw `hiddenpath/ai-protocol` (main)

Provider manifests are resolved in a backward-compatible order:
`dist/v1/providers/<id>.json` → `v1/providers/<id>.yaml`.

### Useful Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_PROTOCOL_PATH` | Custom protocol directory (local path or GitHub URL) | - |
| `AI_HTTP_TIMEOUT_SECS` | HTTP timeout in seconds | 60 |
| `AI_LIB_MAX_INFLIGHT` | Max concurrent requests | 10 |
| `AI_LIB_RPS` | Rate limit (requests per second) | - |
| `AI_LIB_BREAKER_FAILURE_THRESHOLD` | Circuit breaker failure threshold | 5 |
| `AI_LIB_BREAKER_COOLDOWN_SECS` | Circuit breaker cooldown seconds | 30 |
| `MOCK_HTTP_URL` | Mock server URL for testing (ai-protocol-mock) | - |
| `MOCK_MCP_URL` | Mock MCP endpoint for testing | - |

### Provider API Keys

The runtime reads API keys from environment variables in the format: `<PROVIDER_ID>_API_KEY`

```bash
# Set API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
```

**Recommended for production**: Use environment variables for CI/CD, containers, and production deployments.

## 🎨 Protocol-Driven Architecture

No `match provider` statements. All logic is derived from protocol configuration:

```python
# The pipeline is built dynamically from protocol manifest
pipeline = Pipeline.from_manifest(manifest)

# Operators are configured via manifests (YAML/JSON), not hardcoded
# Adding a new provider requires zero code changes
```

### Hot Reload

Protocol configurations can be updated at runtime:

```python
from ai_lib_python.protocol import ProtocolLoader

loader = ProtocolLoader(hot_reload=True)
# Protocol changes are automatically picked up
```

## 🚀 Usage Examples

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

### Token Counting and Cost Estimation

```python
from ai_lib_python.tokens import TokenCounter, estimate_cost, get_model_pricing

# Count tokens
counter = TokenCounter.for_model("gpt-4o")
token_count = counter.count("Hello, how are you?")
print(f"Token count: {token_count}")

# Count message tokens
messages = [Message.user("Hello!"), Message.assistant("Hi there!")]
total_tokens = counter.count_messages(messages)

# Estimate cost
cost = estimate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o")
print(f"Estimated cost: ${cost.total_cost:.4f}")

# Get model pricing info
pricing = get_model_pricing("gpt-4o")
print(f"Input: ${pricing.input_price_per_1k}/1K tokens")
print(f"Context window: {pricing.context_window} tokens")
```

### Metrics and Telemetry

```python
from ai_lib_python.telemetry import (
    get_logger,
    MetricsCollector,
    MetricLabels,
    Tracer,
)

# Structured logging
logger = get_logger("my_app")
logger.info("Request started", model="gpt-4o", tokens=100)

# Metrics collection
collector = MetricsCollector()
labels = MetricLabels(provider="openai", model="gpt-4o")
collector.record_request(labels, latency=0.5, status="success", tokens_in=100, tokens_out=50)

# Get metrics snapshot
snapshot = collector.get_snapshot()
print(f"Total requests: {snapshot.total_requests}")
print(f"P99 latency: {snapshot.latency_p99_ms:.2f}ms")

# Export to Prometheus format
prometheus_metrics = collector.to_prometheus()

# Distributed tracing
tracer = Tracer("my_service")
with tracer.span("api_call") as span:
    span.set_attribute("model", "gpt-4o")
    # ... do work
```

### Batch Processing

```python
from ai_lib_python.batch import BatchExecutor, BatchConfig

# Execute multiple requests concurrently
async def process_question(question: str) -> str:
    client = await AiClient.create("openai/gpt-4o")
    response = await client.chat().user(question).execute()
    await client.close()
    return response.content

questions = ["What is AI?", "What is Python?", "What is async?"]

executor = BatchExecutor(process_question, max_concurrent=5)
result = await executor.execute(questions)

print(f"Successful: {result.successful_count}")
print(f"Failed: {result.failed_count}")
for answer in result.get_successful_results():
    print(answer)
```

### Connection Pooling

```python
from ai_lib_python.transport import ConnectionPool, PoolConfig

# Create connection pool with custom config
pool = ConnectionPool(PoolConfig.high_throughput())

# Use pooled connections
async with pool:
    client = await pool.get_client("openai", "https://api.openai.com")
    response = await client.post("/v1/chat/completions", json=payload)

# Get pool statistics
stats = pool.get_stats("openai")
print(f"Active connections: {stats['openai']['active_connections']}")
```

### Model Routing & Selection

```python
from ai_lib_python.routing import (
    ModelManager, ModelInfo, create_openai_models, create_anthropic_models,
    CostBasedSelector, QualityBasedSelector,
)

# Create a model manager with pre-configured models
manager = create_openai_models()
manager.merge(create_anthropic_models())

# Select model by capability
code_models = manager.filter_by_capability("code_generation")
print(f"Code models: {[m.name for m in code_models]}")

# Select cheapest model
selector = CostBasedSelector()
cheapest = selector.select(manager.list_models())
print(f"Cheapest: {cheapest.name} @ ${cheapest.pricing.input_cost_per_1k}/1K")

# Select highest quality model
quality_selector = QualityBasedSelector()
best = quality_selector.select(manager.list_models())
print(f"Best quality: {best.name}")

# Recommend model for use case
recommended = manager.recommend_for("chat")
```

### Stream Cancellation

```python
from ai_lib_python.client import create_cancel_pair, CancellableStream, CancelReason

async def cancellable_stream():
    client = await AiClient.create("openai/gpt-4o")
    
    # Create cancel token and handle
    token, handle = create_cancel_pair()
    
    # Start streaming with cancellation support
    stream = client.chat().user("Write a long story...").stream()
    cancellable = CancellableStream(stream, token)
    
    # In another task, you can cancel:
    # handle.cancel(CancelReason.USER_REQUEST)
    
    async for event in cancellable:
        if event.is_content_delta:
            print(event.as_content_delta.content, end="")
        
        # Check if cancelled
        if token.is_cancelled:
            print("\n[Cancelled]")
            break
```

### User Feedback Collection

```python
from ai_lib_python.telemetry import (
    RatingFeedback, ThumbsFeedback, ChoiceSelectionFeedback,
    InMemoryFeedbackSink, set_feedback_sink, report_feedback,
)

# Set up feedback collection
sink = InMemoryFeedbackSink(max_events=1000)
set_feedback_sink(sink)

# Report user feedback
await report_feedback(RatingFeedback(
    request_id="req-123",
    rating=5,
    category="helpfulness",
    comment="Great response!"
))

await report_feedback(ThumbsFeedback(
    request_id="req-456",
    is_positive=True
))

# Report multi-candidate selection (for A/B testing)
await report_feedback(ChoiceSelectionFeedback(
    request_id="req-789",
    chosen_index=0,
    rejected_indices=[1, 2],
    latency_to_select_ms=1500.0
))

# Retrieve feedback
all_feedback = sink.get_events()
request_feedback = sink.get_events_by_request("req-123")
```

### Embeddings

```python
from ai_lib_python.embeddings import (
    EmbeddingClient, cosine_similarity, find_most_similar
)

# Create embedding client
client = await EmbeddingClient.create("openai/text-embedding-3-small")

# Generate embeddings
response = await client.embed("Hello, world!")
embedding = response.first.vector
print(f"Dimensions: {len(embedding)}")

# Batch embeddings
texts = ["Hello", "World", "Python", "AI"]
response = await client.embed_batch(texts)

# Find most similar
query = response.embeddings[0].vector
candidates = [e.vector for e in response.embeddings[1:]]
results = find_most_similar(query, candidates, top_k=2)
for idx, score in results:
    print(f"Text '{texts[idx+1]}' similarity: {score:.4f}")

await client.close()
```

### Response Caching

```python
from ai_lib_python.cache import CacheManager, CacheConfig, MemoryCache

# Create cache manager
cache = CacheManager(
    config=CacheConfig(default_ttl_seconds=3600),
    backend=MemoryCache(max_size=1000)
)

# Cache responses
key = cache.generate_key(model="gpt-4o", messages=messages)

# Check cache first
cached = await cache.get(key)
if cached:
    print("Cache hit!")
    response = cached
else:
    response = await client.chat().messages(messages).execute()
    await cache.set(key, response)

# Get cache statistics
stats = cache.stats()
print(f"Hit ratio: {stats.hit_ratio:.2%}")
```

### Plugin System

```python
from ai_lib_python.plugins import (
    Plugin, PluginContext, PluginRegistry, HookType, HookManager
)

# Create a custom plugin
class LoggingPlugin(Plugin):
    def name(self) -> str:
        return "logging"

    async def on_before_request(self, ctx: PluginContext) -> None:
        print(f"Request to {ctx.model}: {ctx.request}")

    async def on_after_response(self, ctx: PluginContext) -> None:
        print(f"Response received: {ctx.response}")

# Register plugin
registry = PluginRegistry()
await registry.register(LoggingPlugin())

# Use hooks for fine-grained control
hooks = HookManager()
hooks.register(HookType.BEFORE_REQUEST, "log", lambda ctx: print(f"Starting {ctx.model}"))

# Trigger hooks
ctx = PluginContext(model="gpt-4o", request={"messages": [...]})
await registry.trigger_before_request(ctx)
```

### Batch Processing

For batch execution with concurrency control:

```python
from ai_lib_python.batch import BatchExecutor, BatchConfig

# Execute multiple requests concurrently
async def process_question(question: str) -> str:
    client = await AiClient.create("openai/gpt-4o")
    response = await client.chat().user(question).execute()
    await client.close()
    return response.content

questions = ["What is AI?", "What is Python?", "What is async?"]

executor = BatchExecutor(process_question, max_concurrent=5)
result = await executor.execute(questions)

print(f"Successful: {result.successful_count}")
print(f"Failed: {result.failed_count}")
for answer in result.get_successful_results():
    print(answer)
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
- **`PreflightChecker`**: Unified request gating
- **`SignalsSnapshot`**: Runtime state aggregation

### Routing Classes

- **`ModelManager`**: Centralized model management
- **`ModelInfo`**: Model information with capabilities
- **`ModelArray`**: Load balancing across endpoints
- **`ModelSelectionStrategy`**: Selection strategies (Cost, Quality, Performance, etc.)

### Telemetry Classes

- **`AiLibLogger`**: Structured logging with masking
- **`MetricsCollector`**: Request metrics collection
- **`Tracer`**: Distributed tracing
- **`HealthChecker`**: Health monitoring
- **`FeedbackSink`**: User feedback collection

### Embedding Classes

- **`EmbeddingClient`**: Embedding generation client
- **`Embedding`**: Single embedding result
- **`EmbeddingResponse`**: Response with usage stats

### Token Classes

- **`TokenCounter`**: Token counting interface
- **`CostEstimate`**: Cost estimation result
- **`ModelPricing`**: Model pricing information

### Cache Classes

- **`CacheManager`**: High-level cache management
- **`CacheBackend`**: Cache backend interface (Memory, Disk, Null)
- **`CacheKeyGenerator`**: Deterministic key generation

### Batch Classes

- **`BatchCollector`**: Request grouping
- **`BatchExecutor`**: Parallel execution

### Plugin Classes

- **`Plugin`**: Base plugin class
- **`PluginRegistry`**: Plugin management
- **`HookManager`**: Event-driven hooks
- **`Middleware`**: Request/response chain

### Transport Classes

- **`ConnectionPool`**: HTTP connection pooling
- **`PoolConfig`**: Pool configuration

### Cancellation Classes

- **`CancelToken`**: Cooperative cancellation token
- **`CancelHandle`**: Public cancel interface
- **`CancellableStream`**: Cancellable async iterator

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

## 🧪 Development

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
│   │   └── validator.py    # Schema validation (+ version/streaming checks)
│   ├── transport/          # HTTP transport
│   │   ├── http.py         # HttpTransport
│   │   ├── auth.py         # API key resolution
│   │   └── pool.py         # ConnectionPool
│   ├── pipeline/           # Stream processing
│   │   ├── decode.py       # SSE/NDJSON decoders
│   │   ├── select.py       # JSONPath selectors
│   │   ├── accumulate.py   # Tool call accumulator
│   │   ├── event_map.py    # Event mappers
│   │   └── fan_out.py      # FanOut, Replicate, Split transforms
│   ├── resilience/         # Resilience patterns
│   │   ├── retry.py        # RetryPolicy
│   │   ├── rate_limiter.py # RateLimiter
│   │   ├── circuit_breaker.py
│   │   ├── backpressure.py
│   │   ├── fallback.py     # FallbackChain
│   │   ├── executor.py     # ResilientExecutor
│   │   ├── signals.py      # SignalsSnapshot
│   │   └── preflight.py    # PreflightChecker
│   ├── routing/            # Model routing & load balancing
│   │   ├── models.py       # ModelInfo, ModelCapabilities
│   │   ├── strategies.py   # Selection strategies
│   │   ├── manager.py      # ModelManager
│   │   └── array.py        # ModelArray (load balancing)
│   ├── client/             # User API
│   │   ├── core.py         # AiClient
│   │   ├── builder.py      # Builders
│   │   ├── response.py     # ChatResponse
│   │   └── cancel.py       # CancelToken, CancellableStream
│   ├── embeddings/         # Embedding support
│   │   ├── client.py       # EmbeddingClient
│   │   ├── types.py        # Embedding, EmbeddingRequest
│   │   └── vectors.py      # Vector operations
│   ├── cache/              # Response caching
│   │   ├── manager.py      # CacheManager
│   │   ├── backend.py      # MemoryCache, DiskCache
│   │   └── key.py          # CacheKeyGenerator
│   ├── tokens/             # Token counting
│   │   ├── counter.py      # TokenCounter, TiktokenCounter
│   │   └── pricing.py      # ModelPricing, CostEstimate
│   ├── telemetry/          # Observability
│   │   ├── logging.py      # AiLibLogger
│   │   ├── metrics.py      # MetricsCollector
│   │   ├── tracing.py      # Tracer
│   │   ├── health.py       # HealthChecker
│   │   └── feedback.py     # Feedback types and sinks
│   ├── batch/              # Request batching
│   │   ├── collector.py    # BatchCollector
│   │   └── executor.py     # BatchExecutor
│   ├── plugins/            # Plugin system
│   │   ├── base.py         # Plugin base class
│   │   ├── registry.py     # PluginRegistry
│   │   ├── hooks.py        # HookManager
│   │   └── middleware.py   # Middleware chain
│   ├── structured/         # Structured output
│   │   ├── json_mode.py    # JsonModeConfig
│   │   ├── schema.py       # SchemaGenerator
│   │   └── validator.py    # OutputValidator
│   ├── utils/              # Utilities
│   │   └── tool_call_assembler.py  # ToolCallAssembler
│   ├── drivers/            # V2 provider drivers (OpenAI, Anthropic, Gemini)
│   ├── mcp/                # MCP tool bridge
│   ├── computer_use/       # Computer Use abstraction
│   ├── multimodal/         # Extended multimodal support
│   ├── registry/           # Capability registry
│   └── errors/             # Error hierarchy
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests (incl. V2 compliance)
├── docs/                   # Documentation
├── examples/               # Example scripts
└── pyproject.toml
```

## 📖 Related Projects

- [AI-Protocol](https://github.com/hiddenpath/ai-protocol) - Protocol specification (v1.5 / V2)
- [ai-lib-rust](https://github.com/hiddenpath/ai-lib-rust) - Rust runtime implementation

## 🤝 Contributing

Contributions are welcome! Please ensure that:

1. All protocol configurations follow the AI-Protocol specification (v1.5 / V2)
2. New features are properly documented with examples
3. Tests are included for new features
4. Compliance tests pass for cross-runtime behaviors (`pytest tests/compliance/`)
5. Code follows Python best practices (PEP 8) and passes `ruff check`
6. Type hints pass `mypy --strict` for modified modules

## 📄 License

This project is licensed under either of:

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT License ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

---

## 🔗 Related Projects

- [AI-Protocol](https://github.com/hiddenpath/ai-protocol): Protocol specification (v1.5 / V2)
- [ai-lib-rust](https://github.com/hiddenpath/ai-lib-rust): Rust runtime implementation

---

**ai-lib-python** - Where protocol meets Pythonic elegance. 🐍✨
