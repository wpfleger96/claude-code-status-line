"""Data types for Claude Code Status Line."""

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenMetrics:
    """Token usage extracted from JSONL message.usage fields."""

    context_length: int = 0
    transcript_exists: bool = False
    session_id: str = ""
    slug: str = ""
    had_compact_boundary: bool = False


@dataclass
class GitStatus:
    """Git repository status information."""

    branch: str | None = None
    insertions: int = 0
    deletions: int = 0
    worktree: str | None = None
    repo_name: str | None = None
    is_git_repo: bool = False


@dataclass
class ContextWindow:
    """Context window data from Claude Code status payload."""

    context_window_size: int = 0
    current_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    used_percentage: float | None = None

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
    token_metrics: TokenMetrics | None = None
    git_status: GitStatus | None = None
    duration_seconds: int | None = None
    terminal_width: int | None = None
    context_window: ContextWindow | None = None
