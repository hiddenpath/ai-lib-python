"""
Plugin registry for managing plugins.

Provides plugin registration, discovery, and lifecycle management.
"""

from __future__ import annotations

from typing import Any

from ai_lib_python.plugins.base import Plugin, PluginContext


class PluginRegistry:
    """Registry for managing plugins.

    Handles plugin registration, lookup, and lifecycle.

    Example:
        >>> registry = PluginRegistry()
        >>> registry.register(LoggingPlugin())
        >>> registry.register(CachingPlugin())
        >>>
        >>> # Initialize all plugins
        >>> await registry.init_all(ctx)
        >>>
        >>> # Process request through plugins
        >>> request = await registry.process_request(ctx, request)
    """

    def __init__(self) -> None:
        """Initialize plugin registry."""
        self._plugins: dict[str, Plugin] = {}
        self._ordered: list[Plugin] = []
        self._initialized = False

    def register(self, plugin: Plugin) -> PluginRegistry:
        """Register a plugin.

        Args:
            plugin: Plugin to register

        Returns:
            Self for chaining
        """
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")

        self._plugins[plugin.name] = plugin
        self._update_order()
        return self

    def unregister(self, name: str) -> bool:
        """Unregister a plugin.

        Args:
            name: Plugin name

        Returns:
            True if unregistered, False if not found
        """
        if name in self._plugins:
            del self._plugins[name]
            self._update_order()
            return True
        return False

    def get(self, name: str) -> Plugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin or None
        """
        return self._plugins.get(name)

    def has(self, name: str) -> bool:
        """Check if a plugin is registered.

        Args:
            name: Plugin name

        Returns:
            True if registered
        """
        return name in self._plugins

    def enable(self, name: str) -> bool:
        """Enable a plugin (no-op if already enabled).

        Args:
            name: Plugin name

        Returns:
            True if plugin exists
        """
        return name in self._plugins

    def disable(self, name: str) -> bool:
        """Disable a plugin by unregistering it.

        Args:
            name: Plugin name

        Returns:
            True if disabled
        """
        return self.unregister(name)

    async def init_all(self, ctx: PluginContext | None = None) -> None:
        """Initialize all registered plugins.

        Args:
            ctx: Plugin context
        """
        if self._initialized:
            return

        ctx = ctx or PluginContext()

        for plugin in self._ordered:
            if plugin.enabled:
                await plugin.on_init(ctx)

        self._initialized = True

    async def shutdown_all(self, ctx: PluginContext | None = None) -> None:
        """Shutdown all registered plugins.

        Args:
            ctx: Plugin context
        """
        if not self._initialized:
            return

        ctx = ctx or PluginContext()

        for plugin in reversed(self._ordered):
            if plugin.enabled:
                await plugin.on_shutdown(ctx)

        self._initialized = False

    async def process_request(
        self,
        ctx: PluginContext,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Process request through all plugins.

        Args:
            ctx: Plugin context
            request: Request payload

        Returns:
            Modified request
        """
        for plugin in self._ordered:
            if plugin.enabled:
                request = await plugin.on_request(ctx, request)
        return request

    async def process_response(
        self,
        ctx: PluginContext,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """Process response through all plugins.

        Args:
            ctx: Plugin context
            response: Response data

        Returns:
            Modified response
        """
        for plugin in reversed(self._ordered):
            if plugin.enabled:
                response = await plugin.on_response(ctx, response)
        return response

    async def process_error(
        self,
        ctx: PluginContext,
        error: Exception,
    ) -> Exception | None:
        """Process error through all plugins.

        Args:
            ctx: Plugin context
            error: The error

        Returns:
            Modified error or None to suppress
        """
        for plugin in self._ordered:
            if plugin.enabled:
                result = await plugin.on_error(ctx, error)
                if result is None:
                    return None
                error = result
        return error

    async def on_stream_start(self, ctx: PluginContext) -> None:
        """Notify plugins of stream start.

        Args:
            ctx: Plugin context
        """
        for plugin in self._ordered:
            if plugin.enabled:
                await plugin.on_stream_start(ctx)

    async def process_stream_chunk(
        self,
        ctx: PluginContext,
        chunk: dict[str, Any],
    ) -> dict[str, Any]:
        """Process stream chunk through all plugins.

        Args:
            ctx: Plugin context
            chunk: Stream chunk

        Returns:
            Modified chunk
        """
        for plugin in self._ordered:
            if plugin.enabled:
                chunk = await plugin.on_stream_chunk(ctx, chunk)
        return chunk

    async def on_stream_end(self, ctx: PluginContext) -> None:
        """Notify plugins of stream end.

        Args:
            ctx: Plugin context
        """
        for plugin in reversed(self._ordered):
            if plugin.enabled:
                await plugin.on_stream_end(ctx)

    def _update_order(self) -> None:
        """Update the plugin execution order."""
        self._ordered = sorted(
            self._plugins.values(),
            key=lambda p: p.priority,
        )

    @property
    def plugins(self) -> list[Plugin]:
        """Get all plugins in execution order."""
        return list(self._ordered)

    @property
    def plugin_names(self) -> list[str]:
        """Get all plugin names."""
        return [p.name for p in self._ordered]

    def __len__(self) -> int:
        """Get number of registered plugins."""
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        """Check if plugin is registered."""
        return name in self._plugins


# Global plugin registry
_global_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry.

    Returns:
        Global PluginRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def set_plugin_registry(registry: PluginRegistry) -> None:
    """Set the global plugin registry.

    Args:
        registry: PluginRegistry instance
    """
    global _global_registry
    _global_registry = registry
