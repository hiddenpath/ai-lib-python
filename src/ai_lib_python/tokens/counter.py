"""
Token counter implementations.

Provides token counting for different models and providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_lib_python.types.message import Message


class TokenCounter(ABC):
    """Abstract base class for token counting.

    Example:
        >>> counter = TokenCounter.for_model("gpt-4o")
        >>> count = counter.count("Hello, world!")
        >>> print(f"Tokens: {count}")
    """

    @abstractmethod
    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        raise NotImplementedError

    def count_messages(self, messages: list[Message]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: Messages to count

        Returns:
            Total token count
        """
        total = 0
        for message in messages:
            # Count role (approximately 1 token)
            total += 1

            # Count content
            if isinstance(message.content, str):
                total += self.count(message.content)
            else:
                # Content blocks
                for block in message.content:
                    if block.type == "text" and block.text:
                        total += self.count(block.text)
                    elif block.type == "image_url" or block.type == "image":
                        # Images have fixed token cost (approximate)
                        total += 85  # Base cost for images

        # Add message overhead (approximately 3 tokens per message)
        total += len(messages) * 3

        return total

    def truncate_to_limit(
        self,
        text: str,
        max_tokens: int,
        suffix: str = "...",
    ) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        current_count = self.count(text)
        if current_count <= max_tokens:
            return text

        # Binary search for optimal truncation point
        suffix_tokens = self.count(suffix) if suffix else 0
        target_tokens = max_tokens - suffix_tokens

        if target_tokens <= 0:
            return suffix

        # Estimate characters per token
        chars_per_token = len(text) / current_count

        # Start with estimate
        estimate_chars = int(target_tokens * chars_per_token)
        truncated = text[:estimate_chars]

        # Refine
        while self.count(truncated) > target_tokens and len(truncated) > 0:
            # Remove 10% at a time
            truncated = truncated[: int(len(truncated) * 0.9)]

        return truncated + suffix

    @classmethod
    def for_model(cls, model: str) -> TokenCounter:
        """Get a token counter for a specific model.

        Args:
            model: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet")

        Returns:
            Appropriate TokenCounter
        """
        model_lower = model.lower()

        # OpenAI models - use tiktoken if available
        if any(x in model_lower for x in ["gpt", "o1", "text-embedding", "davinci"]):
            try:
                return TiktokenCounter.for_model(model)
            except ImportError:
                pass

        # Anthropic models
        if any(x in model_lower for x in ["claude", "anthropic"]):
            return AnthropicEstimator()

        # Default to character-based estimation
        return CharacterEstimator()


class TiktokenCounter(TokenCounter):
    """Token counter using tiktoken for OpenAI models.

    Requires tiktoken package: pip install tiktoken
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        """Initialize with encoding.

        Args:
            encoding_name: Tiktoken encoding name
        """
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding(encoding_name)
        except ImportError as e:
            raise ImportError(
                "tiktoken is required for accurate OpenAI token counting. "
                "Install it with: pip install tiktoken"
            ) from e

    def count(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self._encoding.encode(text))

    @classmethod
    def for_model(cls, model: str) -> TiktokenCounter:
        """Get counter for a specific model.

        Args:
            model: Model name

        Returns:
            TiktokenCounter with appropriate encoding
        """
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(model)
            counter = cls.__new__(cls)
            counter._encoding = encoding
            return counter
        except (ImportError, KeyError):
            # Fall back to cl100k_base for unknown models
            return cls("cl100k_base")


class CharacterEstimator(TokenCounter):
    """Simple character-based token estimator.

    Uses the approximation of ~4 characters per token for English.
    """

    def __init__(self, chars_per_token: float = 4.0) -> None:
        """Initialize estimator.

        Args:
            chars_per_token: Average characters per token
        """
        self._chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        """Estimate tokens from character count."""
        return max(1, int(len(text) / self._chars_per_token))


class AnthropicEstimator(TokenCounter):
    """Token estimator for Anthropic models.

    Uses character-based estimation tuned for Claude models.
    Anthropic's tokenization is similar to GPT but with some differences.
    """

    def __init__(self) -> None:
        """Initialize estimator."""
        # Anthropic uses a slightly different tokenization
        # Approximately 3.5 characters per token on average
        self._chars_per_token = 3.5

    def count(self, text: str) -> int:
        """Estimate tokens for Anthropic models."""
        # Base estimation
        base_count = max(1, int(len(text) / self._chars_per_token))

        # Adjust for whitespace (Anthropic tends to have more tokens for whitespace)
        whitespace_count = text.count(" ") + text.count("\n") + text.count("\t")
        adjustment = int(whitespace_count * 0.1)

        return base_count + adjustment


class CachingCounter(TokenCounter):
    """Token counter with caching for repeated strings.

    Wraps another counter and caches results.
    """

    def __init__(
        self,
        counter: TokenCounter,
        max_cache_size: int = 10000,
    ) -> None:
        """Initialize caching counter.

        Args:
            counter: Underlying counter
            max_cache_size: Maximum cache entries
        """
        self._counter = counter
        self._cache: dict[str, int] = {}
        self._max_cache_size = max_cache_size

    def count(self, text: str) -> int:
        """Count tokens with caching."""
        if text in self._cache:
            return self._cache[text]

        count = self._counter.count(text)

        # Add to cache if not full
        if len(self._cache) < self._max_cache_size:
            self._cache[text] = count

        return count

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()


# Global counters cache
_counters: dict[str, TokenCounter] = {}


def get_token_counter(model: str) -> TokenCounter:
    """Get a token counter for a model (cached).

    Args:
        model: Model identifier

    Returns:
        TokenCounter for the model
    """
    if model not in _counters:
        _counters[model] = TokenCounter.for_model(model)
    return _counters[model]
