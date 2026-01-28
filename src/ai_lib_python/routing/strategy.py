"""
Model selection and load balancing strategies.

Provides various strategies for selecting models and distributing load.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_lib_python.routing.types import ModelEndpoint, ModelInfo


class ModelSelectionStrategy(str, Enum):
    """Model selection strategy types."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    PERFORMANCE_BASED = "performance_based"
    COST_BASED = "cost_based"
    RANDOM = "random"
    QUALITY_BASED = "quality_based"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy types."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


class ModelSelector(ABC):
    """Abstract base class for model selection."""

    @abstractmethod
    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select a model from the list.

        Args:
            models: Available models

        Returns:
            Selected model or None
        """
        raise NotImplementedError


class RoundRobinSelector(ModelSelector):
    """Round-robin model selector.

    Cycles through models in order.
    """

    def __init__(self) -> None:
        """Initialize selector."""
        self._index = 0

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select next model in rotation."""
        if not models:
            return None
        model = models[self._index % len(models)]
        self._index += 1
        return model


class WeightedSelector(ModelSelector):
    """Weighted model selector.

    Selects models based on combined speed and quality scores.
    """

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select model with highest combined score."""
        if not models:
            return None

        def score(model: ModelInfo) -> int:
            from ai_lib_python.routing.types import QualityTier, SpeedTier

            speed_score = {
                SpeedTier.FAST: 3,
                SpeedTier.BALANCED: 2,
                SpeedTier.SLOW: 1,
            }.get(model.performance.speed, 2)

            quality_score = {
                QualityTier.EXCELLENT: 3,
                QualityTier.GOOD: 2,
                QualityTier.BASIC: 1,
            }.get(model.performance.quality, 2)

            return speed_score + quality_score

        return max(models, key=score)


class LeastConnectionsSelector(ModelSelector):
    """Least connections model selector.

    Selects the model with fewest active connections.
    Note: This is a placeholder - actual connection tracking
    would need integration with the transport layer.
    """

    def __init__(self) -> None:
        """Initialize selector."""
        self._connections: dict[str, int] = {}

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select model with fewest connections."""
        if not models:
            return None

        # Find model with minimum connections
        min_connections = float("inf")
        selected = models[0]

        for model in models:
            count = self._connections.get(model.name, 0)
            if count < min_connections:
                min_connections = count
                selected = model

        return selected

    def increment(self, model_name: str) -> None:
        """Increment connection count for a model."""
        self._connections[model_name] = self._connections.get(model_name, 0) + 1

    def decrement(self, model_name: str) -> None:
        """Decrement connection count for a model."""
        count = self._connections.get(model_name, 0)
        self._connections[model_name] = max(0, count - 1)


class PerformanceBasedSelector(ModelSelector):
    """Performance-based model selector.

    Selects the fastest model.
    """

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select fastest model."""
        if not models:
            return None

        from ai_lib_python.routing.types import SpeedTier

        def speed_score(model: ModelInfo) -> int:
            return {
                SpeedTier.FAST: 3,
                SpeedTier.BALANCED: 2,
                SpeedTier.SLOW: 1,
            }.get(model.performance.speed, 2)

        return max(models, key=speed_score)


class CostBasedSelector(ModelSelector):
    """Cost-based model selector.

    Selects the cheapest model.
    """

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select cheapest model."""
        if not models:
            return None

        def cost(model: ModelInfo) -> float:
            if model.pricing is None:
                return float("inf")
            return model.pricing.input_cost_per_1k + model.pricing.output_cost_per_1k

        return min(models, key=cost)


class QualityBasedSelector(ModelSelector):
    """Quality-based model selector.

    Selects the highest quality model.
    """

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select highest quality model."""
        if not models:
            return None

        from ai_lib_python.routing.types import QualityTier

        def quality_score(model: ModelInfo) -> int:
            return {
                QualityTier.EXCELLENT: 3,
                QualityTier.GOOD: 2,
                QualityTier.BASIC: 1,
            }.get(model.performance.quality, 2)

        return max(models, key=quality_score)


class RandomSelector(ModelSelector):
    """Random model selector."""

    def select(self, models: list[ModelInfo]) -> ModelInfo | None:
        """Select random model."""
        if not models:
            return None
        return random.choice(models)


class EndpointSelector(ABC):
    """Abstract base class for endpoint selection."""

    @abstractmethod
    def select(self, endpoints: list[ModelEndpoint]) -> ModelEndpoint | None:
        """Select an endpoint from the list.

        Args:
            endpoints: Available endpoints

        Returns:
            Selected endpoint or None
        """
        raise NotImplementedError


class RoundRobinEndpointSelector(EndpointSelector):
    """Round-robin endpoint selector."""

    def __init__(self) -> None:
        """Initialize selector."""
        self._index = 0

    def select(self, endpoints: list[ModelEndpoint]) -> ModelEndpoint | None:
        """Select next healthy endpoint in rotation."""
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None
        endpoint = healthy[self._index % len(healthy)]
        self._index += 1
        return endpoint


class WeightedEndpointSelector(EndpointSelector):
    """Weighted endpoint selector.

    Selects endpoints based on their weights.
    """

    def select(self, endpoints: list[ModelEndpoint]) -> ModelEndpoint | None:
        """Select endpoint based on weight distribution."""
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None

        total_weight = sum(e.weight for e in healthy)
        if total_weight <= 0:
            return healthy[0]

        # Weighted random selection
        r = random.uniform(0, total_weight)
        cumulative = 0.0
        for endpoint in healthy:
            cumulative += endpoint.weight
            if r <= cumulative:
                return endpoint

        return healthy[-1]


class LeastConnectionsEndpointSelector(EndpointSelector):
    """Least connections endpoint selector."""

    def select(self, endpoints: list[ModelEndpoint]) -> ModelEndpoint | None:
        """Select healthy endpoint with fewest connections."""
        healthy = [e for e in endpoints if e.healthy]
        if not healthy:
            return None
        return min(healthy, key=lambda e: e.connection_count)


class HealthBasedEndpointSelector(EndpointSelector):
    """Health-based endpoint selector.

    Prioritizes healthy endpoints.
    """

    def select(self, endpoints: list[ModelEndpoint]) -> ModelEndpoint | None:
        """Select first healthy endpoint."""
        for endpoint in endpoints:
            if endpoint.healthy:
                return endpoint
        return None


def create_model_selector(strategy: ModelSelectionStrategy) -> ModelSelector:
    """Create a model selector for the given strategy.

    Args:
        strategy: Selection strategy

    Returns:
        ModelSelector instance
    """
    selectors: dict[ModelSelectionStrategy, type[ModelSelector]] = {
        ModelSelectionStrategy.ROUND_ROBIN: RoundRobinSelector,
        ModelSelectionStrategy.WEIGHTED: WeightedSelector,
        ModelSelectionStrategy.LEAST_CONNECTIONS: LeastConnectionsSelector,
        ModelSelectionStrategy.PERFORMANCE_BASED: PerformanceBasedSelector,
        ModelSelectionStrategy.COST_BASED: CostBasedSelector,
        ModelSelectionStrategy.QUALITY_BASED: QualityBasedSelector,
        ModelSelectionStrategy.RANDOM: RandomSelector,
    }
    return selectors.get(strategy, RoundRobinSelector)()


def create_endpoint_selector(strategy: LoadBalancingStrategy) -> EndpointSelector:
    """Create an endpoint selector for the given strategy.

    Args:
        strategy: Load balancing strategy

    Returns:
        EndpointSelector instance
    """
    selectors: dict[LoadBalancingStrategy, type[EndpointSelector]] = {
        LoadBalancingStrategy.ROUND_ROBIN: RoundRobinEndpointSelector,
        LoadBalancingStrategy.WEIGHTED: WeightedEndpointSelector,
        LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsEndpointSelector,
        LoadBalancingStrategy.HEALTH_BASED: HealthBasedEndpointSelector,
        LoadBalancingStrategy.RANDOM: lambda: WeightedEndpointSelector(),  # type: ignore
    }
    selector_class = selectors.get(strategy, RoundRobinEndpointSelector)
    if callable(selector_class):
        return selector_class()
    return selector_class()
