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
9. [Model Routing & Selection](#model-routing--selection)
10. [Stream Cancellation](#stream-cancellation)
11. [User Feedback Collection](#user-feedback-collection)
12. [Embeddings](#embeddings)
13. [Response Caching](#response-caching)
14. [Plugin System](#plugin-system)
15. [Structured Output](#structured-output)
16. [Telemetry & Observability](#telemetry--observability)
17. [Best Practices](#best-practices)

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

## Model Routing & Selection

The routing module provides intelligent model selection and load balancing.

### Model Information

```python
from ai_lib_python.routing import (
    ModelInfo, ModelCapabilities, PricingInfo, PerformanceMetrics,
    ModelManager, create_openai_models, create_anthropic_models,
)

# Create a model info manually
model = ModelInfo(
    id="gpt-4o",
    name="GPT-4o",
    provider="openai",
    capabilities=ModelCapabilities(
        chat=True,
        code_generation=True,
        multimodal=True,
        tool_calling=True,
        context_window=128000,
    ),
    pricing=PricingInfo(
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    ),
    performance=PerformanceMetrics(
        speed_tier="fast",
        quality_tier="high",
    ),
)
```

### Model Manager

```python
# Create with pre-configured models
manager = create_openai_models()
manager.merge(create_anthropic_models())

# Add custom model
manager.add_model(custom_model)

# Filter models
code_models = manager.filter_by_capability("code_generation")
cheap_models = manager.filter_by_max_cost(0.01)
large_context = manager.filter_by_min_context(100000)

# Get recommendation for use case
recommended = manager.recommend_for("chat")

# Export/import configuration
config = manager.to_json()
manager2 = ModelManager.from_json(config)
```

### Selection Strategies

```python
from ai_lib_python.routing import (
    RoundRobinSelector, CostBasedSelector, QualityBasedSelector,
    PerformanceBasedSelector, WeightedSelector, RandomSelector,
)

models = manager.list_models()

# Round-robin (sequential)
selector = RoundRobinSelector()
next_model = selector.select(models)  # Cycles through models

# Cost-based (cheapest)
selector = CostBasedSelector()
cheapest = selector.select(models)

# Quality-based (highest quality tier)
selector = QualityBasedSelector()
best = selector.select(models)

# Performance-based (fastest)
selector = PerformanceBasedSelector()
fastest = selector.select(models)

# Weighted (combines speed + quality)
selector = WeightedSelector(speed_weight=0.3, quality_weight=0.7)
balanced = selector.select(models)
```

### Load Balancing with ModelArray

```python
from ai_lib_python.routing import ModelArray, LoadBalancingStrategy

# Create array with multiple endpoints
array = ModelArray(strategy=LoadBalancingStrategy.ROUND_ROBIN)

array.add_endpoint("primary", "https://api.openai.com", weight=2.0)
array.add_endpoint("secondary", "https://backup.example.com", weight=1.0)

# Get next endpoint
endpoint = array.get_next()

# Track health
array.record_success("primary")
array.record_failure("secondary")

# Health-based selection (excludes unhealthy)
healthy = array.get_healthy_endpoints()
```

## Stream Cancellation

Control streaming operations with cooperative cancellation.

### Basic Cancellation

```python
from ai_lib_python.client import (
    create_cancel_pair, CancellableStream, CancelReason,
)

async def cancellable_chat():
    client = await AiClient.create("openai/gpt-4o")
    
    # Create cancel token and handle
    token, handle = create_cancel_pair()
    
    # Start streaming
    stream = client.chat().user("Write a very long story...").stream()
    cancellable = CancellableStream(stream, token)
    
    # Process stream
    async for event in cancellable:
        if event.is_content_delta:
            print(event.as_content_delta.content, end="")
        
        # Check cancellation
        if token.is_cancelled:
            print("\n[Cancelled]")
            break
    
    await client.close()
```

### Cancellation Reasons

```python
from ai_lib_python.client import CancelReason

# User-initiated cancellation
handle.cancel(CancelReason.USER_REQUEST)

# Timeout cancellation
handle.cancel(CancelReason.TIMEOUT)

# Error cancellation
handle.cancel(CancelReason.ERROR)

# Check reason
if token.is_cancelled:
    print(f"Cancelled: {token.cancel_reason}")
```

### Cancellation Callbacks

```python
def on_cancel(reason: CancelReason):
    print(f"Stream cancelled: {reason}")
    # Cleanup resources

token.on_cancel(on_cancel)
```

### Timeout-based Cancellation

```python
import asyncio

async def stream_with_timeout(timeout_seconds: float):
    token, handle = create_cancel_pair()
    
    # Set up timeout
    async def cancel_after_timeout():
        await asyncio.sleep(timeout_seconds)
        if not token.is_cancelled:
            handle.cancel(CancelReason.TIMEOUT)
    
    timeout_task = asyncio.create_task(cancel_after_timeout())
    
    try:
        async for event in CancellableStream(stream, token):
            yield event
    finally:
        timeout_task.cancel()
```

## User Feedback Collection

Collect and analyze user feedback on model responses.

### Feedback Types

```python
from ai_lib_python.telemetry import (
    RatingFeedback, ThumbsFeedback, TextFeedback,
    ChoiceSelectionFeedback, CorrectionFeedback,
    RegenerateFeedback, StopFeedback,
)

# Star rating (1-5)
feedback = RatingFeedback(
    request_id="req-123",
    rating=5,
    category="helpfulness",
    comment="Very helpful response!",
)

# Thumbs up/down
feedback = ThumbsFeedback(
    request_id="req-456",
    is_positive=True,
)

# Text feedback
feedback = TextFeedback(
    request_id="req-789",
    text="The answer was accurate but too verbose.",
    category="quality",
)

# Multi-candidate selection (A/B testing)
feedback = ChoiceSelectionFeedback(
    request_id="req-abc",
    chosen_index=0,
    rejected_indices=[1, 2],
    latency_to_select_ms=1500.0,
)

# User correction
feedback = CorrectionFeedback(
    request_id="req-def",
    original_text="The capital of France is London.",
    corrected_text="The capital of France is Paris.",
)

# Regenerate request
feedback = RegenerateFeedback(
    request_id="req-ghi",
    attempt_number=2,
)

# Stop generation
feedback = StopFeedback(
    request_id="req-jkl",
    stopped_at_token=150,
    reason="irrelevant",
)
```

### Feedback Sinks

```python
from ai_lib_python.telemetry import (
    InMemoryFeedbackSink, ConsoleFeedbackSink, CompositeFeedbackSink,
    set_feedback_sink, report_feedback,
)

# In-memory storage (for testing/analysis)
memory_sink = InMemoryFeedbackSink(max_events=10000)

# Console output (for debugging)
console_sink = ConsoleFeedbackSink()

# Multiple sinks
composite = CompositeFeedbackSink([memory_sink, console_sink])

# Set global sink
set_feedback_sink(composite)

# Report feedback
await report_feedback(RatingFeedback(
    request_id="req-123",
    rating=5,
))

# Retrieve from memory sink
all_events = memory_sink.get_events()
request_events = memory_sink.get_events_by_request("req-123")
recent = memory_sink.get_events_since(start_time)
```

## Embeddings

Generate and work with text embeddings.

### Basic Embedding Generation

```python
from ai_lib_python.embeddings import EmbeddingClient

# Create client
client = await EmbeddingClient.create("openai/text-embedding-3-small")

# Generate embedding
response = await client.embed("Hello, world!")
vector = response.first.vector
print(f"Dimensions: {len(vector)}")

# Batch embeddings
texts = ["Hello", "World", "Python", "AI"]
response = await client.embed_batch(texts)
for emb in response.embeddings:
    print(f"{emb.index}: {len(emb.vector)} dims")

await client.close()
```

### Vector Operations

```python
from ai_lib_python.embeddings import (
    cosine_similarity, euclidean_distance, dot_product,
    find_most_similar, normalize_vector, average_vectors,
)

# Similarity calculations
sim = cosine_similarity(vec1, vec2)
dist = euclidean_distance(vec1, vec2)
dot = dot_product(vec1, vec2)

# Find most similar vectors
query = embedding.vector
candidates = [e.vector for e in other_embeddings]
results = find_most_similar(query, candidates, top_k=5)

for idx, score in results:
    print(f"Index {idx}: similarity {score:.4f}")

# Normalize and average
normalized = normalize_vector(vec)
avg = average_vectors([vec1, vec2, vec3])
```

### Builder Pattern

```python
client = await (
    EmbeddingClient.builder()
    .model("openai/text-embedding-3-large")
    .dimensions(1024)  # Reduce dimensions
    .timeout(30.0)
    .build()
)
```

## Response Caching

Cache API responses to reduce costs and latency.

### Basic Caching

```python
from ai_lib_python.cache import CacheManager, CacheConfig, MemoryCache

# Create cache manager
cache = CacheManager(
    config=CacheConfig(
        default_ttl_seconds=3600,
        max_entries=1000,
    ),
    backend=MemoryCache(max_size=1000),
)

# Generate cache key
key = cache.generate_key(
    model="gpt-4o",
    messages=[Message.user("Hello!")],
    temperature=0.7,
)

# Check cache
cached = await cache.get(key)
if cached:
    print("Cache hit!")
    response = cached
else:
    response = await client.chat().user("Hello!").execute()
    await cache.set(key, response)
```

### Cache Backends

```python
from ai_lib_python.cache import MemoryCache, DiskCache, NullCache

# In-memory (default)
backend = MemoryCache(max_size=1000)

# Disk-based persistence
backend = DiskCache(
    directory="/tmp/ai_cache",
    max_size_bytes=100_000_000,  # 100MB
)

# No-op (disable caching)
backend = NullCache()
```

### Configuration Presets

```python
# Disable caching
config = CacheConfig.disabled()

# Short TTL (5 minutes)
config = CacheConfig.short_ttl()

# Long TTL (24 hours)
config = CacheConfig.long_ttl()

# Custom
config = CacheConfig(
    enabled=True,
    default_ttl_seconds=7200,
    max_entries=5000,
)
```

### Cache Statistics

```python
stats = cache.stats()
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit ratio: {stats.hit_ratio:.2%}")
print(f"Total entries: {stats.entries}")
```

## Plugin System

Extend functionality with plugins, hooks, and middleware.

### Creating Plugins

```python
from ai_lib_python.plugins import Plugin, PluginContext

class LoggingPlugin(Plugin):
    def name(self) -> str:
        return "logging"
    
    def priority(self) -> int:
        return 100  # Higher = runs first
    
    async def on_init(self) -> None:
        print("Plugin initialized")
    
    async def on_shutdown(self) -> None:
        print("Plugin shutdown")
    
    async def on_before_request(self, ctx: PluginContext) -> None:
        print(f"Request to {ctx.model}")
    
    async def on_after_response(self, ctx: PluginContext) -> None:
        print(f"Response received: {len(ctx.response.content)} chars")
    
    async def on_error(self, ctx: PluginContext, error: Exception) -> None:
        print(f"Error: {error}")
```

### Plugin Registry

```python
from ai_lib_python.plugins import PluginRegistry, get_plugin_registry

# Get global registry
registry = get_plugin_registry()

# Or create custom registry
registry = PluginRegistry()

# Register plugins
await registry.register(LoggingPlugin())
await registry.register(MetricsPlugin())

# List plugins
for name in registry.list_plugins():
    print(f"Plugin: {name}")

# Unregister
await registry.unregister("logging")

# Trigger hooks
ctx = PluginContext(model="gpt-4o", request=request_data)
await registry.trigger_before_request(ctx)
```

### Hook System

```python
from ai_lib_python.plugins import HookManager, HookType

hooks = HookManager()

# Register hook
def log_request(ctx: PluginContext):
    print(f"Request: {ctx.request}")

hooks.register(HookType.BEFORE_REQUEST, "log", log_request, priority=100)

# Register async hook
async def async_hook(ctx: PluginContext):
    await some_async_operation()

hooks.register(HookType.AFTER_RESPONSE, "async", async_hook)

# Trigger hooks
await hooks.trigger(HookType.BEFORE_REQUEST, ctx)

# Unregister
hooks.unregister(HookType.BEFORE_REQUEST, "log")
```

### Middleware

```python
from ai_lib_python.plugins import Middleware, MiddlewareChain, MiddlewareContext

class TimingMiddleware(Middleware):
    async def process(self, ctx: MiddlewareContext, next) -> None:
        start = time.time()
        await next(ctx)
        elapsed = time.time() - start
        print(f"Request took {elapsed:.2f}s")

class AuthMiddleware(Middleware):
    async def process(self, ctx: MiddlewareContext, next) -> None:
        if not ctx.headers.get("Authorization"):
            ctx.abort("Missing auth header")
            return
        await next(ctx)

# Build chain
chain = MiddlewareChain()
chain.add(AuthMiddleware())
chain.add(TimingMiddleware())

# Process request
ctx = MiddlewareContext(request=request_data)
await chain.process(ctx)
```

## Structured Output

Generate JSON-structured responses with schema validation.

### JSON Mode

```python
from ai_lib_python.structured import JsonModeConfig

# Simple JSON mode
response = await (
    client.chat()
    .user("List 3 fruits as JSON array")
    .json_mode(JsonModeConfig.simple())
    .execute()
)

fruits = json.loads(response.content)
```

### Schema-based Output

```python
from ai_lib_python.structured import SchemaGenerator, OutputValidator

# Build schema
schema = (
    SchemaGenerator()
    .object("Person")
    .property("name", "string", required=True)
    .property("age", "integer", minimum=0, maximum=150)
    .property("email", "string", pattern=r"^[\w.-]+@[\w.-]+\.\w+$")
    .property("tags", "array", items={"type": "string"})
    .build()
)

# Request with schema
response = await (
    client.chat()
    .user("Create a person profile for John, age 30")
    .json_mode(JsonModeConfig.with_schema(schema))
    .execute()
)

# Validate output
validator = OutputValidator(schema)
result = validator.validate(response.content)
if result.valid:
    person = result.data
else:
    print(f"Validation errors: {result.errors}")
```

### Pydantic Integration

```python
from pydantic import BaseModel
from ai_lib_python.structured import json_schema_from_pydantic

class Person(BaseModel):
    name: str
    age: int
    email: str | None = None

# Generate schema from Pydantic model
schema = json_schema_from_pydantic(Person)

# Validate with Pydantic
validator = OutputValidator.from_pydantic(Person)
result = validator.validate(response.content)
if result.valid:
    person: Person = result.data  # Typed Pydantic model
```

### Extract JSON from Text

```python
from ai_lib_python.structured import extract_json

# Extract JSON from markdown code blocks
text = """
Here's the data:
```json
{"name": "John", "age": 30}
```
"""

data = extract_json(text)
print(data)  # {"name": "John", "age": 30}
```

## Telemetry & Observability

Monitor and trace your AI application.

### Structured Logging

```python
from ai_lib_python.telemetry import get_logger, LogConfig

# Configure logging
config = LogConfig(
    format="json",  # or "text"
    level="INFO",
    mask_keys=["api_key", "authorization"],
)

logger = get_logger("my_app", config)

# Structured log entries
logger.info("Request started", model="gpt-4o", user_id="123")
logger.warning("Rate limited", retry_after=30)
logger.error("Request failed", error=str(e), request_id="abc")
```

### Metrics Collection

```python
from ai_lib_python.telemetry import MetricsCollector, MetricLabels

collector = MetricsCollector()

# Record request metrics
labels = MetricLabels(provider="openai", model="gpt-4o")
collector.record_request(
    labels,
    latency=0.5,
    status="success",
    tokens_in=100,
    tokens_out=50,
)

# Get snapshot
snapshot = collector.get_snapshot()
print(f"Total requests: {snapshot.total_requests}")
print(f"Success rate: {snapshot.success_rate:.2%}")
print(f"P50 latency: {snapshot.latency_p50_ms:.0f}ms")
print(f"P99 latency: {snapshot.latency_p99_ms:.0f}ms")

# Export Prometheus format
prometheus = collector.to_prometheus()
```

### Distributed Tracing

```python
from ai_lib_python.telemetry import Tracer

tracer = Tracer("my_service")

# Create spans
with tracer.span("chat_request") as span:
    span.set_attribute("model", "gpt-4o")
    span.set_attribute("user_id", "123")
    
    with tracer.span("build_messages"):
        messages = build_messages()
    
    with tracer.span("api_call"):
        response = await client.chat().messages(messages).execute()
    
    span.set_attribute("tokens", response.usage.total_tokens)

# Get trace ID for correlation
trace_id = tracer.current_trace_id()
```

### Health Monitoring

```python
from ai_lib_python.telemetry import HealthChecker

checker = HealthChecker()

# Record health events
checker.record_success("openai")
checker.record_failure("anthropic")

# Check health
status = checker.get_status()
print(f"OpenAI: {status['openai']}")  # "healthy" or "unhealthy"

# Aggregated health
overall = checker.get_aggregate_health()
print(f"Overall healthy: {overall.is_healthy}")
print(f"Unhealthy providers: {overall.unhealthy_providers}")
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
