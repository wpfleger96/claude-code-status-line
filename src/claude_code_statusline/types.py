"""Data types for Claude Code Status Line."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class SubscriptionInfo:
    """Subscription information from Claude credentials."""

    is_subscription: bool = False
    subscription_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None


@dataclass
class TokenMetrics:
    """Token usage extracted from JSONL message.usage fields."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    context_length: int = 0  # Current context size from most recent message
    transcript_exists: bool = False  # Whether transcript file was found and readable
    session_id: str = (
        ""  # Last sessionId from transcript (current session after compaction)
    )
    had_compact_boundary: bool = False  # Whether compact boundary was detected


@dataclass
class GitStatus:
    """Git repository status information."""

    branch: Optional[str] = None
    insertions: int = 0
    deletions: int = 0
    worktree: Optional[str] = None
    is_git_repo: bool = False


@dataclass
class SessionMetrics:
    """Session timing and duration metrics."""

    start_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    duration_seconds: int = 0


@dataclass
class RenderContext:
    """Context passed to widgets during rendering."""

    data: dict[str, Any]  # JSON input from Claude Code
    token_metrics: Optional[TokenMetrics] = None
    git_status: Optional[GitStatus] = None
    session_metrics: Optional[SessionMetrics] = None
    subscription_info: Optional[SubscriptionInfo] = None
    terminal_width: Optional[int] = None
    is_preview: bool = False
