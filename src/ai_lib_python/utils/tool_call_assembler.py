"""
Tool call assembler for streaming responses.

Collects tool call fragments from streaming events and assembles
them into complete ToolCall objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ai_lib_python.types.tool import ToolCall


@dataclass
class ToolCallFragment:
    """Fragment of a tool call being assembled.

    Attributes:
        id: Tool call identifier
        name: Tool/function name
        arguments_buffer: Accumulated arguments string
        index: Position in the tool calls array
    """

    id: str
    name: str = ""
    arguments_buffer: str = ""
    index: int = 0


class ToolCallAssembler:
    """Assembles tool calls from streaming fragments.

    Collects tool call started events and argument fragments,
    then finalizes them into complete ToolCall objects.

    This is intentionally tolerant: if JSON parsing fails,
    it keeps the raw string as arguments.

    Example:
        >>> assembler = ToolCallAssembler()
        >>>
        >>> # Process streaming events
        >>> assembler.on_started("call_123", "get_weather")
        >>> assembler.on_partial("call_123", '{"loc')
        >>> assembler.on_partial("call_123", 'ation": "NYC"}')
        >>>
        >>> # Finalize
        >>> tool_calls = assembler.finalize()
        >>> print(tool_calls[0].arguments)
        {'location': 'NYC'}
    """

    def __init__(self) -> None:
        """Initialize assembler."""
        self._fragments: dict[str, ToolCallFragment] = {}
        self._order: list[str] = []  # Maintain insertion order

    def on_started(
        self,
        tool_call_id: str,
        tool_name: str,
        index: int | None = None,
    ) -> None:
        """Handle tool call started event.

        Args:
            tool_call_id: Unique tool call identifier
            tool_name: Name of the tool/function
            index: Optional index in tool calls array
        """
        if tool_call_id in self._fragments:
            # Update existing fragment with name if empty
            if tool_name and not self._fragments[tool_call_id].name:
                self._fragments[tool_call_id].name = tool_name
            return

        fragment = ToolCallFragment(
            id=tool_call_id,
            name=tool_name,
            index=index if index is not None else len(self._order),
        )
        self._fragments[tool_call_id] = fragment
        self._order.append(tool_call_id)

    def on_partial(
        self,
        tool_call_id: str,
        arguments_fragment: str,
    ) -> None:
        """Handle partial tool call arguments.

        Args:
            tool_call_id: Tool call identifier
            arguments_fragment: Partial arguments string
        """
        if tool_call_id not in self._fragments:
            # Create fragment if it doesn't exist
            self.on_started(tool_call_id, "")

        self._fragments[tool_call_id].arguments_buffer += arguments_fragment

    def on_name(self, tool_call_id: str, name_fragment: str) -> None:
        """Handle partial tool name (some APIs stream the name too).

        Args:
            tool_call_id: Tool call identifier
            name_fragment: Partial name string
        """
        if tool_call_id not in self._fragments:
            self.on_started(tool_call_id, name_fragment)
        else:
            self._fragments[tool_call_id].name += name_fragment

    def finalize(self) -> list[ToolCall]:
        """Finalize all tool calls.

        Parses accumulated argument strings as JSON and creates
        ToolCall objects. If JSON parsing fails, uses empty dict.

        Returns:
            List of assembled ToolCall objects
        """
        tool_calls: list[ToolCall] = []

        for tool_call_id in self._order:
            fragment = self._fragments[tool_call_id]

            # Try to parse arguments as JSON
            raw_arguments = fragment.arguments_buffer.strip()
            arguments: dict[str, Any] = {}
            arguments_raw: str | None = None

            if raw_arguments:
                try:
                    parsed = json.loads(raw_arguments)
                    if isinstance(parsed, dict):
                        arguments = parsed
                    else:
                        # Non-dict JSON, keep as raw
                        arguments_raw = raw_arguments
                except json.JSONDecodeError:
                    # Invalid JSON, store as raw
                    arguments_raw = raw_arguments

            tool_call = ToolCall(
                id=fragment.id,
                function_name=fragment.name,
                arguments=arguments,
                arguments_raw=arguments_raw,
            )
            tool_calls.append(tool_call)

        return tool_calls

    def finalize_and_reset(self) -> list[ToolCall]:
        """Finalize tool calls and reset state.

        Returns:
            List of assembled ToolCall objects
        """
        result = self.finalize()
        self.reset()
        return result

    def reset(self) -> None:
        """Reset assembler state."""
        self._fragments.clear()
        self._order.clear()

    def has_tool_calls(self) -> bool:
        """Check if any tool calls have been started.

        Returns:
            True if any tool calls exist
        """
        return len(self._fragments) > 0

    def get_fragment(self, tool_call_id: str) -> ToolCallFragment | None:
        """Get a specific fragment.

        Args:
            tool_call_id: Tool call identifier

        Returns:
            ToolCallFragment or None
        """
        return self._fragments.get(tool_call_id)

    @property
    def count(self) -> int:
        """Get number of tool calls being assembled."""
        return len(self._fragments)

    def __len__(self) -> int:
        """Get number of tool calls."""
        return len(self._fragments)


class MultiToolCallAssembler:
    """Assembles tool calls from multiple messages/responses.

    Manages multiple ToolCallAssembler instances keyed by message/turn ID.

    Example:
        >>> assembler = MultiToolCallAssembler()
        >>>
        >>> # First turn
        >>> assembler.on_started("turn1", "call_1", "search")
        >>> assembler.on_partial("turn1", "call_1", '{"query": "weather"}')
        >>>
        >>> # Second turn
        >>> assembler.on_started("turn2", "call_2", "calculate")
        >>> assembler.on_partial("turn2", "call_2", '{"expression": "2+2"}')
        >>>
        >>> # Finalize by turn
        >>> turn1_calls = assembler.finalize_turn("turn1")
        >>> turn2_calls = assembler.finalize_turn("turn2")
    """

    def __init__(self) -> None:
        """Initialize multi-assembler."""
        self._assemblers: dict[str, ToolCallAssembler] = {}

    def _get_assembler(self, turn_id: str) -> ToolCallAssembler:
        """Get or create assembler for a turn.

        Args:
            turn_id: Turn/message identifier

        Returns:
            ToolCallAssembler instance
        """
        if turn_id not in self._assemblers:
            self._assemblers[turn_id] = ToolCallAssembler()
        return self._assemblers[turn_id]

    def on_started(
        self,
        turn_id: str,
        tool_call_id: str,
        tool_name: str,
        index: int | None = None,
    ) -> None:
        """Handle tool call started event.

        Args:
            turn_id: Turn/message identifier
            tool_call_id: Tool call identifier
            tool_name: Tool name
            index: Optional index
        """
        self._get_assembler(turn_id).on_started(tool_call_id, tool_name, index)

    def on_partial(
        self,
        turn_id: str,
        tool_call_id: str,
        arguments_fragment: str,
    ) -> None:
        """Handle partial arguments.

        Args:
            turn_id: Turn/message identifier
            tool_call_id: Tool call identifier
            arguments_fragment: Arguments fragment
        """
        self._get_assembler(turn_id).on_partial(tool_call_id, arguments_fragment)

    def finalize_turn(self, turn_id: str) -> list[ToolCall]:
        """Finalize tool calls for a turn.

        Args:
            turn_id: Turn/message identifier

        Returns:
            List of ToolCall objects
        """
        if turn_id not in self._assemblers:
            return []
        return self._assemblers[turn_id].finalize()

    def finalize_all(self) -> dict[str, list[ToolCall]]:
        """Finalize all turns.

        Returns:
            Dictionary mapping turn IDs to tool call lists
        """
        return {
            turn_id: assembler.finalize()
            for turn_id, assembler in self._assemblers.items()
        }

    def reset(self) -> None:
        """Reset all assemblers."""
        self._assemblers.clear()

    def reset_turn(self, turn_id: str) -> None:
        """Reset a specific turn.

        Args:
            turn_id: Turn/message identifier
        """
        if turn_id in self._assemblers:
            del self._assemblers[turn_id]

    @property
    def turns(self) -> list[str]:
        """Get list of turn IDs."""
        return list(self._assemblers.keys())

    def __len__(self) -> int:
        """Get number of turns."""
        return len(self._assemblers)
