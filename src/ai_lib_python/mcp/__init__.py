"""MCP 工具桥接模块 — 将 MCP 服务器工具转换为 AI-Protocol 统一工具格式。

MCP (Model Context Protocol) tool bridge module. Converts tools exposed by
MCP servers into the AI-Protocol unified tool format, and maps tool calls
and results back to MCP wire format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpTool:
    """An MCP tool as received from an MCP server's ``tools/list`` response."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None


@dataclass
class McpToolInvocation:
    """An MCP tool invocation request (sent to an MCP server)."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class McpToolResult:
    """An MCP tool invocation result (received from an MCP server)."""

    content: list[dict[str, Any]] = field(default_factory=list)
    is_error: bool = False


@dataclass
class McpServerSpec:
    """MCP server connection descriptor."""

    name: str
    transport: str
    uri: str
    auth: dict[str, Any] | None = None


@dataclass
class McpProviderConfig:
    """Provider-specific MCP request configuration."""

    tool_type: str = "mcp"
    beta_header: str | None = None
    api_endpoint: str | None = None
    config_method: str = "tool_parameter"


class McpToolBridge:
    """Tool bridge: converts between MCP tools and AI-Protocol tools.

    The bridge is stateless and manifest-driven: it reads the provider's MCP
    configuration to determine naming conventions, filtering rules, and
    provider-specific formatting.

    Usage::

        bridge = McpToolBridge("fileserver")
        protocol_tools = bridge.mcp_tools_to_protocol(mcp_tools)
        # ... AI sends tool call with namespaced name ...
        invocation = bridge.protocol_call_to_mcp(tool_call)
    """

    def __init__(
        self,
        server_name: str,
        *,
        allow_filter: set[str] | None = None,
        deny_filter: set[str] | None = None,
    ) -> None:
        self._namespace = f"mcp__{server_name}__"
        self._allow = allow_filter or set()
        self._deny = deny_filter or set()

    def mcp_tools_to_protocol(
        self,
        mcp_tools: list[McpTool],
    ) -> list[dict[str, Any]]:
        """Convert MCP tools to AI-Protocol ``ToolDefinition`` dicts.

        Applies allow/deny filtering and namespaces tool names.
        """
        return [
            self._convert_tool(t)
            for t in mcp_tools
            if self._is_allowed(t.name)
        ]

    def protocol_call_to_mcp(
        self,
        call: dict[str, Any],
    ) -> McpToolInvocation | None:
        """Convert an AI-Protocol tool call back to MCP format.

        Returns ``None`` if the tool name doesn't match this bridge's namespace.
        """
        name = call.get("name", "")
        original = self._strip_namespace(name)
        if original is None:
            return None
        return McpToolInvocation(
            name=original,
            arguments=call.get("arguments", {}),
        )

    def mcp_result_to_protocol(
        self,
        tool_call_id: str,
        result: McpToolResult,
    ) -> dict[str, Any]:
        """Convert an MCP tool result to AI-Protocol format."""
        text_parts = [c.get("text", "") for c in result.content if c.get("type") == "text"]
        content = "\n".join(text_parts)
        return {
            "tool_use_id": tool_call_id,
            "content": {"error": content} if result.is_error else content,
            "is_error": result.is_error,
        }

    # -- internal --

    def _convert_tool(self, tool: McpTool) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": f"{self._namespace}{tool.name}",
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    def _is_allowed(self, name: str) -> bool:
        if self._deny and name in self._deny:
            return False
        if self._allow:
            return name in self._allow
        return True

    def _strip_namespace(self, namespaced: str) -> str | None:
        if namespaced.startswith(self._namespace):
            return namespaced[len(self._namespace):]
        return None


def extract_provider_config(mcp_config: dict[str, Any] | None) -> McpProviderConfig | None:
    """Extract provider-specific MCP configuration from a manifest's mcp section."""
    if not mcp_config:
        return None

    client = mcp_config if isinstance(mcp_config, dict) and "supported" in mcp_config else mcp_config.get("client", {}) if isinstance(mcp_config, dict) else {}
    if not client.get("supported"):
        return None

    mapping = client.get("provider_mapping", {})
    return McpProviderConfig(
        tool_type=mapping.get("tool_type", "mcp"),
        beta_header=mapping.get("beta_header"),
        api_endpoint=mapping.get("api_endpoint"),
        config_method=mapping.get("config_method", "tool_parameter"),
    )


__all__ = [
    "McpProviderConfig",
    "McpServerSpec",
    "McpTool",
    "McpToolBridge",
    "McpToolInvocation",
    "McpToolResult",
    "extract_provider_config",
]
