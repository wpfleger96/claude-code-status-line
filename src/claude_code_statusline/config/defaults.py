"""Default configuration for Claude Code Status Line."""

from .schema import WidgetConfigModel


def get_default_widgets() -> list[WidgetConfigModel]:
    """Return the default ordered widget list (separators excluded)."""
    return [
        WidgetConfigModel(type="model", color="cyan"),
        WidgetConfigModel(type="directory", color="blue"),
        WidgetConfigModel(type="git-branch", color="magenta"),
        WidgetConfigModel(type="context-percentage"),
        WidgetConfigModel(type="cost"),
        WidgetConfigModel(type="lines-changed"),
        WidgetConfigModel(type="session-id"),
        WidgetConfigModel(type="session-clock"),
    ]
