"""Unit tests for CLI install helpers."""

from claude_code_statusline.cli import commands


def test_migrates_legacy_config(tmp_path, monkeypatch):
    """A pre-rename config is copied to the new location on install."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    legacy = tmp_path / "claude-statusline" / "config.yaml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("version: 2\n")

    message = commands._migrate_legacy_config()

    new = tmp_path / "claude-code-statusline" / "config.yaml"
    assert new.read_text() == "version: 2\n"
    assert message is not None


def test_no_migration_when_new_config_exists(tmp_path, monkeypatch):
    """An existing new-location config is never overwritten."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    new = tmp_path / "claude-code-statusline" / "config.yaml"
    new.parent.mkdir(parents=True)
    new.write_text("version: 2\nwidgets: {}\n")
    legacy = tmp_path / "claude-statusline" / "config.yaml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("version: 2\nlegacy\n")

    assert commands._migrate_legacy_config() is None
    assert new.read_text() == "version: 2\nwidgets: {}\n"


def test_no_migration_without_legacy_config(tmp_path, monkeypatch):
    """No legacy config means nothing to migrate."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert commands._migrate_legacy_config() is None
