"""Context usage widgets."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ...utils.colors import colorize, get_usage_color
from ...utils.formatting import format_number, format_percentage, render_progress_bar
from ...utils.models import get_context_limit_for_render
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "context-percentage",
    display_name="Context Percentage",
    default_color="none",
    description="Context usage percentage with progress bar and token count",
    fallback_text="No active transcript",
)
class ContextPercentageWidget(Widget):
    """Display context usage percentage with progress bar and token count."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render context percentage with progress bar and token count."""
        if not context.token_metrics or not context.token_metrics.transcript_exists:
            return None

        context_limit = get_context_limit_for_render(context)
        context_length = context.token_metrics.context_length

        if context_limit == 0:
            return None

        percentage = round((context_length * 100) / context_limit, 1)
        progress_bar = render_progress_bar(percentage)

        # Format token counts
        current = format_number(context_length)
        limit = format_number(context_limit)

        # Apply usage-based color ONLY to the progress bar
        usage_color = get_usage_color(percentage)
        colored_bar = colorize(progress_bar, usage_color)

        return f"Context: {colored_bar} {format_percentage(percentage)} ({current}/{limit})"


@register_widget(
    "context-tokens",
    display_name="Token Count",
    default_color="auto",
    description="Current/limit token count (e.g., 120K/200K)",
    fallback_text="No active transcript",
)
class ContextTokensWidget(Widget):
    """Display token count (current/limit)."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render token count display."""
        if not context.token_metrics or not context.token_metrics.transcript_exists:
            return None

        context_limit = get_context_limit_for_render(context)
        context_length = context.token_metrics.context_length

        current = format_number(context_length)
        limit = format_number(context_limit)

        return f"{current}/{limit} tokens"
