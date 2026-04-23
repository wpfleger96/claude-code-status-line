#!/usr/bin/env python3

import argparse
import json
import os
import sys

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, cast

from .config.loader import load_config_file
from .parsers.tokens import parse_transcript
from .renderer import render_status_line_with_config
from .types import ContextWindow, RenderContext, TokenMetrics
from .utils.debug import debug_log
from .utils.git import get_git_status
from .utils.models import prefetch_model_data
from .utils.terminal import detect_terminal_width, set_terminal_title


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
    workspace = (data.get("workspace") or {}).get("current_dir", "")

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

    return transcript_path


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


def resolve_duration_seconds(
    data: dict[str, Any], transcript_duration: Optional[int]
) -> Optional[int]:
    """Resolve session duration, preferring payload over transcript.

    Priority:
    1. cost.total_duration_ms from payload (wall-clock time)
    2. transcript_duration from timestamp parsing (fallback)

    Args:
        data: JSON input data from Claude Code
        transcript_duration: Duration in seconds from transcript timestamps

    Returns:
        Duration in seconds, or None if neither source available
    """
    cost = data.get("cost") or {}
    total_duration_ms = cost.get("total_duration_ms")
    if total_duration_ms and total_duration_ms > 0:
        return int(total_duration_ms // 1000)
    return transcript_duration


def extract_context_window(data: dict[str, Any]) -> Optional[ContextWindow]:
    """Extract context_window data from Claude Code payload.

    Args:
        data: JSON input data from Claude Code

    Returns:
        ContextWindow if data is present and valid, None otherwise
    """
    cw = data.get("context_window")
    if not cw or not isinstance(cw, dict):
        return None

    if "context_window_size" not in cw:
        return None

    current_usage = cw.get("current_usage") or {}

    return ContextWindow(
        total_input_tokens=cw.get("total_input_tokens", 0),
        total_output_tokens=cw.get("total_output_tokens", 0),
        context_window_size=cw.get("context_window_size", 0),
        current_input_tokens=current_usage.get("input_tokens"),
        current_output_tokens=current_usage.get("output_tokens"),
        cache_creation_input_tokens=current_usage.get("cache_creation_input_tokens"),
        cache_read_input_tokens=current_usage.get("cache_read_input_tokens"),
        used_percentage=cw.get("used_percentage"),
    )


def resolve_terminal_title(
    data: dict[str, Any], token_metrics: Optional[TokenMetrics]
) -> str:
    session_name: str = data.get("session_name", "")
    if session_name:
        return session_name

    if token_metrics and token_metrics.slug:
        return token_metrics.slug

    workspace = (data.get("workspace") or {}).get("current_dir", "")
    if workspace:
        git_status = get_git_status(workspace)
        if git_status.branch:
            return git_status.branch

    return ""


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser with subcommands.

    Returns:
        Configured argument parser
    """
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="claude-statusline",
        description="Claude Code statusline - context usage tracking for Claude Code",
        epilog="When no subcommand is provided, reads JSON from stdin and outputs the statusline.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    install_parser = subparsers.add_parser(
        "install",
        help="Configure Claude Code to use claude-statusline",
    )
    install_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt for existing config",
    )

    subparsers.add_parser(
        "uninstall",
        help="Remove claude-statusline from Claude Code configuration",
    )

    subparsers.add_parser(
        "doctor",
        help="Verify installation health",
    )

    return parser


def main() -> None:
    """Main entry point with widget-based rendering and parallel I/O."""
    parser = create_argument_parser()
    args = parser.parse_args()

    if args.command == "install":
        from .cli.commands import cmd_install

        sys.exit(cmd_install(force=args.yes))
    elif args.command == "uninstall":
        from .cli.commands import cmd_uninstall

        sys.exit(cmd_uninstall())
    elif args.command == "doctor":
        from .cli.commands import cmd_doctor

        sys.exit(cmd_doctor())

    data = parse_input_data()

    transcript_path = find_transcript_path(data)

    session_id = extract_session_id(data, transcript_path)

    if session_id:
        data["session_id"] = session_id

    context_window = extract_context_window(data)

    debug_log("=== SESSION START ===", session_id)
    debug_log(
        f"Working Directory: {(data.get('workspace') or {}).get('current_dir', '')}",
        session_id,
    )
    debug_log(f"Model ID: {(data.get('model') or {}).get('id', '')}", session_id)
    debug_log(f"Transcript Path: {transcript_path}", session_id)
    debug_log(f"Context window from payload: {context_window is not None}", session_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        transcript_future = executor.submit(parse_transcript, transcript_path)
        if not context_window or context_window.context_window_size == 0:
            executor.submit(prefetch_model_data)

        token_metrics, transcript_duration = transcript_future.result()

    if token_metrics.had_compact_boundary and token_metrics.session_id:
        data["session_id"] = token_metrics.session_id

    duration_seconds = resolve_duration_seconds(data, transcript_duration)

    terminal_width = detect_terminal_width()

    context = RenderContext(
        data=data,
        token_metrics=token_metrics,
        duration_seconds=duration_seconds,
        git_status=None,
        context_window=context_window,
        terminal_width=terminal_width,
    )

    debug_log(f"Token metrics: {token_metrics}", session_id)
    debug_log(f"Duration seconds: {duration_seconds}", session_id)
    debug_log("=" * 25, session_id)

    output = render_status_line_with_config(context)

    config = load_config_file()
    if config.terminal_title.enabled:
        title = resolve_terminal_title(data, token_metrics)
        if title:
            set_terminal_title(title)

    print(output, end="")


if __name__ == "__main__":
    main()
