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
    context_length: int = 0
    transcript_exists: bool = False
    session_id: str = ""
    had_compact_boundary: bool = False


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
class ContextWindow:
    """Context window data from Claude Code status payload."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    context_window_size: int = 0
    current_input_tokens: Optional[int] = None
    current_output_tokens: Optional[int] = None
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None

    @property
    def current_context_tokens(self) -> int:
        """Calculate current context tokens per official formula.

        Formula: input_tokens + cache_creation_input_tokens + cache_read_input_tokens
        """
        if self.current_input_tokens is None:
            return 0
        return (
            (self.current_input_tokens or 0)
            + (self.cache_creation_input_tokens or 0)
            + (self.cache_read_input_tokens or 0)
        )

    @property
    def has_current_usage(self) -> bool:
        """Check if current_usage data is available."""
        return self.current_input_tokens is not None


@dataclass
class RenderContext:
    """Context passed to widgets during rendering."""

    data: dict[str, Any]
    token_metrics: Optional[TokenMetrics] = None
    git_status: Optional[GitStatus] = None
    session_metrics: Optional[SessionMetrics] = None
    subscription_info: Optional[SubscriptionInfo] = None
    terminal_width: Optional[int] = None
    is_preview: bool = False
    context_window: Optional[ContextWindow] = None
