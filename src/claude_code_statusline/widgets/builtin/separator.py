"""Separator widget for visual division."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "separator",
    display_name="Separator",
    default_color="dim",
    description="Visual divider between widgets",
)
class SeparatorWidget(Widget):
    """Visual separator between widgets."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render separator from config or default."""
        # Get separator from metadata or use default
        separator = config.metadata.get("text", "|")
        return f" {separator} "
