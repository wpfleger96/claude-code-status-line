"""Main rendering pipeline for status line."""

from typing import Optional

from .config.loader import get_effective_widgets
from .config.schema import WidgetConfigModel
from .types import RenderContext
from .utils.colors import colorize, get_cost_color, get_usage_color
from .utils.models import get_context_limit_for_render
from .widgets import builtin  # noqa: F401
from .widgets.registry import get_widget


def _resolve_auto_color(widget_type: str, context: RenderContext) -> str:
    """Resolve 'auto' color based on widget type and context.

    Args:
        widget_type: Widget type identifier
        context: Render context with data

    Returns:
        Resolved color name
    """
    if widget_type == "context-percentage" or widget_type == "context-tokens":
        if context.token_metrics:
            context_limit = get_context_limit_for_render(context)

            if context.token_metrics.context_length > 0:
                percentage = (
                    context.token_metrics.context_length * 100
                ) / context_limit
                return get_usage_color(percentage)

    if widget_type == "cost":
        cost = context.data.get("cost", {})
        total_cost = cost.get("total_cost_usd", 0)
        return get_cost_color(total_cost)

    return "white"


def render_widget(
    widget_config: WidgetConfigModel, context: RenderContext
) -> Optional[str]:
    """Render a single widget with colors applied.

    Args:
        widget_config: Widget configuration
        context: Render context

    Returns:
        Rendered and colorized widget string, or None to skip
    """
    widget = get_widget(widget_config.type)
    if not widget:
        return None

    content = widget.render(widget_config, context)

    if content is None:
        if widget.fallback_text is not None:
            content = widget.fallback_text
        else:
            return None

    color = widget_config.color
    if color == "auto":
        color = _resolve_auto_color(widget_config.type, context)
    elif color is None:
        color = widget.default_color
        if color == "auto":
            color = _resolve_auto_color(widget_config.type, context)

    # "none" color means widget handles its own coloring
    if color == "none":
        return content

    return colorize(content, color, widget_config.bold)


def _remove_orphaned_separators(
    pairs: list[tuple[WidgetConfigModel, Optional[str]]],
) -> list[str]:
    """Remove separators that have no adjacent content.

    A separator is orphaned if:
    - It's at the start (nothing visible before it)
    - It's at the end (nothing visible after it)
    - It's adjacent to another separator (no content between)

    Args:
        pairs: List of (widget_config, rendered_string) tuples

    Returns:
        List of rendered strings with orphaned separators removed
    """
    rendered = [(cfg, s) for cfg, s in pairs if s is not None]

    result = []
    prev_was_separator = True  # Treat start as separator to skip leading separators

    for cfg, content in rendered:
        is_separator = cfg.type == "separator"

        if is_separator:
            if not prev_was_separator:
                result.append((cfg, content))
            prev_was_separator = True
        else:
            result.append((cfg, content))
            prev_was_separator = False

    if result and result[-1][0].type == "separator":
        result.pop()

    return [content for _, content in result]


def render_status_line(widgets: list[WidgetConfigModel], context: RenderContext) -> str:
    """Render complete status line from widget list.

    Args:
        widgets: List of widget configurations (with separators)
        context: Render context with data and metrics

    Returns:
        Formatted status line string with ANSI colors
    """
    if not widgets:
        return ""

    rendered_pairs = []
    for widget_config in widgets:
        widget_str = render_widget(widget_config, context)
        rendered_pairs.append((widget_config, widget_str))

    final_widgets = _remove_orphaned_separators(rendered_pairs)

    if not final_widgets:
        return ""

    return "".join(final_widgets)


def render_status_line_with_config(context: RenderContext) -> str:
    """Render status line using loaded configuration.

    Args:
        context: Render context with data and metrics

    Returns:
        Formatted status line string
    """
    widgets = get_effective_widgets()
    return render_status_line(widgets, context)
