"""Tests for feedback collection system."""

import pytest

from ai_lib_python.telemetry import (
    ChoiceSelectionFeedback,
    CompositeFeedbackSink,
    ConsoleFeedbackSink,
    CorrectionFeedback,
    FeedbackType,
    InMemoryFeedbackSink,
    NoopFeedbackSink,
    RatingFeedback,
    RegenerateFeedback,
    StopFeedback,
    TextFeedback,
    ThumbsFeedback,
    get_feedback_sink,
    report_feedback,
    set_feedback_sink,
)


class TestChoiceSelectionFeedback:
    """Tests for ChoiceSelectionFeedback."""

    def test_basic_creation(self) -> None:
        """Test basic feedback creation."""
        feedback = ChoiceSelectionFeedback(
            request_id="req-123",
            chosen_index=1,
        )
        assert feedback.request_id == "req-123"
        assert feedback.chosen_index == 1

    def test_with_rejected(self) -> None:
        """Test feedback with rejected indices."""
        feedback = ChoiceSelectionFeedback(
            request_id="req-123",
            chosen_index=1,
            rejected_indices=[0, 2, 3],
        )
        assert feedback.rejected_indices == [0, 2, 3]

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        feedback = ChoiceSelectionFeedback(
            request_id="req-123",
            chosen_index=1,
            latency_to_select_ms=500.0,
        )
        d = feedback.to_dict()
        assert d["type"] == FeedbackType.CHOICE_SELECTION.value
        assert d["request_id"] == "req-123"
        assert d["chosen_index"] == 1
        assert d["latency_to_select_ms"] == 500.0


class TestRatingFeedback:
    """Tests for RatingFeedback."""

    def test_basic_rating(self) -> None:
        """Test basic rating feedback."""
        feedback = RatingFeedback(
            request_id="req-123",
            rating=4,
        )
        assert feedback.rating == 4
        assert feedback.max_rating == 5

    def test_custom_max_rating(self) -> None:
        """Test custom max rating."""
        feedback = RatingFeedback(
            request_id="req-123",
            rating=8,
            max_rating=10,
        )
        assert feedback.max_rating == 10

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        feedback = RatingFeedback(
            request_id="req-123",
            rating=5,
            category="accuracy",
        )
        d = feedback.to_dict()
        assert d["type"] == FeedbackType.RATING.value
        assert d["rating"] == 5
        assert d["category"] == "accuracy"


class TestThumbsFeedback:
    """Tests for ThumbsFeedback."""

    def test_thumbs_up(self) -> None:
        """Test thumbs up feedback."""
        feedback = ThumbsFeedback(
            request_id="req-123",
            is_positive=True,
        )
        assert feedback.is_positive is True

    def test_thumbs_down_with_reason(self) -> None:
        """Test thumbs down with reason."""
        feedback = ThumbsFeedback(
            request_id="req-123",
            is_positive=False,
            reason="Incorrect information",
        )
        assert feedback.is_positive is False
        assert feedback.reason == "Incorrect information"


class TestTextFeedback:
    """Tests for TextFeedback."""

    def test_text_feedback(self) -> None:
        """Test text feedback."""
        feedback = TextFeedback(
            request_id="req-123",
            text="Great response!",
        )
        assert feedback.text == "Great response!"


class TestCorrectionFeedback:
    """Tests for CorrectionFeedback."""

    def test_correction(self) -> None:
        """Test correction feedback."""
        feedback = CorrectionFeedback(
            request_id="req-123",
            original_hash="abc123",
            corrected_hash="def456",
            edit_distance=15,
        )
        assert feedback.original_hash == "abc123"
        assert feedback.corrected_hash == "def456"
        assert feedback.edit_distance == 15


class TestRegenerateFeedback:
    """Tests for RegenerateFeedback."""

    def test_regenerate(self) -> None:
        """Test regenerate feedback."""
        feedback = RegenerateFeedback(
            request_id="req-123",
            regeneration_count=3,
        )
        assert feedback.regeneration_count == 3


class TestStopFeedback:
    """Tests for StopFeedback."""

    def test_stop(self) -> None:
        """Test stop feedback."""
        feedback = StopFeedback(
            request_id="req-123",
            tokens_generated=150,
        )
        assert feedback.tokens_generated == 150


class TestNoopFeedbackSink:
    """Tests for NoopFeedbackSink."""

    @pytest.mark.asyncio
    async def test_report_noop(self) -> None:
        """Test that noop sink does nothing."""
        sink = NoopFeedbackSink()
        feedback = ThumbsFeedback(request_id="req-123", is_positive=True)
        # Should not raise
        await sink.report(feedback)


class TestInMemoryFeedbackSink:
    """Tests for InMemoryFeedbackSink."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        """Test storing and retrieving events."""
        sink = InMemoryFeedbackSink()
        feedback = ThumbsFeedback(request_id="req-123", is_positive=True)

        await sink.report(feedback)

        events = sink.get_events()
        assert len(events) == 1
        assert events[0].request_id == "req-123"

    @pytest.mark.asyncio
    async def test_get_by_request(self) -> None:
        """Test retrieving events by request ID."""
        sink = InMemoryFeedbackSink()
        await sink.report(ThumbsFeedback(request_id="req-1", is_positive=True))
        await sink.report(ThumbsFeedback(request_id="req-2", is_positive=False))
        await sink.report(RatingFeedback(request_id="req-1", rating=5))

        events = sink.get_events_by_request("req-1")
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_by_type(self) -> None:
        """Test retrieving events by type."""
        sink = InMemoryFeedbackSink()
        await sink.report(ThumbsFeedback(request_id="req-1", is_positive=True))
        await sink.report(RatingFeedback(request_id="req-1", rating=5))
        await sink.report(ThumbsFeedback(request_id="req-2", is_positive=False))

        thumbs = sink.get_events_by_type(FeedbackType.THUMBS)
        assert len(thumbs) == 2

        ratings = sink.get_events_by_type(FeedbackType.RATING)
        assert len(ratings) == 1

    @pytest.mark.asyncio
    async def test_max_events(self) -> None:
        """Test max events limit."""
        sink = InMemoryFeedbackSink(max_events=3)

        for i in range(5):
            await sink.report(ThumbsFeedback(request_id=f"req-{i}", is_positive=True))

        events = sink.get_events()
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing events."""
        sink = InMemoryFeedbackSink()
        await sink.report(ThumbsFeedback(request_id="req-1", is_positive=True))

        sink.clear()
        assert len(sink) == 0


class TestConsoleFeedbackSink:
    """Tests for ConsoleFeedbackSink."""

    @pytest.mark.asyncio
    async def test_report(self, capsys) -> None:
        """Test console output."""
        sink = ConsoleFeedbackSink(prefix="[TEST]")
        feedback = ThumbsFeedback(request_id="req-123", is_positive=True)

        await sink.report(feedback)

        captured = capsys.readouterr()
        assert "[TEST]" in captured.out
        assert "req-123" in captured.out


class TestCompositeFeedbackSink:
    """Tests for CompositeFeedbackSink."""

    @pytest.mark.asyncio
    async def test_report_to_multiple(self) -> None:
        """Test reporting to multiple sinks."""
        sink1 = InMemoryFeedbackSink()
        sink2 = InMemoryFeedbackSink()
        composite = CompositeFeedbackSink([sink1, sink2])

        feedback = ThumbsFeedback(request_id="req-123", is_positive=True)
        await composite.report(feedback)

        assert len(sink1) == 1
        assert len(sink2) == 1

    @pytest.mark.asyncio
    async def test_add_sink(self) -> None:
        """Test adding sink."""
        composite = CompositeFeedbackSink()
        sink = InMemoryFeedbackSink()
        composite.add_sink(sink)

        feedback = ThumbsFeedback(request_id="req-123", is_positive=True)
        await composite.report(feedback)

        assert len(sink) == 1


class TestGlobalSink:
    """Tests for global sink functions."""

    @pytest.mark.asyncio
    async def test_get_default_sink(self) -> None:
        """Test getting default sink."""
        sink = get_feedback_sink()
        # Default should be NoopFeedbackSink
        assert sink is not None

    @pytest.mark.asyncio
    async def test_set_and_report(self) -> None:
        """Test setting sink and reporting."""
        memory_sink = InMemoryFeedbackSink()
        set_feedback_sink(memory_sink)

        feedback = ThumbsFeedback(request_id="req-123", is_positive=True)
        await report_feedback(feedback)

        assert len(memory_sink) == 1

        # Clean up
        set_feedback_sink(NoopFeedbackSink())
