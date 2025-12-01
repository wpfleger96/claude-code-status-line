"""Configuration file loading and saving."""

import os

from pathlib import Path

import yaml

from pydantic import ValidationError

from .defaults import get_default_config
from .schema import StatusLineConfig


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

    # Extract non-separator widget types from defaults
    default_types = {
        w.type for line in default_config.lines for w in line if w.type != "separator"
    }

    # Extract non-separator widget types from user config
    user_types = {
        w.type for line in config.lines for w in line if w.type != "separator"
    }

    return sorted(default_types - user_types)


def load_config() -> StatusLineConfig:
    """
    Load configuration from YAML file.

    If config file doesn't exist, creates it with defaults.
    If config is invalid, falls back to defaults and logs error.
    """
    config_path = get_config_path()

    # If config doesn't exist, create it with defaults
    if not config_path.exists():
        config = get_default_config()
        save_config(config)
        return config

    # Load existing config
    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if config_data is None:
            config_data = {}

        config = StatusLineConfig(**config_data)

        # Check for missing widgets and warn user
        missing = get_missing_widgets(config)
        if missing:
            import sys

            print(
                f"Warning: Config is missing widgets from defaults: {', '.join(missing)}. "
                f"Delete {config_path} to regenerate with new defaults.",
                file=sys.stderr,
            )

        return config

    except (yaml.YAMLError, ValidationError, OSError) as e:
        # Log error and fall back to defaults
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

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Convert config to dict and save as YAML
    config_dict = config.model_dump(mode="python")

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
