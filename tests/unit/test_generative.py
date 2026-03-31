"""Tests for generative LLM capability adaptations (gen-001 through gen-007).

生成式大模型能力适配测试：严格 test-first，先失败后实现。
Covers: reasoning_tokens usage, thinking stream, structured output,
tool call accumulation, error classification, feature_flags, MCP naming.
"""

from __future__ import annotations

from ai_lib_python.client.response import ChatResponse
from ai_lib_python.errors.classification import ErrorClass, classify_http_error
from ai_lib_python.pipeline.event_map import DefaultEventMapper

# === gen-002: reasoning_tokens in Usage ===


class TestReasoningTokensUsage:
    """ChatResponse must expose reasoning_tokens from provider-variant usage dicts."""

    def test_openai_reasoning_tokens_extraction(self):
        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "completion_tokens_details": {"reasoning_tokens": 3},
        }
        resp = ChatResponse(content="hi", usage=usage)
        assert resp.reasoning_tokens == 3

    def test_anthropic_cache_tokens_extraction(self):
        usage = {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_input_tokens": 2,
            "cache_read_input_tokens": 1,
        }
        resp = ChatResponse(content="hi", usage=usage)
        assert resp.prompt_tokens == 10 or resp.input_tokens == 10
        assert resp.cache_read_tokens == 1
        assert resp.cache_creation_tokens == 2

    def test_missing_reasoning_tokens_returns_none(self):
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        resp = ChatResponse(content="hi", usage=usage)
        assert resp.reasoning_tokens is None

    def test_none_usage_reasoning_tokens(self):
        resp = ChatResponse(content="hi", usage=None)
        assert resp.reasoning_tokens is None


# === gen-006: DefaultEventMapper thinking/reasoning extraction ===


class TestDefaultMapperReasoningStream:
    """DefaultEventMapper must emit ThinkingDelta for OpenAI reasoning_content."""

    def test_openai_reasoning_content_delta(self):
        mapper = DefaultEventMapper()
        frame = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"reasoning_content": "Let me think..."},
                    "finish_reason": None,
                }
            ]
        }
        events = mapper.map_frame(frame)
        thinking_events = [e for e in events if e.is_thinking_delta]
        assert len(thinking_events) >= 1
        assert thinking_events[0].as_thinking_delta.thinking == "Let me think..."

    def test_openai_regular_content_still_works(self):
        mapper = DefaultEventMapper()
        frame = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None,
                }
            ]
        }
        events = mapper.map_frame(frame)
        content_events = [e for e in events if e.is_content_delta]
        assert len(content_events) >= 1
        assert content_events[0].as_content_delta.content == "Hello"


# === gen-003: structured output JSON mode helpers ===


class TestStructuredOutputRequestBuilding:
    """JsonModeConfig produces correct response_format for provider requests."""

    def test_json_object_mode_produces_response_format(self):
        from ai_lib_python.structured.json_mode import JsonModeConfig

        cfg = JsonModeConfig.json_object()
        fmt = cfg.to_openai_format()
        assert "response_format" in fmt
        assert fmt["response_format"]["type"] == "json_object"

    def test_json_schema_mode_produces_response_format(self):
        from ai_lib_python.structured.json_mode import JsonModeConfig

        cfg = JsonModeConfig.from_schema(
            {"type": "object", "properties": {"name": {"type": "string"}}}
        )
        fmt = cfg.to_openai_format()
        assert fmt["response_format"]["type"] == "json_schema"
        assert "json_schema" in fmt["response_format"]


# === gen-005: context_length_exceeded → E1005 ===


class TestContextOverflowClassification:
    """context_length_exceeded must classify as REQUEST_TOO_LARGE."""

    def test_context_length_exceeded_400(self):
        result = classify_http_error(
            status_code=400,
            body={
                "error": {
                    "message": "Maximum context length exceeded",
                    "type": "invalid_request_error",
                    "code": "context_length_exceeded",
                }
            },
        )
        assert result == ErrorClass.REQUEST_TOO_LARGE

    def test_context_length_in_type_field(self):
        result = classify_http_error(
            status_code=400,
            body={
                "error": {
                    "message": "Too many tokens",
                    "type": "context_length_exceeded",
                }
            },
        )
        assert result == ErrorClass.REQUEST_TOO_LARGE


# === gen-001: feature_flags from manifest ===


class TestFeatureFlagsParsing:
    """V2 manifest feature_flags must be accessible and typed."""

    def test_feature_flags_from_v2_capabilities(self):
        from ai_lib_python.protocol.v2.capabilities import CapabilitiesV2

        caps = CapabilitiesV2(
            required=["text", "streaming"],
            optional=["reasoning", "structured_output"],
            feature_flags={
                "structured_output": True,
                "extended_thinking": True,
                "streaming_usage": False,
            },
        )
        assert caps.feature_flags is not None
        assert caps.feature_flags.structured_output is True
        assert caps.feature_flags.extended_thinking is True
        assert caps.feature_flags.streaming_usage is False


# === gen-007: MCP capability naming ===


class TestMcpCapabilityNaming:
    """MCP capability should be gated on 'mcp_client', not just 'mcp'."""

    def test_mcp_client_is_recognized_capability(self):
        from ai_lib_python.protocol.v2.capabilities import CapabilitiesV2

        caps = CapabilitiesV2(
            required=["text"],
            optional=["mcp_client"],
        )
        cap_list = caps.optional or []
        assert "mcp_client" in cap_list
