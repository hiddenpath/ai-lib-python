"""Tests for embeddings module."""

import pytest

from ai_lib_python.embeddings import (
    Embedding,
    EmbeddingModel,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingUsage,
    cosine_similarity,
    dot_product,
    euclidean_distance,
    find_most_similar,
    normalize_vector,
)
from ai_lib_python.embeddings.vectors import (
    average_vectors,
    magnitude,
    manhattan_distance,
    weighted_average_vectors,
)


class TestEmbeddingModel:
    """Tests for EmbeddingModel enum."""

    def test_dimensions(self) -> None:
        """Test default dimensions."""
        assert EmbeddingModel.TEXT_EMBEDDING_3_SMALL.dimensions == 1536
        assert EmbeddingModel.TEXT_EMBEDDING_3_LARGE.dimensions == 3072
        assert EmbeddingModel.EMBED_ENGLISH_LIGHT_V3.dimensions == 384

    def test_max_tokens(self) -> None:
        """Test max tokens."""
        assert EmbeddingModel.TEXT_EMBEDDING_3_SMALL.max_tokens == 8191
        assert EmbeddingModel.EMBED_ENGLISH_V3.max_tokens == 512


class TestEmbeddingUsage:
    """Tests for EmbeddingUsage."""

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        usage = EmbeddingUsage(prompt_tokens=100, total_tokens=100)
        d = usage.to_dict()
        assert d["prompt_tokens"] == 100
        assert d["total_tokens"] == 100


class TestEmbedding:
    """Tests for Embedding class."""

    def test_basic_embedding(self) -> None:
        """Test basic embedding creation."""
        emb = Embedding(index=0, vector=[0.1, 0.2, 0.3])
        assert emb.index == 0
        assert emb.dimensions == 3
        assert emb.vector == [0.1, 0.2, 0.3]

    def test_from_openai_format(self) -> None:
        """Test creating from OpenAI format."""
        data = {
            "index": 1,
            "embedding": [0.5, 0.6, 0.7],
            "object": "embedding",
        }
        emb = Embedding.from_openai_format(data)
        assert emb.index == 1
        assert emb.vector == [0.5, 0.6, 0.7]

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        emb = Embedding(index=0, vector=[0.1, 0.2])
        d = emb.to_dict()
        assert d["index"] == 0
        assert d["embedding"] == [0.1, 0.2]
        assert d["object"] == "embedding"


class TestEmbeddingRequest:
    """Tests for EmbeddingRequest."""

    def test_single_input(self) -> None:
        """Test single input request."""
        req = EmbeddingRequest(input="Hello", model="text-embedding-3-small")
        assert not req.is_batch
        assert req.batch_size == 1

    def test_batch_input(self) -> None:
        """Test batch input request."""
        req = EmbeddingRequest(
            input=["Hello", "World"],
            model="text-embedding-3-small",
        )
        assert req.is_batch
        assert req.batch_size == 2

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        req = EmbeddingRequest(
            input="Hello",
            model="text-embedding-3-small",
            dimensions=512,
        )
        d = req.to_dict()
        assert d["input"] == "Hello"
        assert d["model"] == "text-embedding-3-small"
        assert d["dimensions"] == 512


class TestEmbeddingResponse:
    """Tests for EmbeddingResponse."""

    def test_first_property(self) -> None:
        """Test first embedding access."""
        resp = EmbeddingResponse(
            embeddings=[
                Embedding(index=0, vector=[0.1, 0.2]),
                Embedding(index=1, vector=[0.3, 0.4]),
            ],
            model="test",
        )
        assert resp.first is not None
        assert resp.first.index == 0

    def test_vectors_property(self) -> None:
        """Test vectors extraction."""
        resp = EmbeddingResponse(
            embeddings=[
                Embedding(index=0, vector=[0.1, 0.2]),
                Embedding(index=1, vector=[0.3, 0.4]),
            ],
        )
        vectors = resp.vectors
        assert vectors == [[0.1, 0.2], [0.3, 0.4]]

    def test_from_openai_format(self) -> None:
        """Test creating from OpenAI format."""
        data = {
            "object": "list",
            "data": [
                {"index": 0, "embedding": [0.1, 0.2], "object": "embedding"},
            ],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
        resp = EmbeddingResponse.from_openai_format(data)
        assert len(resp.embeddings) == 1
        assert resp.model == "text-embedding-3-small"
        assert resp.usage.prompt_tokens == 5


class TestVectorOperations:
    """Tests for vector operations."""

    def test_dot_product(self) -> None:
        """Test dot product calculation."""
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        result = dot_product(a, b)
        assert result == 32.0  # 1*4 + 2*5 + 3*6

    def test_dot_product_dimension_mismatch(self) -> None:
        """Test dot product with mismatched dimensions."""
        with pytest.raises(ValueError, match="dimensions must match"):
            dot_product([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_magnitude(self) -> None:
        """Test magnitude calculation."""
        v = [3.0, 4.0]
        assert magnitude(v) == 5.0

    def test_normalize_vector(self) -> None:
        """Test vector normalization."""
        v = [3.0, 4.0]
        normalized = normalize_vector(v)
        assert abs(normalized[0] - 0.6) < 0.001
        assert abs(normalized[1] - 0.8) < 0.001

    def test_normalize_zero_vector(self) -> None:
        """Test normalizing zero vector."""
        v = [0.0, 0.0]
        normalized = normalize_vector(v)
        assert normalized == [0.0, 0.0]

    def test_cosine_similarity(self) -> None:
        """Test cosine similarity."""
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 1.0

        c = [-1.0, 0.0]
        assert cosine_similarity(a, c) == -1.0

    def test_euclidean_distance(self) -> None:
        """Test Euclidean distance."""
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        assert euclidean_distance(a, b) == 5.0

    def test_manhattan_distance(self) -> None:
        """Test Manhattan distance."""
        a = [0.0, 0.0]
        b = [3.0, 4.0]
        assert manhattan_distance(a, b) == 7.0

    def test_find_most_similar_cosine(self) -> None:
        """Test finding most similar vectors."""
        query = [1.0, 0.0, 0.0]
        candidates = [
            [1.0, 0.0, 0.0],  # Same direction
            [0.0, 1.0, 0.0],  # Orthogonal
            [-1.0, 0.0, 0.0],  # Opposite
        ]
        results = find_most_similar(query, candidates, top_k=2)
        assert results[0][0] == 0  # Index of most similar
        assert results[0][1] == 1.0  # Perfect similarity

    def test_find_most_similar_euclidean(self) -> None:
        """Test finding most similar with Euclidean."""
        query = [0.0, 0.0]
        candidates = [[1.0, 0.0], [5.0, 0.0], [2.0, 0.0]]
        results = find_most_similar(query, candidates, top_k=2, metric="euclidean")
        assert results[0][0] == 0  # Closest point
        assert results[1][0] == 2  # Second closest

    def test_find_most_similar_invalid_metric(self) -> None:
        """Test invalid metric."""
        with pytest.raises(ValueError, match="Unknown metric"):
            find_most_similar([1.0], [[1.0]], metric="invalid")

    def test_average_vectors(self) -> None:
        """Test vector averaging."""
        vectors = [[1.0, 2.0], [3.0, 4.0]]
        avg = average_vectors(vectors)
        assert avg == [2.0, 3.0]

    def test_average_vectors_empty(self) -> None:
        """Test averaging empty list."""
        with pytest.raises(ValueError, match="empty list"):
            average_vectors([])

    def test_weighted_average_vectors(self) -> None:
        """Test weighted average."""
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        weights = [3.0, 1.0]
        avg = weighted_average_vectors(vectors, weights)
        assert abs(avg[0] - 0.75) < 0.001
        assert abs(avg[1] - 0.25) < 0.001
