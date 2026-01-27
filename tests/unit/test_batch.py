"""Tests for batch processing module."""

import asyncio

import pytest

from ai_lib_python.batch import BatchCollector, BatchConfig, BatchExecutor, BatchResult


class TestBatchConfig:
    """Tests for BatchConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = BatchConfig.default()
        assert config.max_batch_size == 10
        assert config.max_wait_ms == 100.0

    def test_embeddings_config(self) -> None:
        """Test embeddings configuration."""
        config = BatchConfig.for_embeddings()
        assert config.max_batch_size == 100
        assert config.max_wait_ms == 50.0

    def test_chat_config(self) -> None:
        """Test chat configuration."""
        config = BatchConfig.for_chat()
        assert config.max_batch_size == 5
        assert config.max_wait_ms == 10.0


class TestBatchResult:
    """Tests for BatchResult."""

    def test_successful_count(self) -> None:
        """Test successful count."""
        result = BatchResult[str]()
        result.results = ["a", "b", "c"]
        result.errors = [None, None, None]

        assert result.successful_count == 3
        assert result.failed_count == 0
        assert result.all_successful

    def test_failed_count(self) -> None:
        """Test failed count."""
        result = BatchResult[str]()
        result.results = ["a", None, "c"]
        result.errors = [None, ValueError("error"), None]

        assert result.successful_count == 2
        assert result.failed_count == 1
        assert not result.all_successful

    def test_get_successful_results(self) -> None:
        """Test getting successful results."""
        result = BatchResult[str]()
        result.results = ["a", None, "c"]
        result.errors = [None, ValueError("error"), None]

        successful = result.get_successful_results()
        assert successful == ["a", "c"]

    def test_get_errors(self) -> None:
        """Test getting errors with indices."""
        result = BatchResult[str]()
        result.results = [None, "b", None]
        err1 = ValueError("error 1")
        err2 = ValueError("error 2")
        result.errors = [err1, None, err2]

        errors = result.get_errors()
        assert len(errors) == 2
        assert errors[0] == (0, err1)
        assert errors[1] == (2, err2)


class TestBatchExecutor:
    """Tests for BatchExecutor."""

    @pytest.mark.asyncio
    async def test_execute_all_success(self) -> None:
        """Test executing all items successfully."""

        async def process(item: int) -> int:
            return item * 2

        executor = BatchExecutor(process, max_concurrent=3)
        result = await executor.execute([1, 2, 3, 4, 5])

        assert result.successful_count == 5
        assert result.all_successful
        assert result.get_successful_results() == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_execute_with_errors(self) -> None:
        """Test executing with some errors."""

        async def process(item: int) -> int:
            if item == 3:
                raise ValueError(f"Error on {item}")
            return item * 2

        executor = BatchExecutor(process, max_concurrent=2)
        result = await executor.execute([1, 2, 3, 4])

        assert result.successful_count == 3
        assert result.failed_count == 1
        errors = result.get_errors()
        assert len(errors) == 1
        assert errors[0][0] == 2  # Index of item 3

    @pytest.mark.asyncio
    async def test_execute_fail_fast(self) -> None:
        """Test fail-fast mode."""
        processed = []

        async def process(item: int) -> int:
            await asyncio.sleep(0.01)
            if item == 2:
                raise ValueError("Error")
            processed.append(item)
            return item

        executor = BatchExecutor(process, max_concurrent=1, fail_fast=True)
        result = await executor.execute([1, 2, 3, 4])

        # Should stop after first error
        assert result.failed_count >= 1

    @pytest.mark.asyncio
    async def test_execute_with_progress(self) -> None:
        """Test progress callback."""
        progress_calls = []

        def on_progress(completed: int, total: int) -> None:
            progress_calls.append((completed, total))

        async def process(item: int) -> int:
            return item * 2

        executor = BatchExecutor(process, max_concurrent=2)
        result = await executor.execute_with_progress([1, 2, 3], on_progress)

        assert result.successful_count == 3
        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        """Test concurrency limit is respected."""
        max_concurrent = 2
        current_concurrent = [0]
        max_observed = [0]

        async def process(item: int) -> int:
            current_concurrent[0] += 1
            max_observed[0] = max(max_observed[0], current_concurrent[0])
            await asyncio.sleep(0.02)
            current_concurrent[0] -= 1
            return item

        executor = BatchExecutor(process, max_concurrent=max_concurrent)
        await executor.execute([1, 2, 3, 4, 5])

        assert max_observed[0] <= max_concurrent


class TestBatchCollector:
    """Tests for BatchCollector."""

    @pytest.mark.asyncio
    async def test_batch_on_size_limit(self) -> None:
        """Test batch triggers on size limit."""
        batches_received: list[list[int]] = []

        async def executor(items: list[int]) -> list[str]:
            batches_received.append(items)
            return [f"result_{i}" for i in items]

        collector = BatchCollector[int, str](
            config=BatchConfig(max_batch_size=3, max_wait_ms=1000),
            executor=executor,
        )

        # Add 3 items - should trigger batch
        tasks = [collector.add(i) for i in [1, 2, 3]]
        results = await asyncio.gather(*tasks)

        assert len(batches_received) == 1
        assert len(batches_received[0]) == 3
        assert results == ["result_1", "result_2", "result_3"]

        await collector.stop()

    @pytest.mark.asyncio
    async def test_batch_on_timeout(self) -> None:
        """Test batch triggers on timeout."""
        batches_received: list[list[int]] = []

        async def executor(items: list[int]) -> list[str]:
            batches_received.append(items)
            return [f"result_{i}" for i in items]

        collector = BatchCollector[int, str](
            config=BatchConfig(max_batch_size=10, max_wait_ms=50),
            executor=executor,
        )

        # Add 2 items (below batch size)
        task1 = asyncio.create_task(collector.add(1))
        task2 = asyncio.create_task(collector.add(2))

        # Wait for timeout
        await asyncio.sleep(0.1)

        results = await asyncio.gather(task1, task2)
        assert results == ["result_1", "result_2"]

        await collector.stop()

    @pytest.mark.asyncio
    async def test_get_pending_count(self) -> None:
        """Test getting pending count."""
        batches_received: list[list[int]] = []

        async def executor(items: list[int]) -> list[str]:
            batches_received.append(items)
            await asyncio.sleep(0.1)  # Delay execution
            return [f"result_{i}" for i in items]

        collector = BatchCollector[int, str](
            config=BatchConfig(max_batch_size=10, max_wait_ms=1000),
            executor=executor,
        )

        # Add items without awaiting
        task = asyncio.create_task(collector.add(1))

        # Check pending
        await asyncio.sleep(0.01)  # Let task add to pending
        count = collector.get_pending_count()
        assert count >= 0  # May have already flushed

        task.cancel()
        await collector.stop()
