# Types API Reference

## Message Types

### Message

Represents a message in a conversation.

#### Methods

##### `user(content, role="user")` → `Message` (classmethod)

Create a user message.

```python
message = Message.user("What is the weather?")
```

##### `assistant(content, role="assistant")` → `Message` (classmethod)

Create an assistant message.

```python
message = Message.assistant("I'd be happy to help!")
```

##### `system(content, role="system")` → `Message` (classmethod)

Create a system message.

```python
message = Message.system("You are a helpful assistant.")
```

##### `from_dict(data)` → `Message` (classmethod)

Create message from dictionary.

```python
message = Message.from_dict({"role": "user", "content": "Hello"})
```

##### `to_dict()` → `dict`

Convert message to dictionary.

```python
data = message.to_dict()
```

#### Properties

##### `role` → `MessageRole`

Message role (user/assistant/system).

##### `content` → `str | MessageContent`

Content of the message.

##### `tool_calls` → `list[ToolCall] | None`

Tool calls if present.

### MessageRole

Enum representing message roles.

- `USER`: User message
- `ASSISTANT`: Assistant message
- `SYSTEM`: System message
- `TOOL`: Tool/function result message

### MessageContent

Content of a message can be a string or a structured object.

For multimodal messages, this can contain multiple content blocks:

```python
from ai_lib_python.types.message import MessageContent, ContentBlock

content = MessageContent([
    ContentBlock(type="text", text="Describe this image:"),
    ContentBlock(type="image", data="base64..."),
])
```

### ContentBlock

A block of content in a multimodal message.

#### Properties

##### `type` → `str`

Type of content block ("text", "image", "audio", "video").

##### `text` → `str | None`

Text content (for text blocks).

##### `data` → `str | None`

Data (image/audio/video as base64 or URL).

## Tool Types

### ToolDefinition

Definition of a tool/function that can be called by the model.

#### Methods

##### `from_function(name, description, parameters)` → `ToolDefinition` (classmethod)

Create tool definition from function info.

```python
tool = ToolDefinition.from_function(
    name="get_weather",
    description="Get weather for a city",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
)
```

#### Properties

##### `name` → `str`

Tool/function name.

##### `description` → `str

Description of what the tool does.

##### `parameters` → `dict`

JSON schema for parameters.

### ToolCall

Represents a tool/function call requested by the model.

#### Properties

##### `id` → `str`

Unique identifier for this tool call.

##### `function_name` → `str`

Name of the function to call.

##### `arguments` → `dict`

Arguments to pass to the function.

#### Methods

##### `to_message(tool_result)` → `Message` (classmethod)

Convert tool result to a message.

```python
tool_message = ToolCall.to_message(tool_call, {"result": 25})
```

##### `to_dict()` → `dict`

Convert tool call to dictionary.

## Event Types

### StreamingEvent

Event emitted during streaming responses.

#### Properties

##### `type` → `str`

Event type.

##### `data` → `dict`

Event data.

#### Properties (common event types)

##### `is_content_delta` → `bool`

True if this is a content delta event.

##### `is_complete` → `bool`

True if streaming is complete.

##### `is_error` → `bool`

True if this is an error event.

##### `as_content_delta` → `ContentDelta | None`

Content delta if available.

### ContentDelta

Represents a delta in content during streaming.

#### Properties

##### `content` → `str`

Delta content chunk.

##### `index` → `int`

Chunk index.

## Enums

### ToolChoice

Options for when to use tools.

- `AUTO`: Model decides whether to use tools
- `OPTIONAL`: Tools are optional
- `REQUIRED`: Model must call a tool
- String: Specific tool name to call

```python
builder.tool_choice("auto")
builder.tool_choice("required")
builder.tool_choice("get_weather")
```

### FinishReason

Reason for generation completion.

- `STOP`: Model stopped naturally
- `LENGTH`: Max tokens reached
- `TOOL_CALLS`: Model requested tool calls
- `CONTENT_FILTER`: Content was filtered
- `ERROR`: Error occurred
