"""Common code shared between statusline and calibration scripts."""

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ParsedTranscript:
    """Results from parsing a transcript file."""

    session_id: str = ""
    context_chars: int = 0
    total_file_chars: int = 0
    boundaries_found: int = 0
    is_jsonl: bool = False


CHARS_PER_TOKEN = 4

CACHE_FILE_NAME = "claude_code_model_data_cache.json"
CACHE_FILE = os.path.join(tempfile.gettempdir(), CACHE_FILE_NAME)
CACHE_TTL_SECONDS = 604800  # 1 week (7 days)

DEFAULT_SYSTEM_OVERHEAD_TOKENS = 15400
DEFAULT_RESERVED_TOKENS = 45000

MODEL_LIMITS = {
    "default": 200000,
    "claude": 200000,
    "claude-sonnet-4": 200000,
    "claude-sonnet-4-20250514": 200000,
    "claude-sonnet-4-20250514[1m]": 1000000,
    "claude-sonnet-4-5-20250929": 200000,
    "claude-sonnet-4-5-20250929[1m]": 1000000,
    "claude-opus-4": 200000,
    "claude-opus-4.1": 200000,
    "claude-opus-4-1": 200000,
    "claude-opus-4-1-20250805": 200000,
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

    effective_session_id = session_id

    if not effective_session_id and transcript_path:
        filename = os.path.basename(transcript_path)
        if filename.endswith(".jsonl"):
            potential_session_id = filename[:-6]
            if len(potential_session_id) == 36 and potential_session_id.count("-") == 4:
                effective_session_id = potential_session_id
            else:
                effective_session_id = potential_session_id

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

    filtered_message = {}
    field_contributions = {}

    if "role" in message:
        field_value = json.dumps(message["role"])
        filtered_message["role"] = message["role"]
        field_contributions["role"] = len(field_value)
    if "content" in message:
        content = message["content"]
        filtered_content = content
        images_skipped = 0

        if isinstance(content, list):
            filtered_content = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image":
                    images_skipped += 1
                    debug_log(
                        "Skipping base64-encoded image in message (not counted as text tokens)",
                        session_id,
                    )
                else:
                    filtered_content.append(item)

        field_value = json.dumps(filtered_content)
        filtered_message["content"] = filtered_content
        field_contributions["content"] = len(field_value)

        if images_skipped > 0:
            debug_log(
                f"Excluded {images_skipped} base64-encoded image(s) from character count",
                session_id,
            )

    if "model" in message:
        field_value = json.dumps(message["model"])
        filtered_message["model"] = message["model"]
        field_contributions["model"] = len(field_value)
    if "type" in message:
        field_value = json.dumps(message["type"])
        filtered_message["type"] = message["type"]
        field_contributions["type"] = len(field_value)

    for key in ["stop_reason", "stop_sequence"]:
        if key in message:
            field_value = json.dumps(message[key])
            filtered_message[key] = message[key]
            field_contributions[key] = len(field_value)

    total_chars = len(json.dumps(filtered_message))

    if detailed_debug and field_contributions:
        role = message.get("role", "unknown")
        debug_log(
            f"Message field breakdown ({role}): {field_contributions}", session_id
        )
        if total_chars > 1000:
            top_fields = sorted(
                field_contributions.items(), key=lambda x: x[1], reverse=True
            )[:3]
            debug_log(f"Top contributing fields: {top_fields}", session_id)

    return total_chars


def safe_get_file_size(file_path: str) -> int:
    """Safely get file size, returning 0 on error."""
    try:
        return os.path.getsize(file_path)
    except (OSError, IOError):
        return 0


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

    for line_num, line in enumerate(lines):
        if not line.strip():
            continue

        try:
            data = json.loads(line.strip())
            valid_json_lines += 1

            if not session_id and data.get("sessionId"):
                session_id = data["sessionId"]

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

    start_line = (last_boundary_line + 1) if last_boundary_line is not None else 0

    detailed_debug = os.getenv("CLAUDE_CODE_STATUSLINE_DEBUG")
    message_type_counts = {}
    message_type_chars = {}

    for line_num in range(start_line, len(lines)):
        line = lines[line_num].strip()
        if not line:
            continue

        try:
            data = json.loads(line)
            chars = extract_message_content_chars(
                data, session_id, bool(detailed_debug)
            )
            message_content_chars += chars

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


def get_context_limit(model_id: str, model_name: str = "") -> int:
    """Get context limit for model from API data with fallback to hardcoded limits."""
    if not model_id:
        return MODEL_LIMITS["default"]

    if "[1m]" in model_id.lower():
        return 1000000

    if model_name and "1m" in model_name.lower():
        return 1000000

    api_data = get_cached_or_fetch_data()

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


def get_system_overhead_tokens() -> int:
    """Get system overhead tokens from environment or use default."""
    try:
        return int(
            os.getenv("CLAUDE_CODE_SYSTEM_OVERHEAD", DEFAULT_SYSTEM_OVERHEAD_TOKENS)
        )
    except (ValueError, TypeError):
        return DEFAULT_SYSTEM_OVERHEAD_TOKENS


def get_reserved_tokens() -> int:
    """Get reserved tokens for autocompact and output."""
    try:
        return int(os.getenv("CLAUDE_CODE_RESERVED_TOKENS", DEFAULT_RESERVED_TOKENS))
    except (ValueError, TypeError):
        return DEFAULT_RESERVED_TOKENS


def calculate_total_tokens(transcript: ParsedTranscript) -> int:
    """Calculate total tokens from a transcript including conversation, system overhead, and reserved tokens."""
    conversation_tokens = transcript.context_chars // CHARS_PER_TOKEN
    system_overhead_tokens = get_system_overhead_tokens()
    reserved_tokens = get_reserved_tokens()
    return conversation_tokens + system_overhead_tokens + reserved_tokens
