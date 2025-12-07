"""Configuration file loading and saving."""

import os

from pathlib import Path
from typing import Optional

import yaml

from pydantic import ValidationError

from .defaults import get_default_config
from .schema import StatusLineConfigV2, WidgetConfigModel, WidgetOverride

_cached_config: Optional[StatusLineConfigV2] = None
_cached_mtime: float = 0.0


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_home = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_home) / "claude-statusline"


def get_config_path() -> Path:
    """Get the full configuration file path."""
    return get_config_dir() / "config.yaml"


def load_config_file() -> StatusLineConfigV2:
    """Load config file, deleting v1 configs.

    Returns:
        StatusLineConfigV2 with user overrides, or empty config if none exists
    """
    global _cached_config, _cached_mtime

    config_path = get_config_path()

    if _cached_config is not None:
        try:
            current_mtime = config_path.stat().st_mtime
            if current_mtime == _cached_mtime:
                return _cached_config
        except OSError:
            pass

    if not config_path.exists():
        config = StatusLineConfigV2()
        _cached_config = config
        _cached_mtime = 0.0
        return config

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            data = {}

        if data.get("version", 1) == 1:
            config_path.unlink()
            config = StatusLineConfigV2()
            _cached_config = config
            _cached_mtime = 0.0
            return config

        config = StatusLineConfigV2(**data)
        _cached_config = config
        try:
            _cached_mtime = config_path.stat().st_mtime
        except OSError:
            _cached_mtime = 0.0

        return config

    except (yaml.YAMLError, ValidationError, OSError) as e:
        import sys

        print(
            f"Warning: Failed to load config from {config_path}: {e}",
            file=sys.stderr,
        )
        print("Using default configuration.", file=sys.stderr)
        return StatusLineConfigV2()


def get_effective_widgets() -> list[WidgetConfigModel]:
    """Get final widget list with overrides applied.

    Returns:
        List of widgets with separators interleaved, ready for rendering
    """
    config = load_config_file()
    defaults = get_default_config()

    if config.order:
        widget_types = config.order
    else:
        widget_types = [w.type for w in defaults.lines[0] if w.type != "separator"]

    widgets = []
    for wtype in widget_types:
        override = config.widgets.get(wtype, WidgetOverride())
        if not override.enabled:
            continue

        default = next((w for w in defaults.lines[0] if w.type == wtype), None)
        if default:
            widget = default.model_copy()
            if override.color:
                widget.color = override.color
            if override.bold is not None:
                widget.bold = override.bold
            widgets.append(widget)

    result = []
    for i, w in enumerate(widgets):
        if i > 0:
            result.append(WidgetConfigModel(type="separator"))
        result.append(w)

    return result


def save_config(config: StatusLineConfigV2) -> None:
    """Save configuration to YAML file."""
    config_path = get_config_path()
    config_dir = config_path.parent

    config_dir.mkdir(parents=True, exist_ok=True)

    config_dict = config.model_dump(mode="python")

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
