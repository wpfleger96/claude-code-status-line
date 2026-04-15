"""Unit tests for widget compact rendering."""

import pytest

from claude_code_statusline.config.schema import WidgetConfigModel
from claude_code_statusline.types import (
    ContextWindow,
    RenderContext,
    TokenMetrics,
)
from claude_code_statusline.utils.colors import visible_len
from claude_code_statusline.widgets.builtin.context import ContextPercentageWidget
from claude_code_statusline.widgets.builtin.cost import (
    CostWidget,
    LinesAddedWidget,
    LinesChangedWidget,
    LinesRemovedWidget,
)
from claude_code_statusline.widgets.builtin.model import ModelWidget
from claude_code_statusline.widgets.builtin.session import SessionClockWidget


@pytest.fixture
def context_with_data():
    return RenderContext(
        data={
            "model": {"display_name": "Sonnet 4.5"},
            "cost": {
                "total_cost_usd": 2.50,
                "total_lines_added": 150,
                "total_lines_removed": 45,
            },
            "session_id": "abc123-def456-789",
        },
        token_metrics=TokenMetrics(
            input_tokens=85000,
            output_tokens=15000,
            cached_tokens=5000,
            total_tokens=105000,
            context_length=120000,
            transcript_exists=True,
        ),
        duration_seconds=7800,
        context_window=ContextWindow(
            total_input_tokens=50000,
            total_output_tokens=10000,
            context_window_size=200000,
            current_input_tokens=80000,
            current_output_tokens=5000,
            cache_creation_input_tokens=10000,
            cache_read_input_tokens=5000,
        ),
    )


@pytest.fixture
def widget_config():
    return WidgetConfigModel(type="test")


class TestContextPercentageCompact:
    def test_compact_shorter_than_full(self, context_with_data, widget_config):
        widget = ContextPercentageWidget()
        full = widget.render(widget_config, context_with_data)
        compact = widget.render_compact(widget_config, context_with_data)
        assert full is not None and compact is not None
        assert visible_len(compact) < visible_len(full)

    def test_compact_has_no_context_label(self, context_with_data, widget_config):
        widget = ContextPercentageWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "Context:" not in compact

    def test_compact_has_no_token_counts(self, context_with_data, widget_config):
        widget = ContextPercentageWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        # Should not contain the (current/limit) suffix
        assert "(" not in compact
        assert ")" not in compact

    def test_compact_preserves_progress_bar(self, context_with_data, widget_config):
        widget = ContextPercentageWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "●" in compact or "○" in compact


class TestCostCompact:
    def test_compact_shorter_than_full(self, context_with_data, widget_config):
        widget = CostWidget()
        full = widget.render(widget_config, context_with_data)
        compact = widget.render_compact(widget_config, context_with_data)
        assert full is not None and compact is not None
        assert visible_len(compact) < visible_len(full)

    def test_compact_has_no_label(self, context_with_data, widget_config):
        widget = CostWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "Cost:" not in compact
        assert "USD" not in compact

    def test_compact_preserves_color(self, context_with_data, widget_config):
        widget = CostWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "\033[" in compact


class TestLinesChangedCompact:
    def test_compact_shorter_than_full(self, context_with_data, widget_config):
        widget = LinesChangedWidget()
        full = widget.render(widget_config, context_with_data)
        compact = widget.render_compact(widget_config, context_with_data)
        assert full is not None and compact is not None
        assert visible_len(compact) < visible_len(full)

    def test_compact_has_no_labels(self, context_with_data, widget_config):
        widget = LinesChangedWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "(added)" not in compact
        assert "(removed)" not in compact

    def test_compact_preserves_colors(self, context_with_data, widget_config):
        widget = LinesChangedWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "\033[" in compact


class TestLinesAddedCompact:
    def test_compact_drops_label(self, context_with_data, widget_config):
        widget = LinesAddedWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "(added)" not in compact
        assert "+150" in compact


class TestLinesRemovedCompact:
    def test_compact_drops_label(self, context_with_data, widget_config):
        widget = LinesRemovedWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "(removed)" not in compact
        assert "-45" in compact


class TestSessionClockCompact:
    def test_compact_drops_label(self, context_with_data, widget_config):
        widget = SessionClockWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "Elapsed:" not in compact

    def test_compact_preserves_color(self, context_with_data, widget_config):
        widget = SessionClockWidget()
        compact = widget.render_compact(widget_config, context_with_data)
        assert compact is not None
        assert "\033[" in compact


class TestModelCompactFallback:
    def test_compact_same_as_full(self, context_with_data, widget_config):
        widget = ModelWidget()
        full = widget.render(widget_config, context_with_data)
        compact = widget.render_compact(widget_config, context_with_data)
        assert full == compact


class TestWidgetPriorities:
    def test_context_percentage_highest_priority(self):
        widget = ContextPercentageWidget()
        assert widget.default_priority == 10

    def test_model_priority(self):
        widget = ModelWidget()
        assert widget.default_priority == 20

    def test_session_id_lowest_priority(self):
        from claude_code_statusline.widgets.builtin.session import SessionIdWidget

        widget = SessionIdWidget()
        assert widget.default_priority == 80

    def test_priority_ordering(self):
        from claude_code_statusline.widgets.builtin.directory import DirectoryWidget
        from claude_code_statusline.widgets.builtin.git import GitBranchWidget
        from claude_code_statusline.widgets.builtin.session import SessionIdWidget

        priorities = {
            "context": ContextPercentageWidget().default_priority,
            "model": ModelWidget().default_priority,
            "git-branch": GitBranchWidget().default_priority,
            "cost": CostWidget().default_priority,
            "directory": DirectoryWidget().default_priority,
            "session-clock": SessionClockWidget().default_priority,
            "lines-changed": LinesChangedWidget().default_priority,
            "session-id": SessionIdWidget().default_priority,
        }

        sorted_by_priority = sorted(priorities.items(), key=lambda x: x[1])
        names = [name for name, _ in sorted_by_priority]

        assert names[0] == "context"
        assert names[-1] == "session-id"
