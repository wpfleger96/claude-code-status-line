"""Session-related widgets."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...parsers.tokens import format_duration
from ...types import RenderContext
from ...utils.colors import colorize
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "session-id",
    display_name="Session ID",
    default_color="none",
    default_priority=80,
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

        colored_id = colorize(session_id, "grey")
        return f"Session: {colored_id}"


@register_widget(
    "session-clock",
    display_name="Session Clock",
    default_color="none",
    default_priority=60,
    description="Elapsed session time (e.g., 2hr 15m)",
)
class SessionClockWidget(Widget):
    """Display session elapsed time."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render session duration."""
        if context.duration_seconds is None:
            return None

        duration = format_duration(context.duration_seconds)
        colored_duration = colorize(duration, "cyan")
        return f"Elapsed: {colored_duration}"

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: duration with color, no label."""
        if context.duration_seconds is None:
            return None

        duration = format_duration(context.duration_seconds)
        return colorize(duration, "cyan")


MAX_SESSION_NAME_LENGTH = 30


@register_widget(
    "session-name",
    display_name="Session Name",
    default_color="cyan",
    default_priority=82,
    description="Custom session name (set via --name or /rename)",
)
class SessionNameWidget(Widget):
    """Display custom session name."""

    def _get_name(self, context: RenderContext) -> Optional[str]:
        name: str | None = context.data.get("session_name")
        if not name:
            return None
        if len(name) > MAX_SESSION_NAME_LENGTH:
            return name[: MAX_SESSION_NAME_LENGTH - 1] + "\u2026"
        return name

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render session name."""
        name = self._get_name(context)
        if name is None:
            return None
        return f"Session: {name}"

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: just the name, no label."""
        return self._get_name(context)
