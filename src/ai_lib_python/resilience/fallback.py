"""
Fallback chain for multi-model degradation.

Provides automatic failover between multiple AI providers/models.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from ai_lib_python.errors import AiLibError, is_fallbackable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


@dataclass
class FallbackTarget:
    """A target in the fallback chain.

    Attributes:
        name: Identifier for this target
        operation: Async operation factory
        weight: Priority weight (higher = preferred)
        enabled: Whether this target is enabled
    """

    name: str
    operation: Callable[..., Awaitable[T]]
    weight: float = 1.0
    enabled: bool = True


@dataclass
class FallbackConfig:
    """Configuration for fallback chain.

    Attributes:
        retry_all: Whether to retry all targets on failure
        max_attempts_per_target: Max attempts per target before fallback
        delay_between_targets_ms: Delay between fallback attempts
    """

    retry_all: bool = True
    max_attempts_per_target: int = 1
    delay_between_targets_ms: int = 0


@dataclass
class FallbackResult:
    """Result of a fallback chain execution.

    Attributes:
        success: Whether operation succeeded
        value: Result value (if success)
        target_used: Name of target that succeeded
        targets_tried: List of targets attempted
        errors: Mapping of target names to errors
    """

    success: bool
    value: Any = None
    target_used: str | None = None
    targets_tried: list[str] = field(default_factory=list)
    errors: dict[str, Exception] = field(default_factory=dict)


class FallbackChain:
    """Fallback chain for automatic failover.

    Executes operations through a chain of targets, falling back
    to the next target on failure.

    Example:
        >>> chain = FallbackChain()
        >>> chain.add_target("gpt-4", lambda: call_openai("gpt-4"))
        >>> chain.add_target("claude", lambda: call_anthropic("claude"))
        >>> result = await chain.execute()
    """

    def __init__(self, config: FallbackConfig | None = None) -> None:
        """Initialize fallback chain.

        Args:
            config: Fallback configuration
        """
        self._config = config or FallbackConfig()
        self._targets: list[FallbackTarget] = []

    def add_target(
        self,
        name: str,
        operation: Callable[..., Awaitable[T]],
        weight: float = 1.0,
        enabled: bool = True,
    ) -> FallbackChain:
        """Add a target to the fallback chain.

        Args:
            name: Target identifier
            operation: Async operation factory
            weight: Priority weight
            enabled: Whether target is enabled

        Returns:
            Self for chaining
        """
        self._targets.append(
            FallbackTarget(
                name=name,
                operation=operation,
                weight=weight,
                enabled=enabled,
            )
        )
        return self

    def remove_target(self, name: str) -> bool:
        """Remove a target from the chain.

        Args:
            name: Target name to remove

        Returns:
            True if removed, False if not found
        """
        for i, target in enumerate(self._targets):
            if target.name == name:
                self._targets.pop(i)
                return True
        return False

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable a target.

        Args:
            name: Target name
            enabled: Whether to enable

        Returns:
            True if target found, False otherwise
        """
        for target in self._targets:
            if target.name == name:
                target.enabled = enabled
                return True
        return False

    def get_targets(self) -> list[str]:
        """Get list of target names in priority order.

        Returns:
            List of target names
        """
        # Sort by weight (descending)
        sorted_targets = sorted(
            [t for t in self._targets if t.enabled],
            key=lambda t: t.weight,
            reverse=True,
        )
        return [t.name for t in sorted_targets]

    def _should_fallback(self, error: Exception) -> bool:
        """Check if error should trigger fallback.

        Args:
            error: The exception

        Returns:
            True if should fallback
        """
        # Check if error has error_class
        if hasattr(error, "error_class"):
            return is_fallbackable(error.error_class)

        # Default: fallback on any AiLibError
        return isinstance(error, AiLibError)

    async def execute(
        self,
        *args: Any,
        on_fallback: Callable[[str, str, Exception], None] | None = None,
        **kwargs: Any,
    ) -> FallbackResult:
        """Execute operation through fallback chain.

        Args:
            *args: Arguments to pass to operations
            on_fallback: Callback when falling back (from, to, error)
            **kwargs: Keyword arguments to pass to operations

        Returns:
            FallbackResult with outcome
        """
        # Get enabled targets sorted by weight
        targets = sorted(
            [t for t in self._targets if t.enabled],
            key=lambda t: t.weight,
            reverse=True,
        )

        if not targets:
            return FallbackResult(
                success=False,
                errors={"_chain": ValueError("No enabled targets in chain")},
            )

        errors: dict[str, Exception] = {}
        targets_tried: list[str] = []
        last_target: str | None = None

        for target in targets:
            targets_tried.append(target.name)

            for attempt in range(self._config.max_attempts_per_target):
                try:
                    result = await target.operation(*args, **kwargs)
                    return FallbackResult(
                        success=True,
                        value=result,
                        target_used=target.name,
                        targets_tried=targets_tried,
                        errors=errors,
                    )
                except Exception as e:
                    errors[target.name] = e

                    # Check if should fallback
                    if not self._should_fallback(e):
                        # Non-fallbackable error, stop chain
                        return FallbackResult(
                            success=False,
                            errors=errors,
                            targets_tried=targets_tried,
                        )

                    # Only retry if more attempts available
                    if attempt < self._config.max_attempts_per_target - 1:
                        continue
                    break

            # Callback before falling back
            if on_fallback and last_target:
                next_target = (
                    targets[targets.index(target) + 1].name
                    if targets.index(target) + 1 < len(targets)
                    else None
                )
                if next_target:
                    on_fallback(target.name, next_target, errors[target.name])

            last_target = target.name

            # Delay between targets
            if self._config.delay_between_targets_ms > 0:
                await asyncio.sleep(self._config.delay_between_targets_ms / 1000)

        # All targets failed
        return FallbackResult(
            success=False,
            errors=errors,
            targets_tried=targets_tried,
        )


class MultiFallback:
    """Multi-strategy fallback manager.

    Manages multiple fallback chains for different scenarios.

    Example:
        >>> mf = MultiFallback()
        >>> mf.register_chain("chat", chat_chain)
        >>> mf.register_chain("embed", embed_chain)
        >>> result = await mf.execute("chat", messages=[...])
    """

    def __init__(self) -> None:
        """Initialize multi-fallback manager."""
        self._chains: dict[str, FallbackChain] = {}

    def register_chain(self, name: str, chain: FallbackChain) -> MultiFallback:
        """Register a fallback chain.

        Args:
            name: Chain identifier
            chain: FallbackChain instance

        Returns:
            Self for chaining
        """
        self._chains[name] = chain
        return self

    def get_chain(self, name: str) -> FallbackChain | None:
        """Get a registered chain.

        Args:
            name: Chain name

        Returns:
            Chain or None if not found
        """
        return self._chains.get(name)

    async def execute(
        self,
        chain_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> FallbackResult:
        """Execute operation through a named chain.

        Args:
            chain_name: Name of chain to use
            *args: Arguments to pass
            **kwargs: Keyword arguments to pass

        Returns:
            FallbackResult

        Raises:
            ValueError: If chain not found
        """
        chain = self._chains.get(chain_name)
        if not chain:
            raise ValueError(f"Unknown fallback chain: {chain_name}")

        return await chain.execute(*args, **kwargs)

    def list_chains(self) -> list[str]:
        """Get list of registered chain names.

        Returns:
            List of chain names
        """
        return list(self._chains.keys())
