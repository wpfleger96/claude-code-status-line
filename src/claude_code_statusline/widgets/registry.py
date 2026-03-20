"""Widget registry for managing available widgets."""

from typing import Callable, Optional

from .base import Widget

_WIDGET_REGISTRY: dict[str, Widget] = {}


def register_widget(
    widget_type: str,
    display_name: str = "",
    default_color: str = "white",
    default_priority: int = 50,
    description: str = "",
    fallback_text: Optional[str] = None,
) -> Callable[[type[Widget]], type[Widget]]:
    """Decorator to register widget classes with metadata.

    Usage:
        @register_widget("model", display_name="Model", default_color="cyan",
                         default_priority=20,
                         description="Claude model name", fallback_text="Unknown model")
        class ModelWidget(Widget):
            def render(self, config, context):
                ...

    Args:
        widget_type: Widget type identifier (e.g., "model", "git-branch")
        display_name: Human-readable name for TUI (defaults to formatted type)
        default_color: Default color when not in config (defaults to "white")
        default_priority: Drop priority (higher = dropped first, defaults to 50)
        description: Description of what the widget displays
        fallback_text: Text to display when widget renders None (defaults to None - hide widget)
    """

    def decorator(cls: type[Widget]) -> type[Widget]:
        cls.display_name = display_name or widget_type.replace("-", " ").title()
        cls.default_color = default_color
        cls.default_priority = default_priority
        cls.description = description
        cls.fallback_text = fallback_text

        _WIDGET_REGISTRY[widget_type] = cls()
        return cls

    return decorator


def get_widget(widget_type: str) -> Optional[Widget]:
    """Get widget instance by type name.

    Args:
        widget_type: Widget type identifier

    Returns:
        Widget instance or None if not found
    """
    return _WIDGET_REGISTRY.get(widget_type)


def get_all_widgets() -> dict[str, Widget]:
    """Get all registered widgets as instances.

    Returns:
        Dictionary mapping widget type to instance
    """
    return dict(_WIDGET_REGISTRY)
