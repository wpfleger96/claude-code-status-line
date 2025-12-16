import pytest

from claude_code_statusline.statusline import extract_context_window
from claude_code_statusline.types import ContextWindow, RenderContext, TokenMetrics
from claude_code_statusline.utils.models import (
    get_context_limit_for_render,
    get_current_context_length,
)


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
        assert cw.current_context_tokens == 15500  # 8500 + 5000 + 2000
        assert cw.has_current_usage is True

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

        # Should use context_window, not token_metrics
        assert length == 15500  # From context_window
        assert limit == 1000000  # From context_window

    def test_falls_back_to_transcript_when_no_context_window(self):
        """Falls back to transcript parsing when context_window unavailable."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            token_metrics=TokenMetrics(context_length=50000, transcript_exists=True),
            context_window=None,
        )

        length = get_current_context_length(context)
        limit = get_context_limit_for_render(context)

        # Should fallback to token_metrics and model lookup
        assert length == 50000
        assert limit == 200000

    def test_falls_back_when_current_usage_unavailable(self):
        """Falls back to transcript when context_window exists but current_usage is null."""
        context = RenderContext(
            data={"model": {"id": "claude-sonnet-4"}},
            token_metrics=TokenMetrics(context_length=50000, transcript_exists=True),
            context_window=ContextWindow(
                context_window_size=200000,
                current_input_tokens=None,  # No current_usage
            ),
        )

        length = get_current_context_length(context)
        limit = get_context_limit_for_render(context)

        # Should use context_window for limit, fallback to token_metrics for length
        assert length == 50000
        assert limit == 200000
