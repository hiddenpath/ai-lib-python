"""Tests for token counting module."""


from ai_lib_python.tokens import (
    CostEstimate,
    ModelPricing,
    TokenCounter,
    estimate_cost,
    get_model_pricing,
    get_token_counter,
)
from ai_lib_python.tokens.counter import (
    AnthropicEstimator,
    CachingCounter,
    CharacterEstimator,
)


class TestCharacterEstimator:
    """Tests for CharacterEstimator."""

    def test_basic_count(self) -> None:
        """Test basic character counting."""
        counter = CharacterEstimator()
        # With default 4 chars per token
        text = "Hello world!"  # 12 chars
        count = counter.count(text)
        assert count == 3  # 12 / 4 = 3

    def test_minimum_one_token(self) -> None:
        """Test minimum one token for non-empty text."""
        counter = CharacterEstimator()
        count = counter.count("Hi")  # 2 chars
        assert count == 1


class TestAnthropicEstimator:
    """Tests for AnthropicEstimator."""

    def test_basic_count(self) -> None:
        """Test Anthropic estimator."""
        counter = AnthropicEstimator()
        text = "Hello world!"
        count = counter.count(text)
        assert count > 0

    def test_whitespace_adjustment(self) -> None:
        """Test whitespace affects token count."""
        counter = AnthropicEstimator()
        text_no_space = "HelloWorld"
        text_with_space = "Hello World"

        # Text with space should have more tokens
        assert counter.count(text_with_space) >= counter.count(text_no_space)


class TestTokenCounter:
    """Tests for TokenCounter factory."""

    def test_for_model_openai(self) -> None:
        """Test getting counter for OpenAI model."""
        counter = TokenCounter.for_model("gpt-4o")
        assert counter is not None
        count = counter.count("Hello")
        assert count > 0

    def test_for_model_anthropic(self) -> None:
        """Test getting counter for Anthropic model."""
        counter = TokenCounter.for_model("claude-3-5-sonnet")
        assert isinstance(counter, AnthropicEstimator)

    def test_for_model_unknown(self) -> None:
        """Test getting counter for unknown model."""
        counter = TokenCounter.for_model("unknown-model")
        assert isinstance(counter, CharacterEstimator)

    def test_truncate_to_limit(self) -> None:
        """Test truncating text to token limit."""
        counter = CharacterEstimator()
        text = "This is a long text that needs to be truncated"
        truncated = counter.truncate_to_limit(text, max_tokens=5, suffix="...")

        # Should be shorter
        assert len(truncated) < len(text)
        assert truncated.endswith("...")

    def test_truncate_no_change_needed(self) -> None:
        """Test truncation when text is already within limit."""
        counter = CharacterEstimator()
        text = "Short"
        truncated = counter.truncate_to_limit(text, max_tokens=100)

        assert truncated == text


class TestCachingCounter:
    """Tests for CachingCounter."""

    def test_caches_results(self) -> None:
        """Test that results are cached."""
        base_counter = CharacterEstimator()
        counter = CachingCounter(base_counter, max_cache_size=100)

        text = "Hello world"
        count1 = counter.count(text)
        count2 = counter.count(text)

        assert count1 == count2

    def test_cache_limit(self) -> None:
        """Test cache size limit."""
        base_counter = CharacterEstimator()
        counter = CachingCounter(base_counter, max_cache_size=2)

        counter.count("text1")
        counter.count("text2")
        counter.count("text3")  # Should not be cached

        counter.clear_cache()
        # No error should occur
        assert counter.count("text1") > 0


class TestGetTokenCounter:
    """Tests for get_token_counter helper."""

    def test_returns_cached_counter(self) -> None:
        """Test that counters are cached."""
        counter1 = get_token_counter("gpt-4o")
        counter2 = get_token_counter("gpt-4o")
        assert counter1 is counter2


class TestModelPricing:
    """Tests for ModelPricing."""

    def test_pricing_properties(self) -> None:
        """Test pricing property calculations."""
        pricing = ModelPricing(
            model="test",
            input_price_per_1k=0.01,
            output_price_per_1k=0.02,
        )

        assert pricing.input_price_per_token == 0.00001
        assert pricing.output_price_per_token == 0.00002


class TestCostEstimate:
    """Tests for CostEstimate."""

    def test_total_cost(self) -> None:
        """Test total cost calculation."""
        estimate = CostEstimate(
            input_tokens=1000,
            output_tokens=500,
            input_cost=0.01,
            output_cost=0.02,
            model="gpt-4o",
        )

        assert estimate.total_cost == 0.03

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        estimate = CostEstimate(
            input_tokens=100,
            output_tokens=50,
            input_cost=0.001,
            output_cost=0.002,
            model="gpt-4o",
        )

        d = estimate.to_dict()
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 50
        assert d["total_cost"] == 0.003


class TestGetModelPricing:
    """Tests for get_model_pricing."""

    def test_known_model(self) -> None:
        """Test getting pricing for known model."""
        pricing = get_model_pricing("gpt-4o")
        assert pricing is not None
        assert pricing.input_price_per_1k > 0

    def test_model_alias(self) -> None:
        """Test model alias resolution."""
        pricing = get_model_pricing("claude-3-5-sonnet")
        assert pricing is not None
        assert "claude" in pricing.model.lower()

    def test_unknown_model(self) -> None:
        """Test unknown model returns None."""
        pricing = get_model_pricing("completely-unknown-model-xyz")
        assert pricing is None


class TestEstimateCost:
    """Tests for estimate_cost."""

    def test_known_model(self) -> None:
        """Test cost estimation for known model."""
        cost = estimate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4o",
        )

        assert cost.input_tokens == 1000
        assert cost.output_tokens == 500
        assert cost.total_cost > 0

    def test_unknown_model_default_pricing(self) -> None:
        """Test cost estimation with default pricing for unknown model."""
        cost = estimate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="unknown-model",
        )

        # Should use default pricing
        assert cost.total_cost > 0
