"""Git command execution utilities."""

import re
import subprocess
import time

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ..types import GitStatus

# Module-level cache for git status
_git_cache: Optional[tuple[float, Optional[str], GitStatus]] = None
GIT_CACHE_TTL = 2.0  # seconds


def _run_git(args: list[str], cwd: Optional[str] = None) -> Optional[str]:
    """Run git command and return stdout, or None on error.

    Args:
        args: Git command arguments
        cwd: Working directory for git command

    Returns:
        Command stdout or None if command failed
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def get_git_status(cwd: Optional[str] = None) -> GitStatus:
    """Get comprehensive git repository status with 2-second TTL cache.

    Args:
        cwd: Working directory to check git status in

    Returns:
        GitStatus with branch, changes, and worktree info
    """
    global _git_cache

    now = time.monotonic()

    if _git_cache is not None:
        cache_time, cache_cwd, cached_status = _git_cache
        if cache_cwd == cwd and (now - cache_time) < GIT_CACHE_TTL:
            return cached_status

    git_dir = _run_git(["rev-parse", "--git-dir"], cwd=cwd)
    if git_dir is None:
        status = GitStatus(is_git_repo=False)
        _git_cache = (now, cwd, status)
        return status

    # Run remaining commands in parallel for faster execution
    with ThreadPoolExecutor(max_workers=4) as executor:
        branch_future = executor.submit(_run_git, ["branch", "--show-current"], cwd)
        unstaged_future = executor.submit(_run_git, ["diff", "--shortstat"], cwd)
        staged_future = executor.submit(
            _run_git, ["diff", "--cached", "--shortstat"], cwd
        )
        worktree_future = executor.submit(_run_git, ["worktree", "list"], cwd)

        branch = branch_future.result()
        unstaged = unstaged_future.result()
        staged = staged_future.result()
        worktree_list = worktree_future.result()

    insertions = 0
    deletions = 0

    if unstaged:
        insertions += _parse_insertions(unstaged)
        deletions += _parse_deletions(unstaged)

    if staged:
        insertions += _parse_insertions(staged)
        deletions += _parse_deletions(staged)

    worktree = None
    if worktree_list and cwd:
        for line in worktree_list.split("\n"):
            if cwd in line:
                parts = line.split()
                if len(parts) >= 3:
                    worktree_path = parts[0]
                    worktree = worktree_path.rstrip("/").split("/")[-1]
                break

    status = GitStatus(
        branch=branch,
        insertions=insertions,
        deletions=deletions,
        worktree=worktree,
        is_git_repo=True,
    )

    _git_cache = (now, cwd, status)
    return status


def _parse_insertions(stat_output: str) -> int:
    """Parse insertions from git diff --shortstat output."""
    match = re.search(r"(\d+) insertion", stat_output)
    return int(match.group(1)) if match else 0


def _parse_deletions(stat_output: str) -> int:
    """Parse deletions from git diff --shortstat output."""
    match = re.search(r"(\d+) deletion", stat_output)
    return int(match.group(1)) if match else 0
