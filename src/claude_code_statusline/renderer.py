"""Main rendering pipeline for status line."""

from typing import Optional

from .config.loader import get_effective_widgets
from .config.schema import WidgetConfigModel
from .types import RenderContext
from .utils.colors import colorize, get_cost_color, get_usage_color, visible_len
from .utils.models import get_context_limit_for_render, get_current_context_length
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
    if widget_type in ("context-percentage", "context-tokens"):
        if (
            context.context_window is not None
            and context.context_window.used_percentage is not None
        ):
            return get_usage_color(context.context_window.used_percentage)

        context_limit = get_context_limit_for_render(context)
        context_length = get_current_context_length(context)

        if context_length > 0 and context_limit > 0:
            percentage = (context_length * 100) / context_limit
            return get_usage_color(percentage)

    if widget_type == "cost":
        cost = context.data.get("cost") or {}
        total_cost = cost.get("total_cost_usd", 0)
        return get_cost_color(total_cost)

    return "white"


def _apply_color(
    content: str, widget_config: WidgetConfigModel, context: RenderContext
) -> str:
    """Apply color to rendered widget content."""
    widget = get_widget(widget_config.type)
    if not widget:
        return content

    color = widget_config.color
    if color == "auto":
        color = _resolve_auto_color(widget_config.type, context)
    elif color is None:
        color = widget.default_color
        if color == "auto":
            color = _resolve_auto_color(widget_config.type, context)

    if color == "none":
        return content

    return colorize(content, color, widget_config.bold)


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

    return _apply_color(content, widget_config, context)


def render_widget_compact(
    widget_config: WidgetConfigModel, context: RenderContext
) -> Optional[str]:
    """Render a widget in compact mode with colors applied."""
    widget = get_widget(widget_config.type)
    if not widget:
        return None

    content = widget.render_compact(widget_config, context)

    if content is None:
        if widget.fallback_text is not None:
            content = widget.fallback_text
        else:
            return None

    return _apply_color(content, widget_config, context)


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
    prev_was_separator = True

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


def _render_line(
    pairs: list[tuple[WidgetConfigModel, Optional[str]]],
) -> str:
    """Render a list of widget pairs into a single line string."""
    parts = _remove_orphaned_separators(pairs)
    return "".join(parts)


def _get_widget_priority(widget_config: WidgetConfigModel) -> int:
    """Get effective priority for a widget (config override or widget default)."""
    if widget_config.priority is not None:
        return widget_config.priority
    widget = get_widget(widget_config.type)
    if widget:
        return widget.default_priority
    return 50


def _find_split_index(
    pairs: list[tuple[WidgetConfigModel, Optional[str]]], target_width: int
) -> int:
    """Find the best index to split widget pairs into two balanced lines.

    Splits after the content widget whose cumulative visible width is
    closest to target_width. Only considers content widgets (not separators)
    as split points.
    """
    cumulative = 0
    best_idx = 0
    best_diff = float("inf")

    for i, (cfg, rendered) in enumerate(pairs):
        if rendered is None:
            continue
        cumulative += visible_len(rendered)

        if cfg.type != "separator":
            diff = abs(cumulative - target_width)
            if diff < best_diff:
                best_diff = diff
                best_idx = i + 1

    if best_idx == 0:
        best_idx = len(pairs) // 2

    return best_idx


def _try_two_line_split(
    pairs: list[tuple[WidgetConfigModel, Optional[str]]], terminal_width: int
) -> Optional[str]:
    """Try to split widget pairs into two lines that both fit."""
    total_width = sum(visible_len(r) for _, r in pairs if r is not None)
    split_idx = _find_split_index(pairs, total_width // 2)
    first_half = pairs[:split_idx]
    second_half = pairs[split_idx:]

    if not first_half or not second_half:
        return None

    line1 = _render_line(first_half)
    line2 = _render_line(second_half)

    if not line1 or not line2:
        return None

    if visible_len(line1) <= terminal_width and visible_len(line2) <= terminal_width:
        return f"{line1}\n{line2}"

    return None


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


def render_status_line_width_aware(
    widgets: list[WidgetConfigModel], context: RenderContext, terminal_width: int
) -> str:
    """Render status line with progressive degradation for narrow terminals.

    Cascade:
    1. Full render on one line
    2. Compact render on one line
    3. Compact render split across two lines
    4. Drop lowest-priority widgets until two-line fits
    """
    # Step 1: full render
    full_pairs: list[tuple[WidgetConfigModel, Optional[str]]] = [
        (cfg, render_widget(cfg, context)) for cfg in widgets
    ]
    full_line = _render_line(full_pairs)
    if visible_len(full_line) <= terminal_width:
        return full_line

    # Step 2: compact render
    compact_pairs: list[tuple[WidgetConfigModel, Optional[str]]] = [
        (cfg, render_widget_compact(cfg, context)) for cfg in widgets
    ]
    compact_line = _render_line(compact_pairs)
    if visible_len(compact_line) <= terminal_width:
        return compact_line

    # Step 3: two-line split of compact render
    two_line = _try_two_line_split(compact_pairs, terminal_width)
    if two_line is not None:
        return two_line

    # Step 4: drop lowest-priority widgets until two-line fits
    content_widgets = [cfg for cfg in widgets if cfg.type != "separator"]
    drop_order = sorted(content_widgets, key=_get_widget_priority, reverse=True)

    dropped: set[str] = set()
    for to_drop in drop_order:
        dropped.add(to_drop.id)

        remaining_pairs = [
            (cfg, render_widget_compact(cfg, context))
            for cfg in widgets
            if cfg.id not in dropped
        ]

        # Try single line first
        single = _render_line(remaining_pairs)
        if visible_len(single) <= terminal_width:
            return single

        # Try two-line split
        two_line = _try_two_line_split(remaining_pairs, terminal_width)
        if two_line is not None:
            return two_line

    # Floor: return highest-priority widget alone (best effort)
    if content_widgets:
        best = min(content_widgets, key=_get_widget_priority)
        return _render_line([(best, render_widget_compact(best, context))])
    return ""


def render_status_line_with_config(context: RenderContext) -> str:
    """Render status line using loaded configuration.

    Args:
        context: Render context with data and metrics

    Returns:
        Formatted status line string
    """
    widgets = get_effective_widgets()

    if context.terminal_width is not None and context.terminal_width > 0:
        return render_status_line_width_aware(widgets, context, context.terminal_width)

    return render_status_line(widgets, context)
