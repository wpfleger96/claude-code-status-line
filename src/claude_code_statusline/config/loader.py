"""Configuration file loading and saving."""

import os

from pathlib import Path
from typing import Optional

import yaml

from pydantic import ValidationError

from .defaults import get_default_config
from .schema import StatusLineConfig

# Module-level cache for config
_cached_config: Optional[StatusLineConfig] = None
_cached_mtime: float = 0.0


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_home = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_home) / "claude-statusline"


def get_config_path() -> Path:
    """Get the full configuration file path."""
    return get_config_dir() / "config.yaml"


def merge_missing_widgets(config: StatusLineConfig) -> StatusLineConfig:
    """Merge new widgets from defaults into user config at matching positions.

    For each missing widget, find its position in defaults relative to
    neighboring widgets, then insert at the same relative position in user config.
    """
    from .schema import WidgetConfigModel

    default_config = get_default_config()

    user_types = {
        w.type for line in config.lines for w in line if w.type != "separator"
    }

    for line_idx, default_line in enumerate(default_config.lines):
        if line_idx >= len(config.lines):
            continue

        user_line = config.lines[line_idx]

        for widget_idx, widget in enumerate(default_line):
            if widget.type == "separator" or widget.type in user_types:
                continue

            prev_widget_type = None
            for i in range(widget_idx - 1, -1, -1):
                if default_line[i].type != "separator":
                    prev_widget_type = default_line[i].type
                    break

            insert_pos = 0
            if prev_widget_type:
                for i, w in enumerate(user_line):
                    if w.type == prev_widget_type:
                        insert_pos = i + 1
                        if (
                            insert_pos < len(user_line)
                            and user_line[insert_pos].type == "separator"
                        ):
                            insert_pos += 1
                        break

            # Only insert separator if there isn't one already at insert_pos - 1
            if insert_pos > 0 and user_line[insert_pos - 1].type != "separator":
                user_line.insert(insert_pos, WidgetConfigModel(type="separator"))
                insert_pos += 1

            user_line.insert(insert_pos, widget)
            user_types.add(widget.type)

    return config


def load_config() -> StatusLineConfig:
    """
    Load configuration from YAML file with mtime-based caching.

    If config file doesn't exist, creates it with defaults.
    If config is invalid, falls back to defaults and logs error.
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
        config = get_default_config()
        save_config(config)
        _cached_config = config
        try:
            _cached_mtime = config_path.stat().st_mtime
        except OSError:
            _cached_mtime = 0.0
        return config

    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            config_data = {}

        config = StatusLineConfig(**config_data)

        config = merge_missing_widgets(config)
        save_config(config)

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
        return get_default_config()


def save_config(config: StatusLineConfig) -> None:
    """Save configuration to YAML file."""
    config_path = get_config_path()
    config_dir = config_path.parent

    config_dir.mkdir(parents=True, exist_ok=True)

    config_dict = config.model_dump(mode="python")

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
