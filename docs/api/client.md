# Client API Reference

## AiClient

Main entry point for AI model interaction.

### Methods

#### `create(model, api_key=None, base_url=None, timeout=None)` → `AiClient`

Create a new `AiClient` instance.

```python
client = await AiClient.create("openai/gpt-4o", api_key="sk-...")
```

#### `chat()` → `ChatRequestBuilder`

Create a chat request builder.

```python
response = await client.chat().messages([...]).execute()
```

## AiClientBuilder

Fluent API for configuring and building `AiClient` instances.

### Methods

#### `model(model_id)` → `AiClientBuilder`

Set the primary model to use.

```python
builder.model("openai/gpt-4o")
```

#### `api_key(api_key)` → `AiClientBuilder`

Set the API key for the primary model.

```python
builder.api_key("sk-...")
```

#### `base_url(base_url)` → `AiClientBuilder`

Set custom base URL for the provider.

```python
builder.base_url("https://custom.api.example.com/v1")
```

#### `timeout(seconds)` → `AiClientBuilder`

Set request timeout in seconds.

```python
builder.timeout(30.0)
```

#### `max_inflight(limit)` → `AiClientBuilder`

Set maximum concurrent requests.

```python
builder.max_inflight(10)
```

#### `with_fallbacks(models)` → `AiClientBuilder`

Set fallback models for automatic failover.

```python
builder.with_fallbacks(["anthropic/claude-3-5-sonnet"])
```

#### `api_key_for(model, api_key)` → `AiClientBuilder`

Set API key for a specific model (useful with fallbacks).

```python
builder.api_key_for("anthropic/claude-3-5-sonnet", "sk-ant-...")
```

#### `retry(max_attempts, backoff)` → `AiClientBuilder`

Enable retry mechanism.

```python
builder.retry(max_attempts=3, backoff=0.5)
```

#### `production_ready()` → `AiClientBuilder`

Enable all resilience patterns (retries, circuit breaker, etc.).

```python
builder.production_ready()
```

#### `build()` → `AiClient`

Build and return the configured `AiClient` instance.

```python
client = await builder.build()
```

## ChatRequestBuilder

Fluent API for building chat requests.

### Methods

#### `messages(messages)` → `ChatRequestBuilder`

Set the conversation messages.

```python
builder.messages([Message.user("Hello")])
```

#### `user(content)` → `ChatRequestBuilder`

Add a user message (shorthand).

```python
builder.user("What is the weather?")
```

#### `assistant(content)` → `ChatRequestBuilder`

Add an assistant message (shorthand).

```python
builder.assistant("I'd be happy to help!")
```

#### `system(content)` → `ChatRequestBuilder`

Add a system message.

```python
builder.system("You are a helpful assistant.")
```

#### `temperature(value)` → `ChatRequestBuilder`

Set sampling temperature (0.0-2.0).

```python
builder.temperature(0.7)
```

#### `max_tokens(limit)` → `ChatRequestBuilder`

Set maximum tokens for response.

```python
builder.max_tokens(1000)
```

#### `top_p(value)` → `ChatRequestBuilder`

Set nucleus sampling parameter (0.0-1.0).

```python
builder.top_p(0.9)
```

#### `stop(sequences)` → `ChatRequestBuilder`

Set stop sequences.

```python
builder.stop(["\n", "END"])
```

#### `tools(tool_definitions)` → `ChatRequestBuilder`

Set tool/function definitions.

```python
builder.tools([tool_definition])
```

#### `tool_choice(choice)` → `ChatRequestBuilder`

Set tool choice strategy ("auto", "optional", "required", or tool name).

```python
builder.tool_choice("auto")
```

#### `param(key, value)` → `ChatRequestBuilder`

Set custom parameter.

```python
builder.param("custom_param", "value")
```

#### `execute()` → `ChatResponse`

Execute the request (non-streaming).

```python
response = await builder.execute()
```

#### `stream()` → `AsyncIterator[StreamingEvent]`

Execute the request (streaming).

```python
async for event in await builder.stream():
    if event.is_content_delta:
        print(event.as_content_delta.content, end="")
```

## ChatResponse

Response from a chat completion request.

### Properties

#### `content` → `str`

The response text content.

#### `model` → `str`

The model that generated the response.

#### `finish_reason` → `str | None`

Reason for generation stop ("stop", "length", "tool_calls", etc.).

#### `has_tool_calls` → `bool`

Whether the response includes tool/function calls.

#### `tool_calls` → `list[ToolCall]`

List of tool calls (if present).

#### `usage` → `dict | None`

Token usage statistics.

### Properties (from usage)

#### `prompt_tokens` → `int`

Number of tokens in the prompt.

#### `completion_tokens` → `int`

Number of tokens in the completion.

#### `total_tokens` → `int`

Total tokens (prompt + completion).

### Methods

#### `to_message()` → `Message`

Convert response to a Message object.

```python
message = response.to_message()
```

## CallStats

Statistics about the API call.

### Properties

#### `client_request_id` → `str`

Unique identifier for this request.

#### `latency_ms` → `float`

Total latency in milliseconds.

#### `time_to_first_token_ms` → `float | None`

Time to first token (streaming only).

#### `retry_count` → `int`

Number of retry attempts.

#### `prompt_tokens` → `int`

Prompt tokens used.

#### `completion_tokens` → `int`

Completion tokens generated.

#### `total_tokens` → `int`

Total tokens used.

### Methods

#### `record_start()`

Record request start time.

#### `record_first_token()`

Record time to first token.

#### `record_end()`

Record request end time.

#### `record_usage(usage)`

Record token usage statistics.

## Cancellation

### `create_cancel_pair()` → `(CancelToken, CancelHandle)`

Create a cancellation token and handle.

```python
cancel_token, cancel_handle = create_cancel_pair()
```

### `with_cancellation(stream, cancel_token)`

Wrap a stream with cancellation support.

```python
stream = with_cancellation(stream, cancel_token)
```

## CancelToken

Token for cancelling async operations.

### Methods

#### `cancel(reason)`

Cancel the operation.

```python
cancel_token.cancel("User requested")
```

#### `is_cancelled()` → `bool`

Check if cancellation was requested.

## CancelHandle

Handle for managing cancellation.

### Properties

#### `state` → `CancelState`

Current cancellation state.

#### `reason` → `CancelReason | None`

Reason for cancellation.

### Methods

#### `cancel(reason)`

Cancel with optional reason.

```python
cancel_handle.cancel("Timeout")
```

## Enums

### `CancelState`

- `ACTIVE`: Not cancelled
- `CANCELLING`: Cancellation in progress
- `CANCELLED`: Cancellation complete

### `CancelReason`

- `USER_REQUESTED`: User initiated cancellation
- `TIMEOUT`: Timeout occurred
- `ERROR`: Error occurred
- `SHUTDOWN`: System shutdown
