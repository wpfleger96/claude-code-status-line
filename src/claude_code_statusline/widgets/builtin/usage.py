"""Subscription rate-limit usage widgets (5-hour and weekly windows)."""

import time

from typing import TypeGuard

from ...config.schema import WidgetConfigModel
from ...parsers.tokens import format_duration
from ...types import RenderContext
from ...utils.colors import colorize, get_usage_color
from ..base import Widget
from ..registry import register_widget

_SECONDS_PER_DAY = 86400
_MAX_RESET_SECONDS = 8 * _SECONDS_PER_DAY


def _is_number(value: object) -> TypeGuard[int | float]:
    """True for JSON numbers; excludes bools, which are ints in Python.

    Callers bound-check with comparisons only, which reject NaN/inf and never
    convert huge ints to float (that would raise OverflowError).
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
        if not (_is_number(pct) and 0 <= pct <= 100):
            return None
        rounded_pct = int(pct + 0.5)  # half-up; round() is banker's rounding

        resets_at = window.get("resets_at")
        now = time.time()
        seconds_left = None
        if _is_number(resets_at) and now < resets_at <= now + _MAX_RESET_SECONDS:
            seconds_left = int(resets_at - now)

        return colorize(f"{rounded_pct}%", get_usage_color(rounded_pct)), seconds_left

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
