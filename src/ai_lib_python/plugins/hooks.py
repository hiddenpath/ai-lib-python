"""
Hook system for event-driven extensibility.

Provides a publish-subscribe pattern for plugin integration.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class HookType(str, Enum):
    """Types of hooks available."""

    # Request lifecycle
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"

    # Response lifecycle
    PRE_RESPONSE = "pre_response"
    POST_RESPONSE = "post_response"

    # Streaming
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"

    # Error handling
    ON_ERROR = "on_error"
    ON_RETRY = "on_retry"

    # Client lifecycle
    CLIENT_INIT = "client_init"
    CLIENT_CLOSE = "client_close"

    # Cache events
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_SET = "cache_set"


@dataclass
class Hook:
    """A registered hook.

    Attributes:
        hook_type: Type of hook
        callback: Callback function
        priority: Execution priority
        name: Optional hook name
    """

    hook_type: HookType
    callback: Callable[..., Awaitable[Any]]
    priority: int = 50
    name: str = ""

    def __lt__(self, other: Hook) -> bool:
        """Compare by priority."""
        return self.priority < other.priority


class HookManager:
    """Manages hooks and their execution.

    Example:
        >>> manager = HookManager()
        >>>
        >>> @manager.hook(HookType.PRE_REQUEST)
        >>> async def log_request(request):
        ...     print(f"Request: {request}")
        ...     return request
        >>>
        >>> # Execute hooks
        >>> modified = await manager.execute(HookType.PRE_REQUEST, request)
    """

    def __init__(self) -> None:
        """Initialize hook manager."""
        self._hooks: dict[HookType, list[Hook]] = {}

    def register(
        self,
        hook_type: HookType,
        callback: Callable[..., Awaitable[Any]],
        priority: int = 50,
        name: str = "",
    ) -> Hook:
        """Register a hook callback.

        Args:
            hook_type: Type of hook
            callback: Async callback function
            priority: Execution priority (lower = first)
            name: Optional name for the hook

        Returns:
            The registered Hook
        """
        hook = Hook(
            hook_type=hook_type,
            callback=callback,
            priority=priority,
            name=name or callback.__name__,
        )

        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        self._hooks[hook_type].append(hook)
        self._hooks[hook_type].sort()

        return hook

    def unregister(self, hook: Hook) -> bool:
        """Unregister a hook.

        Args:
            hook: Hook to unregister

        Returns:
            True if unregistered, False if not found
        """
        hooks = self._hooks.get(hook.hook_type, [])
        if hook in hooks:
            hooks.remove(hook)
            return True
        return False

    def hook(
        self,
        hook_type: HookType,
        priority: int = 50,
        name: str = "",
    ) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        """Decorator for registering hooks.

        Args:
            hook_type: Type of hook
            priority: Execution priority
            name: Optional hook name

        Returns:
            Decorator function
        """

        def decorator(
            func: Callable[..., Awaitable[Any]]
        ) -> Callable[..., Awaitable[Any]]:
            self.register(hook_type, func, priority, name)
            return func

        return decorator

    async def execute(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute all hooks of a type sequentially.

        Each hook receives the result of the previous hook.

        Args:
            hook_type: Type of hook to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Final result after all hooks
        """
        hooks = self._hooks.get(hook_type, [])

        if not hooks:
            return args[0] if args else None

        result = args[0] if args else None

        for hook in hooks:
            try:
                if result is not None:
                    result = await hook.callback(result, *args[1:], **kwargs)
                else:
                    result = await hook.callback(*args, **kwargs)
            except Exception:
                # Log error but continue
                pass

        return result

    async def execute_all(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> list[Any]:
        """Execute all hooks and collect results.

        Args:
            hook_type: Type of hook to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of results from all hooks
        """
        hooks = self._hooks.get(hook_type, [])

        if not hooks:
            return []

        results = []
        for hook in hooks:
            try:
                result = await hook.callback(*args, **kwargs)
                results.append(result)
            except Exception:
                results.append(None)

        return results

    async def execute_parallel(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> list[Any]:
        """Execute all hooks in parallel.

        Args:
            hook_type: Type of hook to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of results
        """
        hooks = self._hooks.get(hook_type, [])

        if not hooks:
            return []

        tasks = [hook.callback(*args, **kwargs) for hook in hooks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r if not isinstance(r, Exception) else None for r in results]

    def get_hooks(self, hook_type: HookType) -> list[Hook]:
        """Get all hooks of a type.

        Args:
            hook_type: Type of hook

        Returns:
            List of hooks
        """
        return list(self._hooks.get(hook_type, []))

    def clear(self, hook_type: HookType | None = None) -> None:
        """Clear hooks.

        Args:
            hook_type: Type to clear (all if None)
        """
        if hook_type:
            self._hooks[hook_type] = []
        else:
            self._hooks.clear()

    @property
    def hook_counts(self) -> dict[str, int]:
        """Get count of hooks by type."""
        return {ht.value: len(hooks) for ht, hooks in self._hooks.items()}


# Global hook manager
_global_hook_manager: HookManager | None = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager.

    Returns:
        Global HookManager instance
    """
    global _global_hook_manager
    if _global_hook_manager is None:
        _global_hook_manager = HookManager()
    return _global_hook_manager
