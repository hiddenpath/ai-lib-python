"""Tests for client module."""

import pytest

from ai_lib_python.client import CallStats, ChatResponse
from ai_lib_python.client.builder import AiClientBuilder, ChatRequestBuilder
from ai_lib_python.types.message import Message
from ai_lib_python.types.tool import ToolCall, ToolDefinition


class TestChatResponse:
    """Tests for ChatResponse."""

    def test_empty_response(self) -> None:
        """Test empty response defaults."""
        response = ChatResponse()
        assert response.content == ""
        assert response.tool_calls == []
        assert response.finish_reason is None
        assert not response.has_tool_calls

    def test_response_with_content(self) -> None:
        """Test response with content."""
        response = ChatResponse(
            content="Hello, world!",
            finish_reason="stop",
            model="gpt-4",
        )
        assert response.content == "Hello, world!"
        assert response.finish_reason == "stop"
        assert response.model == "gpt-4"

    def test_response_with_tool_calls(self) -> None:
        """Test response with tool calls."""
        tool_call = ToolCall(
            id="call_123",
            function_name="get_weather",
            arguments={"city": "Tokyo"},
        )
        response = ChatResponse(tool_calls=[tool_call])

        assert response.has_tool_calls
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].function_name == "get_weather"

    def test_response_with_usage(self) -> None:
        """Test response with usage data."""
        response = ChatResponse(
            content="Hi",
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

        assert response.prompt_tokens == 10
        assert response.completion_tokens == 5
        assert response.total_tokens == 15

    def test_to_message(self) -> None:
        """Test converting response to message."""
        response = ChatResponse(content="I'm an assistant")
        message = response.to_message()

        # Role may be enum or string depending on serialization
        role = message.role.value if hasattr(message.role, "value") else message.role
        assert role == "assistant"
        assert message.content == "I'm an assistant"


class TestCallStats:
    """Tests for CallStats."""

    def test_default_stats(self) -> None:
        """Test default stats values."""
        stats = CallStats()
        assert stats.client_request_id is not None
        assert stats.latency_ms == 0.0
        assert stats.retry_count == 0

    def test_record_timing(self) -> None:
        """Test timing recording."""
        stats = CallStats()
        stats.record_start()

        # Simulate some work
        import time
        time.sleep(0.01)

        stats.record_first_token()
        stats.record_end()

        assert stats.time_to_first_token_ms is not None
        assert stats.time_to_first_token_ms > 0
        assert stats.latency_ms > stats.time_to_first_token_ms

    def test_record_usage(self) -> None:
        """Test usage recording."""
        stats = CallStats()
        stats.record_usage({
            "prompt_tokens": 100,
            "completion_tokens": 50,
        })

        assert stats.prompt_tokens == 100
        assert stats.completion_tokens == 50
        assert stats.total_tokens == 150


class TestAiClientBuilder:
    """Tests for AiClientBuilder."""

    @pytest.mark.asyncio
    async def test_builder_requires_model(self) -> None:
        """Test builder requires model to be set."""
        builder = AiClientBuilder()

        with pytest.raises(ValueError, match="Model must be set"):
            await builder.build()

    def test_builder_fluent_api(self) -> None:
        """Test builder fluent API."""
        builder = (
            AiClientBuilder()
            .model("openai/gpt-4o")
            .api_key("sk-test")
            .timeout(30.0)
            .max_inflight(10)
            .with_fallbacks(["anthropic/claude-3-5-sonnet"])
        )

        assert builder._model == "openai/gpt-4o"
        assert builder._api_key == "sk-test"
        assert builder._timeout == 30.0
        assert builder._max_inflight == 10
        assert "anthropic/claude-3-5-sonnet" in builder._fallbacks


class TestChatRequestBuilder:
    """Tests for ChatRequestBuilder (without client)."""

    def test_build_simple_payload(self) -> None:
        """Test building simple payload."""
        # Create a mock client
        class MockClient:
            _manifest = None
            _model_id = "gpt-4"

        builder = ChatRequestBuilder(MockClient())
        builder.messages([Message.user("Hello")])
        builder.temperature(0.7)
        builder.max_tokens(100)

        payload = builder.build_payload()

        assert payload["model"] == "gpt-4"
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 100
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Hello"

    def test_build_payload_with_tools(self) -> None:
        """Test building payload with tools."""
        class MockClient:
            _manifest = None
            _model_id = "gpt-4"

        tool = ToolDefinition.from_function(
            name="get_weather",
            description="Get weather for a city",
            parameters={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        )

        builder = ChatRequestBuilder(MockClient())
        builder.messages([Message.user("What's the weather?")])
        builder.tools([tool])
        builder.tool_choice("auto")

        payload = builder.build_payload()

        assert "tools" in payload
        assert len(payload["tools"]) == 1
        assert payload["tools"][0]["function"]["name"] == "get_weather"
        assert payload["tool_choice"] == "auto"

    def test_builder_chaining(self) -> None:
        """Test builder method chaining."""
        class MockClient:
            _manifest = None
            _model_id = "gpt-4"

        builder = (
            ChatRequestBuilder(MockClient())
            .system("You are helpful")
            .user("Hello")
            .temperature(0.5)
            .max_tokens(200)
            .top_p(0.9)
            .stop(["\n"])
            .param("custom_param", "value")
        )

        payload = builder.build_payload()

        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 200
        assert payload["top_p"] == 0.9
        assert payload["stop"] == ["\n"]
        assert payload["custom_param"] == "value"
