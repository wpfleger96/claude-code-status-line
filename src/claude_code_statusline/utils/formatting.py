"""Formatting utilities for numbers and progress bars."""


def format_number(num: int, decimals: int = 0) -> str:
    """Format a number with K/M suffix.

    Args:
        num: Number to format
        decimals: Number of decimal places for K/M formatting

    Returns:
        Formatted string (e.g., "120K", "1.5M")
    """
    if num < 1000:
        return str(num)
    elif num < 1_000_000:
        k = num / 1000
        if decimals == 0:
            return f"{round(k)}K"
        return f"{k:.{decimals}f}K".rstrip("0").rstrip(".")
    else:
        m = num / 1_000_000
        if decimals == 0:
            return f"{round(m)}M"
        return f"{m:.{decimals}f}M".rstrip("0").rstrip(".")


def render_progress_bar(
    percentage: float, segments: int = 10, filled_char: str = "●", empty_char: str = "○"
) -> str:
    """Render a progress bar with filled/empty circles.

    Args:
        percentage: Progress percentage (0-100)
        segments: Number of segments in progress bar
        filled_char: Character for filled segments
        empty_char: Character for empty segments

    Returns:
        Progress bar string (e.g., "●●●●●●○○○○")
    """
    filled = int((percentage / 100) * segments)
    empty = segments - filled
    return filled_char * filled + empty_char * empty


def format_percentage(percentage: float, decimals: int = 1) -> str:
    """Format percentage with specified decimal places.

    Args:
        percentage: Percentage value (0-100)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string (e.g., "67.5%")
    """
    return f"{percentage:.{decimals}f}%"
