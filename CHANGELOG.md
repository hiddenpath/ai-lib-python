# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-02-15

### Added

#### V2 Standard Error Codes (`errors/standard_codes.py`)
- 13 `StandardErrorCode` frozen dataclass instances (E1001–E9999) aligned with AI-Protocol V2
- `from_error_class()`: Maps `ErrorClass` enum to standard codes (cached mapping)
- `from_http_status()`: Maps HTTP status codes including Anthropic 529
- `from_name()`: Lookup standard code by name string
- `STANDARD_ERROR_CODES` registry for code-based access

#### Feature Flags (`_features.py`)
- Runtime feature detection for 6 optional extras: vision, audio, telemetry, tokenizer, keyring, watchdog
- `require_extra()`: Raises `ImportError` with pip install hint when extra is unavailable
- 8 pip extras in `pyproject.toml`: vision, audio, embeddings, structured, batch, agentic, telemetry, tokenizer

#### Compliance Testing (`tests/compliance/`)
- YAML-based compliance test runner using pytest parametrization
- 20/20 test cases passing against `ai-protocol/tests/compliance/cases/`

### Changed

#### Error Classification Improvements
- E4001/E4002 category corrected from "conflict" to "operational" (aligned with Rust runtime and V2 spec)
- `Authentication` added to `_FALLBACKABLE_CLASSES` (per-provider key; another provider may succeed)
- HTTP 529 → E3002 (overloaded) added to `_HTTP_STATUS_TO_CODE` mapping
- `from_error_class()` optimized: module-level lazy cache instead of per-call dict creation
- `RemoteError` context now includes `retryable` and `fallbackable` fields

#### Documentation
- Added Chinese one-line description to all module doc headers (10 modules)
- All remaining documentation in English per project convention

#### .gitignore
- Added Chinese-named internal document patterns
- Strengthened wildcard patterns for work documents

## [0.5.0] - 2026-02-05

### Added

#### Integration Tests (`tests/integration/`)
- **Test Suite Expansion**: 6 comprehensive integration test files
  - `test_chat.py`: Basic and streaming chat functionality (13 tests)
  - `test_tools.py`: Tool/function calling scenarios (8 tests)
  - `test_resilience.py`: Error handling, retries, circuit breaker (11 tests)
  - `test_concurrency.py`: Concurrent request handling (9 tests)
  - `test_protocol.py`: Protocol loading and configuration (9 tests)
  - `conftest.py`: Mock helpers for OpenAI and Anthropic APIs

- **Test Coverage**: Target increased from ~13% to 80%+
  - Mock API responses using pytest-httpx
  - Concurrent request testing
  - Error scenario coverage
  - Resilience pattern verification

### Changed

#### Development Status
- **Beta Release**: Development status upgraded from "3 - Alpha" to "4 - Beta"
- **Production Readiness**: Library now suitable for production use with proper testing coverage

### Improvements

- **Test Infrastructure**: Comprehensive mocking for integration tests
  - OpenAI API response mocking
  - Anthropic API response mocking
  - Streaming chunk simulation
  - Tool call response mocking
  - Error scenario simulation

### Internal

- Test coverage infrastructure improvements
- Mock utilities for integration testing
- Concurrent load testing patterns

## [0.4.0] - 2026-01-27

### Added

#### Model Routing & Load Balancing (`routing/`)
- **ModelInfo**: Complete model information structure
  - `ModelCapabilities`: Capability definition (chat, code, multimodal, tools)
  - `PricingInfo`: Pricing information with cost calculation
  - `PerformanceMetrics`: Speed and quality tier classification

- **Model Selection Strategies**
  - `RoundRobinSelector`: Cyclic model selection
  - `WeightedSelector`: Speed + quality weighted selection
  - `CostBasedSelector`: Cheapest model selection
  - `PerformanceBasedSelector`: Fastest model selection
  - `QualityBasedSelector`: Highest quality selection
  - `RandomSelector`: Random model selection

- **ModelManager**: Centralized model management
  - Add/remove/list models
  - Filter by capability, cost, context window
  - Model recommendation by use case
  - JSON config import/export

- **ModelArray**: Load balancing across endpoints
  - Multiple load balancing strategies
  - Health-based endpoint selection
  - Endpoint health tracking

- **Pre-configured Managers**
  - `create_openai_models()`: OpenAI model catalog
  - `create_anthropic_models()`: Anthropic model catalog

#### Resilience Signals & Preflight (`resilience/`)
- **SignalsSnapshot**: Unified runtime state aggregation
  - `InflightSnapshot`: In-flight request state
  - `RateLimiterSnapshot`: Rate limiter state
  - `CircuitBreakerSnapshot`: Circuit breaker state
  - `health_score`: Composite health metric (0.0-1.0)

- **PreflightChecker**: Unified request gating
  - Rate limiter pre-check
  - Circuit breaker pre-check
  - Backpressure permit acquisition
  - Response header rate limit extraction

- **PreflightContext**: Async context manager for preflight

#### FanOut Stream Operator (`pipeline/`)
- **FanOutTransform**: Expand arrays into separate events
  - Configurable array path
  - Metadata preservation
  - Common pattern auto-detection (choices, candidates, results)

- **ReplicateTransform**: Duplicate each event
- **SplitTransform**: Filter events by predicate

#### User Feedback Collection (`telemetry/`)
- **Feedback Types**
  - `ChoiceSelectionFeedback`: Multi-candidate selection
  - `RatingFeedback`: 1-5 star ratings
  - `ThumbsFeedback`: Up/down feedback
  - `TextFeedback`: Free-form text
  - `CorrectionFeedback`: Edit tracking
  - `RegenerateFeedback`: Regeneration events
  - `StopFeedback`: Stop generation events

- **FeedbackSink** implementations
  - `NoopFeedbackSink`: Discard feedback (default)
  - `InMemoryFeedbackSink`: Store in memory
  - `ConsoleFeedbackSink`: Print to console
  - `CompositeFeedbackSink`: Multi-sink routing

#### Stream Cancellation (`client/`)
- **CancelToken**: Cooperative cancellation token
  - Cancel with reason (user_request, timeout, error)
  - Callback registration
  - Async wait support

- **CancelHandle**: Public cancel interface
- **CancellableStream**: Wrap async iterators for cancellation
- `create_cancel_pair()`: Factory for cancel pair

#### ToolCall Assembler (`utils/`)
- **ToolCallAssembler**: Assemble streaming tool calls
  - Handle started events
  - Accumulate argument fragments
  - JSON parsing with fallback

- **MultiToolCallAssembler**: Multi-turn tool call tracking

#### Protocol Validation Enhancements (`protocol/`)
- **Protocol Version Validation**
  - `SUPPORTED_PROTOCOL_VERSIONS`: 1.0, 1.1, 1.5, 2.0
  - Deprecation warnings for old versions

- **Strict Streaming Validation**
  - Decoder format check
  - Content path requirements
  - Tool call path requirements
  - `AI_LIB_STRICT_STREAMING` environment variable

- New validation functions
  - `validate_protocol_version()`
  - `validate_streaming_config()`
  - `validate_manifest()`
  - `validate_manifest_or_raise()`

### Changed
- Version updated to 0.4.0-dev

## [0.3.0] - 2026-01-27

### Added

#### Embedding Support
- **EmbeddingClient**: Unified client for embedding generation
  - Simple `EmbeddingClient.create()` factory method
  - Fluent builder API with `EmbeddingClientBuilder`
  - Batch embedding with automatic chunking
  - Multiple provider support

- **Embedding Types**
  - `Embedding`: Single embedding result
  - `EmbeddingRequest`: Request configuration
  - `EmbeddingResponse`: Response with usage stats
  - `EmbeddingModel`: Standard model enum

- **Vector Operations**
  - `cosine_similarity()`: Cosine similarity calculation
  - `euclidean_distance()`: Euclidean distance
  - `dot_product()`: Dot product
  - `find_most_similar()`: Find top-k similar vectors
  - `normalize_vector()`: Unit normalization
  - `average_vectors()`: Vector averaging

#### Structured Output (JSON Mode)
- **JsonModeConfig**: JSON mode configuration
  - Simple JSON object mode
  - JSON Schema mode with validation
  - Pydantic model integration

- **SchemaGenerator**: JSON schema building
  - Fluent API for schema construction
  - Type constraints (min/max, pattern, enum)
  - Pydantic model conversion

- **OutputValidator**: Response validation
  - JSON Schema validation
  - Pydantic model validation
  - `validate_or_raise()` for strict mode

- **Utilities**
  - `extract_json()`: Extract JSON from markdown
  - `json_schema_from_type()`: Python type to schema
  - `json_schema_from_pydantic()`: Pydantic model to schema

#### Response Caching
- **CacheManager**: High-level cache management
  - Response caching with TTL
  - Embedding caching
  - Cache invalidation
  - Statistics tracking

- **Cache Backends**
  - `MemoryCache`: In-memory with LRU eviction
  - `DiskCache`: File-based persistence
  - `NullCache`: No-op for testing

- **CacheConfig**: Configuration presets
  - `disabled()`: Disable caching
  - `short_ttl()`: 5-minute TTL
  - `long_ttl()`: 24-hour TTL

- **CacheKeyGenerator**: Deterministic key generation
  - Message-based keys
  - Embedding-specific keys
  - Parameter inclusion/exclusion

#### Plugin System
- **Plugin**: Base plugin class
  - Lifecycle hooks (init, shutdown)
  - Request/response processing
  - Error handling
  - Streaming support

- **PluginRegistry**: Plugin management
  - Registration and lookup
  - Priority-based ordering
  - Lifecycle management

- **HookManager**: Event-driven hooks
  - Multiple hook types
  - Priority-based execution
  - Sequential and parallel execution

- **Middleware**: Request/response chain
  - `MiddlewareChain`: Chain-of-responsibility
  - `FunctionMiddleware`: Function wrapper
  - Abort support

### Changed
- Updated version to 0.3.0-dev
- Added B027 to ruff ignore list (optional plugin hooks)

## [0.2.0] - 2026-01-27

### Added

#### Telemetry & Observability
- **AiLibLogger**: Structured logging with context support
  - JSON and text output formats
  - Request-scoped logging context
  - Sensitive data masking (API keys, tokens)

- **MetricsCollector**: Request metrics collection
  - Latency tracking with percentiles (p50, p90, p99)
  - Token usage tracking
  - Error rate calculation
  - Prometheus format export

- **Tracer**: Distributed tracing support
  - Span creation with context propagation
  - W3C traceparent header support
  - In-memory and console exporters

- **HealthChecker**: Health monitoring
  - Provider health tracking
  - Aggregated health status
  - Error rate-based health determination

#### Connection Pooling
- **ConnectionPool**: HTTP connection management
  - Per-provider client isolation
  - Configurable pool limits
  - Connection statistics tracking
  - HTTP/2 support

- **PoolConfig**: Pool configuration presets
  - `default()`: Balanced configuration
  - `high_throughput()`: Optimized for many requests
  - `low_latency()`: Optimized for quick responses

#### Request Batching
- **BatchCollector**: Request grouping
  - Configurable batch size and timeout
  - Group-by function support
  - Automatic flush on limits

- **BatchExecutor**: Parallel execution
  - Concurrent request execution
  - Configurable concurrency limits
  - Progress callbacks
  - Fail-fast option

#### Token Counting
- **TokenCounter**: Token counting utilities
  - tiktoken integration for OpenAI models
  - Character-based estimation fallback
  - Message token counting
  - Text truncation to token limit

- **CostEstimate**: Cost estimation
  - Model pricing data for major providers
  - Input/output cost breakdown
  - Context window information

### Changed
- Updated version to 0.2.0-dev
- Added telemetry and tokenizer optional dependencies

## [0.1.0] - 2026-01-27

### Added

#### Core Features
- **AiClient**: Unified client for AI model interaction
  - Simple `AiClient.create()` factory method
  - Fluent builder API with `AiClientBuilder`
  - Async context manager support
  - Configurable timeout and base URL

- **Chat Completions**
  - `ChatRequestBuilder` with fluent API
  - Support for system, user, and assistant messages
  - Temperature, max_tokens, top_p parameters
  - Stop sequences support

- **Streaming**
  - Native async streaming with `async for`
  - Typed streaming events
  - Time-to-first-token metrics
  - `stream_with_stats()` for monitoring

- **Tool Calling**
  - `ToolDefinition` for function definitions
  - `ToolCall` for parsed tool invocations
  - OpenAI and Anthropic format support
  - Tool choice configuration

- **Multimodal Support**
  - Image support (base64 and URL)
  - Audio support (base64)
  - Mixed content blocks

#### Protocol Layer
- **ProtocolLoader**: Load AI-Protocol manifests
  - Local file loading
  - GitHub raw URL fallback
  - Caching support
  - Hot reload for development

- **ProtocolValidator**: JSON Schema validation
  - Fast validation with fastjsonschema
  - Detailed error reporting

- **ProtocolManifest**: Full manifest model
  - Endpoint configuration
  - Authentication settings
  - Streaming configuration
  - Error classification rules

#### Pipeline Layer
- **Decoders**
  - SSEDecoder for Server-Sent Events
  - JsonLinesDecoder for NDJSON streams
  - AnthropicSSEDecoder for Anthropic format

- **Transforms**
  - JsonPathSelector for filtering
  - ToolCallAccumulator for argument assembly

- **Event Mappers**
  - ProtocolEventMapper (rule-based)
  - DefaultEventMapper (OpenAI-compatible)
  - AnthropicEventMapper

#### Resilience Layer
- **RetryPolicy**
  - Exponential backoff
  - Full, equal, and none jitter strategies
  - Configurable retry conditions
  - Retry-after header support

- **RateLimiter**
  - Token bucket algorithm
  - Burst support
  - Configurable RPS/RPM

- **AdaptiveRateLimiter**
  - Dynamic rate adjustment
  - Response header parsing

- **CircuitBreaker**
  - Closed/Open/Half-Open states
  - Configurable thresholds
  - Automatic recovery

- **Backpressure**
  - Semaphore-based concurrency control
  - Queue timeout
  - Statistics tracking

- **FallbackChain**
  - Multi-target failover
  - Weight-based priority
  - Per-target enable/disable

- **ResilientExecutor**
  - Unified resilience wrapper
  - Production-ready defaults
  - Statistics collection

#### Error Handling
- Comprehensive error hierarchy
  - AiLibError (base)
  - ProtocolError
  - TransportError
  - PipelineError
  - ValidationError
  - RemoteError

- Error classification
  - 13 standard error classes
  - Retryable/fallbackable detection
  - Provider-specific mapping

#### Transport Layer
- **HttpTransport**
  - Async HTTP with httpx
  - Streaming support
  - Automatic authentication
  - Timeout configuration

- **API Key Resolution**
  - Explicit key
  - Environment variables
  - System keyring (optional)

### Developer Experience
- Full type hints (py.typed)
- Pydantic v2 models
- Comprehensive docstrings
- Example scripts
- Unit test suite (143 tests)

### Documentation
- README with quick start
- User guide
- API reference
- Example scripts

### Infrastructure
- GitHub Actions CI/CD
- pytest configuration
- mypy strict mode
- ruff linting

[Unreleased]: https://github.com/hiddenpath/ai-lib-python/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.6.0
[0.5.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.5.0
[0.4.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.4.0
[0.3.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.3.0
[0.2.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.2.0
[0.1.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.1.0
