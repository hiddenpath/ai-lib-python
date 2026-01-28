"""Tests for routing module."""

import pytest

from ai_lib_python.routing import (
    CostBasedSelector,
    HealthCheckConfig,
    LoadBalancingStrategy,
    ModelArray,
    ModelCapabilities,
    ModelEndpoint,
    ModelInfo,
    ModelManager,
    ModelSelectionStrategy,
    PerformanceBasedSelector,
    PerformanceMetrics,
    PricingInfo,
    QualityBasedSelector,
    QualityTier,
    RandomSelector,
    RoundRobinSelector,
    SpeedTier,
    WeightedSelector,
    create_anthropic_models,
    create_model_selector,
    create_openai_models,
    get_model_manager,
)


class TestModelCapabilities:
    """Tests for ModelCapabilities."""

    def test_default_values(self) -> None:
        """Test default capability values."""
        caps = ModelCapabilities()
        assert caps.chat is True
        assert caps.code_generation is False
        assert caps.multimodal is False
        assert caps.streaming is True

    def test_supports_capability(self) -> None:
        """Test capability checking."""
        caps = ModelCapabilities(
            chat=True,
            code_generation=True,
            multimodal=False,
            function_calling=True,
        )
        assert caps.supports("chat") is True
        assert caps.supports("code") is True
        assert caps.supports("multimodal") is False
        assert caps.supports("functions") is True
        assert caps.supports("tools") is True  # tool_use or function_calling
        assert caps.supports("unknown") is False

    def test_fluent_api(self) -> None:
        """Test fluent builder methods."""
        caps = (
            ModelCapabilities()
            .with_chat()
            .with_code_generation()
            .with_multimodal()
            .with_function_calling()
            .with_context_window(128000)
        )
        assert caps.chat is True
        assert caps.code_generation is True
        assert caps.multimodal is True
        assert caps.function_calling is True
        assert caps.context_window == 128000

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        caps = ModelCapabilities(chat=True, multimodal=True, context_window=100000)
        d = caps.to_dict()
        assert d["chat"] is True
        assert d["multimodal"] is True
        assert d["context_window"] == 100000

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {"chat": True, "multimodal": True, "context_window": 200000}
        caps = ModelCapabilities.from_dict(data)
        assert caps.chat is True
        assert caps.multimodal is True
        assert caps.context_window == 200000


class TestPricingInfo:
    """Tests for PricingInfo."""

    def test_cost_calculation(self) -> None:
        """Test cost calculation."""
        pricing = PricingInfo(input_cost_per_1k=2.5, output_cost_per_1k=10.0)
        # 1000 input + 500 output = 2.5 + 5.0 = 7.5
        cost = pricing.calculate_cost(1000, 500)
        assert cost == 7.5

    def test_with_currency(self) -> None:
        """Test currency setting."""
        pricing = PricingInfo(input_cost_per_1k=1.0, output_cost_per_1k=2.0)
        pricing = pricing.with_currency("EUR")
        assert pricing.currency == "EUR"


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics."""

    def test_default_values(self) -> None:
        """Test default performance values."""
        perf = PerformanceMetrics()
        assert perf.speed == SpeedTier.BALANCED
        assert perf.quality == QualityTier.GOOD

    def test_fluent_api(self) -> None:
        """Test fluent builder methods."""
        perf = (
            PerformanceMetrics()
            .with_speed(SpeedTier.FAST)
            .with_quality(QualityTier.EXCELLENT)
            .with_avg_response_time(500.0)
            .with_throughput(100.0)
        )
        assert perf.speed == SpeedTier.FAST
        assert perf.quality == QualityTier.EXCELLENT
        assert perf.avg_response_time_ms == 500.0
        assert perf.throughput_tps == 100.0


class TestModelInfo:
    """Tests for ModelInfo."""

    def test_full_id(self) -> None:
        """Test full model ID generation."""
        model = ModelInfo(name="gpt-4o", provider="openai")
        assert model.full_id == "openai/gpt-4o"

    def test_full_id_no_provider(self) -> None:
        """Test full ID without provider."""
        model = ModelInfo(name="gpt-4o")
        assert model.full_id == "gpt-4o"

    def test_supports(self) -> None:
        """Test capability support check."""
        model = ModelInfo(
            name="test",
            capabilities=ModelCapabilities(chat=True, multimodal=True),
        )
        assert model.supports("chat") is True
        assert model.supports("multimodal") is True
        assert model.supports("code") is False


class TestModelSelectors:
    """Tests for model selection strategies."""

    @pytest.fixture
    def models(self) -> list[ModelInfo]:
        """Create test models."""
        return [
            ModelInfo(
                name="fast-cheap",
                pricing=PricingInfo(0.1, 0.2),
                performance=PerformanceMetrics(
                    speed=SpeedTier.FAST, quality=QualityTier.BASIC
                ),
            ),
            ModelInfo(
                name="balanced",
                pricing=PricingInfo(1.0, 2.0),
                performance=PerformanceMetrics(
                    speed=SpeedTier.BALANCED, quality=QualityTier.GOOD
                ),
            ),
            ModelInfo(
                name="slow-quality",
                pricing=PricingInfo(10.0, 20.0),
                performance=PerformanceMetrics(
                    speed=SpeedTier.SLOW, quality=QualityTier.EXCELLENT
                ),
            ),
        ]

    def test_round_robin_selector(self, models: list[ModelInfo]) -> None:
        """Test round robin selection."""
        selector = RoundRobinSelector()
        selected = [selector.select(models) for _ in range(6)]
        names = [m.name if m else None for m in selected]
        # Should cycle through
        assert names[0] == "fast-cheap"
        assert names[1] == "balanced"
        assert names[2] == "slow-quality"
        assert names[3] == "fast-cheap"

    def test_cost_based_selector(self, models: list[ModelInfo]) -> None:
        """Test cost-based selection."""
        selector = CostBasedSelector()
        selected = selector.select(models)
        assert selected is not None
        assert selected.name == "fast-cheap"  # Cheapest

    def test_performance_based_selector(self, models: list[ModelInfo]) -> None:
        """Test performance-based selection."""
        selector = PerformanceBasedSelector()
        selected = selector.select(models)
        assert selected is not None
        assert selected.name == "fast-cheap"  # Fastest

    def test_quality_based_selector(self, models: list[ModelInfo]) -> None:
        """Test quality-based selection."""
        selector = QualityBasedSelector()
        selected = selector.select(models)
        assert selected is not None
        assert selected.name == "slow-quality"  # Highest quality

    def test_weighted_selector(self, models: list[ModelInfo]) -> None:
        """Test weighted selection."""
        selector = WeightedSelector()
        selected = selector.select(models)
        assert selected is not None
        # Should prefer fast + quality combination

    def test_random_selector(self, models: list[ModelInfo]) -> None:
        """Test random selection."""
        selector = RandomSelector()
        selected = selector.select(models)
        assert selected is not None
        assert selected in models

    def test_create_selector(self) -> None:
        """Test selector factory."""
        selector = create_model_selector(ModelSelectionStrategy.COST_BASED)
        assert isinstance(selector, CostBasedSelector)

    def test_empty_list(self) -> None:
        """Test selection from empty list."""
        selector = RoundRobinSelector()
        assert selector.select([]) is None


class TestModelManager:
    """Tests for ModelManager."""

    def test_add_and_get_model(self) -> None:
        """Test adding and retrieving models."""
        manager = ModelManager(provider="test")
        model = ModelInfo(name="test-model")
        manager.add_model(model)

        retrieved = manager.get_model("test-model")
        assert retrieved is not None
        assert retrieved.name == "test-model"
        assert retrieved.provider == "test"

    def test_remove_model(self) -> None:
        """Test removing models."""
        manager = ModelManager()
        manager.add_model(ModelInfo(name="model1"))
        manager.add_model(ModelInfo(name="model2"))

        removed = manager.remove_model("model1")
        assert removed is not None
        assert removed.name == "model1"
        assert manager.get_model("model1") is None
        assert manager.get_model("model2") is not None

    def test_list_models(self) -> None:
        """Test listing all models."""
        manager = ModelManager()
        manager.add_model(ModelInfo(name="m1"))
        manager.add_model(ModelInfo(name="m2"))

        models = manager.list_models()
        assert len(models) == 2

    def test_select_model(self) -> None:
        """Test model selection."""
        manager = ModelManager()
        manager.add_model(ModelInfo(name="m1"))
        manager.add_model(ModelInfo(name="m2"))

        selected = manager.select_model()
        assert selected is not None

    def test_recommend_for(self) -> None:
        """Test recommendation by capability."""
        manager = ModelManager()
        manager.add_model(
            ModelInfo(
                name="vision-model",
                capabilities=ModelCapabilities(multimodal=True),
            )
        )
        manager.add_model(
            ModelInfo(
                name="text-model",
                capabilities=ModelCapabilities(chat=True, multimodal=False),
            )
        )

        recommended = manager.recommend_for("multimodal")
        assert recommended is not None
        assert recommended.name == "vision-model"

    def test_filter_by_capability(self) -> None:
        """Test filtering by capability."""
        manager = ModelManager()
        manager.add_model(
            ModelInfo(
                name="m1", capabilities=ModelCapabilities(code_generation=True)
            )
        )
        manager.add_model(
            ModelInfo(
                name="m2", capabilities=ModelCapabilities(code_generation=False)
            )
        )

        filtered = manager.filter_by_capability("code")
        assert len(filtered) == 1
        assert filtered[0].name == "m1"

    def test_filter_by_cost(self) -> None:
        """Test filtering by cost."""
        manager = ModelManager()
        manager.add_model(ModelInfo(name="cheap", pricing=PricingInfo(0.1, 0.2)))
        manager.add_model(ModelInfo(name="expensive", pricing=PricingInfo(10.0, 20.0)))

        filtered = manager.filter_by_cost(1.0)
        assert len(filtered) == 1
        assert filtered[0].name == "cheap"

    def test_with_strategy(self) -> None:
        """Test changing selection strategy."""
        manager = ModelManager()
        manager.with_strategy(ModelSelectionStrategy.COST_BASED)
        assert manager.strategy == ModelSelectionStrategy.COST_BASED

    def test_contains(self) -> None:
        """Test contains check."""
        manager = ModelManager()
        manager.add_model(ModelInfo(name="test"))
        assert "test" in manager
        assert "other" not in manager


class TestModelArray:
    """Tests for ModelArray."""

    def test_add_endpoint(self) -> None:
        """Test adding endpoints."""
        array = ModelArray("cluster")
        array.add_endpoint(ModelEndpoint("e1", "gpt-4o", "http://api1.example.com"))
        array.add_endpoint(ModelEndpoint("e2", "gpt-4o", "http://api2.example.com"))

        assert len(array) == 2
        assert array.get_endpoint("e1") is not None

    def test_select_endpoint(self) -> None:
        """Test endpoint selection."""
        array = ModelArray("cluster")
        array.add_endpoint(ModelEndpoint("e1", "gpt-4o", "http://api1.example.com"))
        array.add_endpoint(ModelEndpoint("e2", "gpt-4o", "http://api2.example.com"))

        selected = array.select_endpoint()
        assert selected is not None

    def test_mark_unhealthy(self) -> None:
        """Test marking endpoint unhealthy."""
        array = ModelArray("cluster")
        array.add_endpoint(ModelEndpoint("e1", "gpt-4o", "http://api1.example.com"))

        array.mark_unhealthy("e1")
        endpoint = array.get_endpoint("e1")
        assert endpoint is not None
        assert endpoint.healthy is False

    def test_mark_healthy(self) -> None:
        """Test marking endpoint healthy."""
        array = ModelArray("cluster")
        ep = ModelEndpoint("e1", "gpt-4o", "http://api.example.com", healthy=False)
        array.add_endpoint(ep)

        array.mark_healthy("e1")
        endpoint = array.get_endpoint("e1")
        assert endpoint is not None
        assert endpoint.healthy is True

    def test_is_healthy(self) -> None:
        """Test cluster health check."""
        array = ModelArray("cluster")
        array.add_endpoint(
            ModelEndpoint("e1", "m", "http://a.com", healthy=False)
        )
        array.add_endpoint(
            ModelEndpoint("e2", "m", "http://b.com", healthy=True)
        )

        assert array.is_healthy() is True

        array.mark_unhealthy("e2")
        assert array.is_healthy() is False

    def test_healthy_endpoints(self) -> None:
        """Test getting healthy endpoints."""
        array = ModelArray("cluster")
        array.add_endpoint(ModelEndpoint("e1", "m", "http://a.com", healthy=True))
        array.add_endpoint(ModelEndpoint("e2", "m", "http://b.com", healthy=False))
        array.add_endpoint(ModelEndpoint("e3", "m", "http://c.com", healthy=True))

        healthy = array.healthy_endpoints()
        assert len(healthy) == 2

    def test_with_strategy(self) -> None:
        """Test changing load balancing strategy."""
        array = ModelArray("cluster")
        array.with_strategy(LoadBalancingStrategy.WEIGHTED)
        assert array.strategy == LoadBalancingStrategy.WEIGHTED


class TestPreConfiguredManagers:
    """Tests for pre-configured model managers."""

    def test_create_openai_models(self) -> None:
        """Test OpenAI model creation."""
        manager = create_openai_models()
        assert len(manager) > 0
        assert "gpt-4o" in manager
        assert "gpt-4o-mini" in manager

    def test_create_anthropic_models(self) -> None:
        """Test Anthropic model creation."""
        manager = create_anthropic_models()
        assert len(manager) > 0
        # Check for claude models
        models = manager.list_models()
        assert any("claude" in m.name for m in models)

    def test_get_model_manager(self) -> None:
        """Test global manager retrieval."""
        manager = get_model_manager("openai")
        assert manager is not None
        assert manager.provider == "openai"


class TestHealthCheckConfig:
    """Tests for HealthCheckConfig."""

    def test_default_values(self) -> None:
        """Test default health check values."""
        config = HealthCheckConfig()
        assert config.endpoint == "/health"
        assert config.interval_seconds == 30.0
        assert config.timeout_seconds == 5.0
        assert config.max_failures == 3
