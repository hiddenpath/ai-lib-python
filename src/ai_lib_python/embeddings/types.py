"""
Embedding types and data models.

Defines the core types for embedding operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EmbeddingModel(str, Enum):
    """Standard embedding models."""

    # OpenAI
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"

    # Cohere
    EMBED_ENGLISH_V3 = "embed-english-v3.0"
    EMBED_MULTILINGUAL_V3 = "embed-multilingual-v3.0"
    EMBED_ENGLISH_LIGHT_V3 = "embed-english-light-v3.0"

    # Voyage
    VOYAGE_LARGE_2 = "voyage-large-2"
    VOYAGE_CODE_2 = "voyage-code-2"

    # Google
    TEXT_EMBEDDING_004 = "text-embedding-004"

    @property
    def dimensions(self) -> int:
        """Get default dimensions for the model."""
        dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "embed-english-v3.0": 1024,
            "embed-multilingual-v3.0": 1024,
            "embed-english-light-v3.0": 384,
            "voyage-large-2": 1536,
            "voyage-code-2": 1536,
            "text-embedding-004": 768,
        }
        return dimensions_map.get(self.value, 1536)

    @property
    def max_tokens(self) -> int:
        """Get maximum input tokens for the model."""
        max_tokens_map = {
            "text-embedding-3-small": 8191,
            "text-embedding-3-large": 8191,
            "text-embedding-ada-002": 8191,
            "embed-english-v3.0": 512,
            "embed-multilingual-v3.0": 512,
            "embed-english-light-v3.0": 512,
            "voyage-large-2": 16000,
            "voyage-code-2": 16000,
            "text-embedding-004": 2048,
        }
        return max_tokens_map.get(self.value, 8191)


@dataclass
class EmbeddingUsage:
    """Token usage information for embedding request.

    Attributes:
        prompt_tokens: Number of tokens in the input
        total_tokens: Total tokens used
    """

    prompt_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class Embedding:
    """A single embedding result.

    Attributes:
        index: Index in the batch
        vector: The embedding vector
        object_type: Object type (always "embedding")
    """

    index: int
    vector: list[float]
    object_type: str = "embedding"

    @property
    def dimensions(self) -> int:
        """Get the dimensionality of the embedding."""
        return len(self.vector)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "embedding": self.vector,
            "object": self.object_type,
        }

    @classmethod
    def from_openai_format(cls, data: dict[str, Any]) -> Embedding:
        """Create from OpenAI API response format.

        Args:
            data: OpenAI embedding object

        Returns:
            Embedding instance
        """
        return cls(
            index=data.get("index", 0),
            vector=data.get("embedding", []),
            object_type=data.get("object", "embedding"),
        )


@dataclass
class EmbeddingRequest:
    """Request for generating embeddings.

    Attributes:
        input: Text or list of texts to embed
        model: Model to use
        dimensions: Output dimensions (if supported)
        encoding_format: Output format ("float" or "base64")
        user: User identifier for tracking
    """

    input: str | list[str]
    model: str = "text-embedding-3-small"
    dimensions: int | None = None
    encoding_format: str = "float"
    user: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API request format."""
        data: dict[str, Any] = {
            "input": self.input,
            "model": self.model,
        }
        if self.dimensions is not None:
            data["dimensions"] = self.dimensions
        if self.encoding_format != "float":
            data["encoding_format"] = self.encoding_format
        if self.user:
            data["user"] = self.user
        return data

    @property
    def is_batch(self) -> bool:
        """Check if this is a batch request."""
        return isinstance(self.input, list)

    @property
    def batch_size(self) -> int:
        """Get the number of inputs."""
        if isinstance(self.input, list):
            return len(self.input)
        return 1


@dataclass
class EmbeddingResponse:
    """Response from embedding generation.

    Attributes:
        embeddings: List of embedding results
        model: Model used
        usage: Token usage information
        object_type: Object type (always "list")
    """

    embeddings: list[Embedding] = field(default_factory=list)
    model: str = ""
    usage: EmbeddingUsage = field(default_factory=EmbeddingUsage)
    object_type: str = "list"

    @property
    def first(self) -> Embedding | None:
        """Get the first embedding."""
        return self.embeddings[0] if self.embeddings else None

    @property
    def vectors(self) -> list[list[float]]:
        """Get all vectors."""
        return [e.vector for e in self.embeddings]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "object": self.object_type,
            "data": [e.to_dict() for e in self.embeddings],
            "model": self.model,
            "usage": self.usage.to_dict(),
        }

    @classmethod
    def from_openai_format(cls, data: dict[str, Any]) -> EmbeddingResponse:
        """Create from OpenAI API response format.

        Args:
            data: OpenAI embeddings response

        Returns:
            EmbeddingResponse instance
        """
        embeddings = [
            Embedding.from_openai_format(e) for e in data.get("data", [])
        ]
        usage_data = data.get("usage", {})
        usage = EmbeddingUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )
        return cls(
            embeddings=embeddings,
            model=data.get("model", ""),
            usage=usage,
            object_type=data.get("object", "list"),
        )
