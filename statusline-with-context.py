#!/usr/bin/env python3

import json
import os
import sys
from typing import Dict, Tuple

from common import (
    CHARS_PER_TOKEN,
    ParsedTranscript,
    calculate_total_tokens,
    debug_log,
    get_context_limit,
    get_reserved_tokens,
    get_system_overhead_tokens,
    parse_transcript,
)

# Display Constants
PROGRESS_BAR_SEGMENTS = 10
PERCENT_PER_SEGMENT = 10

# ANSI Color Codes
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[36m"
COLOR_DIM = "\033[2m"
COLOR_RESET = "\033[0m"


def get_usage_color(usage_percent: int) -> str:
    """Get color based on usage percentage."""
    if usage_percent < 50:
        return COLOR_GREEN
    elif usage_percent < 80:
        return COLOR_YELLOW
    return COLOR_RED


def format_number(number: int) -> str:
    """Format large numbers with K or M suffix."""
    if number >= 10000 and number < 1000000:
        thousands = number / 1000
        if thousands == int(thousands):
            return f"{int(thousands)}K"
        return f"{thousands:.2f}".rstrip("0").rstrip(".") + "K"
    elif number >= 1000000:
        millions = number / 1000000
        if millions == int(millions):
            return f"{int(millions)}M"
        return f"{millions:.2f}".rstrip("0").rstrip(".") + "M"
    return str(number)


def render_progress_bar(usage_percent: int) -> str:
    """Create visual progress bar."""
    filled = min(usage_percent // PERCENT_PER_SEGMENT, PROGRESS_BAR_SEGMENTS)
    empty = PROGRESS_BAR_SEGMENTS - filled
    color = get_usage_color(usage_percent)
    return f"{color}{'●' * filled}{'○' * empty}{COLOR_RESET}"


def format_context_info(transcript: ParsedTranscript, model_id: str) -> str:
    """Format context usage information for display."""

    if transcript.context_chars == 0:
        return f" Context: {COLOR_DIM}No active transcript{COLOR_RESET}"

    total_tokens = calculate_total_tokens(transcript)
    context_limit = get_context_limit(model_id)

    if context_limit > 0:
        usage_percent = (total_tokens * 100) // context_limit
        progress_bar = render_progress_bar(usage_percent)
        formatted_tokens = format_number(total_tokens)
        formatted_limit = format_number(context_limit)

        if os.getenv("CLAUDE_CODE_STATUSLINE_DEBUG") and transcript.is_jsonl:
            conversation_tokens = transcript.context_chars // CHARS_PER_TOKEN
            system_overhead_tokens = get_system_overhead_tokens()
            reserved_tokens = get_reserved_tokens()
            naive_tokens = transcript.total_file_chars // CHARS_PER_TOKEN
            debug_log(
                f"Token breakdown: Conversation={conversation_tokens}, System={system_overhead_tokens}, Reserved={reserved_tokens}, Total={total_tokens}",
                transcript.session_id,
            )
            if transcript.boundaries_found > 0:
                debug_log(
                    f"Token reduction from compaction: {naive_tokens - conversation_tokens}",
                    transcript.session_id,
                )
            else:
                debug_log(
                    f"File size tokens (naive): {naive_tokens}", transcript.session_id
                )

        return f" Context: {progress_bar} {usage_percent}% ({formatted_tokens}/{formatted_limit} tokens)"

    return ""


def parse_input_data() -> Tuple[str, str, str, str, Dict, str]:
    """Parse JSON input from stdin and extract relevant fields."""
    try:
        input_data = sys.stdin.read()
        data = json.loads(input_data)
    except (json.JSONDecodeError, ValueError):
        data = {}

    cwd = data.get("workspace", {}).get("current_dir", "")
    transcript_path = data.get("transcript_path", "")
    model_id = data.get("model", {}).get("id", "")
    model_name = data.get("model", {}).get("display_name", "")
    cost_data = data.get("cost", {})
    claude_code_version = data.get("version", "unknown")

    return cwd, transcript_path, model_id, model_name, cost_data, claude_code_version


def get_dir_basename(cwd: str) -> str:
    """Safely get basename of directory."""
    try:
        return os.path.basename(cwd) if cwd else ""
    except (OSError, TypeError):
        return ""


def get_cost_color(cost_usd: float) -> str:
    """Get color based on cost amount."""
    if cost_usd == 0.0:
        return COLOR_DIM
    elif cost_usd < 5.0:
        return COLOR_GREEN
    elif cost_usd < 10.0:
        return COLOR_YELLOW
    return COLOR_RED


def format_cost(cost_data: Dict) -> str:
    """Format cost information for display."""
    cost_usd = cost_data.get("total_cost_usd", 0) if cost_data else 0
    lines_added = cost_data.get("total_lines_added", 0) if cost_data else 0
    lines_removed = cost_data.get("total_lines_removed", 0) if cost_data else 0

    parts = []

    # Always show cost, even if $0.00
    cost_color = get_cost_color(cost_usd)
    parts.append(f"Cost: {cost_color}${cost_usd:.2f}{COLOR_RESET} USD")

    # Always show lines added, even if 0
    added_color = COLOR_DIM if lines_added == 0 else COLOR_GREEN
    parts.append(f"{added_color}+{lines_added} lines added{COLOR_RESET}")

    # Always show lines removed, even if 0
    removed_color = COLOR_DIM if lines_removed == 0 else COLOR_RED
    parts.append(f"{removed_color}-{lines_removed} lines removed{COLOR_RESET}")

    return " | " + " | ".join(parts)


def main():
    """Main entry point."""
    cwd, transcript_path, model_id, model_name, cost_data, claude_code_version = (
        parse_input_data()
    )

    # Parse transcript once and use it for both metadata logging and context info
    transcript = parse_transcript(transcript_path)

    # Log session metadata using direct debug_log calls
    debug_log("=== SESSION METADATA ===", transcript.session_id)
    debug_log(f"Working Directory: {cwd}", transcript.session_id)
    debug_log(f"Model ID: {model_id}", transcript.session_id)
    debug_log(f"Model Name: {model_name}", transcript.session_id)
    debug_log(f"Claude Code Version: {claude_code_version}", transcript.session_id)
    debug_log("=" * 25, transcript.session_id)

    context_info = format_context_info(transcript, model_id)
    dir_basename = get_dir_basename(cwd)
    cost_info = format_cost(cost_data)

    print(
        f"{COLOR_BLUE}{model_name}{COLOR_RESET} | {COLOR_DIM}{dir_basename}{COLOR_RESET} |{context_info}{cost_info}",
        end="",
    )


if __name__ == "__main__":
    main()
