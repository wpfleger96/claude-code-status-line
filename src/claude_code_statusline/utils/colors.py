"""ANSI color codes and utilities."""

from typing import Optional

# Basic ANSI 16 colors
COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_black": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

# Color aliases
COLORS["gray"] = COLORS["bright_black"]
COLORS["grey"] = COLORS["bright_black"]


def get_color_code(color_name: Optional[str]) -> str:
    """Get ANSI color code by name.

    Args:
        color_name: Color name (e.g., "cyan", "red") or None

    Returns:
        ANSI color code or empty string if not found
    """
    if not color_name:
        return ""
    return COLORS.get(color_name.lower(), "")


def colorize(text: str, color: Optional[str] = None, bold: bool = False) -> str:
    """Apply color to text with ANSI codes.

    Args:
        text: Text to colorize
        color: Color name, None, or "none" to skip colorization
        bold: Whether to apply bold formatting

    Returns:
        Colorized text with ANSI codes
    """
    if not text:
        return text

    # "none" color means skip colorization entirely
    if color == "none":
        return text

    codes = []
    if bold:
        codes.append(COLORS["bold"])
    if color:
        color_code = get_color_code(color)
        if color_code:
            codes.append(color_code)

    if not codes:
        return text

    return "".join(codes) + text + COLORS["reset"]


def get_usage_color(percentage: float) -> str:
    """Get color based on usage percentage.

    Args:
        percentage: Usage percentage (0-100)

    Returns:
        Color name ("green", "yellow", or "red")
    """
    if percentage < 50:
        return "green"
    elif percentage < 80:
        return "yellow"
    else:
        return "red"


def get_cost_color(cost_usd: float) -> str:
    """Get color based on cost in USD.

    Args:
        cost_usd: Cost in USD

    Returns:
        Color name
    """
    if cost_usd == 0:
        return "grey"
    elif cost_usd < 5:
        return "green"
    elif cost_usd < 10:
        return "yellow"
    else:
        return "red"
