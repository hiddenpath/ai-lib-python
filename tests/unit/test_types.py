"""Tests for types module."""

import pytest

from ai_lib_python.types import (
    ContentBlock,
    Message,
    MessageRole,
    StreamingEvent,
    ToolCall,
    ToolDefinition,
)


class TestMessage:
    """Tests for Message class."""

    def test_system_message(self) -> None:
        """Test creating a system message."""
        msg = Message.system("You are a helpful assistant.")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are a helpful assistant."

    def test_user_message(self) -> None:
        """Test creating a user message."""
        msg = Message.user("Hello!")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello!"

    def test_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = Message.assistant("Hi there!")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hi there!"

    def test_tool_message(self) -> None:
        """Test creating a tool result message."""
        msg = Message.tool("call_abc123", "42")
        assert msg.role == MessageRole.TOOL
        assert msg.content == "42"
        assert msg.tool_call_id == "call_abc123"

    def test_message_with_content_blocks(self) -> None:
        """Test creating a message with content blocks."""
        blocks = [
            ContentBlock.text_block("Describe this:"),
            ContentBlock.image_base64("base64data", "image/png"),
        ]
        msg = Message.with_content(MessageRole.USER, blocks)
        assert msg.role == MessageRole.USER
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2

    def test_contains_image(self) -> None:
        """Test image detection in message."""
        text_msg = Message.user("Hello")
        assert not text_msg.contains_image()

        blocks = [
            ContentBlock.text_block("Image:"),
            ContentBlock.image_base64("data", "image/png"),
        ]
        img_msg = Message.with_content(MessageRole.USER, blocks)
        assert img_msg.contains_image()

    def test_get_text_content(self) -> None:
        """Test extracting text from message."""
        # Simple text
        msg = Message.user("Hello world")
        assert msg.get_text_content() == "Hello world"

        # Content blocks
        blocks = [
            ContentBlock.text_block("First"),
            ContentBlock.text_block("Second"),
        ]
        msg = Message.with_content(MessageRole.USER, blocks)
        assert msg.get_text_content() == "First\nSecond"

    def test_message_serialization(self) -> None:
        """Test message serialization to dict."""
        msg = Message.user("Hello")
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "Hello"


class TestContentBlock:
    """Tests for ContentBlock class."""

    def test_text_block(self) -> None:
        """Test creating a text block."""
        block = ContentBlock.text_block("Hello")
        assert block.type == "text"
        assert block.text == "Hello"

    def test_image_base64(self) -> None:
        """Test creating an image block from base64."""
        block = ContentBlock.image_base64("encoded_data", "image/jpeg")
        assert block.type == "image"
        assert block.source is not None
        assert block.source.source_type == "base64"
        assert block.source.data == "encoded_data"
        assert block.source.media_type == "image/jpeg"

    def test_image_url(self) -> None:
        """Test creating an image block from URL."""
        block = ContentBlock.image_url("https://example.com/image.png")
        assert block.type == "image"
        assert block.source is not None
        assert block.source.source_type == "url"
        assert block.source.data == "https://example.com/image.png"

    def test_tool_use(self) -> None:
        """Test creating a tool use block."""
        block = ContentBlock.tool_use(
            id="call_123",
            name="get_weather",
            input={"city": "Tokyo"},
        )
        assert block.type == "tool_use"
        assert block.id == "call_123"
        assert block.name == "get_weather"
        assert block.input == {"city": "Tokyo"}

    def test_tool_result(self) -> None:
        """Test creating a tool result block."""
        block = ContentBlock.tool_result(
            tool_use_id="call_123",
            content={"temperature": 25},
            is_error=False,
        )
        assert block.type == "tool_result"
        assert block.tool_use_id == "call_123"
        assert block.content == {"temperature": 25}


class TestToolDefinition:
    """Tests for ToolDefinition class."""

    def test_from_function(self) -> None:
        """Test creating tool definition from function details."""
        tool = ToolDefinition.from_function(
            name="get_weather",
            description="Get weather for a city",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                },
                "required": ["city"],
            },
        )
        assert tool.type == "function"
        assert tool.function.name == "get_weather"
        assert tool.function.description == "Get weather for a city"
        assert tool.name == "get_weather"

    def test_tool_serialization(self) -> None:
        """Test tool serialization."""
        tool = ToolDefinition.from_function(
            name="test_func",
            description="A test function",
        )
        data = tool.model_dump()
        assert data["type"] == "function"
        assert data["function"]["name"] == "test_func"


class TestToolCall:
    """Tests for ToolCall class."""

    def test_from_openai_format_dict(self) -> None:
        """Test creating tool call from OpenAI format with dict args."""
        tool_call = ToolCall.from_openai_format(
            id="call_123",
            function_name="get_weather",
            arguments={"city": "Tokyo"},
        )
        assert tool_call.id == "call_123"
        assert tool_call.function_name == "get_weather"
        assert tool_call.arguments == {"city": "Tokyo"}

    def test_from_openai_format_string(self) -> None:
        """Test creating tool call from OpenAI format with string args."""
        tool_call = ToolCall.from_openai_format(
            id="call_456",
            function_name="search",
            arguments='{"query": "python"}',
        )
        assert tool_call.id == "call_456"
        assert tool_call.function_name == "search"
        assert tool_call.arguments == {"query": "python"}
        assert tool_call.arguments_raw == '{"query": "python"}'

    def test_to_content_block(self) -> None:
        """Test converting tool call to content block."""
        tool_call = ToolCall(
            id="call_789",
            function_name="test",
            arguments={"key": "value"},
        )
        block = tool_call.to_content_block()
        assert block["type"] == "tool_use"
        assert block["id"] == "call_789"
        assert block["name"] == "test"
        assert block["input"] == {"key": "value"}


class TestStreamingEvent:
    """Tests for StreamingEvent class."""

    def test_content_delta(self) -> None:
        """Test creating content delta event."""
        event = StreamingEvent.content_delta("Hello", sequence_id=1)
        assert event.event_type == "PartialContentDelta"
        assert event.is_content_delta
        assert event.as_content_delta.content == "Hello"
        assert event.as_content_delta.sequence_id == 1

    def test_tool_call_started(self) -> None:
        """Test creating tool call started event."""
        event = StreamingEvent.tool_call_started(
            tool_call_id="call_123",
            tool_name="get_weather",
            index=0,
        )
        assert event.event_type == "ToolCallStarted"
        assert event.is_tool_call_started
        assert event.as_tool_call_started.tool_call_id == "call_123"
        assert event.as_tool_call_started.tool_name == "get_weather"

    def test_partial_tool_call(self) -> None:
        """Test creating partial tool call event."""
        event = StreamingEvent.partial_tool_call(
            tool_call_id="call_123",
            arguments='{"city":',
            index=0,
        )
        assert event.event_type == "PartialToolCall"
        assert event.is_partial_tool_call
        assert event.as_partial_tool_call.arguments == '{"city":'

    def test_stream_end(self) -> None:
        """Test creating stream end event."""
        event = StreamingEvent.stream_end(finish_reason="stop")
        assert event.event_type == "StreamEnd"
        assert event.is_stream_end
        assert event.as_stream_end.finish_reason == "stop"

    def test_stream_error(self) -> None:
        """Test creating stream error event."""
        event = StreamingEvent.stream_error(
            error={"message": "Something went wrong"},
            event_id="evt_123",
        )
        assert event.event_type == "StreamError"
        assert event.is_stream_error
        assert event.as_stream_error.error == {"message": "Something went wrong"}

    def test_typed_accessor_wrong_type(self) -> None:
        """Test that typed accessor raises on wrong type."""
        event = StreamingEvent.content_delta("Hello")
        with pytest.raises(TypeError):
            _ = event.as_tool_call_started
