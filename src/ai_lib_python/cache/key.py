"""
Cache key generation utilities.

Provides deterministic cache key generation for requests.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheKey:
    """A cache key with metadata.

    Attributes:
        key: The cache key string
        model: Model used
        messages_hash: Hash of messages
        params_hash: Hash of parameters
    """

    key: str
    model: str = ""
    messages_hash: str = ""
    params_hash: str = ""

    def __str__(self) -> str:
        """Return the key string."""
        return self.key

    def __hash__(self) -> int:
        """Return hash of the key."""
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if isinstance(other, CacheKey):
            return self.key == other.key
        if isinstance(other, str):
            return self.key == other
        return False


class CacheKeyGenerator:
    """Generates deterministic cache keys for requests.

    Example:
        >>> generator = CacheKeyGenerator()
        >>> key = generator.generate(
        ...     model="gpt-4o",
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     temperature=0.7,
        ... )
        >>> print(key.key)  # "ai:gpt-4o:a1b2c3..."
    """

    def __init__(
        self,
        prefix: str = "ai",
        include_model: bool = True,
        include_params: bool = True,
        excluded_params: list[str] | None = None,
    ) -> None:
        """Initialize key generator.

        Args:
            prefix: Key prefix
            include_model: Whether to include model in key
            include_params: Whether to include params in key
            excluded_params: Parameters to exclude from key
        """
        self._prefix = prefix
        self._include_model = include_model
        self._include_params = include_params
        self._excluded_params = set(excluded_params or ["user", "stream"])

    def generate(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **params: Any,
    ) -> CacheKey:
        """Generate a cache key.

        Args:
            model: Model name
            messages: Chat messages
            **params: Additional parameters

        Returns:
            CacheKey instance
        """
        # Hash messages
        messages_hash = self._hash_messages(messages)

        # Hash parameters
        filtered_params = {
            k: v for k, v in params.items() if k not in self._excluded_params
        }
        params_hash = self._hash_params(filtered_params)

        # Build key
        parts = [self._prefix]

        if self._include_model:
            parts.append(model)

        parts.append(messages_hash[:16])

        if self._include_params and params_hash:
            parts.append(params_hash[:8])

        key = ":".join(parts)

        return CacheKey(
            key=key,
            model=model,
            messages_hash=messages_hash,
            params_hash=params_hash,
        )

    def generate_for_embedding(
        self,
        model: str,
        input_text: str | list[str],
        dimensions: int | None = None,
    ) -> CacheKey:
        """Generate cache key for embedding request.

        Args:
            model: Model name
            input_text: Input text or list of texts
            dimensions: Output dimensions

        Returns:
            CacheKey instance
        """
        # Normalize input
        if isinstance(input_text, str):
            input_hash = self._hash_string(input_text)
        else:
            input_hash = self._hash_string(json.dumps(input_text, sort_keys=True))

        # Build key
        parts = [self._prefix, "emb", model, input_hash[:16]]

        if dimensions:
            parts.append(str(dimensions))

        key = ":".join(parts)

        return CacheKey(
            key=key,
            model=model,
            messages_hash=input_hash,
        )

    def _hash_messages(self, messages: list[dict[str, Any]]) -> str:
        """Hash a list of messages.

        Args:
            messages: Messages to hash

        Returns:
            Hash string
        """
        # Normalize messages for hashing
        normalized = []
        for msg in messages:
            normalized.append({
                "role": msg.get("role", ""),
                "content": self._normalize_content(msg.get("content", "")),
            })

        content = json.dumps(normalized, sort_keys=True, ensure_ascii=True)
        return self._hash_string(content)

    def _normalize_content(self, content: Any) -> Any:
        """Normalize message content for hashing.

        Args:
            content: Content to normalize

        Returns:
            Normalized content
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Handle content blocks
            normalized = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        normalized.append({"type": "text", "text": block.get("text", "")})
                    elif block.get("type") == "image_url":
                        # Include image URL in hash
                        normalized.append({
                            "type": "image_url",
                            "url": block.get("image_url", {}).get("url", ""),
                        })
                    else:
                        normalized.append(block)
                else:
                    normalized.append(block)
            return normalized
        return content

    def _hash_params(self, params: dict[str, Any]) -> str:
        """Hash parameters.

        Args:
            params: Parameters to hash

        Returns:
            Hash string
        """
        if not params:
            return ""

        content = json.dumps(params, sort_keys=True, ensure_ascii=True)
        return self._hash_string(content)

    def _hash_string(self, content: str) -> str:
        """Hash a string using SHA-256.

        Args:
            content: String to hash

        Returns:
            Hex digest
        """
        return hashlib.sha256(content.encode()).hexdigest()
