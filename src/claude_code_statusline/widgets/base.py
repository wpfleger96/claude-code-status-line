"""Base widget interface for status line components."""

from abc import ABC, abstractmethod
from typing import Optional

from ..config.schema import WidgetConfigModel
from ..types import RenderContext


class Widget(ABC):
    """Base widget interface - all widgets must implement this.

    Widget metadata (display_name, description, default_color) is set by the
    @register_widget decorator rather than requiring implementation of methods.
    """

    # Class attributes set by @register_widget decorator
    display_name: str = ""
    description: str = ""
    default_color: str = "white"
    fallback_text: Optional[str] = None

    @abstractmethod
    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render widget content.

        Args:
            config: Widget configuration including colors and metadata
            context: Rendering context with data and metrics

        Returns:
            Rendered string or None to hide widget
        """
        pass
