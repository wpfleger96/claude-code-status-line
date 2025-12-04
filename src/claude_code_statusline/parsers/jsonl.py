"""JSONL transcript parsing utilities."""

import json
import os

from dataclasses import dataclass, field
from typing import Any

from ..utils.debug import debug_log


@dataclass
class ParsedTranscript:
    """Results from parsing a transcript file."""

    session_id: str = ""
    context_chars: int = 0
    total_file_chars: int = 0
    boundaries_found: int = 0
    is_jsonl: bool = False


@dataclass
class ExclusionRules:
    """Configuration for which lines to exclude from token counting.

    These fields are stored in Claude Code's JSONL files for debugging and
    UI purposes but are not included in the actual context sent to Claude.
    """

    metadata_fields: list[str] = field(
        default_factory=lambda: [
            "snapshot",
            "leafUuid",
        ]
    )
    excluded_types: list[str] = field(default_factory=lambda: ["summary", "system"])
    excluded_flags: list[str] = field(default_factory=lambda: [])


EXCLUSION_RULES = ExclusionRules()
CHARS_PER_TOKEN = 3.31  # Fallback estimation for transcripts without message.usage
DEFAULT_SYSTEM_OVERHEAD_TOKENS = 21400  # For character-based fallback


def get_system_overhead_tokens() -> int:
    """Get system overhead tokens from environment or use default."""
    try:
        return int(
            os.getenv("CLAUDE_CODE_SYSTEM_OVERHEAD", DEFAULT_SYSTEM_OVERHEAD_TOKENS)
        )
    except (ValueError, TypeError):
        return DEFAULT_SYSTEM_OVERHEAD_TOKENS


def calculate_total_tokens(transcript: ParsedTranscript) -> int:
    """Calculate total tokens from a transcript including conversation and system overhead.

    This uses character-based estimation and is kept for backwards compatibility.
    For real token counts, use parsers.tokens.get_token_metrics() instead.

    Args:
        transcript: Parsed transcript with character counts

    Returns:
        Estimated total tokens
    """
    conversation_tokens = int(transcript.context_chars // CHARS_PER_TOKEN)
    system_overhead_tokens = get_system_overhead_tokens()
    return conversation_tokens + system_overhead_tokens


def safe_get_file_size(file_path: str) -> int:
    """Safely get file size, returning 0 on error."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def is_real_compact_boundary(data: dict[str, Any]) -> bool:
    """Check if this is a real compact boundary set by Claude Code.

    Args:
        data: Parsed JSON line from transcript

    Returns:
        True if this line is a valid compact boundary marker
    """
    return (
        data.get("type") == "system"
        and data.get("subtype") == "compact_boundary"
        and "compactMetadata" in data
        and isinstance(data["compactMetadata"], dict)
        and "trigger" in data["compactMetadata"]
    )


def should_exclude_line(
    data: dict[str, Any], rules: ExclusionRules = EXCLUSION_RULES
) -> tuple[bool, str]:
    """Check if a line should be excluded from token counting.

    Args:
        data: Parsed JSON line from transcript
        rules: Exclusion rules configuration (defaults to global rules)

    Returns:
        Tuple of (should_exclude, reason) where reason is empty if not excluded
    """
    for metadata_field in rules.metadata_fields:
        if metadata_field in data:
            return True, f"has {metadata_field}"

    line_type = data.get("type")
    if line_type in rules.excluded_types:
        return True, f"type={line_type}"

    for flag_name in rules.excluded_flags:
        if data.get(flag_name):
            return True, f"{flag_name}=true"

    return False, ""


def extract_message_content_chars(
    data: dict[str, Any], session_id: str = "", detailed_debug: bool = False
) -> int:
    """Extract content that contributes to context.

    Only counts role and content fields, as these are what actually gets sent to Claude.
    Response metadata fields (model, type, stop_reason, etc.) are not counted.

    Args:
        data: Parsed JSON line from transcript
        session_id: Session identifier for debug logging
        detailed_debug: Whether to log detailed debug information

    Returns:
        Number of characters that contribute to context
    """
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

    total_chars = len(json.dumps(filtered_message))

    if detailed_debug and field_contributions:
        role = message.get("role", "unknown")
        debug_log(
            f"Message field breakdown ({role}): {field_contributions}", session_id
        )

    return total_chars


def parse_transcript(file_path: str) -> ParsedTranscript:
    """Parse transcript file in a single pass.

    Args:
        file_path: Path to the JSONL transcript file

    Returns:
        ParsedTranscript with character counts and session metadata
    """
    if not file_path or not os.path.isfile(file_path):
        debug_log("No valid transcript file", transcript_path=file_path)
        return ParsedTranscript()

    total_file_chars = safe_get_file_size(file_path)
    debug_log(
        f"Parsing transcript: {file_path} ({total_file_chars} chars)",
        transcript_path=file_path,
    )

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        debug_log(f"Failed to read file: {e}", transcript_path=file_path)
        return ParsedTranscript(total_file_chars=total_file_chars)

    # Single-pass parsing: track all state simultaneously
    session_id = ""
    boundary_count = 0
    is_jsonl = False
    detailed_debug = os.getenv("CLAUDE_CODE_STATUSLINE_DEBUG")

    chars_before_latest_boundary = 0
    chars_after_latest_boundary = 0

    message_type_counts: dict[str, int] = {}
    message_type_chars: dict[str, int] = {}
    excluded_line_counts: dict[str, int] = {}
    total_excluded_lines = 0

    for _line_num, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        try:
            data = json.loads(stripped)
            is_jsonl = True  # At least one valid JSON line

            if not session_id and data.get("sessionId"):
                session_id = data["sessionId"]

            if is_real_compact_boundary(data):
                boundary_count += 1
                chars_before_latest_boundary += chars_after_latest_boundary
                chars_after_latest_boundary = 0
                continue

            should_exclude, exclusion_reason = should_exclude_line(data)
            if should_exclude:
                total_excluded_lines += 1
                excluded_line_counts[exclusion_reason] = (
                    excluded_line_counts.get(exclusion_reason, 0) + 1
                )
                continue

            chars = extract_message_content_chars(
                data, session_id, bool(detailed_debug)
            )
            chars_after_latest_boundary += chars

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

    if not is_jsonl:
        debug_log("File is not JSONL format, using fallback", transcript_path=file_path)
        return ParsedTranscript(
            session_id="",
            total_file_chars=total_file_chars,
            context_chars=total_file_chars,
            is_jsonl=False,
        )

    message_content_chars = (
        chars_after_latest_boundary
        if boundary_count > 0
        else (chars_before_latest_boundary + chars_after_latest_boundary)
    )

    debug_log(f"Session: {session_id}, boundaries: {boundary_count}", session_id)
    debug_log(
        f"Message content chars: {message_content_chars}/{total_file_chars}", session_id
    )

    if detailed_debug:
        if total_excluded_lines > 0:
            debug_log(
                f"=== Excluded {total_excluded_lines} lines from token counting ===",
                session_id,
            )
            for reason, count in sorted(
                excluded_line_counts.items(), key=lambda x: x[1], reverse=True
            ):
                debug_log(f"  {reason}: {count} lines", session_id)
            debug_log("=" * 40, session_id)

        if message_type_chars:
            debug_log("=== Token Breakdown by Message Type ===", session_id)
            sorted_types = sorted(
                message_type_chars.items(), key=lambda x: x[1], reverse=True
            )
            total_tracked = sum(message_type_chars.values())

            for msg_type, chars in sorted_types:
                count = message_type_counts.get(msg_type, 0)
                tokens = int(chars // CHARS_PER_TOKEN)
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
