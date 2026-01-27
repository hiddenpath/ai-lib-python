"""
Stream decoders for various formats.

Implements:
- SSEDecoder: Server-Sent Events (most common)
- JsonLinesDecoder: JSON Lines / NDJSON
"""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING, Any

from ai_lib_python.pipeline.base import Decoder

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ai_lib_python.protocol.manifest import DecoderConfig


class SSEDecoder(Decoder):
    """Server-Sent Events (SSE) decoder.

    Parses SSE format:
    ```
    data: {"key": "value"}

    data: {"key": "value2"}

    data: [DONE]
    ```

    Attributes:
        delimiter: Frame delimiter (default: "\\n\\n")
        prefix: Data line prefix (default: "data: ")
        done_signal: End of stream signal (default: "[DONE]")
    """

    def __init__(
        self,
        delimiter: str = "\n\n",
        prefix: str = "data: ",
        done_signal: str = "[DONE]",
    ) -> None:
        """Initialize SSE decoder.

        Args:
            delimiter: Frame delimiter
            prefix: Data line prefix to strip
            done_signal: Signal indicating end of stream
        """
        self._delimiter = delimiter
        self._prefix = prefix
        self._done_signal = done_signal

    async def decode(
        self, byte_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[dict[str, Any]]:
        """Decode SSE byte stream into JSON frames.

        Args:
            byte_stream: Async iterator of raw bytes

        Yields:
            Parsed JSON frames
        """
        buffer = ""

        async for chunk in byte_stream:
            # Decode bytes to string
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                # Try with replacement for malformed bytes
                text = chunk.decode("utf-8", errors="replace")

            buffer += text

            # Split by delimiter and process complete frames
            while self._delimiter in buffer:
                frame, buffer = buffer.split(self._delimiter, 1)
                frame = frame.strip()

                if not frame:
                    continue

                # Process each line in the frame
                for line in frame.split("\n"):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith(":"):
                        continue

                    # Handle data lines
                    if line.startswith(self._prefix):
                        data = line[len(self._prefix) :]

                        # Check for done signal
                        if data == self._done_signal:
                            return

                        # Parse JSON
                        if data:
                            try:
                                yield json.loads(data)
                            except json.JSONDecodeError:
                                # Skip malformed JSON, but log it
                                pass

                    # Handle event: lines (for event type)
                    elif line.startswith("event:"):
                        # Event type - could be used for routing
                        pass

        # Process any remaining data in buffer
        if buffer.strip():
            for line in buffer.strip().split("\n"):
                line = line.strip()
                if line.startswith(self._prefix):
                    data = line[len(self._prefix) :]
                    if data and data != self._done_signal:
                        with contextlib.suppress(json.JSONDecodeError):
                            yield json.loads(data)


class JsonLinesDecoder(Decoder):
    """JSON Lines (NDJSON) decoder.

    Parses newline-delimited JSON:
    ```
    {"key": "value"}
    {"key": "value2"}
    ```
    """

    def __init__(self, delimiter: str = "\n") -> None:
        """Initialize JSON Lines decoder.

        Args:
            delimiter: Line delimiter (default: newline)
        """
        self._delimiter = delimiter

    async def decode(
        self, byte_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[dict[str, Any]]:
        """Decode JSON Lines byte stream into JSON frames.

        Args:
            byte_stream: Async iterator of raw bytes

        Yields:
            Parsed JSON frames
        """
        buffer = ""

        async for chunk in byte_stream:
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                text = chunk.decode("utf-8", errors="replace")

            buffer += text

            # Split by delimiter and process complete lines
            while self._delimiter in buffer:
                line, buffer = buffer.split(self._delimiter, 1)
                line = line.strip()

                if not line:
                    continue

                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed JSON
                    pass

        # Process remaining buffer
        if buffer.strip():
            with contextlib.suppress(json.JSONDecodeError):
                yield json.loads(buffer.strip())


class AnthropicSSEDecoder(Decoder):
    """Anthropic-specific SSE decoder.

    Handles Anthropic's event stream format with event types:
    ```
    event: message_start
    data: {"type": "message_start", ...}

    event: content_block_delta
    data: {"type": "content_block_delta", ...}
    ```
    """

    def __init__(self) -> None:
        """Initialize Anthropic SSE decoder."""
        self._delimiter = "\n\n"

    async def decode(
        self, byte_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[dict[str, Any]]:
        """Decode Anthropic SSE byte stream.

        Args:
            byte_stream: Async iterator of raw bytes

        Yields:
            Parsed JSON frames with event type included
        """
        buffer = ""

        async for chunk in byte_stream:
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                text = chunk.decode("utf-8", errors="replace")

            buffer += text

            while self._delimiter in buffer:
                frame, buffer = buffer.split(self._delimiter, 1)
                frame = frame.strip()

                if not frame:
                    continue

                event_type = None
                data = None

                for line in frame.split("\n"):
                    line = line.strip()

                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data = line[5:].strip()

                if data:
                    try:
                        parsed = json.loads(data)
                        # Include event type if not already in data
                        if event_type and "event" not in parsed:
                            parsed["_event_type"] = event_type
                        yield parsed
                    except json.JSONDecodeError:
                        pass


def create_decoder(config: DecoderConfig | None) -> Decoder:
    """Create a decoder from configuration.

    Args:
        config: Decoder configuration from manifest

    Returns:
        Appropriate decoder instance
    """
    if config is None:
        return SSEDecoder()

    format_type = config.format.lower() if config.format else "sse"

    if format_type == "sse":
        return SSEDecoder(
            delimiter=config.delimiter or "\n\n",
            prefix=config.prefix or "data: ",
            done_signal=config.done_signal or "[DONE]",
        )
    elif format_type == "json_lines" or format_type == "ndjson":
        return JsonLinesDecoder(delimiter=config.delimiter or "\n")
    elif format_type == "anthropic_sse":
        return AnthropicSSEDecoder()
    else:
        # Default to SSE
        return SSEDecoder()
