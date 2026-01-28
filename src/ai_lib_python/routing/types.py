"""
Model routing types and data structures.

Provides types for model information, capabilities, pricing, and performance metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpeedTier(str, Enum):
    """Speed tier classification for models."""

    FAST = "fast"
    BALANCED = "balanced"
    SLOW = "slow"


class QualityTier(str, Enum):
    """Quality tier classification for models."""

    BASIC = "basic"
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass
class ModelCapabilities:
    """Model capabilities definition.

    Attributes:
        chat: Supports chat completion
        code_generation: Optimized for code generation
        multimodal: Supports multiple modalities (text, image, audio)
        function_calling: Supports function/tool calling
        tool_use: Supports tool use (Anthropic style)
        multilingual: Supports multiple languages
        context_window: Maximum context window size in tokens
        embedding: Supports embedding generation
        streaming: Supports streaming responses
    """

    chat: bool = True
    code_generation: bool = False
    multimodal: bool = False
    function_calling: bool = False
    tool_use: bool = False
    multilingual: bool = False
    context_window: int | None = None
    embedding: bool = False
    streaming: bool = True

    def supports(self, capability: str) -> bool:
        """Check if a capability is supported.

        Args:
            capability: Capability name

        Returns:
            True if supported
        """
        capability_map = {
            "chat": self.chat,
            "code_generation": self.code_generation,
            "code": self.code_generation,
            "multimodal": self.multimodal,
            "vision": self.multimodal,
            "function_calling": self.function_calling,
            "functions": self.function_calling,
            "tool_use": self.tool_use,
            "tools": self.tool_use or self.function_calling,
            "multilingual": self.multilingual,
            "embedding": self.embedding,
            "embeddings": self.embedding,
            "streaming": self.streaming,
            "stream": self.streaming,
        }
        return capability_map.get(capability.lower(), False)

    def with_chat(self) -> ModelCapabilities:
        """Enable chat capability."""
        self.chat = True
        return self

    def with_code_generation(self) -> ModelCapabilities:
        """Enable code generation capability."""
        self.code_generation = True
        return self

    def with_multimodal(self) -> ModelCapabilities:
        """Enable multimodal capability."""
        self.multimodal = True
        return self

    def with_function_calling(self) -> ModelCapabilities:
        """Enable function calling capability."""
        self.function_calling = True
        return self

    def with_tool_use(self) -> ModelCapabilities:
        """Enable tool use capability."""
        self.tool_use = True
        return self

    def with_context_window(self, size: int) -> ModelCapabilities:
        """Set context window size."""
        self.context_window = size
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chat": self.chat,
            "code_generation": self.code_generation,
            "multimodal": self.multimodal,
            "function_calling": self.function_calling,
            "tool_use": self.tool_use,
            "multilingual": self.multilingual,
            "context_window": self.context_window,
            "embedding": self.embedding,
            "streaming": self.streaming,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelCapabilities:
        """Create from dictionary."""
        return cls(
            chat=data.get("chat", True),
            code_generation=data.get("code_generation", False),
            multimodal=data.get("multimodal", False),
            function_calling=data.get("function_calling", False),
            tool_use=data.get("tool_use", False),
            multilingual=data.get("multilingual", False),
            context_window=data.get("context_window"),
            embedding=data.get("embedding", False),
            streaming=data.get("streaming", True),
        )


@dataclass
class PricingInfo:
    """Pricing information for a model.

    Attributes:
        input_cost_per_1k: Cost per 1000 input tokens
        output_cost_per_1k: Cost per 1000 output tokens
        currency: Currency code (default: USD)
    """

    input_cost_per_1k: float
    output_cost_per_1k: float
    currency: str = "USD"

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for given token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost
        """
        input_cost = (input_tokens / 1000.0) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000.0) * self.output_cost_per_1k
        return input_cost + output_cost

    def with_currency(self, currency: str) -> PricingInfo:
        """Set currency."""
        self.currency = currency
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "input_cost_per_1k": self.input_cost_per_1k,
            "output_cost_per_1k": self.output_cost_per_1k,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PricingInfo:
        """Create from dictionary."""
        return cls(
            input_cost_per_1k=data["input_cost_per_1k"],
            output_cost_per_1k=data["output_cost_per_1k"],
            currency=data.get("currency", "USD"),
        )


@dataclass
class PerformanceMetrics:
    """Performance metrics for a model.

    Attributes:
        speed: Speed tier classification
        quality: Quality tier classification
        avg_response_time_ms: Average response time in milliseconds
        throughput_tps: Throughput in tokens per second
    """

    speed: SpeedTier = SpeedTier.BALANCED
    quality: QualityTier = QualityTier.GOOD
    avg_response_time_ms: float | None = None
    throughput_tps: float | None = None

    def with_speed(self, speed: SpeedTier) -> PerformanceMetrics:
        """Set speed tier."""
        self.speed = speed
        return self

    def with_quality(self, quality: QualityTier) -> PerformanceMetrics:
        """Set quality tier."""
        self.quality = quality
        return self

    def with_avg_response_time(self, time_ms: float) -> PerformanceMetrics:
        """Set average response time."""
        self.avg_response_time_ms = time_ms
        return self

    def with_throughput(self, tps: float) -> PerformanceMetrics:
        """Set throughput."""
        self.throughput_tps = tps
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "speed": self.speed.value,
            "quality": self.quality.value,
            "avg_response_time_ms": self.avg_response_time_ms,
            "throughput_tps": self.throughput_tps,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerformanceMetrics:
        """Create from dictionary."""
        return cls(
            speed=SpeedTier(data.get("speed", "balanced")),
            quality=QualityTier(data.get("quality", "good")),
            avg_response_time_ms=data.get("avg_response_time_ms"),
            throughput_tps=data.get("throughput_tps"),
        )


@dataclass
class ModelInfo:
    """Complete model information.

    Attributes:
        name: Model identifier (e.g., "gpt-4o")
        display_name: Human-readable name
        description: Model description
        provider: Provider identifier (e.g., "openai")
        capabilities: Model capabilities
        pricing: Pricing information
        performance: Performance metrics
        metadata: Additional metadata
    """

    name: str
    display_name: str = ""
    description: str = ""
    provider: str = ""
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    pricing: PricingInfo | None = None
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.display_name:
            self.display_name = self.name

    @property
    def full_id(self) -> str:
        """Get full model identifier (provider/name)."""
        if self.provider:
            return f"{self.provider}/{self.name}"
        return self.name

    def supports(self, capability: str) -> bool:
        """Check if model supports a capability."""
        return self.capabilities.supports(capability)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "provider": self.provider,
            "capabilities": self.capabilities.to_dict(),
            "pricing": self.pricing.to_dict() if self.pricing else None,
            "performance": self.performance.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelInfo:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            provider=data.get("provider", ""),
            capabilities=ModelCapabilities.from_dict(data.get("capabilities", {})),
            pricing=(
                PricingInfo.from_dict(data["pricing"]) if data.get("pricing") else None
            ),
            performance=PerformanceMetrics.from_dict(data.get("performance", {})),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ModelEndpoint:
    """Model endpoint for load balancing.

    Attributes:
        name: Endpoint name/identifier
        model_name: Provider-native model name
        url: Base URL for the endpoint
        weight: Load balancing weight
        healthy: Whether endpoint is healthy
        connection_count: Current connection count
    """

    name: str
    model_name: str
    url: str
    weight: float = 1.0
    healthy: bool = True
    connection_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "model_name": self.model_name,
            "url": self.url,
            "weight": self.weight,
            "healthy": self.healthy,
            "connection_count": self.connection_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelEndpoint:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            model_name=data["model_name"],
            url=data["url"],
            weight=data.get("weight", 1.0),
            healthy=data.get("healthy", True),
            connection_count=data.get("connection_count", 0),
        )


@dataclass
class HealthCheckConfig:
    """Health check configuration for endpoints.

    Attributes:
        endpoint: Health check endpoint path
        interval_seconds: Check interval in seconds
        timeout_seconds: Request timeout in seconds
        max_failures: Maximum failures before marking unhealthy
    """

    endpoint: str = "/health"
    interval_seconds: float = 30.0
    timeout_seconds: float = 5.0
    max_failures: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "endpoint": self.endpoint,
            "interval_seconds": self.interval_seconds,
            "timeout_seconds": self.timeout_seconds,
            "max_failures": self.max_failures,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HealthCheckConfig:
        """Create from dictionary."""
        return cls(
            endpoint=data.get("endpoint", "/health"),
            interval_seconds=data.get("interval_seconds", 30.0),
            timeout_seconds=data.get("timeout_seconds", 5.0),
            max_failures=data.get("max_failures", 3),
        )
