"""A broken widget must not prevent other widgets from rendering."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from claude_code_statusline import renderer
from claude_code_statusline.config.schema import WidgetConfigModel
from claude_code_statusline.types import RenderContext


@pytest.mark.unit
@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("fallback", [None, "unavailable"])
def test_widget_exception_uses_fallback(monkeypatch, compact, fallback):
    widget = SimpleNamespace(
        render=Mock(side_effect=ZeroDivisionError("invalid duration")),
        render_compact=Mock(side_effect=ZeroDivisionError("invalid duration")),
        fallback_text=fallback,
    )
    monkeypatch.setattr(renderer, "get_widget", lambda name: widget)
    log = Mock()
    monkeypatch.setattr(renderer, "debug_log", log)
    render = renderer.render_widget_compact if compact else renderer.render_widget

    result = render(
        WidgetConfigModel(type="cost", color="none"),
        RenderContext(data={"session_id": "synthetic-session"}),
    )

    assert result == fallback
    log.assert_called_once()
    assert "cost" in log.call_args.args[0]
    assert "invalid duration" in log.call_args.args[0]
    assert log.call_args.args[1] == "synthetic-session"


@pytest.mark.unit
@pytest.mark.parametrize("width", [None, 8])
def test_widget_exception_preserves_rest_of_line(monkeypatch, width):
    broken = SimpleNamespace(
        render=Mock(side_effect=ValueError("bad widget data")),
        render_compact=Mock(side_effect=ValueError("bad widget data")),
        fallback_text=None,
        default_priority=50,
    )
    healthy = SimpleNamespace(
        render=Mock(return_value="healthy"),
        render_compact=Mock(return_value="healthy"),
        default_priority=50,
    )
    widgets = {"cost": broken, "model": healthy}
    monkeypatch.setattr(renderer, "get_widget", widgets.get)
    monkeypatch.setattr(renderer, "debug_log", Mock())
    config = [WidgetConfigModel(type=name, color="none") for name in widgets]
    context = RenderContext(data={})

    if width is None:
        result = renderer.render_status_line(config, context)
    else:
        result = renderer.render_status_line_width_aware(config, context, width)

    assert result == "healthy"


@pytest.mark.unit
@pytest.mark.parametrize("compact", [False, True])
def test_process_interrupts_are_not_swallowed(monkeypatch, compact):
    widget = SimpleNamespace(
        render=Mock(side_effect=KeyboardInterrupt),
        render_compact=Mock(side_effect=KeyboardInterrupt),
    )
    monkeypatch.setattr(renderer, "get_widget", lambda name: widget)
    render = renderer.render_widget_compact if compact else renderer.render_widget
    with pytest.raises(KeyboardInterrupt):
        render(WidgetConfigModel(type="cost"), RenderContext(data={}))


@pytest.mark.unit
@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("content", [None, "rendered"])
def test_auto_color_exception_returns_uncolored_fallback(monkeypatch, compact, content):
    widget = SimpleNamespace(
        render=Mock(return_value=content),
        render_compact=Mock(return_value=content),
        fallback_text="unavailable",
    )
    monkeypatch.setattr(renderer, "get_widget", lambda name: widget)
    log = Mock()
    monkeypatch.setattr(renderer, "debug_log", log)
    render = renderer.render_widget_compact if compact else renderer.render_widget

    result = render(
        WidgetConfigModel(type="cost", color="auto"),
        RenderContext(data={"cost": "oops"}),
    )

    assert result == "unavailable"
    log.assert_called_once()
    assert "AttributeError" in log.call_args.args[0]
