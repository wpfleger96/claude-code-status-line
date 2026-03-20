"""Terminal width detection for piped subprocess environments."""

import os
import sys

from typing import Optional


def _get_width_from_stderr() -> Optional[int]:
    """Try to get terminal width from stderr fd."""
    try:
        width = os.get_terminal_size(sys.stderr.fileno()).columns
        if width > 0:
            return width
    except (OSError, ValueError, AttributeError):
        pass
    return None


def _get_width_from_tty() -> Optional[int]:
    """Try to get terminal width via /dev/tty ioctl."""
    try:
        import fcntl
        import struct
        import termios

        fd = os.open("/dev/tty", os.O_RDONLY | os.O_NOCTTY)
        try:
            result = fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8)
            width: int = struct.unpack("HHHH", result)[1]
            if width > 0:
                return width
        finally:
            os.close(fd)
    except (OSError, ImportError):
        pass
    return None


def _get_width_from_env() -> Optional[int]:
    """Try to get terminal width from COLUMNS env var."""
    columns = os.environ.get("COLUMNS")
    if columns and columns.isdigit() and int(columns) > 0:
        return int(columns)
    return None


def detect_terminal_width() -> Optional[int]:
    """Detect terminal width, accounting for piped stdin/stdout.

    Claude Code pipes stdin/stdout when invoking status line commands,
    so standard methods like shutil.get_terminal_size() (which checks
    stdout) return a wrong hardcoded 80. This function tries multiple
    methods in order of reliability.

    Returns:
        Terminal width in columns, or None if undetectable.
    """
    return _get_width_from_stderr() or _get_width_from_tty() or _get_width_from_env()
