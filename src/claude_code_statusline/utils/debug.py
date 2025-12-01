"""Debug logging utilities."""

import os
import sys
import time


def debug_log(message: str, session_id: str = "", transcript_path: str = "") -> None:
    """Log debug messages to per-session debug log files if debug mode is enabled.

    Args:
        message: Debug message to log
        session_id: Optional session identifier
        transcript_path: Optional path to transcript (used to extract session ID)
    """
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

    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    log_file = os.path.join(logs_dir, f"statusline_debug_{effective_session_id}.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    session_prefix = f"[{session_id}] " if session_id else ""
    log_message = f"[{timestamp}] {session_prefix}{message}\n"

    try:
        os.makedirs(logs_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_message)
    except OSError:
        print(
            f"DEBUG (couldn't write to {log_file}): {session_prefix}{message}",
            file=sys.stderr,
        )
