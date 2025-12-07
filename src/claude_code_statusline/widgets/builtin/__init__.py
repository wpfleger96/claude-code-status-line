"""Built-in widgets for status line.

Importing this module registers all built-in widgets with the registry.
"""

from .context import ContextPercentageWidget, ContextTokensWidget
from .cost import CostWidget, LinesAddedWidget, LinesChangedWidget, LinesRemovedWidget
from .directory import DirectoryWidget
from .git import GitBranchWidget, GitChangesWidget, GitWorktreeWidget
from .model import ModelWidget
from .separator import SeparatorWidget
from .session import SessionClockWidget, SessionIdWidget
from .subscription import SubscriptionWidget

__all__ = [
    "SeparatorWidget",
    "ModelWidget",
    "DirectoryWidget",
    "ContextPercentageWidget",
    "ContextTokensWidget",
    "CostWidget",
    "LinesAddedWidget",
    "LinesChangedWidget",
    "LinesRemovedWidget",
    "SessionIdWidget",
    "SessionClockWidget",
    "GitBranchWidget",
    "GitChangesWidget",
    "GitWorktreeWidget",
    "SubscriptionWidget",
]
