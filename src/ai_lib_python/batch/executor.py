"""
Batch executor for parallel request execution.

Executes multiple requests concurrently with rate limiting.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class BatchResult(Generic[R]):
    """Result of a batch execution.

    Attributes:
        results: List of results (None for failed requests)
        errors: List of errors (None for successful requests)
        total_time_ms: Total execution time in milliseconds
        successful_count: Number of successful requests
        failed_count: Number of failed requests
    """

    results: list[R | None] = field(default_factory=list)
    errors: list[Exception | None] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def successful_count(self) -> int:
        """Get count of successful results."""
        return sum(1 for e in self.errors if e is None)

    @property
    def failed_count(self) -> int:
        """Get count of failed results."""
        return sum(1 for e in self.errors if e is not None)

    @property
    def all_successful(self) -> bool:
        """Check if all requests succeeded."""
        return all(e is None for e in self.errors)

    def get_successful_results(self) -> list[R]:
        """Get only successful results."""
        return [r for r, e in zip(self.results, self.errors, strict=False) if e is None and r is not None]

    def get_errors(self) -> list[tuple[int, Exception]]:
        """Get errors with their indices."""
        return [(i, e) for i, e in enumerate(self.errors) if e is not None]


class BatchExecutor(Generic[T, R]):
    """Executes batches of requests concurrently.

    Provides controlled parallel execution with configurable
    concurrency limits.

    Example:
        >>> async def call_api(item):
        ...     return await client.chat().user(item).execute()
        ...
        >>> executor = BatchExecutor(call_api, max_concurrent=5)
        >>> result = await executor.execute(["Q1", "Q2", "Q3"])
        >>> print(result.successful_count)
    """

    def __init__(
        self,
        operation: Callable[[T], Awaitable[R]],
        max_concurrent: int = 10,
        fail_fast: bool = False,
    ) -> None:
        """Initialize batch executor.

        Args:
            operation: Async function to execute for each item
            max_concurrent: Maximum concurrent operations
            fail_fast: Stop on first error
        """
        self._operation = operation
        self._max_concurrent = max_concurrent
        self._fail_fast = fail_fast
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, items: Sequence[T]) -> BatchResult[R]:
        """Execute operation for all items.

        Args:
            items: Items to process

        Returns:
            BatchResult with results and errors
        """
        start_time = time.time()
        result = BatchResult[R]()

        # Create tasks
        tasks = [
            self._execute_one(item, idx, result)
            for idx, item in enumerate(items)
        ]

        # Initialize result lists
        result.results = [None] * len(items)
        result.errors = [None] * len(items)

        # Execute all tasks
        if self._fail_fast:
            # Stop on first error
            try:
                await asyncio.gather(*tasks)
            except Exception:
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
        else:
            # Continue on errors
            await asyncio.gather(*tasks, return_exceptions=True)

        result.total_time_ms = (time.time() - start_time) * 1000
        return result

    async def _execute_one(
        self,
        item: T,
        index: int,
        result: BatchResult[R],
    ) -> None:
        """Execute operation for a single item.

        Args:
            item: Item to process
            index: Item index
            result: Result object to update
        """
        async with self._semaphore:
            try:
                value = await self._operation(item)
                result.results[index] = value
            except Exception as e:
                result.errors[index] = e
                if self._fail_fast:
                    raise

    async def execute_with_progress(
        self,
        items: Sequence[T],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> BatchResult[R]:
        """Execute with progress callback.

        Args:
            items: Items to process
            on_progress: Callback(completed, total)

        Returns:
            BatchResult with results and errors
        """
        start_time = time.time()
        result = BatchResult[R]()
        completed = 0
        total = len(items)

        # Initialize result lists
        result.results = [None] * total
        result.errors = [None] * total

        async def execute_with_callback(item: T, index: int) -> None:
            nonlocal completed
            async with self._semaphore:
                try:
                    value = await self._operation(item)
                    result.results[index] = value
                except Exception as e:
                    result.errors[index] = e

                completed += 1
                if on_progress:
                    on_progress(completed, total)

        # Execute all tasks
        tasks = [execute_with_callback(item, idx) for idx, item in enumerate(items)]
        await asyncio.gather(*tasks, return_exceptions=True)

        result.total_time_ms = (time.time() - start_time) * 1000
        return result

    @property
    def max_concurrent(self) -> int:
        """Get maximum concurrent operations."""
        return self._max_concurrent


async def batch_execute(
    items: Sequence[T],
    operation: Callable[[T], Awaitable[R]],
    max_concurrent: int = 10,
    fail_fast: bool = False,
) -> BatchResult[R]:
    """Convenience function for batch execution.

    Args:
        items: Items to process
        operation: Async function for each item
        max_concurrent: Maximum concurrent operations
        fail_fast: Stop on first error

    Returns:
        BatchResult with results and errors
    """
    executor = BatchExecutor(operation, max_concurrent, fail_fast)
    return await executor.execute(items)
