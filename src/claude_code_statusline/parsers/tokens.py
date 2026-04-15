"""Real token extraction from JSONL message.usage fields."""

import json
import os
import re

from datetime import datetime
from typing import Optional

from ..types import TokenMetrics
from .jsonl import is_real_compact_boundary

_ISO_TZ_RE = re.compile(r"Z$")


def _parse_timestamp_seconds(ts: str) -> Optional[float]:
    """Parse ISO timestamp string to epoch seconds for duration calculation."""
    try:
        dt = datetime.fromisoformat(_ISO_TZ_RE.sub("+00:00", ts))
        return dt.timestamp()
    except ValueError:
        return None


def parse_transcript(
    transcript_path: str,
) -> tuple[TokenMetrics, Optional[int]]:
    """Extract token metrics and session duration in single file read.

    Args:
        transcript_path: Path to the JSONL transcript file

    Returns:
        Tuple of (TokenMetrics, duration_seconds or None)
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return TokenMetrics(transcript_exists=False), None

    input_tokens = 0
    output_tokens = 0
    cached_tokens = 0
    context_length = 0

    most_recent_usage: Optional[dict[str, int]] = None

    first_ts: Optional[float] = None
    last_ts: Optional[float] = None

    session_id = ""
    had_compact_boundary = False

    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    if data.get("sessionId"):
                        session_id = data["sessionId"]

                    if is_real_compact_boundary(data):
                        had_compact_boundary = True
                        input_tokens = 0
                        output_tokens = 0
                        cached_tokens = 0
                        most_recent_usage = None
                        first_ts = None
                        continue

                    timestamp_str = data.get("timestamp")
                    if timestamp_str:
                        ts = _parse_timestamp_seconds(timestamp_str)
                        if ts is not None:
                            if first_ts is None:
                                first_ts = ts
                            last_ts = ts

                    usage = data.get("message", {}).get("usage")
                    if not usage:
                        continue

                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    cached_tokens += usage.get("cache_read_input_tokens", 0)
                    cached_tokens += usage.get("cache_creation_input_tokens", 0)

                    is_sidechain = data.get("isSidechain", False)
                    is_api_error = data.get("isApiErrorMessage", False)

                    # JSONL entries are appended chronologically; last valid entry is most recent
                    if not is_sidechain and not is_api_error:
                        most_recent_usage = usage

                except (json.JSONDecodeError, ValueError):
                    continue

    except OSError:
        return TokenMetrics(transcript_exists=False), None

    if most_recent_usage:
        context_length = (
            most_recent_usage.get("input_tokens", 0)
            + most_recent_usage.get("cache_read_input_tokens", 0)
            + most_recent_usage.get("cache_creation_input_tokens", 0)
        )

    total_tokens = input_tokens + output_tokens + cached_tokens

    token_metrics = TokenMetrics(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        total_tokens=total_tokens,
        context_length=context_length,
        transcript_exists=True,
        session_id=session_id,
        had_compact_boundary=had_compact_boundary,
    )

    duration_seconds = None
    if first_ts is not None and last_ts is not None:
        duration_seconds = int(last_ts - first_ts)

    return token_metrics, duration_seconds


def format_duration(duration_seconds: int) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        duration_seconds: Duration in seconds

    Returns:
        Formatted string like "2hr 15m" or "45m" or "<1m"
    """
    if duration_seconds < 60:
        return "<1m"

    total_minutes = duration_seconds // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours == 0:
        return f"{minutes}m"
    elif minutes == 0:
        return f"{hours}hr"
    else:
        return f"{hours}hr {minutes}m"
