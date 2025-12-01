#!/usr/bin/env python3

import json
import os
import sys

from concurrent.futures import ThreadPoolExecutor

from .parsers.tokens import get_session_duration, get_token_metrics
from .renderer import render_status_line_with_config
from .types import RenderContext
from .utils.debug import debug_log
from .utils.models import prefetch_model_data


def parse_input_data() -> dict:
    """Parse JSON input from stdin and return as dict.

    Returns:
        Dictionary with Claude Code JSON payload
    """
    try:
        input_data = sys.stdin.read()
        return json.loads(input_data)
    except (json.JSONDecodeError, ValueError):
        return {}


def find_transcript_path(data: dict) -> str:
    """Find transcript path, with fallback to construct from session_id.

    Args:
        data: JSON input data

    Returns:
        Path to transcript file, or empty string if not found
    """
    # Try provided path first
    transcript_path = data.get("transcript_path", "")
    if transcript_path and os.path.isfile(transcript_path):
        return transcript_path

    # Fallback: construct from session_id and workspace
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


def extract_session_id(data: dict, transcript_path: str) -> str:
    """Extract session ID from data or transcript filename.

    Args:
        data: JSON input data
        transcript_path: Path to transcript file

    Returns:
        Session ID or empty string
    """
    # Try JSON input first
    session_id = data.get("session_id", "")
    if session_id:
        return session_id

    # Fallback: extract from transcript filename
    if transcript_path:
        filename = os.path.basename(transcript_path)
        if filename.endswith(".jsonl"):
            potential_id = filename[:-6]
            # Validate UUID format (36 chars, 4 hyphens)
            if len(potential_id) == 36 and potential_id.count("-") == 4:
                return potential_id

    return ""


def main():
    """Main entry point with widget-based rendering and parallel I/O."""
    data = parse_input_data()

    # Find transcript path with fallback for forked sessions
    transcript_path = find_transcript_path(data)

    # Extract/infer session ID
    session_id = extract_session_id(data, transcript_path)

    # Add session_id to data for widgets to use
    if session_id:
        data["session_id"] = session_id

    debug_log("=== SESSION START ===", session_id)
    debug_log(
        f"Working Directory: {data.get('workspace', {}).get('current_dir', '')}",
        session_id,
    )
    debug_log(f"Model ID: {data.get('model', {}).get('id', '')}", session_id)
    debug_log(f"Transcript Path: {transcript_path}", session_id)

    # Parallel I/O for fast startup
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit I/O tasks
        token_future = executor.submit(get_token_metrics, transcript_path)
        session_future = executor.submit(get_session_duration, transcript_path)
        executor.submit(prefetch_model_data)  # Fire and forget

        # Wait for results
        token_metrics = token_future.result()
        session_metrics = session_future.result()

    # Build render context
    context = RenderContext(
        data=data,
        token_metrics=token_metrics,
        session_metrics=session_metrics,
        git_status=None,  # Lazy-loaded by git widgets
    )

    debug_log(f"Token metrics: {token_metrics}", session_id)
    debug_log(f"Session metrics: {session_metrics}", session_id)
    debug_log("=" * 25, session_id)

    # Render using widget system
    output = render_status_line_with_config(context)
    print(output, end="")


if __name__ == "__main__":
    main()
