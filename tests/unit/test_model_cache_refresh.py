from unittest.mock import MagicMock

import pytest

from claude_code_statusline.utils import models


@pytest.fixture
def thread_class(monkeypatch):
    """Replace the thread class so a refresh is observed but never started."""
    thread_class = MagicMock()
    monkeypatch.setattr(
        "claude_code_statusline.utils.models.threading.Thread", thread_class
    )
    monkeypatch.setattr(models, "_refresh_started", False)
    return thread_class


@pytest.mark.unit
def test_repeated_lookups_with_stale_cache_start_one_refresh(monkeypatch, thread_class):
    monkeypatch.setattr(models, "_is_cache_stale", lambda: True)

    for _ in range(100):
        models.get_context_limit("claude-sonnet-4")

    thread_class.assert_called_once()
    thread_class.return_value.start.assert_called_once()


@pytest.mark.unit
def test_lookup_with_fresh_cache_starts_no_refresh(monkeypatch, thread_class):
    monkeypatch.setattr(models, "_is_cache_stale", lambda: False)

    models.get_context_limit("claude-sonnet-4")

    thread_class.assert_not_called()
