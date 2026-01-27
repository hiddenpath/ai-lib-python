# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## Future Releases

### Planned for 0.2.0
- Telemetry and observability
- Connection pooling
- Request batching
- Token counting utilities

### Planned for 0.3.0
- Embedding support
- Structured output (JSON mode)
- Response caching
- Plugin system

[Unreleased]: https://github.com/hiddenpath/ai-lib-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hiddenpath/ai-lib-python/releases/tag/v0.1.0
