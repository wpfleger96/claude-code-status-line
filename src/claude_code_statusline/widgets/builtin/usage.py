"""Subscription rate-limit usage widgets (5-hour and weekly windows)."""

import math
import time

from ...config.schema import WidgetConfigModel
from ...parsers.tokens import format_duration
from ...types import RenderContext
from ...utils.colors import colorize, get_usage_color
from ..base import Widget
from ..registry import register_widget

_SECONDS_PER_DAY = 86400


def _format_countdown(seconds: int) -> str:
    """Format seconds until reset: hr/m under a day, days + hours beyond."""
    if seconds < _SECONDS_PER_DAY:
        return format_duration(seconds)
    days, remainder = divmod(seconds, _SECONDS_PER_DAY)
    hours = remainder // 3600
    return f"{days}d {hours}hr" if hours else f"{days}d"


class _RateLimitWidget(Widget):
    """Shared rendering for one `rate_limits` window from the stdin payload."""

    window_key: str
    label: str

    def _read_window(self, context: RenderContext) -> tuple[str, int | None] | None:
        """Return (colored percentage, seconds until reset) or None if unavailable."""
        rate_limits = context.data.get("rate_limits")
        window = (
            rate_limits.get(self.window_key) if isinstance(rate_limits, dict) else None
        )
        if not isinstance(window, dict):
            return None

        pct = window.get("used_percentage")
        if (
            isinstance(pct, bool)
            or not isinstance(pct, (int, float))
            or not math.isfinite(pct)
        ):
            return None

        resets_at = window.get("resets_at")
        seconds_left = None
        if isinstance(resets_at, int) and not isinstance(resets_at, bool):
            seconds_left = resets_at - int(time.time())
            if seconds_left <= 0:
                seconds_left = None

        return colorize(f"{pct:.0f}%", get_usage_color(pct)), seconds_left

    def render(self, config: WidgetConfigModel, context: RenderContext) -> str | None:
        """Render usage with reset countdown, e.g. `5h: 24% (resets in 2hr 14m)`."""
        window = self._read_window(context)
        if window is None:
            return None

        colored_pct, seconds_left = window
        if seconds_left is None:
            return f"{self.label}: {colored_pct}"
        return (
            f"{self.label}: {colored_pct} (resets in {_format_countdown(seconds_left)})"
        )

    def render_compact(
        self, config: WidgetConfigModel, context: RenderContext
    ) -> str | None:
        """Compact: label and percentage only, e.g. `5h 24%`."""
        window = self._read_window(context)
        if window is None:
            return None
        return f"{self.label} {window[0]}"


@register_widget(
    "usage-5h",
    display_name="5-Hour Usage",
    default_color="none",
    default_priority=35,
    description="Subscription 5-hour rate-limit usage with reset countdown",
)
class FiveHourUsageWidget(_RateLimitWidget):
    """Display 5-hour rate-limit window usage."""

    window_key = "five_hour"
    label = "5h"


@register_widget(
    "usage-7d",
    display_name="Weekly Usage",
    default_color="none",
    default_priority=45,
    description="Subscription weekly rate-limit usage with reset countdown",
)
class WeeklyUsageWidget(_RateLimitWidget):
    """Display 7-day rate-limit window usage."""

    window_key = "seven_day"
    label = "7d"
