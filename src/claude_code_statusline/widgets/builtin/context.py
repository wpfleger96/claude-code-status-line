"""Context usage widgets."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ...utils.colors import colorize, get_usage_color
from ...utils.formatting import format_number, format_percentage, render_progress_bar
from ...utils.models import get_context_limit_for_render, get_current_context_length
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "context-percentage",
    display_name="Context Percentage",
    default_color="none",
    default_priority=10,
    description="Context usage percentage with progress bar and token count",
    fallback_text="No active transcript",
)
class ContextPercentageWidget(Widget):
    """Display context usage percentage with progress bar and token count."""

    def _get_context_data(
        self, context: RenderContext
    ) -> Optional[tuple[float, str, str, int, int]]:
        """Extract context percentage, colored bar, formatted percentage, and token counts.

        Returns (percentage, colored_bar, pct_str, context_length, context_limit)
        with all values consistent — when used_percentage comes from the payload,
        context_length is derived from it so the numbers agree.
        """
        # Priority 1: pre-calculated used_percentage from payload (0-100 scale)
        if (
            context.context_window is not None
            and context.context_window.used_percentage is not None
        ):
            percentage = round(context.context_window.used_percentage, 1)
            context_limit = get_context_limit_for_render(context)
            context_length = (
                int(percentage * context_limit / 100) if context_limit > 0 else 0
            )
        else:
            # Priority 2: compute from token counts
            has_context_window = (
                context.context_window is not None
                and context.context_window.has_current_usage
            )
            has_transcript = (
                context.token_metrics is not None
                and context.token_metrics.transcript_exists
            )

            if not has_context_window and not has_transcript:
                return None

            context_limit = get_context_limit_for_render(context)
            context_length = get_current_context_length(context)

            if context_limit == 0:
                return None

            percentage = round((context_length * 100) / context_limit, 1)

        progress_bar = render_progress_bar(percentage)
        usage_color = get_usage_color(percentage)
        colored_bar = colorize(progress_bar, usage_color)

        return (
            percentage,
            colored_bar,
            format_percentage(percentage),
            context_length,
            context_limit,
        )

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render context percentage with progress bar and token count."""
        data = self._get_context_data(context)
        if data is None:
            return None

        _, colored_bar, pct_str, context_length, context_limit = data
        current = format_number(context_length)
        limit = format_number(context_limit)

        return f"Context: {colored_bar} {pct_str} ({current}/{limit})"

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: progress bar + percentage + token counts, no label."""
        data = self._get_context_data(context)
        if data is None:
            return None

        _, colored_bar, pct_str, context_length, context_limit = data
        current = format_number(context_length)
        limit = format_number(context_limit)
        return f"{colored_bar} {pct_str} ({current}/{limit})"


@register_widget(
    "context-tokens",
    display_name="Token Count",
    default_color="auto",
    default_priority=15,
    description="Current/limit token count (e.g., 120K/200K)",
    fallback_text="No active transcript",
)
class ContextTokensWidget(Widget):
    """Display token count (current/limit)."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render token count display."""
        has_context_window = (
            context.context_window is not None
            and context.context_window.has_current_usage
        )
        has_transcript = (
            context.token_metrics is not None
            and context.token_metrics.transcript_exists
        )

        if not has_context_window and not has_transcript:
            return None

        context_limit = get_context_limit_for_render(context)
        context_length = get_current_context_length(context)

        current = format_number(context_length)
        limit = format_number(context_limit)

        return f"{current}/{limit} tokens"
