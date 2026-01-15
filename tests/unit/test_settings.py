"""Unit tests for settings utility."""

import json

from claude_code_statusline.utils.settings import (
    configure_statusline,
    remove_statusline,
)


class TestConfigureStatusline:
    """Tests for configure_statusline function."""

    def test_adds_statusline_config(self, tmp_path, monkeypatch):
        """Core behavior: statusLine is correctly configured."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({}))

        monkeypatch.setattr(
            "claude_code_statusline.utils.settings.get_settings_path",
            lambda: settings_file,
        )

        success, _ = configure_statusline()

        assert success is True

        result = json.loads(settings_file.read_text())
        assert "statusLine" in result
        assert result["statusLine"]["type"] == "command"
        assert result["statusLine"]["command"] == "claude-statusline"
        assert result["statusLine"]["padding"] == 0

    def test_preserves_other_settings(self, tmp_path, monkeypatch):
        """Critical: Don't break user's other Claude Code settings."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "someOtherSetting": True,
                    "anotherKey": {"nested": "value"},
                    "statusLine": {
                        "type": "command",
                        "command": "old-command",
                    },
                }
            )
        )

        monkeypatch.setattr(
            "claude_code_statusline.utils.settings.get_settings_path",
            lambda: settings_file,
        )

        success, _ = configure_statusline()

        assert success is True

        result = json.loads(settings_file.read_text())
        assert result["someOtherSetting"] is True
        assert result["anotherKey"]["nested"] == "value"
        assert result["statusLine"]["command"] == "claude-statusline"


class TestRemoveStatusline:
    """Tests for remove_statusline function."""

    def test_removes_statusline(self, tmp_path, monkeypatch):
        """Core behavior: statusLine is removed."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "statusLine": {
                        "type": "command",
                        "command": "claude-statusline",
                    }
                }
            )
        )

        monkeypatch.setattr(
            "claude_code_statusline.utils.settings.get_settings_path",
            lambda: settings_file,
        )

        success, _ = remove_statusline()

        assert success is True

        result = json.loads(settings_file.read_text())
        assert "statusLine" not in result

    def test_preserves_other_settings(self, tmp_path, monkeypatch):
        """Critical: Don't break user's other Claude Code settings."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "someOtherSetting": True,
                    "anotherKey": {"nested": "value"},
                    "statusLine": {
                        "type": "command",
                        "command": "claude-statusline",
                    },
                }
            )
        )

        monkeypatch.setattr(
            "claude_code_statusline.utils.settings.get_settings_path",
            lambda: settings_file,
        )

        success, _ = remove_statusline()

        assert success is True

        result = json.loads(settings_file.read_text())
        assert result["someOtherSetting"] is True
        assert result["anotherKey"]["nested"] == "value"
        assert "statusLine" not in result
