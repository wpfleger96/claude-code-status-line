"""Unit tests for widget rendering."""

import pytest

from claude_code_statusline.config.schema import WidgetConfigModel
from claude_code_statusline.types import (
    GitStatus,
    RenderContext,
    SessionMetrics,
    TokenMetrics,
)
from claude_code_statusline.widgets.builtin.context import (
    ContextPercentageWidget,
    ContextTokensWidget,
)
from claude_code_statusline.widgets.builtin.cost import (
    CostWidget,
    LinesAddedWidget,
    LinesChangedWidget,
    LinesRemovedWidget,
)
from claude_code_statusline.widgets.builtin.directory import DirectoryWidget
from claude_code_statusline.widgets.builtin.git import (
    GitBranchWidget,
    GitChangesWidget,
    GitWorktreeWidget,
)
from claude_code_statusline.widgets.builtin.model import ModelWidget
from claude_code_statusline.widgets.builtin.separator import SeparatorWidget
from claude_code_statusline.widgets.builtin.session import (
    SessionClockWidget,
    SessionIdWidget,
)


@pytest.fixture
def sample_context():
    """Create a sample render context for testing."""
    return RenderContext(
        data={
            "model": {
                "id": "claude-sonnet-4-5-20250929",
                "display_name": "Sonnet 4.5",
            },
            "workspace": {"current_dir": "/Users/test/my-project"},
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
        ),
        session_metrics=SessionMetrics(
            start_time=None, last_activity=None, duration_seconds=7800
        ),
        git_status=GitStatus(
            branch="main", insertions=50, deletions=10, worktree=None, is_git_repo=True
        ),
    )


@pytest.fixture
def widget_config():
    """Create a basic widget config."""
    return WidgetConfigModel(type="test")


class TestModelWidget:
    """Tests for ModelWidget."""

    def test_renders_display_name(self, sample_context, widget_config):
        widget = ModelWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "Sonnet 4.5"

    def test_fallback_to_id(self, widget_config):
        context = RenderContext(
            data={"model": {"id": "test-model"}},
            token_metrics=None,
        )
        widget = ModelWidget()
        result = widget.render(widget_config, context)
        assert result == "test-model"

    def test_returns_none_when_no_model(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = ModelWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestDirectoryWidget:
    """Tests for DirectoryWidget."""

    def test_renders_basename(self, sample_context, widget_config):
        widget = DirectoryWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "my-project"

    def test_returns_none_when_no_directory(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = DirectoryWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestContextPercentageWidget:
    """Tests for ContextPercentageWidget."""

    def test_renders_with_progress_bar_and_tokens(self, sample_context, widget_config):
        widget = ContextPercentageWidget()
        result = widget.render(widget_config, sample_context)
        assert result is not None
        assert "Context:" in result
        assert "%" in result
        assert "●" in result or "○" in result  # Progress bar characters
        assert "/" in result  # Token count separator
        assert "K" in result  # K suffix for thousands

    def test_returns_none_without_token_metrics(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = ContextPercentageWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestContextTokensWidget:
    """Tests for ContextTokensWidget."""

    def test_renders_token_count(self, sample_context, widget_config):
        widget = ContextTokensWidget()
        result = widget.render(widget_config, sample_context)
        assert result is not None
        assert "/" in result
        assert "tokens" in result
        assert "K" in result  # Should have K suffix for thousands

    def test_returns_none_without_token_metrics(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = ContextTokensWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestCostWidget:
    """Tests for CostWidget."""

    def test_renders_cost(self, sample_context, widget_config):
        widget = CostWidget()
        result = widget.render(widget_config, sample_context)
        assert result.startswith("Cost: ")
        assert "$2.50 USD" in result

    def test_returns_none_when_no_cost(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = CostWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestLinesAddedWidget:
    """Tests for LinesAddedWidget."""

    def test_renders_lines_added(self, sample_context, widget_config):
        widget = LinesAddedWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "+150 (added)"

    def test_returns_none_when_zero(self, widget_config):
        context = RenderContext(
            data={"cost": {"total_lines_added": 0}}, token_metrics=None
        )
        widget = LinesAddedWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestLinesRemovedWidget:
    """Tests for LinesRemovedWidget."""

    def test_renders_lines_removed(self, sample_context, widget_config):
        widget = LinesRemovedWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "-45 (removed)"

    def test_returns_none_when_zero(self, widget_config):
        context = RenderContext(
            data={"cost": {"total_lines_removed": 0}}, token_metrics=None
        )
        widget = LinesRemovedWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestLinesChangedWidget:
    """Tests for LinesChangedWidget."""

    def test_renders_both_added_and_removed(self, sample_context, widget_config):
        widget = LinesChangedWidget()
        result = widget.render(widget_config, sample_context)
        assert "+150 (added)" in result
        assert "-45 (removed)" in result
        assert " / " in result

    def test_renders_only_added(self, widget_config):
        context = RenderContext(
            data={"cost": {"total_lines_added": 100, "total_lines_removed": 0}},
            token_metrics=None,
        )
        widget = LinesChangedWidget()
        result = widget.render(widget_config, context)
        assert "+100 (added)" in result
        assert "removed" not in result

    def test_renders_only_removed(self, widget_config):
        context = RenderContext(
            data={"cost": {"total_lines_added": 0, "total_lines_removed": 50}},
            token_metrics=None,
        )
        widget = LinesChangedWidget()
        result = widget.render(widget_config, context)
        assert "-50 (removed)" in result
        assert "added" not in result

    def test_returns_none_when_zero(self, widget_config):
        context = RenderContext(
            data={"cost": {"total_lines_added": 0, "total_lines_removed": 0}},
            token_metrics=None,
        )
        widget = LinesChangedWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestSessionIdWidget:
    """Tests for SessionIdWidget."""

    def test_renders_session_id(self, sample_context, widget_config):
        widget = SessionIdWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "Session: abc123-def456-789"

    def test_returns_none_when_no_session_id(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = SessionIdWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestSessionClockWidget:
    """Tests for SessionClockWidget."""

    def test_renders_duration(self, sample_context, widget_config):
        widget = SessionClockWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "Elapsed: 2hr 10m"

    def test_returns_none_without_session_metrics(self, widget_config):
        context = RenderContext(data={}, token_metrics=None, session_metrics=None)
        widget = SessionClockWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestGitBranchWidget:
    """Tests for GitBranchWidget."""

    def test_renders_branch_name(self, sample_context, widget_config):
        widget = GitBranchWidget()
        result = widget.render(widget_config, sample_context)
        assert result == "main"

    def test_returns_none_when_not_git_repo(self, widget_config):
        context = RenderContext(
            data={},
            token_metrics=None,
            git_status=GitStatus(is_git_repo=False),
        )
        widget = GitBranchWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestGitChangesWidget:
    """Tests for GitChangesWidget."""

    def test_renders_changes(self, sample_context, widget_config):
        widget = GitChangesWidget()
        result = widget.render(widget_config, sample_context)
        assert result == " +50/-10"

    def test_renders_only_insertions(self, widget_config):
        context = RenderContext(
            data={},
            token_metrics=None,
            git_status=GitStatus(
                branch="main", insertions=50, deletions=0, is_git_repo=True
            ),
        )
        widget = GitChangesWidget()
        result = widget.render(widget_config, context)
        assert result == " +50"

    def test_returns_none_when_no_changes(self, widget_config):
        context = RenderContext(
            data={},
            token_metrics=None,
            git_status=GitStatus(
                branch="main", insertions=0, deletions=0, is_git_repo=True
            ),
        )
        widget = GitChangesWidget()
        result = widget.render(widget_config, context)
        assert result is None


class TestGitWorktreeWidget:
    """Tests for GitWorktreeWidget."""

    def test_renders_worktree_name(self, widget_config):
        context = RenderContext(
            data={},
            token_metrics=None,
            git_status=GitStatus(
                branch="main", worktree="feature-branch", is_git_repo=True
            ),
        )
        widget = GitWorktreeWidget()
        result = widget.render(widget_config, context)
        assert result == " [feature-branch]"

    def test_returns_none_when_no_worktree(self, sample_context, widget_config):
        widget = GitWorktreeWidget()
        result = widget.render(widget_config, sample_context)
        assert result is None


class TestSeparatorWidget:
    """Tests for SeparatorWidget."""

    def test_renders_default_separator(self, widget_config):
        context = RenderContext(data={}, token_metrics=None)
        widget = SeparatorWidget()
        result = widget.render(widget_config, context)
        assert result == " | "

    def test_renders_custom_separator(self):
        config = WidgetConfigModel(type="separator", metadata={"text": "•"})
        context = RenderContext(data={}, token_metrics=None)
        widget = SeparatorWidget()
        result = widget.render(config, context)
        assert result == " • "
