#!/usr/bin/env python3

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class ParsedTranscript:
    """Results from parsing a transcript file."""

    session_id: str = ""
    context_chars: int = 0
    total_file_chars: int = 0
    boundaries_found: int = 0
    is_jsonl: bool = False


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

# System Overhead (tokens used by Claude Code's system prompt, tools, memory, etc.)
DEFAULT_SYSTEM_OVERHEAD_TOKENS = 16500

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


def debug_log(message: str, session_id: str = "", transcript_path: str = "") -> None:
    """Log debug messages to per-session debug log files if debug mode is enabled."""
    if not os.getenv("CLAUDE_CODE_STATUSLINE_DEBUG"):
        return

    # Determine the session ID for the log file name
    effective_session_id = session_id

    # If no session_id provided, try to extract from transcript filename
    if not effective_session_id and transcript_path:
        filename = os.path.basename(transcript_path)
        if filename.endswith(".jsonl"):
            potential_session_id = filename[:-6]  # Remove .jsonl extension
            # Check if it looks like a UUID (36 chars) or use the filename as-is
            if len(potential_session_id) == 36 and potential_session_id.count("-") == 4:
                effective_session_id = potential_session_id
            else:
                # Use the full filename without extension for non-UUID files
                effective_session_id = potential_session_id

    # Use "unknown" as last resort
    if not effective_session_id:
        effective_session_id = "unknown"

    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    log_file = os.path.join(logs_dir, f"statusline_debug_{effective_session_id}.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    session_prefix = f"[{session_id}] " if session_id else ""
    log_message = f"[{timestamp}] {session_prefix}{message}\n"

    try:
        os.makedirs(logs_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_message)
    except (OSError, IOError):
        print(
            f"DEBUG (couldn't write to {log_file}): {session_prefix}{message}",
            file=sys.stderr,
        )


def is_real_compact_boundary(data: dict) -> bool:
    """Check if this is a real compact boundary set by Claude Code."""
    return (
        data.get("type") == "system"
        and data.get("subtype") == "compact_boundary"
        and "compactMetadata" in data
        and isinstance(data["compactMetadata"], dict)
        and "trigger" in data["compactMetadata"]
    )


def extract_message_content_chars(
    data: dict, session_id: str = "", detailed_debug: bool = False
) -> int:
    """Extract content that contributes to context, excluding excessive metadata."""
    message = data.get("message", {})
    if not message:
        return 0

    # Create a filtered version that excludes heavy metadata but keeps content-relevant fields
    filtered_message = {}
    field_contributions = {}

    # Always include role and content
    if "role" in message:
        field_value = json.dumps(message["role"])
        filtered_message["role"] = message["role"]
        field_contributions["role"] = len(field_value)
    if "content" in message:
        field_value = json.dumps(message["content"])
        filtered_message["content"] = message["content"]
        field_contributions["content"] = len(field_value)

    # Include model info but not detailed usage stats
    if "model" in message:
        field_value = json.dumps(message["model"])
        filtered_message["model"] = message["model"]
        field_contributions["model"] = len(field_value)
    if "type" in message:
        field_value = json.dumps(message["type"])
        filtered_message["type"] = message["type"]
        field_contributions["type"] = len(field_value)

    # Exclude heavy metadata like detailed usage stats, request IDs, etc.
    # but keep stop_reason and stop_sequence as they're content-relevant
    for key in ["stop_reason", "stop_sequence"]:
        if key in message:
            field_value = json.dumps(message[key])
            filtered_message[key] = message[key]
            field_contributions[key] = len(field_value)

    total_chars = len(json.dumps(filtered_message))

    # Enhanced debug logging with field breakdown
    if detailed_debug and field_contributions:
        role = message.get("role", "unknown")
        debug_log(
            f"Message field breakdown ({role}): {field_contributions}", session_id
        )
        if total_chars > 1000:  # Only log large messages
            top_fields = sorted(
                field_contributions.items(), key=lambda x: x[1], reverse=True
            )[:3]
            debug_log(f"Top contributing fields: {top_fields}", session_id)

    return total_chars


def parse_transcript(file_path: str) -> ParsedTranscript:
    """Parse transcript file and return structured information."""
    if not file_path or not os.path.isfile(file_path):
        debug_log("No valid transcript file", transcript_path=file_path)
        return ParsedTranscript()

    total_file_chars = safe_get_file_size(file_path)
    debug_log(
        f"Parsing transcript: {file_path} ({total_file_chars} chars)",
        transcript_path=file_path,
    )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, IOError) as e:
        debug_log(f"Failed to read file: {e}", transcript_path=file_path)
        return ParsedTranscript(total_file_chars=total_file_chars)

    session_id = ""
    last_boundary_line = None
    boundary_count = 0
    message_content_chars = 0
    valid_json_lines = 0

    # Single pass: parse JSON and detect real compact boundaries
    for line_num, line in enumerate(lines):
        if not line.strip():
            continue

        try:
            data = json.loads(line.strip())
            valid_json_lines += 1

            if not session_id and data.get("sessionId"):
                session_id = data["sessionId"]

            # Check for REAL compact boundaries with strict criteria
            if is_real_compact_boundary(data):
                last_boundary_line = line_num
                boundary_count += 1
                debug_log(f"Found compact boundary at line {line_num + 1}", session_id)
        except json.JSONDecodeError:
            continue

    is_jsonl = valid_json_lines > 0
    if not is_jsonl:
        debug_log("File is not JSONL format, using fallback", session_id)
        return ParsedTranscript(
            session_id=session_id,
            total_file_chars=total_file_chars,
            context_chars=total_file_chars,
            is_jsonl=False,
        )

    debug_log(f"Session: {session_id}, boundaries: {boundary_count}", session_id)
    if last_boundary_line is not None:
        debug_log(
            f"Using content from line {last_boundary_line + 2} onwards", session_id
        )

    # Count only message content after the last boundary
    start_line = (last_boundary_line + 1) if last_boundary_line is not None else 0

    # Enhanced debug tracking
    detailed_debug = os.getenv("CLAUDE_CODE_STATUSLINE_DEBUG")
    message_type_counts = {}
    message_type_chars = {}

    for line_num in range(start_line, len(lines)):
        line = lines[line_num].strip()
        if not line:
            continue

        try:
            data = json.loads(line)
            # Only count actual message content, not metadata
            chars = extract_message_content_chars(
                data, session_id, bool(detailed_debug)
            )
            message_content_chars += chars

            # Track by message type for debug output
            if detailed_debug and chars > 0:
                msg_type = data.get("type", "unknown")
                role = data.get("message", {}).get("role", "")
                type_key = f"{msg_type}:{role}" if role else msg_type

                message_type_counts[type_key] = message_type_counts.get(type_key, 0) + 1
                message_type_chars[type_key] = (
                    message_type_chars.get(type_key, 0) + chars
                )
        except json.JSONDecodeError:
            continue

    debug_log(
        f"Message content chars: {message_content_chars}/{total_file_chars}", session_id
    )

    # Enhanced debug output with breakdown by message type
    if detailed_debug and message_type_chars:
        debug_log("=== Token Breakdown by Message Type ===", session_id)
        sorted_types = sorted(
            message_type_chars.items(), key=lambda x: x[1], reverse=True
        )
        total_tracked = sum(message_type_chars.values())

        for msg_type, chars in sorted_types:
            count = message_type_counts.get(msg_type, 0)
            tokens = chars // CHARS_PER_TOKEN
            percentage = (chars * 100) // total_tracked if total_tracked > 0 else 0
            debug_log(
                f"  {msg_type}: {count} messages, {chars} chars, {tokens} tokens ({percentage}%)",
                session_id,
            )
        debug_log("=" * 40, session_id)

    return ParsedTranscript(
        session_id=session_id,
        context_chars=message_content_chars,
        total_file_chars=total_file_chars,
        boundaries_found=boundary_count,
        is_jsonl=True,
    )


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


def get_system_overhead_tokens() -> int:
    """Get system overhead tokens from environment or use default."""
    try:
        return int(
            os.getenv("CLAUDE_CODE_SYSTEM_OVERHEAD", DEFAULT_SYSTEM_OVERHEAD_TOKENS)
        )
    except (ValueError, TypeError):
        return DEFAULT_SYSTEM_OVERHEAD_TOKENS


def format_context_info(transcript_path: str, model_id: str) -> str:
    """Format context usage information for display."""
    transcript = parse_transcript(transcript_path)

    if transcript.context_chars == 0:
        return f" Context: {COLOR_DIM}No active transcript{COLOR_RESET}"

    conversation_tokens = transcript.context_chars // CHARS_PER_TOKEN
    system_overhead_tokens = get_system_overhead_tokens()
    total_tokens = conversation_tokens + system_overhead_tokens
    context_limit = get_context_limit(model_id)

    if context_limit > 0:
        usage_percent = (total_tokens * 100) // context_limit
        progress_bar = render_progress_bar(usage_percent)
        formatted_tokens = format_number(total_tokens)
        formatted_limit = format_number(context_limit)

        # Debug logging only - no display clutter
        if os.getenv("CLAUDE_CODE_STATUSLINE_DEBUG") and transcript.is_jsonl:
            naive_tokens = transcript.total_file_chars // CHARS_PER_TOKEN
            debug_log(
                f"Token breakdown: Conversation={conversation_tokens}, System={system_overhead_tokens}, Total={total_tokens}",
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
