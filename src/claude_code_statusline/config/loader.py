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


def get_missing_widgets(config: StatusLineConfig) -> list[str]:
    """Return widget types in defaults but missing from user config."""
    default_config = get_default_config()

    default_types = {
        w.type for line in default_config.lines for w in line if w.type != "separator"
    }

    user_types = {
        w.type for line in config.lines for w in line if w.type != "separator"
    }

    return sorted(default_types - user_types)


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

        missing = get_missing_widgets(config)
        if missing:
            import sys

            print(
                f"Warning: Config is missing widgets from defaults: {', '.join(missing)}. "
                f"Delete {config_path} to regenerate with new defaults.",
                file=sys.stderr,
            )

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
