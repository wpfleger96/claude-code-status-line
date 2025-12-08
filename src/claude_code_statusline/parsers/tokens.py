"""Real token extraction from JSONL message.usage fields."""

import json
import os

from datetime import datetime
from typing import Optional

from ..types import SessionMetrics, TokenMetrics
from .jsonl import is_real_compact_boundary


def parse_transcript(
    transcript_path: str,
) -> tuple[TokenMetrics, Optional[SessionMetrics]]:
    """Extract token metrics and session duration in single file read.

    Combines the logic of get_token_metrics() and get_session_duration()
    to avoid reading the transcript file twice.

    Args:
        transcript_path: Path to the JSONL transcript file

    Returns:
        Tuple of (TokenMetrics, SessionMetrics) from single file pass
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return TokenMetrics(transcript_exists=False), None

    input_tokens = 0
    output_tokens = 0
    cached_tokens = 0
    context_length = 0

    most_recent_time: Optional[datetime] = None
    most_recent_usage: Optional[dict[str, int]] = None

    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None

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
                        most_recent_time = None
                        most_recent_usage = None
                        first_timestamp = None
                        continue

                    timestamp_str = data.get("timestamp")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(
                                timestamp_str.replace("Z", "+00:00")
                            )
                            if first_timestamp is None:
                                first_timestamp = timestamp
                            last_timestamp = timestamp
                        except ValueError:
                            pass

                    usage = data.get("message", {}).get("usage")
                    if not usage:
                        continue

                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    cached_tokens += usage.get("cache_read_input_tokens", 0)
                    cached_tokens += usage.get("cache_creation_input_tokens", 0)

                    is_sidechain = data.get("isSidechain", False)
                    is_api_error = data.get("isApiErrorMessage", False)

                    if not is_sidechain and not is_api_error and timestamp_str:
                        try:
                            entry_time = datetime.fromisoformat(
                                timestamp_str.replace("Z", "+00:00")
                            )
                            if (
                                most_recent_time is None
                                or entry_time > most_recent_time
                            ):
                                most_recent_time = entry_time
                                most_recent_usage = usage
                        except ValueError:
                            continue

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

    session_metrics = None
    if first_timestamp and last_timestamp:
        duration_seconds = int((last_timestamp - first_timestamp).total_seconds())
        session_metrics = SessionMetrics(
            start_time=first_timestamp,
            last_activity=last_timestamp,
            duration_seconds=duration_seconds,
        )

    return token_metrics, session_metrics


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
