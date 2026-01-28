"""
Plugin system for ai-lib-python.

Provides extensibility through hooks, middleware, and plugins.
"""

from ai_lib_python.plugins.base import Plugin, PluginContext, PluginPriority
from ai_lib_python.plugins.hooks import (
    Hook,
    HookManager,
    HookType,
)
from ai_lib_python.plugins.middleware import (
    Middleware,
    MiddlewareChain,
    MiddlewareContext,
)
from ai_lib_python.plugins.registry import PluginRegistry, get_plugin_registry

__all__ = [
    "Hook",
    "HookManager",
    "HookType",
    "Middleware",
    "MiddlewareChain",
    "MiddlewareContext",
    "Plugin",
    "PluginContext",
    "PluginPriority",
    "PluginRegistry",
    "get_plugin_registry",
]
