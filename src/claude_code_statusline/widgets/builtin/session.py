"""Session-related widgets."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...parsers.tokens import format_duration
from ...types import RenderContext
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "session-id",
    display_name="Session ID",
    default_color="dim",
    description="Claude Code session identifier",
    fallback_text="No session",
)
class SessionIdWidget(Widget):
    """Display session ID."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render session ID."""
        session_id = context.data.get("session_id")

        if not session_id:
            return None

        return f"Session: {session_id}"


@register_widget(
    "session-clock",
    display_name="Session Clock",
    default_color="white",
    description="Elapsed session time (e.g., 2hr 15m)",
)
class SessionClockWidget(Widget):
    """Display session elapsed time."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render session duration."""
        if not context.session_metrics:
            return None

        return f"Elapsed: {format_duration(context.session_metrics.duration_seconds)}"
