"""
Model manager for routing and load balancing.

Provides model management, selection, and load balancing capabilities.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_lib_python.routing.strategy import (
    EndpointSelector,
    LoadBalancingStrategy,
    ModelSelectionStrategy,
    ModelSelector,
    create_endpoint_selector,
    create_model_selector,
)
from ai_lib_python.routing.types import (
    HealthCheckConfig,
    ModelCapabilities,
    ModelEndpoint,
    ModelInfo,
    PerformanceMetrics,
    PricingInfo,
    QualityTier,
    SpeedTier,
)


class ModelManager:
    """Manager for model registration and selection.

    Provides methods for registering models, selecting models based on
    various strategies, and filtering by capabilities.

    Example:
        >>> manager = ModelManager(provider="openai")
        >>> manager.add_model(ModelInfo(
        ...     name="gpt-4o",
        ...     capabilities=ModelCapabilities(multimodal=True),
        ...     pricing=PricingInfo(2.5, 10.0),
        ... ))
        >>> model = manager.select_model()
        >>> recommended = manager.recommend_for("multimodal")
    """

    def __init__(
        self,
        provider: str = "",
        strategy: ModelSelectionStrategy = ModelSelectionStrategy.ROUND_ROBIN,
    ) -> None:
        """Initialize model manager.

        Args:
            provider: Provider identifier
            strategy: Model selection strategy
        """
        self.provider = provider
        self._models: dict[str, ModelInfo] = {}
        self._strategy = strategy
        self._selector: ModelSelector = create_model_selector(strategy)

    def add_model(self, model: ModelInfo) -> ModelManager:
        """Add a model to the manager.

        Args:
            model: Model information

        Returns:
            Self for chaining
        """
        if not model.provider and self.provider:
            model.provider = self.provider
        self._models[model.name] = model
        return self

    def remove_model(self, model_name: str) -> ModelInfo | None:
        """Remove a model from the manager.

        Args:
            model_name: Model name

        Returns:
            Removed model or None
        """
        return self._models.pop(model_name, None)

    def get_model(self, model_name: str) -> ModelInfo | None:
        """Get a model by name.

        Args:
            model_name: Model name

        Returns:
            Model info or None
        """
        return self._models.get(model_name)

    def list_models(self) -> list[ModelInfo]:
        """List all registered models.

        Returns:
            List of model info
        """
        return list(self._models.values())

    def with_strategy(self, strategy: ModelSelectionStrategy) -> ModelManager:
        """Set the selection strategy.

        Args:
            strategy: Selection strategy

        Returns:
            Self for chaining
        """
        self._strategy = strategy
        self._selector = create_model_selector(strategy)
        return self

    def select_model(self) -> ModelInfo | None:
        """Select a model using the current strategy.

        Returns:
            Selected model or None
        """
        models = list(self._models.values())
        return self._selector.select(models)

    def recommend_for(self, use_case: str) -> ModelInfo | None:
        """Recommend a model for a specific use case.

        Args:
            use_case: Use case or capability name

        Returns:
            Recommended model or None
        """
        supported = [m for m in self._models.values() if m.supports(use_case)]
        if not supported:
            return None
        return self._selector.select(supported)

    def filter_by_capability(self, capability: str) -> list[ModelInfo]:
        """Filter models by capability.

        Args:
            capability: Capability name

        Returns:
            List of models with the capability
        """
        return [m for m in self._models.values() if m.supports(capability)]

    def filter_by_cost(self, max_cost_per_1k: float) -> list[ModelInfo]:
        """Filter models by maximum cost.

        Args:
            max_cost_per_1k: Maximum cost per 1000 tokens

        Returns:
            List of affordable models
        """
        return [
            m
            for m in self._models.values()
            if m.pricing and (m.pricing.input_cost_per_1k <= max_cost_per_1k)
        ]

    def filter_by_context_window(self, min_tokens: int) -> list[ModelInfo]:
        """Filter models by minimum context window.

        Args:
            min_tokens: Minimum context window size

        Returns:
            List of models meeting the requirement
        """
        return [
            m
            for m in self._models.values()
            if m.capabilities.context_window
            and m.capabilities.context_window >= min_tokens
        ]

    def load_from_config(self, config_path: str | Path) -> ModelManager:
        """Load models from a JSON configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            Self for chaining

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config is invalid JSON
        """
        path = Path(config_path)
        content = path.read_text()
        models = json.loads(content)

        if isinstance(models, list):
            for model_data in models:
                self.add_model(ModelInfo.from_dict(model_data))
        elif isinstance(models, dict) and "models" in models:
            for model_data in models["models"]:
                self.add_model(ModelInfo.from_dict(model_data))

        return self

    def save_to_config(self, config_path: str | Path) -> None:
        """Save models to a JSON configuration file.

        Args:
            config_path: Path to configuration file
        """
        path = Path(config_path)
        models = [m.to_dict() for m in self._models.values()]
        content = json.dumps(models, indent=2)
        path.write_text(content)

    @property
    def strategy(self) -> ModelSelectionStrategy:
        """Get current selection strategy."""
        return self._strategy

    def __len__(self) -> int:
        """Get number of registered models."""
        return len(self._models)

    def __contains__(self, model_name: str) -> bool:
        """Check if model is registered."""
        return model_name in self._models


class ModelArray:
    """Model array for load balancing across multiple endpoints.

    Supports A/B testing and failover scenarios.

    Example:
        >>> array = ModelArray("gpt-4-cluster")
        >>> array.add_endpoint(ModelEndpoint("primary", "gpt-4o", "https://api1.example.com"))
        >>> array.add_endpoint(ModelEndpoint("secondary", "gpt-4o", "https://api2.example.com"))
        >>> endpoint = array.select_endpoint()
    """

    def __init__(
        self,
        name: str,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check: HealthCheckConfig | None = None,
    ) -> None:
        """Initialize model array.

        Args:
            name: Array name/identifier
            strategy: Load balancing strategy
            health_check: Health check configuration
        """
        self.name = name
        self._endpoints: list[ModelEndpoint] = []
        self._strategy = strategy
        self._selector: EndpointSelector = create_endpoint_selector(strategy)
        self.health_check = health_check or HealthCheckConfig()

    def add_endpoint(self, endpoint: ModelEndpoint) -> ModelArray:
        """Add an endpoint to the array.

        Args:
            endpoint: Endpoint to add

        Returns:
            Self for chaining
        """
        self._endpoints.append(endpoint)
        return self

    def remove_endpoint(self, endpoint_name: str) -> ModelEndpoint | None:
        """Remove an endpoint by name.

        Args:
            endpoint_name: Endpoint name

        Returns:
            Removed endpoint or None
        """
        for i, endpoint in enumerate(self._endpoints):
            if endpoint.name == endpoint_name:
                return self._endpoints.pop(i)
        return None

    def get_endpoint(self, endpoint_name: str) -> ModelEndpoint | None:
        """Get an endpoint by name.

        Args:
            endpoint_name: Endpoint name

        Returns:
            Endpoint or None
        """
        for endpoint in self._endpoints:
            if endpoint.name == endpoint_name:
                return endpoint
        return None

    def with_strategy(self, strategy: LoadBalancingStrategy) -> ModelArray:
        """Set the load balancing strategy.

        Args:
            strategy: Load balancing strategy

        Returns:
            Self for chaining
        """
        self._strategy = strategy
        self._selector = create_endpoint_selector(strategy)
        return self

    def select_endpoint(self) -> ModelEndpoint | None:
        """Select an endpoint using the current strategy.

        Returns:
            Selected endpoint or None
        """
        return self._selector.select(self._endpoints)

    def mark_healthy(self, endpoint_name: str) -> bool:
        """Mark an endpoint as healthy.

        Args:
            endpoint_name: Endpoint name

        Returns:
            True if endpoint was found
        """
        endpoint = self.get_endpoint(endpoint_name)
        if endpoint:
            endpoint.healthy = True
            return True
        return False

    def mark_unhealthy(self, endpoint_name: str) -> bool:
        """Mark an endpoint as unhealthy.

        Args:
            endpoint_name: Endpoint name

        Returns:
            True if endpoint was found
        """
        endpoint = self.get_endpoint(endpoint_name)
        if endpoint:
            endpoint.healthy = False
            return True
        return False

    def is_healthy(self) -> bool:
        """Check if any endpoint is healthy.

        Returns:
            True if at least one endpoint is healthy
        """
        return any(e.healthy for e in self._endpoints)

    def healthy_endpoints(self) -> list[ModelEndpoint]:
        """Get all healthy endpoints.

        Returns:
            List of healthy endpoints
        """
        return [e for e in self._endpoints if e.healthy]

    @property
    def endpoints(self) -> list[ModelEndpoint]:
        """Get all endpoints."""
        return list(self._endpoints)

    @property
    def strategy(self) -> LoadBalancingStrategy:
        """Get current strategy."""
        return self._strategy

    def __len__(self) -> int:
        """Get number of endpoints."""
        return len(self._endpoints)


# Pre-configured model catalogs


def create_openai_models() -> ModelManager:
    """Create a pre-configured OpenAI model manager.

    Returns:
        ModelManager with OpenAI models
    """
    manager = ModelManager(provider="openai")

    # GPT-4o
    manager.add_model(
        ModelInfo(
            name="gpt-4o",
            display_name="GPT-4o",
            description="Most capable GPT-4 model for complex tasks",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=True,
                function_calling=True,
                context_window=128000,
            ),
            pricing=PricingInfo(2.5, 10.0),
            performance=PerformanceMetrics(
                speed=SpeedTier.BALANCED,
                quality=QualityTier.EXCELLENT,
            ),
        )
    )

    # GPT-4o-mini
    manager.add_model(
        ModelInfo(
            name="gpt-4o-mini",
            display_name="GPT-4o Mini",
            description="Smaller, faster GPT-4o variant",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=True,
                function_calling=True,
                context_window=128000,
            ),
            pricing=PricingInfo(0.15, 0.60),
            performance=PerformanceMetrics(
                speed=SpeedTier.FAST,
                quality=QualityTier.GOOD,
            ),
        )
    )

    # GPT-4-turbo
    manager.add_model(
        ModelInfo(
            name="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            description="GPT-4 Turbo with vision capabilities",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=True,
                function_calling=True,
                context_window=128000,
            ),
            pricing=PricingInfo(10.0, 30.0),
            performance=PerformanceMetrics(
                speed=SpeedTier.BALANCED,
                quality=QualityTier.EXCELLENT,
            ),
        )
    )

    # o1-preview
    manager.add_model(
        ModelInfo(
            name="o1-preview",
            display_name="o1 Preview",
            description="Reasoning model for complex problems",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=False,
                function_calling=False,
                context_window=128000,
            ),
            pricing=PricingInfo(15.0, 60.0),
            performance=PerformanceMetrics(
                speed=SpeedTier.SLOW,
                quality=QualityTier.EXCELLENT,
            ),
        )
    )

    return manager


def create_anthropic_models() -> ModelManager:
    """Create a pre-configured Anthropic model manager.

    Returns:
        ModelManager with Anthropic models
    """
    manager = ModelManager(provider="anthropic")

    # Claude 3.5 Sonnet
    manager.add_model(
        ModelInfo(
            name="claude-3-5-sonnet-20241022",
            display_name="Claude 3.5 Sonnet",
            description="Most intelligent Claude model",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=True,
                tool_use=True,
                context_window=200000,
            ),
            pricing=PricingInfo(3.0, 15.0),
            performance=PerformanceMetrics(
                speed=SpeedTier.BALANCED,
                quality=QualityTier.EXCELLENT,
            ),
        )
    )

    # Claude 3.5 Haiku
    manager.add_model(
        ModelInfo(
            name="claude-3-5-haiku-20241022",
            display_name="Claude 3.5 Haiku",
            description="Fast and efficient Claude model",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=True,
                tool_use=True,
                context_window=200000,
            ),
            pricing=PricingInfo(0.80, 4.0),
            performance=PerformanceMetrics(
                speed=SpeedTier.FAST,
                quality=QualityTier.GOOD,
            ),
        )
    )

    # Claude 3 Opus
    manager.add_model(
        ModelInfo(
            name="claude-3-opus-20240229",
            display_name="Claude 3 Opus",
            description="Most powerful Claude 3 model",
            capabilities=ModelCapabilities(
                chat=True,
                code_generation=True,
                multimodal=True,
                tool_use=True,
                context_window=200000,
            ),
            pricing=PricingInfo(15.0, 75.0),
            performance=PerformanceMetrics(
                speed=SpeedTier.SLOW,
                quality=QualityTier.EXCELLENT,
            ),
        )
    )

    return manager


# Global model registry
_global_managers: dict[str, ModelManager] = {}


def get_model_manager(provider: str) -> ModelManager:
    """Get or create a model manager for a provider.

    Args:
        provider: Provider identifier

    Returns:
        ModelManager instance
    """
    if provider not in _global_managers:
        if provider == "openai":
            _global_managers[provider] = create_openai_models()
        elif provider == "anthropic":
            _global_managers[provider] = create_anthropic_models()
        else:
            _global_managers[provider] = ModelManager(provider=provider)
    return _global_managers[provider]


def register_model_manager(provider: str, manager: ModelManager) -> None:
    """Register a custom model manager.

    Args:
        provider: Provider identifier
        manager: ModelManager instance
    """
    _global_managers[provider] = manager
