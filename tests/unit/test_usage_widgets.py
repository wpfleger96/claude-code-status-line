"""Unit tests for subscription rate-limit usage widgets."""

import re

from typing import Any

import pytest

from claude_code_statusline.config.schema import WidgetConfigModel
from claude_code_statusline.types import RenderContext
from claude_code_statusline.utils.colors import COLORS
from claude_code_statusline.widgets.base import Widget
from claude_code_statusline.widgets.builtin.usage import (
    FiveHourUsageWidget,
    WeeklyUsageWidget,
)

NOW = 1_700_000_000
ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_SGR.sub("", text)


@pytest.fixture(autouse=True)
def frozen_time(monkeypatch):
    monkeypatch.setattr(
        "claude_code_statusline.widgets.builtin.usage.time.time", lambda: float(NOW)
    )


@pytest.fixture
def widget_config():
    return WidgetConfigModel(type="test")


def make_context(rate_limits: Any = None) -> RenderContext:
    data = {} if rate_limits is None else {"rate_limits": rate_limits}
    return RenderContext(data=data)


def render_plain(
    widget: Widget, config: WidgetConfigModel, context: RenderContext
) -> str | None:
    rendered = widget.render(config, context)
    return None if rendered is None else strip_ansi(rendered)


@pytest.mark.unit
class TestMissingData:
    @pytest.mark.parametrize("widget", [FiveHourUsageWidget(), WeeklyUsageWidget()])
    def test_no_rate_limits_key_returns_none(self, widget, widget_config):
        context = make_context()

        assert widget.render(widget_config, context) is None
        assert widget.render_compact(widget_config, context) is None

    def test_only_five_hour_present_renders_5h_only(self, widget_config):
        context = make_context({"five_hour": {"used_percentage": 23.5}})

        five_hour = render_plain(FiveHourUsageWidget(), widget_config, context)
        weekly = WeeklyUsageWidget().render(widget_config, context)

        assert five_hour == "5h: 24%"
        assert weekly is None

    @pytest.mark.parametrize("bad_pct", ["23.5", None, True, float("nan")])
    def test_invalid_used_percentage_returns_none(self, bad_pct, widget_config):
        context = make_context({"five_hour": {"used_percentage": bad_pct}})
        widget = FiveHourUsageWidget()

        assert widget.render(widget_config, context) is None
        assert widget.render_compact(widget_config, context) is None

    @pytest.mark.parametrize("rate_limits", ["oops", {"five_hour": "oops"}])
    def test_malformed_rate_limits_returns_none(self, rate_limits, widget_config):
        context = make_context(rate_limits)

        assert FiveHourUsageWidget().render(widget_config, context) is None


@pytest.mark.unit
class TestResetCountdown:
    def test_reset_in_past_omits_suffix(self, widget_config):
        context = make_context(
            {"five_hour": {"used_percentage": 40, "resets_at": NOW - 10}}
        )

        assert render_plain(FiveHourUsageWidget(), widget_config, context) == "5h: 40%"

    @pytest.mark.parametrize("resets_at", [None, "soon", 1.5e9, True])
    def test_missing_or_invalid_resets_at_omits_suffix(self, resets_at, widget_config):
        window = {"used_percentage": 40}
        if resets_at is not None:
            window["resets_at"] = resets_at
        context = make_context({"five_hour": window})

        assert render_plain(FiveHourUsageWidget(), widget_config, context) == "5h: 40%"

    def test_reset_under_a_day_uses_hours_and_minutes(self, widget_config):
        context = make_context(
            {
                "five_hour": {
                    "used_percentage": 24,
                    "resets_at": NOW + 2 * 3600 + 14 * 60,
                }
            }
        )

        rendered = render_plain(FiveHourUsageWidget(), widget_config, context)

        assert rendered == "5h: 24% (resets in 2hr 14m)"

    def test_reset_over_a_day_uses_days_and_hours(self, widget_config):
        context = make_context(
            {
                "seven_day": {
                    "used_percentage": 41.2,
                    "resets_at": NOW + 4 * 86400 + 3 * 3600 + 59,
                }
            }
        )

        rendered = render_plain(WeeklyUsageWidget(), widget_config, context)

        assert rendered == "7d: 41% (resets in 4d 3hr)"

    def test_reset_whole_days_omits_hours(self, widget_config):
        context = make_context(
            {"seven_day": {"used_percentage": 41, "resets_at": NOW + 4 * 86400 + 120}}
        )

        rendered = render_plain(WeeklyUsageWidget(), widget_config, context)

        assert rendered == "7d: 41% (resets in 4d)"

    def test_compact_omits_reset_info(self, widget_config):
        context = make_context(
            {"five_hour": {"used_percentage": 23.5, "resets_at": NOW + 8000}}
        )

        compact = FiveHourUsageWidget().render_compact(widget_config, context)

        assert compact is not None
        assert strip_ansi(compact) == "5h 24%"


@pytest.mark.unit
class TestColor:
    def test_high_usage_colors_only_percentage_red(self, widget_config):
        context = make_context(
            {"five_hour": {"used_percentage": 90, "resets_at": NOW + 600}}
        )

        rendered = FiveHourUsageWidget().render(widget_config, context)

        assert rendered is not None
        assert f"{COLORS['red']}90%{COLORS['reset']}" in rendered
        assert rendered.startswith("5h: ")

    def test_low_usage_colors_percentage_green(self, widget_config):
        context = make_context({"seven_day": {"used_percentage": 10}})

        rendered = WeeklyUsageWidget().render_compact(widget_config, context)

        assert rendered == f"7d {COLORS['green']}10%{COLORS['reset']}"
