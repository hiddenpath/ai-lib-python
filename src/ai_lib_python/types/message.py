"""
Unified message format based on AI-Protocol standard_schema.

Provides Pythonic APIs for building messages with support for:
- Text messages
- Multimodal content (images, audio)
- Tool use and tool results
"""

from __future__ import annotations

import base64
import mimetypes
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Message role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ImageSource(BaseModel):
    """Image source for multimodal content."""

    model_config = ConfigDict(populate_by_name=True)

    source_type: str = Field(alias="type", description="Source type: 'base64' or 'url'")
    media_type: str | None = Field(default=None, description="MIME type of the image")
    data: str = Field(description="Base64 encoded data or URL")

    @classmethod
    def from_base64(cls, data: str, media_type: str | None = None) -> ImageSource:
        """Create from base64 encoded data."""
        return cls(source_type="base64", media_type=media_type, data=data)

    @classmethod
    def from_url(cls, url: str) -> ImageSource:
        """Create from URL."""
        return cls(source_type="url", data=url)


class AudioSource(BaseModel):
    """Audio source for multimodal content."""

    model_config = ConfigDict(populate_by_name=True)

    source_type: str = Field(alias="type", description="Source type: 'base64' or 'url'")
    media_type: str | None = Field(default=None, description="MIME type of the audio")
    data: str = Field(description="Base64 encoded data or URL")

    @classmethod
    def from_base64(cls, data: str, media_type: str | None = None) -> AudioSource:
        """Create from base64 encoded data."""
        return cls(source_type="base64", media_type=media_type, data=data)

    @classmethod
    def from_url(cls, url: str) -> AudioSource:
        """Create from URL."""
        return cls(source_type="url", data=url)


class ContentBlock(BaseModel):
    """Content block for multimodal or tool results.

    Supports the following types:
    - text: Plain text content
    - image: Image content (base64 or URL)
    - audio: Audio content (base64 or URL)
    - tool_use: Tool invocation request from the model
    - tool_result: Result of a tool execution
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(description="Content block type")

    # Text content
    text: str | None = Field(default=None, description="Text content")

    # Image content
    source: ImageSource | AudioSource | None = Field(
        default=None, description="Source for image/audio content"
    )

    # Tool use fields
    id: str | None = Field(default=None, description="Tool use ID")
    name: str | None = Field(default=None, description="Tool name")
    input: dict[str, Any] | None = Field(default=None, description="Tool input parameters")

    # Tool result fields
    tool_use_id: str | None = Field(default=None, description="Reference to tool_use ID")
    content: Any | None = Field(default=None, description="Tool result content")
    is_error: bool | None = Field(default=None, description="Whether the tool execution failed")

    @classmethod
    def text_block(cls, text: str) -> ContentBlock:
        """Create a text content block."""
        return cls(type="text", text=text)

    @classmethod
    def image_base64(cls, data: str, media_type: str | None = None) -> ContentBlock:
        """Create an image block from base64 data."""
        return cls(
            type="image",
            source=ImageSource.from_base64(data, media_type),
        )

    @classmethod
    def image_url(cls, url: str) -> ContentBlock:
        """Create an image block from URL."""
        return cls(
            type="image",
            source=ImageSource.from_url(url),
        )

    @classmethod
    def image_from_file(cls, path: str | Path) -> ContentBlock:
        """Create an image block from a local file.

        Args:
            path: Path to the image file

        Returns:
            ContentBlock with base64 encoded image data
        """
        file_path = Path(path)
        data = file_path.read_bytes()
        encoded = base64.standard_b64encode(data).decode("ascii")
        media_type = _guess_media_type(file_path)
        return cls.image_base64(encoded, media_type)

    @classmethod
    def audio_base64(cls, data: str, media_type: str | None = None) -> ContentBlock:
        """Create an audio block from base64 data."""
        return cls(
            type="audio",
            source=AudioSource.from_base64(data, media_type),
        )

    @classmethod
    def audio_from_file(cls, path: str | Path) -> ContentBlock:
        """Create an audio block from a local file.

        Args:
            path: Path to the audio file

        Returns:
            ContentBlock with base64 encoded audio data
        """
        file_path = Path(path)
        data = file_path.read_bytes()
        encoded = base64.standard_b64encode(data).decode("ascii")
        media_type = _guess_media_type(file_path)
        return cls.audio_base64(encoded, media_type)

    @classmethod
    def tool_use(cls, id: str, name: str, input: dict[str, Any]) -> ContentBlock:
        """Create a tool use content block.

        Args:
            id: Unique identifier for this tool invocation
            name: Tool name to invoke
            input: Tool input parameters

        Returns:
            ContentBlock representing a tool use request
        """
        return cls(type="tool_use", id=id, name=name, input=input)

    @classmethod
    def tool_result(
        cls,
        tool_use_id: str,
        content: Any,
        is_error: bool = False,
    ) -> ContentBlock:
        """Create a tool result content block.

        Args:
            tool_use_id: The ID of the corresponding tool_use
            content: Result content
            is_error: Whether the tool execution failed

        Returns:
            ContentBlock representing a tool result
        """
        return cls(
            type="tool_result",
            tool_use_id=tool_use_id,
            content=content,
            is_error=is_error if is_error else None,
        )


# Type alias for message content
MessageContent = str | list[ContentBlock]


class Message(BaseModel):
    """Unified message structure for AI conversations.

    Provides factory methods for common message patterns:
    - Message.system("prompt") - System message
    - Message.user("text") - User text message
    - Message.assistant("response") - Assistant response
    - Message.with_content(role, blocks) - Multimodal message

    Examples:
        >>> msg = Message.user("Hello!")
        >>> msg = Message.system("You are a helpful assistant.")
        >>> msg = Message.with_content(
        ...     MessageRole.USER,
        ...     [ContentBlock.text_block("Describe this:"), ContentBlock.image_from_file("photo.jpg")]
        ... )
    """

    model_config = ConfigDict(use_enum_values=True)

    role: MessageRole = Field(description="Message role")
    content: MessageContent = Field(description="Message content (text or content blocks)")

    @classmethod
    def system(cls, text: str) -> Message:
        """Create a system message.

        Args:
            text: System prompt text

        Returns:
            Message with system role
        """
        return cls(role=MessageRole.SYSTEM, content=text)

    @classmethod
    def user(cls, text: str) -> Message:
        """Create a user message with text content.

        Args:
            text: User message text

        Returns:
            Message with user role
        """
        return cls(role=MessageRole.USER, content=text)

    @classmethod
    def assistant(cls, text: str) -> Message:
        """Create an assistant message.

        Args:
            text: Assistant response text

        Returns:
            Message with assistant role
        """
        return cls(role=MessageRole.ASSISTANT, content=text)

    @classmethod
    def with_content(
        cls,
        role: MessageRole,
        content: list[ContentBlock],
    ) -> Message:
        """Create a message with multiple content blocks.

        Args:
            role: Message role
            content: List of content blocks

        Returns:
            Message with the specified content blocks
        """
        return cls(role=role, content=content)

    def contains_image(self) -> bool:
        """Check if the message contains image content."""
        if isinstance(self.content, str):
            return False
        return any(block.type == "image" for block in self.content)

    def contains_audio(self) -> bool:
        """Check if the message contains audio content."""
        if isinstance(self.content, str):
            return False
        return any(block.type == "audio" for block in self.content)

    def is_multimodal(self) -> bool:
        """Check if the message contains multimodal content."""
        return self.contains_image() or self.contains_audio()

    def get_text_content(self) -> str:
        """Extract text content from the message.

        Returns:
            Combined text content from all text blocks, or the string content directly.
        """
        if isinstance(self.content, str):
            return self.content
        texts = [block.text for block in self.content if block.type == "text" and block.text]
        return "\n".join(texts)


def _guess_media_type(path: Path) -> str | None:
    """Guess the MIME type from file extension."""
    # Common mappings that mimetypes might miss
    extension_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
    }

    suffix = path.suffix.lower()
    if suffix in extension_map:
        return extension_map[suffix]

    # Fallback to mimetypes
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type
