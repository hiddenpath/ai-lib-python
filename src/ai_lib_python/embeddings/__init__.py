"""
Embedding module for ai-lib-python.

Provides embedding generation and vector operations.
"""

from ai_lib_python.embeddings.client import EmbeddingClient, EmbeddingClientBuilder
from ai_lib_python.embeddings.types import (
    Embedding,
    EmbeddingModel,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingUsage,
)
from ai_lib_python.embeddings.vectors import (
    cosine_similarity,
    dot_product,
    euclidean_distance,
    find_most_similar,
    normalize_vector,
)

__all__ = [
    "Embedding",
    "EmbeddingClient",
    "EmbeddingClientBuilder",
    "EmbeddingModel",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "EmbeddingUsage",
    "cosine_similarity",
    "dot_product",
    "euclidean_distance",
    "find_most_similar",
    "normalize_vector",
]
