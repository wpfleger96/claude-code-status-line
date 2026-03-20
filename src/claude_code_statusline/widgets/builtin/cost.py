"""Cost and line change widgets."""

from typing import Optional

from ...config.schema import WidgetConfigModel
from ...types import RenderContext
from ...utils.colors import colorize, get_cost_color
from ..base import Widget
from ..registry import register_widget


@register_widget(
    "cost",
    display_name="Cost",
    default_color="none",
    default_priority=40,
    description="Session cost in USD",
    fallback_text="Cost: Not Found",
)
class CostWidget(Widget):
    """Display session cost in USD."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render cost in USD."""
        cost = context.data.get("cost", {})
        total_cost = cost.get("total_cost_usd")

        if total_cost is None:
            return None

        cost_color = get_cost_color(total_cost)
        colored_amount = colorize(f"${total_cost:.2f} USD", cost_color)

        return f"Cost: {colored_amount}"

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: just the dollar amount with color, no label."""
        cost = context.data.get("cost", {})
        total_cost = cost.get("total_cost_usd")

        if total_cost is None:
            return None

        cost_color = get_cost_color(total_cost)
        return colorize(f"${total_cost:.2f}", cost_color)


@register_widget(
    "lines-added",
    display_name="Lines Added",
    default_color="green",
    default_priority=75,
    description="Number of lines added in session",
)
class LinesAddedWidget(Widget):
    """Display lines added."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render lines added."""
        cost = context.data.get("cost", {})
        lines_added = cost.get("total_lines_added")

        if not lines_added or lines_added == 0:
            return None

        return f"+{lines_added} (added)"

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: just +N, no label."""
        cost = context.data.get("cost", {})
        lines_added = cost.get("total_lines_added")

        if not lines_added or lines_added == 0:
            return None

        return f"+{lines_added}"


@register_widget(
    "lines-removed",
    display_name="Lines Removed",
    default_color="red",
    default_priority=75,
    description="Number of lines removed in session",
)
class LinesRemovedWidget(Widget):
    """Display lines removed."""

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render lines removed."""
        cost = context.data.get("cost", {})
        lines_removed = cost.get("total_lines_removed")

        if not lines_removed or lines_removed == 0:
            return None

        return f"-{lines_removed} (removed)"

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: just -N, no label."""
        cost = context.data.get("cost", {})
        lines_removed = cost.get("total_lines_removed")

        if not lines_removed or lines_removed == 0:
            return None

        return f"-{lines_removed}"


@register_widget(
    "lines-changed",
    display_name="Lines Changed",
    default_color="none",
    default_priority=70,
    description="Lines added and removed in session (+X (added)/-Y (removed))",
)
class LinesChangedWidget(Widget):
    """Display lines added and removed in a single widget."""

    def _get_lines(self, context: RenderContext) -> tuple[int, int]:
        cost = context.data.get("cost", {})
        return cost.get("total_lines_added", 0), cost.get("total_lines_removed", 0)

    def render(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Render lines changed."""
        lines_added, lines_removed = self._get_lines(context)

        if lines_added == 0 and lines_removed == 0:
            return None

        parts = []
        if lines_added > 0:
            parts.append(colorize(f"+{lines_added} (added)", "green"))
        if lines_removed > 0:
            parts.append(colorize(f"-{lines_removed} (removed)", "red"))

        if not parts:
            return None

        return " / ".join(parts)

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> Optional[str]:
        """Compact: +N/-M with colors, no labels."""
        lines_added, lines_removed = self._get_lines(context)

        if lines_added == 0 and lines_removed == 0:
            return None

        parts = []
        if lines_added > 0:
            parts.append(colorize(f"+{lines_added}", "green"))
        if lines_removed > 0:
            parts.append(colorize(f"-{lines_removed}", "red"))

        if not parts:
            return None

        return "/".join(parts)
