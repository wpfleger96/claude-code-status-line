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
