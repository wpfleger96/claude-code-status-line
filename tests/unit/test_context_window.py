import pytest

from claude_code_statusline.config.schema import WidgetConfigModel
from claude_code_statusline.statusline import (
    extract_context_window,
    resolve_duration_seconds,
)
from claude_code_statusline.types import ContextWindow, RenderContext, TokenMetrics
from claude_code_statusline.utils.models import (
    get_context_limit_for_render,
    get_current_context_length,
)
from claude_code_statusline.widgets.builtin.context import ContextPercentageWidget


@pytest.mark.unit
class TestContextWindowExtraction:
    """Test extraction and fallback behavior."""

    def test_extracts_complete_context_window(self):
        """Full context_window payload is extracted correctly."""
        data = {
            "context_window": {
                "total_input_tokens": 15234,
                "total_output_tokens": 4521,
                "context_window_size": 200000,
                "used_percentage": 8,
                "current_usage": {
                    "input_tokens": 8500,
                    "output_tokens": 1200,
                    "cache_creation_input_tokens": 5000,
                    "cache_read_input_tokens": 2000,
                },
            }
        }

        cw = extract_context_window(data)

        assert cw is not None
        assert cw.context_window_size == 200000
        assert cw.current_context_tokens == 15500
        assert cw.has_current_usage is True
        assert cw.used_percentage == 8

    def test_handles_null_current_usage(self):
        """Falls back when current_usage is null (no messages yet)."""
        data = {
            "context_window": {
                "context_window_size": 200000,
                "current_usage": None,
            }
        }

        cw = extract_context_window(data)

        assert cw is not None
        assert cw.context_window_size == 200000
        assert cw.has_current_usage is False

    def test_returns_none_when_context_window_missing_or_null(self):
        """Returns None for old payloads or null context_window."""
        assert extract_context_window({}) is None
        assert extract_context_window({"context_window": None}) is None


@pytest.mark.unit
class TestContextWindowPriority:
    """Test that context_window is prioritized over transcript parsing."""

    def test_context_window_preferred_over_transcript(self):
        """context_window takes priority over token_metrics."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            token_metrics=TokenMetrics(context_length=50000, transcript_exists=True),
            context_window=ContextWindow(
                context_window_size=1000000,
                current_input_tokens=8500,
                cache_creation_input_tokens=5000,
                cache_read_input_tokens=2000,
            ),
        )

        length = get_current_context_length(context)
        limit = get_context_limit_for_render(context)

        assert length == 15500
        assert limit == 1000000

    def test_falls_back_to_transcript_when_no_context_window(self):
        """Falls back to transcript parsing when context_window unavailable."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            token_metrics=TokenMetrics(context_length=50000, transcript_exists=True),
            context_window=None,
        )

        length = get_current_context_length(context)
        limit = get_context_limit_for_render(context)

        assert length == 50000
        assert limit == 200000

    def test_falls_back_when_current_usage_unavailable(self):
        """Falls back to transcript when context_window exists but current_usage is null."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            token_metrics=TokenMetrics(context_length=50000, transcript_exists=True),
            context_window=ContextWindow(
                context_window_size=200000,
                current_input_tokens=None,
            ),
        )

        length = get_current_context_length(context)
        limit = get_context_limit_for_render(context)

        assert length == 50000
        assert limit == 200000


@pytest.mark.unit
class TestUsedPercentagePriority:
    """Test that used_percentage from payload is preferred over computed value."""

    def test_payload_percentage_preferred(self):
        """Widget uses used_percentage from payload when available."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            token_metrics=TokenMetrics(context_length=50000, transcript_exists=True),
            context_window=ContextWindow(
                context_window_size=200000,
                current_input_tokens=80000,
                cache_creation_input_tokens=10000,
                cache_read_input_tokens=10000,
                used_percentage=42.0,
            ),
        )

        widget = ContextPercentageWidget()
        config = WidgetConfigModel(type="context-percentage")
        result = widget.render(config, context)

        assert result is not None
        assert "42.0%" in result

    def test_falls_back_to_computed_when_null(self):
        """Widget computes percentage when used_percentage is null."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            context_window=ContextWindow(
                context_window_size=200000,
                current_input_tokens=80000,
                cache_creation_input_tokens=10000,
                cache_read_input_tokens=10000,
                used_percentage=None,
            ),
        )

        widget = ContextPercentageWidget()
        config = WidgetConfigModel(type="context-percentage")
        result = widget.render(config, context)

        assert result is not None
        assert "50.0%" in result

    def test_extraction_preserves_null_percentage(self):
        """extract_context_window passes through null used_percentage."""
        data = {
            "context_window": {
                "context_window_size": 200000,
                "used_percentage": None,
                "current_usage": None,
            }
        }

        cw = extract_context_window(data)

        assert cw is not None
        assert cw.used_percentage is None


@pytest.mark.unit
class TestResolveDurationSeconds:
    """Test that total_duration_ms from payload takes priority over transcript."""

    def test_payload_wins_over_transcript(self):
        """cost.total_duration_ms takes priority when present."""
        data = {"cost": {"total_duration_ms": 45000}}
        assert resolve_duration_seconds(data, transcript_duration=60) == 45

    def test_falls_back_to_transcript_when_absent(self):
        """Falls back to transcript duration when total_duration_ms missing."""
        data = {"cost": {"total_cost_usd": 1.0}}
        assert resolve_duration_seconds(data, transcript_duration=60) == 60

    def test_zero_duration_falls_back(self):
        """total_duration_ms of 0 is treated as absent."""
        data = {"cost": {"total_duration_ms": 0}}
        assert resolve_duration_seconds(data, transcript_duration=60) == 60

    def test_null_cost_does_not_crash(self):
        """Explicit null cost in payload does not raise."""
        data = {"cost": None}
        assert resolve_duration_seconds(data, transcript_duration=60) == 60

    def test_missing_cost_does_not_crash(self):
        """Missing cost key does not raise."""
        assert resolve_duration_seconds({}, transcript_duration=60) == 60

    def test_both_absent_returns_none(self):
        """Returns None when neither source is available."""
        assert resolve_duration_seconds({}, transcript_duration=None) is None
