"""Tests for pipeline module."""

import pytest

from ai_lib_python.pipeline import (
    DefaultEventMapper,
    JsonLinesDecoder,
    JsonPathSelector,
    Pipeline,
    SSEDecoder,
)


class TestSSEDecoder:
    """Tests for SSE decoder."""

    @pytest.mark.asyncio
    async def test_decode_simple_sse(self) -> None:
        """Test decoding simple SSE stream."""
        async def byte_stream():
            yield b'data: {"content": "Hello"}\n\n'
            yield b'data: {"content": "World"}\n\n'
            yield b'data: [DONE]\n\n'

        decoder = SSEDecoder()
        frames = []
        async for frame in decoder.decode(byte_stream()):
            frames.append(frame)

        assert len(frames) == 2
        assert frames[0]["content"] == "Hello"
        assert frames[1]["content"] == "World"

    @pytest.mark.asyncio
    async def test_decode_chunked_sse(self) -> None:
        """Test decoding SSE with chunked data."""
        async def byte_stream():
            yield b'data: {"con'
            yield b'tent": "Hello"}\n\n'
            yield b'data: [DONE]\n\n'

        decoder = SSEDecoder()
        frames = []
        async for frame in decoder.decode(byte_stream()):
            frames.append(frame)

        assert len(frames) == 1
        assert frames[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_decode_with_comments(self) -> None:
        """Test SSE decoder ignores comments."""
        async def byte_stream():
            yield b': this is a comment\n'
            yield b'data: {"value": 1}\n\n'
            yield b'data: [DONE]\n\n'

        decoder = SSEDecoder()
        frames = []
        async for frame in decoder.decode(byte_stream()):
            frames.append(frame)

        assert len(frames) == 1
        assert frames[0]["value"] == 1

    @pytest.mark.asyncio
    async def test_custom_done_signal(self) -> None:
        """Test SSE decoder with custom done signal."""
        async def byte_stream():
            yield b'data: {"value": 1}\n\n'
            yield b'data: END\n\n'

        decoder = SSEDecoder(done_signal="END")
        frames = []
        async for frame in decoder.decode(byte_stream()):
            frames.append(frame)

        assert len(frames) == 1


class TestJsonLinesDecoder:
    """Tests for JSON Lines decoder."""

    @pytest.mark.asyncio
    async def test_decode_json_lines(self) -> None:
        """Test decoding JSON Lines stream."""
        async def byte_stream():
            yield b'{"id": 1}\n'
            yield b'{"id": 2}\n'
            yield b'{"id": 3}\n'

        decoder = JsonLinesDecoder()
        frames = []
        async for frame in decoder.decode(byte_stream()):
            frames.append(frame)

        assert len(frames) == 3
        assert frames[0]["id"] == 1
        assert frames[1]["id"] == 2
        assert frames[2]["id"] == 3

    @pytest.mark.asyncio
    async def test_decode_chunked_json_lines(self) -> None:
        """Test decoding chunked JSON Lines."""
        async def byte_stream():
            yield b'{"id": '
            yield b'1}\n{"id": 2}\n'

        decoder = JsonLinesDecoder()
        frames = []
        async for frame in decoder.decode(byte_stream()):
            frames.append(frame)

        assert len(frames) == 2


class TestJsonPathSelector:
    """Tests for JSONPath selector."""

    def test_exists_expression(self) -> None:
        """Test exists() expression."""
        selector = JsonPathSelector("exists($.choices)")

        assert selector.matches({"choices": [{"delta": {}}]})
        assert not selector.matches({"other": "value"})
        assert not selector.matches({})

    def test_equality_expression(self) -> None:
        """Test equality expression."""
        selector = JsonPathSelector("$.type == 'content_block_delta'")

        assert selector.matches({"type": "content_block_delta"})
        assert not selector.matches({"type": "message_start"})
        assert not selector.matches({})

    def test_or_expression(self) -> None:
        """Test logical OR expression."""
        selector = JsonPathSelector("exists($.choices) || exists($.error)")

        assert selector.matches({"choices": []})
        assert selector.matches({"error": "something"})
        assert not selector.matches({"other": "value"})

    def test_and_expression(self) -> None:
        """Test logical AND expression."""
        selector = JsonPathSelector("exists($.type) && $.type == 'delta'")

        assert selector.matches({"type": "delta"})
        assert not selector.matches({"type": "other"})
        assert not selector.matches({})

    def test_nested_path(self) -> None:
        """Test nested path access."""
        selector = JsonPathSelector("exists($.choices[0].delta.content)")

        assert selector.matches({"choices": [{"delta": {"content": "hi"}}]})
        assert not selector.matches({"choices": [{"delta": {}}]})
        assert not selector.matches({"choices": []})

    def test_wildcard_path(self) -> None:
        """Test wildcard array access."""
        selector = JsonPathSelector("exists($.choices[*].delta.content)")

        assert selector.matches({"choices": [{"delta": {"content": "hi"}}]})
        assert selector.matches({"choices": [{"delta": {}}, {"delta": {"content": "hi"}}]})
        assert not selector.matches({"choices": [{"delta": {}}]})

    @pytest.mark.asyncio
    async def test_transform_filters_frames(self) -> None:
        """Test selector as transform filters frames."""
        async def frames():
            yield {"type": "delta", "content": "a"}
            yield {"type": "other", "content": "b"}
            yield {"type": "delta", "content": "c"}

        selector = JsonPathSelector("$.type == 'delta'")
        filtered = []
        async for frame in selector.transform(frames()):
            filtered.append(frame)

        assert len(filtered) == 2
        assert filtered[0]["content"] == "a"
        assert filtered[1]["content"] == "c"


class TestDefaultEventMapper:
    """Tests for default event mapper."""

    @pytest.mark.asyncio
    async def test_map_content_delta(self) -> None:
        """Test mapping content delta events."""
        async def frames():
            yield {"choices": [{"delta": {"content": "Hello"}}]}
            yield {"choices": [{"delta": {"content": " World"}}]}

        mapper = DefaultEventMapper()
        events = []
        async for event in mapper.map_events(frames()):
            events.append(event)

        assert len(events) == 2
        assert events[0].is_content_delta
        assert events[0].as_content_delta.content == "Hello"
        assert events[1].as_content_delta.content == " World"

    @pytest.mark.asyncio
    async def test_map_tool_calls(self) -> None:
        """Test mapping tool call events."""
        async def frames():
            yield {
                "choices": [{
                    "delta": {
                        "tool_calls": [{
                            "index": 0,
                            "id": "call_123",
                            "function": {"name": "get_weather"}
                        }]
                    }
                }]
            }
            yield {
                "choices": [{
                    "delta": {
                        "tool_calls": [{
                            "index": 0,
                            "function": {"arguments": '{"city":'}
                        }]
                    }
                }]
            }
            yield {
                "choices": [{
                    "delta": {
                        "tool_calls": [{
                            "index": 0,
                            "function": {"arguments": '"Tokyo"}'}
                        }]
                    }
                }]
            }

        mapper = DefaultEventMapper()
        events = []
        async for event in mapper.map_events(frames()):
            events.append(event)

        # Should have: ToolCallStarted, PartialToolCall x2
        assert any(e.is_tool_call_started for e in events)
        partial_events = [e for e in events if e.is_partial_tool_call]
        assert len(partial_events) == 2

        # Last partial should be complete
        assert partial_events[-1].as_partial_tool_call.is_complete

    @pytest.mark.asyncio
    async def test_map_error(self) -> None:
        """Test mapping error events."""
        async def frames():
            yield {"error": {"message": "Something went wrong"}}

        mapper = DefaultEventMapper()
        events = []
        async for event in mapper.map_events(frames()):
            events.append(event)

        assert len(events) == 1
        assert events[0].is_stream_error


class TestPipeline:
    """Tests for Pipeline class."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self) -> None:
        """Test full pipeline processing."""
        async def byte_stream():
            yield b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n'
            yield b'data: {"choices": [{"delta": {"content": " World"}}]}\n\n'
            yield b'data: [DONE]\n\n'

        pipeline = Pipeline(
            decoder=SSEDecoder(),
            event_mapper=DefaultEventMapper(),
        )

        events = []
        async for event in pipeline.process(byte_stream()):
            events.append(event)

        content_events = [e for e in events if e.is_content_delta]
        assert len(content_events) == 2

        full_content = "".join(e.as_content_delta.content for e in content_events)
        assert full_content == "Hello World"

    @pytest.mark.asyncio
    async def test_pipeline_with_selector(self) -> None:
        """Test pipeline with frame selector."""
        async def byte_stream():
            yield b'data: {"type": "ping"}\n\n'
            yield b'data: {"choices": [{"delta": {"content": "Hi"}}]}\n\n'
            yield b'data: [DONE]\n\n'

        pipeline = Pipeline(
            decoder=SSEDecoder(),
            transforms=[JsonPathSelector("exists($.choices)")],
            event_mapper=DefaultEventMapper(),
        )

        events = []
        async for event in pipeline.process(byte_stream()):
            events.append(event)

        # Ping frame should be filtered out
        content_events = [e for e in events if e.is_content_delta]
        assert len(content_events) == 1
        assert content_events[0].as_content_delta.content == "Hi"
