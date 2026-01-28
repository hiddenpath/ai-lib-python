"""
Base plugin classes and interfaces.

Defines the core plugin architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class PluginPriority(IntEnum):
    """Plugin execution priority.

    Lower values execute first.
    """

    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class PluginContext:
    """Context passed to plugins.

    Attributes:
        model: Model identifier
        provider: Provider identifier
        request_id: Unique request ID
        metadata: Additional metadata
    """

    model: str = ""
    provider: str = ""
    request_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **kwargs: Any) -> PluginContext:
        """Create new context with additional metadata.

        Args:
            **kwargs: Metadata to add

        Returns:
            New PluginContext
        """
        return PluginContext(
            model=self.model,
            provider=self.provider,
            request_id=self.request_id,
            metadata={**self.metadata, **kwargs},
        )


class Plugin(ABC):
    """Base class for plugins.

    Plugins can hook into the request lifecycle to modify
    requests, responses, or add functionality.

    Example:
        >>> class LoggingPlugin(Plugin):
        ...     @property
        ...     def name(self) -> str:
        ...         return "logging"
        ...
        ...     async def on_request(self, ctx, request):
        ...         print(f"Request: {request}")
        ...         return request
        ...
        ...     async def on_response(self, ctx, response):
        ...         print(f"Response: {response}")
        ...         return response
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the plugin name.

        Returns:
            Plugin name
        """
        raise NotImplementedError

    @property
    def priority(self) -> PluginPriority:
        """Get plugin priority.

        Returns:
            Plugin priority
        """
        return PluginPriority.NORMAL

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled.

        Returns:
            True if enabled
        """
        return True

    async def on_init(self, ctx: PluginContext) -> None:
        """Called when plugin is initialized.

        Args:
            ctx: Plugin context
        """
        pass

    async def on_shutdown(self, ctx: PluginContext) -> None:
        """Called when plugin is shut down.

        Args:
            ctx: Plugin context
        """
        pass

    async def on_request(
        self,
        ctx: PluginContext,  # noqa: ARG002
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Called before sending a request.

        Args:
            ctx: Plugin context
            request: Request payload

        Returns:
            Modified request payload
        """
        return request

    async def on_response(
        self,
        ctx: PluginContext,  # noqa: ARG002
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Called after receiving a response.

        Args:
            ctx: Plugin context
            response: Response data

        Returns:
            Modified response data
        """
        return response

    async def on_error(
        self,
        ctx: PluginContext,  # noqa: ARG002
        error: Exception,
    ) -> Exception | None:
        """Called when an error occurs.

        Args:
            ctx: Plugin context
            error: The error

        Returns:
            Modified error or None to suppress
        """
        return error

    async def on_stream_start(
        self,
        ctx: PluginContext,
    ) -> None:
        """Called when streaming starts.

        Args:
            ctx: Plugin context
        """
        pass

    async def on_stream_chunk(
        self,
        ctx: PluginContext,  # noqa: ARG002
        chunk: dict[str, Any],
    ) -> dict[str, Any]:
        """Called for each streaming chunk.

        Args:
            ctx: Plugin context
            chunk: Stream chunk

        Returns:
            Modified chunk
        """
        return chunk

    async def on_stream_end(
        self,
        ctx: PluginContext,
    ) -> None:
        """Called when streaming ends.

        Args:
            ctx: Plugin context
        """
        pass


class CompositePlugin(Plugin):
    """Plugin that combines multiple plugins.

    Example:
        >>> composite = CompositePlugin("combined", [plugin1, plugin2])
        >>> registry.register(composite)
    """

    def __init__(
        self,
        name: str,
        plugins: list[Plugin],
        priority: PluginPriority = PluginPriority.NORMAL,
    ) -> None:
        """Initialize composite plugin.

        Args:
            name: Plugin name
            plugins: List of plugins to combine
            priority: Plugin priority
        """
        self._name = name
        self._plugins = sorted(plugins, key=lambda p: p.priority)
        self._priority = priority

    @property
    def name(self) -> str:
        """Get plugin name."""
        return self._name

    @property
    def priority(self) -> PluginPriority:
        """Get plugin priority."""
        return self._priority

    async def on_init(self, ctx: PluginContext) -> None:
        """Initialize all plugins."""
        for plugin in self._plugins:
            if plugin.enabled:
                await plugin.on_init(ctx)

    async def on_shutdown(self, ctx: PluginContext) -> None:
        """Shutdown all plugins."""
        for plugin in reversed(self._plugins):
            if plugin.enabled:
                await plugin.on_shutdown(ctx)

    async def on_request(
        self,
        ctx: PluginContext,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Process request through all plugins."""
        for plugin in self._plugins:
            if plugin.enabled:
                request = await plugin.on_request(ctx, request)
        return request

    async def on_response(
        self,
        ctx: PluginContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Process response through all plugins."""
        for plugin in reversed(self._plugins):
            if plugin.enabled:
                response = await plugin.on_response(ctx, response)
        return response

    async def on_error(
        self,
        ctx: PluginContext,
        error: Exception,
    ) -> Exception | None:
        """Process error through all plugins."""
        for plugin in self._plugins:
            if plugin.enabled:
                result = await plugin.on_error(ctx, error)
                if result is None:
                    return None
                error = result
        return error
