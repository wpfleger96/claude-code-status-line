"""Real token extraction from JSONL message.usage fields."""

import json
import os

from datetime import datetime
from typing import Optional

from ..types import SessionMetrics, TokenMetrics


def get_token_metrics(transcript_path: str) -> TokenMetrics:
    """Extract real token counts from JSONL message.usage fields.

    Reads actual token usage from Claude API responses instead of estimating.
    Skips sidechain messages and API error messages.

    Args:
        transcript_path: Path to the JSONL transcript file

    Returns:
        TokenMetrics with accurate token counts from API
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return TokenMetrics()

    input_tokens = 0
    output_tokens = 0
    cached_tokens = 0
    context_length = 0

    most_recent_time: Optional[datetime] = None
    most_recent_usage: Optional[dict] = None

    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    usage = data.get("message", {}).get("usage")
                    if not usage:
                        continue

                    # Sum totals across all messages
                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    cached_tokens += usage.get("cache_read_input_tokens", 0)
                    cached_tokens += usage.get("cache_creation_input_tokens", 0)

                    # Track most recent main chain entry for context_length
                    is_sidechain = data.get("isSidechain", False)
                    is_api_error = data.get("isApiErrorMessage", False)
                    timestamp_str = data.get("timestamp")
                    stop_reason = data.get("message", {}).get("stop_reason")

                    # Only use completed messages (skip streaming partials with stop_reason: null)
                    if (
                        not is_sidechain
                        and not is_api_error
                        and timestamp_str
                        and stop_reason is not None
                    ):
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
                            # Skip invalid timestamps
                            continue

                except (json.JSONDecodeError, ValueError):
                    continue

    except OSError:
        return TokenMetrics()

    # Calculate context_length from most recent main chain message
    if most_recent_usage:
        context_length = (
            most_recent_usage.get("input_tokens", 0)
            + most_recent_usage.get("cache_read_input_tokens", 0)
            + most_recent_usage.get("cache_creation_input_tokens", 0)
        )

    total_tokens = input_tokens + output_tokens + cached_tokens

    return TokenMetrics(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        total_tokens=total_tokens,
        context_length=context_length,
    )


def get_session_duration(transcript_path: str) -> Optional[SessionMetrics]:
    """Calculate session duration from first to last timestamp.

    Args:
        transcript_path: Path to the JSONL transcript file

    Returns:
        SessionMetrics with start time, last activity, and duration
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return None

    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None

    try:
        with open(transcript_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Find first valid timestamp
        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                timestamp_str = data.get("timestamp")
                if timestamp_str:
                    first_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    break
            except (json.JSONDecodeError, ValueError):
                continue

        # Find last valid timestamp (iterate backwards)
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                timestamp_str = data.get("timestamp")
                if timestamp_str:
                    last_timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                    break
            except (json.JSONDecodeError, ValueError):
                continue

    except OSError:
        return None

    if not first_timestamp or not last_timestamp:
        return None

    duration_seconds = int((last_timestamp - first_timestamp).total_seconds())

    return SessionMetrics(
        start_time=first_timestamp,
        last_activity=last_timestamp,
        duration_seconds=duration_seconds,
    )


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
