"""Tests for plugins module."""

import pytest

from ai_lib_python.plugins import (
    HookManager,
    HookType,
    Middleware,
    MiddlewareChain,
    MiddlewareContext,
    Plugin,
    PluginContext,
    PluginRegistry,
)
from ai_lib_python.plugins.middleware import FunctionMiddleware


class TestPluginContext:
    """Tests for PluginContext."""

    def test_basic_context(self) -> None:
        """Test basic context creation."""
        ctx = PluginContext(model="gpt-4o", provider="openai")
        assert ctx.model == "gpt-4o"
        assert ctx.provider == "openai"

    def test_with_metadata(self) -> None:
        """Test adding metadata."""
        ctx = PluginContext(model="gpt-4o")
        new_ctx = ctx.with_metadata(key="value", count=42)
        assert new_ctx.metadata["key"] == "value"
        assert new_ctx.metadata["count"] == 42
        assert ctx.model == new_ctx.model


class SimplePlugin(Plugin):
    """Simple test plugin."""

    def __init__(self, name: str = "simple") -> None:
        self._name = name
        self.request_count = 0
        self.response_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def on_request(
        self, ctx: PluginContext, request: dict  # noqa: ARG002
    ) -> dict:
        self.request_count += 1
        request["modified_by"] = self._name
        return request

    async def on_response(
        self, ctx: PluginContext, response: dict  # noqa: ARG002
    ) -> dict:
        self.response_count += 1
        return response


class TestPlugin:
    """Tests for Plugin base class."""

    @pytest.mark.asyncio
    async def test_on_request(self) -> None:
        """Test on_request hook."""
        plugin = SimplePlugin()
        ctx = PluginContext()
        request = {"prompt": "Hello"}

        result = await plugin.on_request(ctx, request)
        assert result["modified_by"] == "simple"
        assert plugin.request_count == 1

    @pytest.mark.asyncio
    async def test_on_response(self) -> None:
        """Test on_response hook."""
        plugin = SimplePlugin()
        ctx = PluginContext()
        response = {"content": "Hi"}

        await plugin.on_response(ctx, response)
        assert plugin.response_count == 1


class TestPluginRegistry:
    """Tests for PluginRegistry."""

    def test_register(self) -> None:
        """Test plugin registration."""
        registry = PluginRegistry()
        plugin = SimplePlugin("test")

        registry.register(plugin)
        assert "test" in registry
        assert len(registry) == 1

    def test_register_duplicate(self) -> None:
        """Test duplicate registration raises error."""
        registry = PluginRegistry()
        plugin = SimplePlugin("test")

        registry.register(plugin)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(plugin)

    def test_unregister(self) -> None:
        """Test plugin unregistration."""
        registry = PluginRegistry()
        plugin = SimplePlugin("test")

        registry.register(plugin)
        removed = registry.unregister("test")
        assert removed
        assert "test" not in registry

    def test_get_plugin(self) -> None:
        """Test getting plugin by name."""
        registry = PluginRegistry()
        plugin = SimplePlugin("test")

        registry.register(plugin)
        retrieved = registry.get("test")
        assert retrieved is plugin

    @pytest.mark.asyncio
    async def test_process_request(self) -> None:
        """Test processing request through plugins."""
        registry = PluginRegistry()
        plugin1 = SimplePlugin("p1")
        plugin2 = SimplePlugin("p2")

        registry.register(plugin1)
        registry.register(plugin2)

        ctx = PluginContext()
        request = {"prompt": "Hello"}

        await registry.process_request(ctx, request)
        assert plugin1.request_count == 1
        assert plugin2.request_count == 1

    @pytest.mark.asyncio
    async def test_init_and_shutdown(self) -> None:
        """Test initialization and shutdown."""
        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin)

        await registry.init_all(PluginContext())
        # Should not error on double init
        await registry.init_all(PluginContext())

        await registry.shutdown_all(PluginContext())


class TestHookManager:
    """Tests for HookManager."""

    def test_register_hook(self) -> None:
        """Test hook registration."""
        manager = HookManager()

        async def my_hook(request: dict) -> dict:
            return request

        hook = manager.register(HookType.PRE_REQUEST, my_hook)
        assert hook.hook_type == HookType.PRE_REQUEST
        hooks = manager.get_hooks(HookType.PRE_REQUEST)
        assert len(hooks) == 1

    def test_unregister_hook(self) -> None:
        """Test hook unregistration."""
        manager = HookManager()

        async def my_hook(request: dict) -> dict:
            return request

        hook = manager.register(HookType.PRE_REQUEST, my_hook)
        removed = manager.unregister(hook)
        assert removed
        assert len(manager.get_hooks(HookType.PRE_REQUEST)) == 0

    def test_decorator(self) -> None:
        """Test decorator registration."""
        manager = HookManager()

        @manager.hook(HookType.POST_RESPONSE)
        async def process_response(response: dict) -> dict:
            return response

        hooks = manager.get_hooks(HookType.POST_RESPONSE)
        assert len(hooks) == 1

    @pytest.mark.asyncio
    async def test_execute_hooks(self) -> None:
        """Test hook execution."""
        manager = HookManager()
        calls = []

        async def hook1(data: dict) -> dict:
            calls.append("hook1")
            data["hook1"] = True
            return data

        async def hook2(data: dict) -> dict:
            calls.append("hook2")
            data["hook2"] = True
            return data

        manager.register(HookType.PRE_REQUEST, hook1, priority=10)
        manager.register(HookType.PRE_REQUEST, hook2, priority=20)

        result = await manager.execute(HookType.PRE_REQUEST, {"original": True})
        assert calls == ["hook1", "hook2"]  # Ordered by priority
        assert result["hook1"]
        assert result["hook2"]

    @pytest.mark.asyncio
    async def test_execute_parallel(self) -> None:
        """Test parallel hook execution."""
        manager = HookManager()

        async def hook1(data: dict) -> str:
            return "result1"

        async def hook2(data: dict) -> str:
            return "result2"

        manager.register(HookType.CACHE_HIT, hook1)
        manager.register(HookType.CACHE_HIT, hook2)

        results = await manager.execute_parallel(HookType.CACHE_HIT, {})
        assert "result1" in results
        assert "result2" in results

    def test_clear_hooks(self) -> None:
        """Test clearing hooks."""
        manager = HookManager()

        async def my_hook(data: dict) -> dict:
            return data

        manager.register(HookType.PRE_REQUEST, my_hook)
        manager.register(HookType.POST_REQUEST, my_hook)

        manager.clear(HookType.PRE_REQUEST)
        assert len(manager.get_hooks(HookType.PRE_REQUEST)) == 0
        assert len(manager.get_hooks(HookType.POST_REQUEST)) == 1

        manager.clear()
        assert len(manager.get_hooks(HookType.POST_REQUEST)) == 0


class SimpleMiddleware(Middleware):
    """Simple test middleware."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    async def process(self, ctx, next):
        self.calls.append(f"{self._name}:before")
        result = await next(ctx)
        self.calls.append(f"{self._name}:after")
        return result


class TestMiddlewareChain:
    """Tests for MiddlewareChain."""

    def test_use_middleware(self) -> None:
        """Test adding middleware."""
        chain = MiddlewareChain()
        m1 = SimpleMiddleware("m1")
        m2 = SimpleMiddleware("m2")

        chain.use(m1).use(m2)
        assert len(chain) == 2
        assert chain.middleware_names == ["m1", "m2"]

    def test_remove_middleware(self) -> None:
        """Test removing middleware."""
        chain = MiddlewareChain()
        m1 = SimpleMiddleware("m1")

        chain.use(m1)
        removed = chain.remove(m1)
        assert removed
        assert len(chain) == 0

    @pytest.mark.asyncio
    async def test_execute_chain(self) -> None:
        """Test middleware chain execution."""
        chain = MiddlewareChain()
        m1 = SimpleMiddleware("m1")
        m2 = SimpleMiddleware("m2")

        chain.use(m1).use(m2)

        async def handler(ctx):
            return {"handled": True}

        ctx = MiddlewareContext(request={"test": True})
        result = await chain.execute(ctx, handler)

        assert result == {"handled": True}
        assert m1.calls == ["m1:before", "m1:after"]
        assert m2.calls == ["m2:before", "m2:after"]

    @pytest.mark.asyncio
    async def test_abort_chain(self) -> None:
        """Test aborting middleware chain."""

        class AbortingMiddleware(Middleware):
            @property
            def name(self) -> str:
                return "aborting"

            async def process(self, ctx, next):  # noqa: ARG002
                ctx.abort({"aborted": True})
                return ctx.response

        chain = MiddlewareChain()
        chain.use(AbortingMiddleware())
        chain.use(SimpleMiddleware("should_not_run"))

        async def handler(ctx):
            return {"handled": True}

        ctx = MiddlewareContext()
        result = await chain.execute(ctx, handler)
        assert result == {"aborted": True}

    @pytest.mark.asyncio
    async def test_function_middleware(self) -> None:
        """Test FunctionMiddleware."""
        calls = []

        async def log_middleware(ctx, next):
            calls.append("before")
            result = await next(ctx)
            calls.append("after")
            return result

        chain = MiddlewareChain()
        chain.use(FunctionMiddleware("logger", log_middleware))

        async def handler(ctx):
            calls.append("handler")
            return {"done": True}

        await chain.execute(MiddlewareContext(), handler)
        assert calls == ["before", "handler", "after"]
