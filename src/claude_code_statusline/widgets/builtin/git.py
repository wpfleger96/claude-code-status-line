"""Git-related widgets."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ...utils.git import get_git_status
from ..base import Widget
from ..registry import register_widget


def _get_or_fetch_git_status(context: RenderContext) -> None:
    """Get git status from context or fetch it."""
    if context.git_status is not None:
        return

    # Get working directory
    workspace = context.data.get("workspace", {})
    cwd = workspace.get("current_dir")

    if cwd:
        context.git_status = get_git_status(cwd)


@register_widget(
    "git-branch",
    display_name="Git Branch",
    default_color="magenta",
    description="Current git branch name",
    fallback_text="No repo",
)
class GitBranchWidget(Widget):
    """Display current git branch name."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render git branch name."""
        _get_or_fetch_git_status(context)

        if not context.git_status or not context.git_status.is_git_repo:
            return None

        if not context.git_status.branch:
            return None

        return f"{context.git_status.branch}"


@register_widget(
    "git-changes",
    display_name="Git Changes",
    default_color="yellow",
    description="Uncommitted insertions and deletions",
)
class GitChangesWidget(Widget):
    """Display git insertions and deletions."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render git changes (+insertions/-deletions)."""
        _get_or_fetch_git_status(context)

        if not context.git_status or not context.git_status.is_git_repo:
            return None

        insertions = context.git_status.insertions
        deletions = context.git_status.deletions

        if insertions == 0 and deletions == 0:
            return None

        parts = []
        if insertions > 0:
            parts.append(f"+{insertions}")
        if deletions > 0:
            parts.append(f"-{deletions}")

        return " " + "/".join(parts)


@register_widget(
    "git-worktree",
    display_name="Git Worktree",
    default_color="blue",
    description="Current git worktree name",
)
class GitWorktreeWidget(Widget):
    """Display git worktree name."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render git worktree name."""
        _get_or_fetch_git_status(context)

        if not context.git_status or not context.git_status.is_git_repo:
            return None

        if not context.git_status.worktree:
            return None

        return f" [{context.git_status.worktree}]"
