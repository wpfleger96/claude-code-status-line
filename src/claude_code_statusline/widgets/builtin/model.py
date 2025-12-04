"""Model name widget."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "model",
    display_name="Model",
    default_color="cyan",
    description="Claude model name (e.g., Sonnet 4.5)",
    fallback_text="Unknown model",
)
class ModelWidget(Widget):
    """Display Claude model name."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render model display name."""
        model = context.data.get("model", {})
        display_name: str | None = model.get("display_name") or model.get("id")

        if not display_name:
            return None

        return display_name
