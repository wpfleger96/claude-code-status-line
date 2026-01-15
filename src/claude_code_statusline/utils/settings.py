"""Utilities for managing Claude Code settings.json file."""

import json
import shutil
import time

from pathlib import Path
from typing import Any, Optional

__all__ = [
    "get_settings_path",
    "read_settings",
    "write_settings",
    "configure_statusline",
    "remove_statusline",
]


def get_settings_path() -> Path:
    """Get path to Claude Code settings file.

    Returns:
        Path to ~/.claude/settings.json
    """
    return Path.home() / ".claude" / "settings.json"


def read_settings() -> dict[str, Any]:
    """Read Claude Code settings.

    Returns:
        Dictionary with settings, or empty dict if file doesn't exist
    """
    settings_path = get_settings_path()

    if not settings_path.exists():
        return {}

    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_settings(data: dict[str, Any], backup: bool = True) -> Optional[Path]:
    """Write Claude Code settings.

    Args:
        data: Settings dictionary to write
        backup: If True, create timestamped backup before writing

    Returns:
        Path to backup file if created, None otherwise

    Raises:
        OSError: If file operations fail
    """
    settings_path = get_settings_path()
    settings_dir = settings_path.parent

    settings_dir.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if backup and settings_path.exists():
        timestamp = int(time.time())
        backup_path = settings_path.parent / f"settings.json.backup.{timestamp}"
        shutil.copy2(settings_path, backup_path)

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    return backup_path


def configure_statusline() -> tuple[bool, str]:
    """Configure Claude Code to use claude-statusline.

    Adds or updates the statusLine configuration in settings.json.
    Creates a backup if statusLine already exists.

    Returns:
        Tuple of (success: bool, message: str)
    """
    settings = read_settings()

    had_existing = "statusLine" in settings

    settings["statusLine"] = {
        "type": "command",
        "command": "claude-statusline",
        "padding": 0,
    }

    try:
        backup_path = write_settings(settings, backup=had_existing)
    except OSError as e:
        return False, f"Failed to write settings: {e}"

    if had_existing and backup_path:
        return True, f"Existing statusLine configuration backed up to {backup_path}"

    return True, "Claude Code configured successfully"


def remove_statusline() -> tuple[bool, str]:
    """Remove statusLine configuration from Claude Code settings.

    Creates a backup before modification.

    Returns:
        Tuple of (success: bool, message: str)
    """
    settings = read_settings()

    if "statusLine" not in settings:
        return True, "No statusLine configuration found"

    del settings["statusLine"]

    try:
        write_settings(settings, backup=True)
    except OSError as e:
        return False, f"Failed to write settings: {e}"

    return True, "statusLine configuration removed"
