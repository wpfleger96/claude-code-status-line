"""Directory widget."""

import os

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ..base import Widget
from ..registry import register_widget
from .git import _get_or_fetch_git_status


@register_widget(
    "directory",
    display_name="Directory",
    default_color="blue",
    description="Current working directory name",
    fallback_text="--",
)
class DirectoryWidget(Widget):
    """Display current working directory basename."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render directory basename."""
        workspace = context.data.get("workspace", {})
        current_dir: str | None = workspace.get("current_dir")

        if not current_dir:
            return None

        _get_or_fetch_git_status(context)

        if (
            context.git_status
            and context.git_status.is_git_repo
            and context.git_status.repo_name
        ):
            return context.git_status.repo_name

        return str(os.path.basename(current_dir))
