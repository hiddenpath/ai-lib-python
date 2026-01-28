"""
Vector operations for embeddings.

Provides similarity calculations and vector manipulation.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_lib_python.embeddings.types import Embedding

# Type alias for vectors
Vector = list[float]


def dot_product(a: Vector, b: Vector) -> float:
    """Calculate dot product of two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Dot product value

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: {len(a)} != {len(b)}")

    return sum(x * y for x, y in zip(a, b, strict=True))


def magnitude(v: Vector) -> float:
    """Calculate the magnitude (L2 norm) of a vector.

    Args:
        v: Input vector

    Returns:
        Magnitude value
    """
    return math.sqrt(sum(x * x for x in v))


def normalize_vector(v: Vector) -> Vector:
    """Normalize a vector to unit length.

    Args:
        v: Input vector

    Returns:
        Normalized vector
    """
    mag = magnitude(v)
    if mag == 0:
        return v
    return [x / mag for x in v]


def cosine_similarity(a: Vector, b: Vector) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity value (-1 to 1)

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: {len(a)} != {len(b)}")

    dot = dot_product(a, b)
    mag_a = magnitude(a)
    mag_b = magnitude(b)

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def euclidean_distance(a: Vector, b: Vector) -> float:
    """Calculate Euclidean distance between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Euclidean distance value

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: {len(a)} != {len(b)}")

    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def manhattan_distance(a: Vector, b: Vector) -> float:
    """Calculate Manhattan (L1) distance between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Manhattan distance value

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: {len(a)} != {len(b)}")

    return sum(abs(x - y) for x, y in zip(a, b, strict=True))


def find_most_similar(
    query: Vector,
    candidates: list[Vector],
    top_k: int = 5,
    metric: str = "cosine",
) -> list[tuple[int, float]]:
    """Find the most similar vectors to a query.

    Args:
        query: Query vector
        candidates: List of candidate vectors
        top_k: Number of results to return
        metric: Similarity metric ("cosine", "euclidean", "dot")

    Returns:
        List of (index, score) tuples, sorted by similarity

    Raises:
        ValueError: If metric is not supported
    """
    if metric == "cosine":
        scores = [(i, cosine_similarity(query, c)) for i, c in enumerate(candidates)]
        # Higher is better for cosine
        scores.sort(key=lambda x: x[1], reverse=True)
    elif metric == "euclidean":
        scores = [(i, euclidean_distance(query, c)) for i, c in enumerate(candidates)]
        # Lower is better for distance
        scores.sort(key=lambda x: x[1])
    elif metric == "dot":
        scores = [(i, dot_product(query, c)) for i, c in enumerate(candidates)]
        # Higher is better for dot product
        scores.sort(key=lambda x: x[1], reverse=True)
    else:
        raise ValueError(f"Unknown metric: {metric}. Use 'cosine', 'euclidean', or 'dot'")

    return scores[:top_k]


def find_most_similar_embeddings(
    query: Embedding,
    candidates: list[Embedding],
    top_k: int = 5,
    metric: str = "cosine",
) -> list[tuple[Embedding, float]]:
    """Find the most similar embeddings to a query.

    Args:
        query: Query embedding
        candidates: List of candidate embeddings
        top_k: Number of results to return
        metric: Similarity metric

    Returns:
        List of (embedding, score) tuples
    """
    candidate_vectors = [e.vector for e in candidates]
    results = find_most_similar(query.vector, candidate_vectors, top_k, metric)
    return [(candidates[i], score) for i, score in results]


def average_vectors(vectors: list[Vector]) -> Vector:
    """Calculate the average of multiple vectors.

    Args:
        vectors: List of vectors

    Returns:
        Average vector

    Raises:
        ValueError: If vectors have different dimensions or list is empty
    """
    if not vectors:
        raise ValueError("Cannot average empty list of vectors")

    dim = len(vectors[0])
    if not all(len(v) == dim for v in vectors):
        raise ValueError("All vectors must have the same dimensions")

    n = len(vectors)
    return [sum(v[i] for v in vectors) / n for i in range(dim)]


def weighted_average_vectors(
    vectors: list[Vector],
    weights: list[float],
) -> Vector:
    """Calculate weighted average of vectors.

    Args:
        vectors: List of vectors
        weights: List of weights (should sum to 1, or will be normalized)

    Returns:
        Weighted average vector

    Raises:
        ValueError: If vectors/weights mismatch or list is empty
    """
    if not vectors:
        raise ValueError("Cannot average empty list of vectors")
    if len(vectors) != len(weights):
        raise ValueError("Number of vectors must match number of weights")

    # Normalize weights
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("Total weight cannot be zero")
    normalized_weights = [w / total_weight for w in weights]

    dim = len(vectors[0])
    if not all(len(v) == dim for v in vectors):
        raise ValueError("All vectors must have the same dimensions")

    return [
        sum(v[i] * w for v, w in zip(vectors, normalized_weights, strict=True))
        for i in range(dim)
    ]
