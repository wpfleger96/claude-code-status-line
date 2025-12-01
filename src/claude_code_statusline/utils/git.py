"""Git command execution utilities."""

import re
import subprocess

from typing import Optional

from ..types import GitStatus


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
    """Get comprehensive git repository status.

    Args:
        cwd: Working directory to check git status in

    Returns:
        GitStatus with branch, changes, and worktree info
    """
    # Check if in a git repo
    git_dir = _run_git(["rev-parse", "--git-dir"], cwd=cwd)
    if git_dir is None:
        return GitStatus(is_git_repo=False)

    # Get branch name
    branch = _run_git(["branch", "--show-current"], cwd=cwd)

    # Get changes (insertions and deletions)
    insertions = 0
    deletions = 0

    # Unstaged changes
    unstaged = _run_git(["diff", "--shortstat"], cwd=cwd)
    if unstaged:
        insertions += _parse_insertions(unstaged)
        deletions += _parse_deletions(unstaged)

    # Staged changes
    staged = _run_git(["diff", "--cached", "--shortstat"], cwd=cwd)
    if staged:
        insertions += _parse_insertions(staged)
        deletions += _parse_deletions(staged)

    # Get worktree name if in a worktree
    worktree = None
    worktree_list = _run_git(["worktree", "list"], cwd=cwd)
    if worktree_list and cwd:
        for line in worktree_list.split("\n"):
            if cwd in line:
                # Extract worktree name from path
                parts = line.split()
                if len(parts) >= 3:
                    worktree_path = parts[0]
                    worktree = worktree_path.rstrip("/").split("/")[-1]
                break

    return GitStatus(
        branch=branch,
        insertions=insertions,
        deletions=deletions,
        worktree=worktree,
        is_git_repo=True,
    )


def _parse_insertions(stat_output: str) -> int:
    """Parse insertions from git diff --shortstat output."""
    match = re.search(r"(\d+) insertion", stat_output)
    return int(match.group(1)) if match else 0


def _parse_deletions(stat_output: str) -> int:
    """Parse deletions from git diff --shortstat output."""
    match = re.search(r"(\d+) deletion", stat_output)
    return int(match.group(1)) if match else 0
