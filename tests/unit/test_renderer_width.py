"""Unit tests for width-aware rendering."""

import re

import pytest

from claude_code_statusline.config.loader import get_effective_widgets
from claude_code_statusline.config.schema import WidgetConfigModel
from claude_code_statusline.renderer import (
    render_status_line,
    render_status_line_width_aware,
    render_status_line_with_config,
    render_widget,
)
from claude_code_statusline.types import (
    ContextWindow,
    RenderContext,
    TokenMetrics,
)
from claude_code_statusline.utils.colors import visible_len


@pytest.fixture
def rich_context():
    """Context with all widgets populated for width testing."""
    return RenderContext(
        data={
            "model": {"display_name": "Opus 4.6"},
            "workspace": {"current_dir": "/Users/test/my-long-project-name"},
            "cost": {
                "total_cost_usd": 12.50,
                "total_lines_added": 1500,
                "total_lines_removed": 450,
            },
            "session_id": "abc12345-def6-7890-abcd-ef1234567890",
        },
        token_metrics=TokenMetrics(
            context_length=120000,
            transcript_exists=True,
        ),
        duration_seconds=7800,
        context_window=ContextWindow(
            context_window_size=200000,
            current_input_tokens=80000,
            cache_creation_input_tokens=10000,
            cache_read_input_tokens=5000,
        ),
    )


@pytest.fixture
def default_widgets():
    return get_effective_widgets()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _separator_text(widgets, context) -> str:
    separator = next(cfg for cfg in widgets if cfg.type == "separator")
    rendered = render_widget(separator, context)
    assert rendered
    return _strip_ansi(rendered)


class TestNoWidthPreservesCurrentBehavior:
    def test_no_terminal_width_uses_standard_render(
        self, rich_context, default_widgets
    ):
        """When terminal_width is None, output matches render_status_line exactly."""
        rich_context.terminal_width = None
        standard = render_status_line(default_widgets, rich_context)
        with_config = render_status_line_with_config(rich_context)
        assert standard == with_config

    def test_no_terminal_width_is_single_line(self, rich_context):
        rich_context.terminal_width = None
        output = render_status_line_with_config(rich_context)
        assert "\n" not in output


class TestFullRenderFits:
    def test_wide_terminal_returns_full_render(self, rich_context, default_widgets):
        """Very wide terminal should return full (non-compact) render."""
        full_line = render_status_line(default_widgets, rich_context)
        full_width = visible_len(full_line)

        result = render_status_line_width_aware(
            default_widgets, rich_context, full_width + 50
        )
        assert result == full_line
        assert "\n" not in result


class TestCompactRender:
    def test_unsplittable_full_too_wide_uses_compact(self, rich_context):
        """A lone widget can't split, so compact wins once full overflows."""
        widgets = [WidgetConfigModel(type="context-percentage")]
        full_width = visible_len(render_status_line(widgets, rich_context))

        result = render_status_line_width_aware(widgets, rich_context, full_width - 1)

        assert "\n" not in result
        assert "Context:" not in result
        assert visible_len(result) <= full_width - 1


class TestFullTwoLine:
    def test_full_fits_on_two_lines_keeps_labels(self, rich_context, default_widgets):
        """Full form on two lines is preferred over compact on one or two."""
        full_width = visible_len(render_status_line(default_widgets, rich_context))
        assert full_width > 120

        result = render_status_line_width_aware(default_widgets, rich_context, 120)

        lines = result.split("\n")
        assert len(lines) == 2
        assert all(visible_len(line) <= 120 for line in lines)
        for label in ("Context:", "USD", "Elapsed:"):
            assert label in result

    def test_full_too_wide_for_two_lines_uses_compact(
        self, rich_context, default_widgets
    ):
        result = render_status_line_width_aware(default_widgets, rich_context, 60)

        lines = result.split("\n")
        assert len(lines) == 2
        assert all(visible_len(line) <= 60 for line in lines)
        assert "Context:" not in result


class TestFillFirstSplit:
    @pytest.mark.parametrize("width", [120, 100, 80, 60])
    def test_line_one_cannot_fit_next_widget(
        self, rich_context, default_widgets, width
    ):
        """Moving line 2's first widget onto line 1 would overflow the width."""
        separator = _separator_text(default_widgets, rich_context)

        result = render_status_line_width_aware(default_widgets, rich_context, width)

        line1, line2 = (_strip_ansi(line) for line in result.split("\n"))
        next_widget = line2.split(separator)[0]
        assert len(line1 + separator + next_widget) > width


class TestTwoLineSplit:
    def test_triggers_two_line_when_compact_too_wide(
        self, rich_context, default_widgets
    ):
        """Narrow terminal should split into two lines."""
        result = render_status_line_width_aware(default_widgets, rich_context, 60)

        assert "\n" in result, "Expected two-line split at width=60, got single line"
        lines = result.split("\n")
        assert len(lines) == 2
        for line in lines:
            assert visible_len(line) <= 60

    def test_both_lines_have_content(self, rich_context, default_widgets):
        result = render_status_line_width_aware(default_widgets, rich_context, 60)
        assert "\n" in result, "Expected two-line split at width=60"
        lines = result.split("\n")
        for line in lines:
            assert len(line.strip()) > 0


class TestPriorityDropping:
    def test_very_narrow_drops_widgets(self, rich_context, default_widgets):
        """Extremely narrow terminal should drop low-priority widgets."""
        result = render_status_line_width_aware(default_widgets, rich_context, 30)
        # Should still produce some output
        assert len(result) > 0

    def test_session_id_dropped_first(self, rich_context, default_widgets):
        """Session ID (priority 80) should be dropped before model (priority 20)."""
        result = render_status_line_width_aware(default_widgets, rich_context, 40)
        # Session ID should not appear in narrow renders
        assert "Session:" not in result
        # But critical widgets should survive when possible
        # (model is rendered by the outer colorize, so check for the display name)


class TestNoOrphanedSeparators:
    def test_no_double_separators_after_drop(self, rich_context, default_widgets):
        """After dropping widgets, no || artifacts should appear."""
        for width in [30, 40, 50, 60, 80, 100]:
            result = render_status_line_width_aware(
                default_widgets, rich_context, width
            )
            for line in result.split("\n"):
                assert "| |" not in line
                assert line.strip() != "|"
                # No leading or trailing separators
                stripped = line.strip()
                if stripped:
                    assert not stripped.startswith("|")
                    assert not stripped.endswith("|")


class TestEdgeCases:
    def test_extremely_narrow_does_not_crash(self, rich_context, default_widgets):
        result = render_status_line_width_aware(default_widgets, rich_context, 5)
        assert isinstance(result, str)

    def test_width_of_one(self, rich_context, default_widgets):
        result = render_status_line_width_aware(default_widgets, rich_context, 1)
        assert isinstance(result, str)

    def test_empty_widgets(self, rich_context):
        result = render_status_line_width_aware([], rich_context, 80)
        assert result == ""

    def test_single_widget(self, rich_context):
        widgets = [WidgetConfigModel(type="model", color="cyan")]
        result = render_status_line_width_aware(widgets, rich_context, 200)
        assert "Opus 4.6" in result
