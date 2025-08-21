#!/usr/bin/env python3

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import Dict, Optional, Tuple

# Display Constants
CHARS_PER_TOKEN = 4
PROGRESS_BAR_SEGMENTS = 10
PERCENT_PER_SEGMENT = 10

# ANSI Color Codes
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_BLUE = "\033[36m"
COLOR_DIM = "\033[2m"
COLOR_RESET = "\033[0m"

# Cache Configuration
CACHE_FILE_NAME = "claude_code_model_data_cache.json"
CACHE_FILE = os.path.join(tempfile.gettempdir(), CACHE_FILE_NAME)
CACHE_TTL_SECONDS = 604800  # 1 week (7 days)

# Model Context Limits (fallback when API data unavailable)
MODEL_LIMITS = {
    "default": 200000,
    "claude": 200000,
    "claude-sonnet-4": 200000,
    "claude-opus-4": 200000,
    "claude-opus-4.1": 200000,
    "claude-opus-4-1": 200000,
    "gemini": 1000000,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-5": 400000,
}


def extract_token_limit(model_info: Dict) -> Optional[int]:
    """Extract token limit from model info dictionary."""
    limit = model_info.get("max_input_tokens") or model_info.get("max_tokens")
    return int(limit) if limit else None


def get_context_limit(model_id: str) -> int:
    """Get context limit for model from API data with fallback to hardcoded limits."""
    if not model_id:
        return MODEL_LIMITS["default"]

    # Try to get fresh/cached API data first
    api_data = get_cached_or_fetch_data()

    # Search through API data if available
    if api_data:
        model_lower = model_id.lower()

        if model_id in api_data:
            limit = extract_token_limit(api_data[model_id])
            if limit:
                return limit

        if model_lower in api_data:
            limit = extract_token_limit(api_data[model_lower])
            if limit:
                return limit

        for key in sorted(api_data.keys(), key=len, reverse=True):
            key_lower = key.lower()
            if model_lower in key_lower or key_lower in model_lower:
                limit = extract_token_limit(api_data[key])
                if limit:
                    return limit

    model_lower = model_id.lower()

    if model_lower in MODEL_LIMITS:
        return MODEL_LIMITS[model_lower]

    for key in sorted(MODEL_LIMITS.keys(), key=len, reverse=True):
        if key != "default" and (model_lower in key or key in model_lower):
            return MODEL_LIMITS[key]

    return MODEL_LIMITS["default"]


def get_cached_or_fetch_data() -> Optional[Dict]:
    """Get model data from cache or fetch from API if cache is expired or does not exist."""
    try:
        if os.path.exists(CACHE_FILE):
            cache_age = time.time() - os.path.getmtime(CACHE_FILE)
            if cache_age <= CACHE_TTL_SECONDS:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    # Fetch fresh data if cache data is expired or does not exist
    url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            try:
                with open(CACHE_FILE, "w") as f:
                    json.dump(data, f)
            except (OSError, IOError):
                pass
            return data
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        TimeoutError,
    ):
        return None


def get_usage_color(usage_percent: int) -> str:
    """Get color based on usage percentage."""
    if usage_percent < 50:
        return COLOR_GREEN
    elif usage_percent < 80:
        return COLOR_YELLOW
    return COLOR_RED


def format_number(number: int) -> str:
    """Format large numbers with K suffix."""
    if number >= 10000:
        thousands = number / 1000
        if thousands == int(thousands):
            return f"{int(thousands)}K"
        return f"{thousands:.2f}".rstrip("0").rstrip(".") + "K"
    return str(number)


def render_progress_bar(usage_percent: int) -> str:
    """Create visual progress bar."""
    filled = min(usage_percent // PERCENT_PER_SEGMENT, PROGRESS_BAR_SEGMENTS)
    empty = PROGRESS_BAR_SEGMENTS - filled
    color = get_usage_color(usage_percent)
    return f"{color}{'●' * filled}{'○' * empty}{COLOR_RESET}"


def safe_get_file_size(file_path: str) -> int:
    """Safely get file size, returning 0 on error."""
    try:
        return os.path.getsize(file_path)
    except (OSError, IOError):
        return 0


def format_context_info(transcript_path: str, model_id: str) -> str:
    """Format context usage information for display."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return f" Context: {COLOR_DIM}No active transcript{COLOR_RESET}"

    char_count = safe_get_file_size(transcript_path)
    if char_count == 0:
        return f" Context: {COLOR_DIM}Empty transcript{COLOR_RESET}"

    token_estimate = char_count // CHARS_PER_TOKEN
    context_limit = get_context_limit(model_id)

    if context_limit > 0:
        usage_percent = (token_estimate * 100) // context_limit
        progress_bar = render_progress_bar(usage_percent)
        formatted_tokens = format_number(token_estimate)
        formatted_limit = format_number(context_limit)
        return f" Context: {progress_bar} {usage_percent}% ({formatted_tokens}/{formatted_limit} tokens)"

    return ""


def parse_input_data() -> Tuple[str, str, str, str, Dict]:
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

    return cwd, transcript_path, model_id, model_name, cost_data


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
    cwd, transcript_path, model_id, model_name, cost_data = parse_input_data()
    context_info = format_context_info(transcript_path, model_id)
    dir_basename = get_dir_basename(cwd)
    cost_info = format_cost(cost_data)

    print(
        f"{COLOR_BLUE}{model_name}{COLOR_RESET} | {COLOR_DIM}{dir_basename}{COLOR_RESET} |{context_info}{cost_info}",
        end="",
    )


if __name__ == "__main__":
    main()
