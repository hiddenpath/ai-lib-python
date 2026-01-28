"""
Middleware system for request/response processing.

Provides a chain-of-responsibility pattern for processing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass
class MiddlewareContext:
    """Context for middleware execution.

    Attributes:
        request: Current request
        response: Current response (if available)
        model: Model identifier
        provider: Provider identifier
        metadata: Additional metadata
        aborted: Whether processing was aborted
    """

    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] | None = None
    model: str = ""
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    aborted: bool = False

    def abort(self, response: dict[str, Any] | None = None) -> None:
        """Abort middleware chain and return response.

        Args:
            response: Response to return
        """
        self.aborted = True
        if response:
            self.response = response


class Middleware(ABC):
    """Base class for middleware.

    Middleware processes requests and responses in a chain.

    Example:
        >>> class LoggingMiddleware(Middleware):
        ...     async def process(self, ctx, next):
        ...         print(f"Request: {ctx.request}")
        ...         response = await next(ctx)
        ...         print(f"Response: {response}")
        ...         return response
    """

    @property
    def name(self) -> str:
        """Get middleware name.

        Returns:
            Middleware name
        """
        return self.__class__.__name__

    @abstractmethod
    async def process(
        self,
        ctx: MiddlewareContext,
        next: Callable[[MiddlewareContext], Awaitable[dict[str, Any] | None]],
    ) -> dict[str, Any] | None:
        """Process the request/response.

        Args:
            ctx: Middleware context
            next: Next middleware in chain

        Returns:
            Response data
        """
        raise NotImplementedError


class MiddlewareChain:
    """Chain of middleware for processing.

    Example:
        >>> chain = MiddlewareChain()
        >>> chain.use(LoggingMiddleware())
        >>> chain.use(CachingMiddleware())
        >>>
        >>> async def handler(ctx):
        ...     # Make actual request
        ...     return response
        >>>
        >>> result = await chain.execute(ctx, handler)
    """

    def __init__(self) -> None:
        """Initialize middleware chain."""
        self._middleware: list[Middleware] = []

    def use(self, middleware: Middleware) -> MiddlewareChain:
        """Add middleware to the chain.

        Args:
            middleware: Middleware to add

        Returns:
            Self for chaining
        """
        self._middleware.append(middleware)
        return self

    def use_before(
        self, middleware: Middleware, before: type | str
    ) -> MiddlewareChain:
        """Add middleware before another.

        Args:
            middleware: Middleware to add
            before: Middleware class or name to insert before

        Returns:
            Self for chaining
        """
        for i, m in enumerate(self._middleware):
            if (isinstance(before, type) and isinstance(m, before)) or (
                isinstance(before, str) and m.name == before
            ):
                self._middleware.insert(i, middleware)
                return self

        # If not found, add at start
        self._middleware.insert(0, middleware)
        return self

    def use_after(
        self, middleware: Middleware, after: type | str
    ) -> MiddlewareChain:
        """Add middleware after another.

        Args:
            middleware: Middleware to add
            after: Middleware class or name to insert after

        Returns:
            Self for chaining
        """
        for i, m in enumerate(self._middleware):
            if (isinstance(after, type) and isinstance(m, after)) or (
                isinstance(after, str) and m.name == after
            ):
                self._middleware.insert(i + 1, middleware)
                return self

        # If not found, add at end
        self._middleware.append(middleware)
        return self

    def remove(self, middleware: type | str | Middleware) -> bool:
        """Remove middleware from the chain.

        Args:
            middleware: Middleware to remove (class, name, or instance)

        Returns:
            True if removed, False if not found
        """
        for i, m in enumerate(self._middleware):
            if (
                m is middleware
                or (isinstance(middleware, type) and isinstance(m, middleware))
                or (isinstance(middleware, str) and m.name == middleware)
            ):
                self._middleware.pop(i)
                return True
        return False

    async def execute(
        self,
        ctx: MiddlewareContext,
        handler: Callable[[MiddlewareContext], Awaitable[dict[str, Any] | None]],
    ) -> dict[str, Any] | None:
        """Execute the middleware chain.

        Args:
            ctx: Middleware context
            handler: Final handler to execute

        Returns:
            Response data
        """
        if not self._middleware:
            return await handler(ctx)

        # Build chain from end to start
        chain = handler

        for middleware in reversed(self._middleware):
            # Capture middleware in closure
            chain = self._create_next(middleware, chain)

        return await chain(ctx)

    def _create_next(
        self,
        middleware: Middleware,
        next_handler: Callable[[MiddlewareContext], Awaitable[dict[str, Any] | None]],
    ) -> Callable[[MiddlewareContext], Awaitable[dict[str, Any] | None]]:
        """Create next handler in chain.

        Args:
            middleware: Current middleware
            next_handler: Next handler

        Returns:
            Wrapped handler
        """

        async def handler(ctx: MiddlewareContext) -> dict[str, Any] | None:
            if ctx.aborted:
                return ctx.response
            return await middleware.process(ctx, next_handler)

        return handler

    @property
    def middleware_names(self) -> list[str]:
        """Get list of middleware names."""
        return [m.name for m in self._middleware]

    def __len__(self) -> int:
        """Get number of middleware."""
        return len(self._middleware)


class FunctionMiddleware(Middleware):
    """Middleware created from a function.

    Example:
        >>> async def log_request(ctx, next):
        ...     print(f"Request: {ctx.request}")
        ...     return await next(ctx)
        >>>
        >>> middleware = FunctionMiddleware("logging", log_request)
    """

    def __init__(
        self,
        name: str,
        func: Callable[
            [
                MiddlewareContext,
                Callable[[MiddlewareContext], Awaitable[dict[str, Any] | None]],
            ],
            Awaitable[dict[str, Any] | None],
        ],
    ) -> None:
        """Initialize function middleware.

        Args:
            name: Middleware name
            func: Middleware function
        """
        self._name = name
        self._func = func

    @property
    def name(self) -> str:
        """Get middleware name."""
        return self._name

    async def process(
        self,
        ctx: MiddlewareContext,
        next: Callable[[MiddlewareContext], Awaitable[dict[str, Any] | None]],
    ) -> dict[str, Any] | None:
        """Process using the function."""
        return await self._func(ctx, next)
