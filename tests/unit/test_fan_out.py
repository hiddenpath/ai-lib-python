"""Tests for FanOut transform."""

import pytest

from ai_lib_python.pipeline import (
    FanOutTransform,
    ReplicateTransform,
    SplitTransform,
    create_fan_out,
)


async def async_list(items: list) -> list:
    """Helper to collect async iterator results."""
    result = []
    async for item in items:
        result.append(item)
    return result


async def create_async_iter(items: list):
    """Create async iterator from list."""
    for item in items:
        yield item


class TestFanOutTransform:
    """Tests for FanOutTransform."""

    @pytest.mark.asyncio
    async def test_disabled_passthrough(self) -> None:
        """Test disabled fan-out passes through."""
        fan_out = FanOutTransform(enabled=False)
        input_data = [{"choices": [1, 2, 3]}]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 1
        assert result[0] == {"choices": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_expand_top_level_array(self) -> None:
        """Test expanding top-level arrays."""
        fan_out = FanOutTransform()
        input_data = [[1, 2, 3]]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_expand_choices_array(self) -> None:
        """Test expanding choices array."""
        fan_out = FanOutTransform()
        input_data = [{"choices": [{"text": "a"}, {"text": "b"}]}]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_expand_with_path(self) -> None:
        """Test expanding with explicit path."""
        fan_out = FanOutTransform(array_path="data.items")
        input_data = [{"data": {"items": [1, 2, 3]}}]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_preserve_metadata(self) -> None:
        """Test preserving metadata from parent."""
        fan_out = FanOutTransform(array_path="choices", preserve_metadata=True)
        input_data = [{"model": "gpt-4", "choices": [{"text": "a"}]}]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 1
        assert result[0]["model"] == "gpt-4"
        assert result[0]["text"] == "a"

    @pytest.mark.asyncio
    async def test_no_array_passthrough(self) -> None:
        """Test non-array objects pass through."""
        fan_out = FanOutTransform()
        input_data = [{"key": "value"}]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert result == [{"key": "value"}]

    @pytest.mark.asyncio
    async def test_non_dict_passthrough(self) -> None:
        """Test non-dict items pass through."""
        fan_out = FanOutTransform()
        input_data = ["string", 123]

        result = []
        async for item in fan_out.transform(create_async_iter(input_data)):
            result.append(item)

        assert result == ["string", 123]


class TestReplicateTransform:
    """Tests for ReplicateTransform."""

    @pytest.mark.asyncio
    async def test_replicate_default(self) -> None:
        """Test default replication (2 copies)."""
        replicate = ReplicateTransform()
        input_data = [{"value": 1}]

        result = []
        async for item in replicate.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 2
        assert result[0] == result[1]

    @pytest.mark.asyncio
    async def test_replicate_count(self) -> None:
        """Test custom replication count."""
        replicate = ReplicateTransform(count=5)
        input_data = ["item"]

        result = []
        async for item in replicate.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_replicate_with_index(self) -> None:
        """Test replication with index."""
        replicate = ReplicateTransform(count=3, add_index=True)
        input_data = [{"value": 1}]

        result = []
        async for item in replicate.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 3
        assert result[0]["_replica_index"] == 0
        assert result[1]["_replica_index"] == 1
        assert result[2]["_replica_index"] == 2


class TestSplitTransform:
    """Tests for SplitTransform."""

    @pytest.mark.asyncio
    async def test_split_with_predicate(self) -> None:
        """Test splitting with predicate."""
        split = SplitTransform(predicate=lambda x: x.get("type") == "content")
        input_data = [
            {"type": "content", "text": "hello"},
            {"type": "metadata", "count": 1},
            {"type": "content", "text": "world"},
        ]

        result = []
        async for item in split.transform(create_async_iter(input_data)):
            result.append(item)

        assert len(result) == 2  # Only content items
        assert all(item["type"] == "content" for item in result)

    @pytest.mark.asyncio
    async def test_get_filtered(self) -> None:
        """Test getting filtered items."""
        split = SplitTransform(predicate=lambda x: x > 5)
        input_data = [1, 10, 3, 15, 2]

        result = []
        async for item in split.transform(create_async_iter(input_data)):
            result.append(item)

        filtered = split.get_filtered()
        assert result == [10, 15]
        assert filtered == [1, 3, 2]

    @pytest.mark.asyncio
    async def test_clear_filtered(self) -> None:
        """Test clearing filtered buffer."""
        split = SplitTransform(predicate=lambda x: x > 5)
        input_data = [1, 10]

        async for _ in split.transform(create_async_iter(input_data)):
            pass

        assert len(split.get_filtered()) == 1
        split.clear_filtered()
        assert len(split.get_filtered()) == 0


class TestCreateFanOut:
    """Tests for create_fan_out factory."""

    def test_create_enabled(self) -> None:
        """Test creating enabled fan-out."""
        fan_out = create_fan_out(enabled=True)
        assert isinstance(fan_out, FanOutTransform)

    def test_create_with_path(self) -> None:
        """Test creating with array path."""
        fan_out = create_fan_out(array_path="results")
        assert fan_out._array_path == "results"
