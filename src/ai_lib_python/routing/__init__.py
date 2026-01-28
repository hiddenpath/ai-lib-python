"""
Model routing and load balancing.

Provides model management, selection strategies, and load balancing
for multi-model deployments.

Example:
    >>> from ai_lib_python.routing import (
    ...     ModelManager,
    ...     ModelInfo,
    ...     ModelCapabilities,
    ...     ModelSelectionStrategy,
    ... )
    >>>
    >>> # Create and configure a model manager
    >>> manager = ModelManager(provider="openai")
    >>> manager.with_strategy(ModelSelectionStrategy.COST_BASED)
    >>>
    >>> # Add models
    >>> manager.add_model(ModelInfo(
    ...     name="gpt-4o",
    ...     capabilities=ModelCapabilities(multimodal=True),
    ... ))
    >>>
    >>> # Select a model
    >>> model = manager.select_model()
    >>> print(f"Selected: {model.name}")

Example with load balancing:
    >>> from ai_lib_python.routing import (
    ...     ModelArray,
    ...     ModelEndpoint,
    ...     LoadBalancingStrategy,
    ... )
    >>>
    >>> # Create a model array for load balancing
    >>> array = ModelArray("gpt-4-cluster")
    >>> array.with_strategy(LoadBalancingStrategy.WEIGHTED)
    >>>
    >>> # Add endpoints
    >>> array.add_endpoint(ModelEndpoint("primary", "gpt-4o", "https://api1.example.com", weight=2.0))
    >>> array.add_endpoint(ModelEndpoint("secondary", "gpt-4o", "https://api2.example.com", weight=1.0))
    >>>
    >>> # Select an endpoint
    >>> endpoint = array.select_endpoint()
"""

from ai_lib_python.routing.manager import (
    ModelArray,
    ModelManager,
    create_anthropic_models,
    create_openai_models,
    get_model_manager,
    register_model_manager,
)
from ai_lib_python.routing.strategy import (
    CostBasedSelector,
    EndpointSelector,
    HealthBasedEndpointSelector,
    LeastConnectionsEndpointSelector,
    LeastConnectionsSelector,
    LoadBalancingStrategy,
    ModelSelectionStrategy,
    ModelSelector,
    PerformanceBasedSelector,
    QualityBasedSelector,
    RandomSelector,
    RoundRobinEndpointSelector,
    RoundRobinSelector,
    WeightedEndpointSelector,
    WeightedSelector,
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

__all__ = [
    "CostBasedSelector",
    "EndpointSelector",
    "HealthBasedEndpointSelector",
    "HealthCheckConfig",
    "LeastConnectionsEndpointSelector",
    "LeastConnectionsSelector",
    "LoadBalancingStrategy",
    "ModelArray",
    "ModelCapabilities",
    "ModelEndpoint",
    "ModelInfo",
    "ModelManager",
    "ModelSelectionStrategy",
    "ModelSelector",
    "PerformanceBasedSelector",
    "PerformanceMetrics",
    "PricingInfo",
    "QualityBasedSelector",
    "QualityTier",
    "RandomSelector",
    "RoundRobinEndpointSelector",
    "RoundRobinSelector",
    "SpeedTier",
    "WeightedEndpointSelector",
    "WeightedSelector",
    "create_anthropic_models",
    "create_endpoint_selector",
    "create_model_selector",
    "create_openai_models",
    "get_model_manager",
    "register_model_manager",
]
