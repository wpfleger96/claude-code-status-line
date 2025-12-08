#!/usr/bin/env python3

import json
import os
import sys

from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from .parsers.tokens import parse_transcript
from .renderer import render_status_line_with_config
from .types import RenderContext
from .utils.credentials import read_subscription_info
from .utils.debug import debug_log
from .utils.models import prefetch_model_data


def parse_input_data() -> dict[str, Any]:
    """Parse JSON input from stdin and return as dict.

    Returns:
        Dictionary with Claude Code JSON payload
    """
    try:
        input_data = sys.stdin.read()
        return cast(dict[str, Any], json.loads(input_data))
    except (json.JSONDecodeError, ValueError):
        return {}


def find_transcript_path(data: dict[str, Any]) -> str:
    """Find transcript path, with fallback to construct from session_id.

    Args:
        data: JSON input data

    Returns:
        Path to transcript file, or empty string if not found
    """
    transcript_path: str = data.get("transcript_path", "")
    if transcript_path and os.path.isfile(transcript_path):
        return transcript_path

    session_id = data.get("session_id", "")
    workspace = data.get("workspace", {}).get("current_dir", "")

    if session_id and workspace:
        # Claude Code stores transcripts in ~/.claude/projects/{encoded_path}/{session_id}.jsonl
        encoded_path = workspace.replace("/", "-")
        if encoded_path.startswith("-"):
            encoded_path = encoded_path[1:]  # Remove leading dash
        potential_path = os.path.expanduser(
            f"~/.claude/projects/-{encoded_path}/{session_id}.jsonl"
        )
        if os.path.isfile(potential_path):
            return potential_path

    return transcript_path  # Return original (may be empty)


def extract_session_id(data: dict[str, Any], transcript_path: str) -> str:
    """Extract session ID from data or transcript filename.

    Args:
        data: JSON input data
        transcript_path: Path to transcript file

    Returns:
        Session ID or empty string
    """
    session_id: str = data.get("session_id", "")
    if session_id:
        return session_id

    if transcript_path:
        filename = os.path.basename(transcript_path)
        if filename.endswith(".jsonl"):
            potential_id = filename[:-6]
            if len(potential_id) == 36 and potential_id.count("-") == 4:
                return potential_id

    return ""


def main() -> None:
    """Main entry point with widget-based rendering and parallel I/O."""
    data = parse_input_data()

    transcript_path = find_transcript_path(data)

    session_id = extract_session_id(data, transcript_path)

    if session_id:
        data["session_id"] = session_id

    debug_log("=== SESSION START ===", session_id)
    debug_log(
        f"Working Directory: {data.get('workspace', {}).get('current_dir', '')}",
        session_id,
    )
    debug_log(f"Model ID: {data.get('model', {}).get('id', '')}", session_id)
    debug_log(f"Transcript Path: {transcript_path}", session_id)

    with ThreadPoolExecutor(max_workers=3) as executor:
        transcript_future = executor.submit(parse_transcript, transcript_path)
        subscription_future = executor.submit(read_subscription_info)
        executor.submit(prefetch_model_data)

        token_metrics, session_metrics = transcript_future.result()
        subscription_info = subscription_future.result()

    # Prefer transcript's session_id if compaction was detected
    # This fixes stale session_id display after /compact
    if token_metrics.had_compact_boundary and token_metrics.session_id:
        data["session_id"] = token_metrics.session_id

    context = RenderContext(
        data=data,
        token_metrics=token_metrics,
        session_metrics=session_metrics,
        subscription_info=subscription_info,
        git_status=None,  # Lazy-loaded by git widgets
    )

    debug_log(f"Token metrics: {token_metrics}", session_id)
    debug_log(f"Session metrics: {session_metrics}", session_id)
    debug_log("=" * 25, session_id)

    output = render_status_line_with_config(context)
    print(output, end="")


if __name__ == "__main__":
    main()
