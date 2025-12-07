"""Default configuration for Claude Code Status Line."""

from .schema import StatusLineConfig, WidgetConfigModel


def get_default_config() -> StatusLineConfig:
    """Generate the default status line configuration."""
    return StatusLineConfig(
        version=1,
        lines=[
            [
                WidgetConfigModel(type="model", color="cyan"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="directory", color="blue"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="git-branch", color="magenta"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="context-percentage"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="cost"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="lines-changed"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="session-id"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="session-clock"),
                WidgetConfigModel(type="separator"),
                WidgetConfigModel(type="subscription", color="cyan"),
            ]
        ],
    )
