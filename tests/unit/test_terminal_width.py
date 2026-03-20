"""Unit tests for terminal width detection."""

from unittest.mock import patch

from claude_code_statusline.utils.terminal import detect_terminal_width


class TestDetectTerminalWidth:
    def test_returns_width_from_stderr(self):
        with patch(
            "claude_code_statusline.utils.terminal.os.get_terminal_size"
        ) as mock_size:
            mock_size.return_value.columns = 120
            result = detect_terminal_width()
            assert result == 120

    def test_falls_back_to_tty_when_stderr_fails(self):
        with (
            patch(
                "claude_code_statusline.utils.terminal.os.get_terminal_size",
                side_effect=OSError,
            ),
            patch("claude_code_statusline.utils.terminal.os.open", return_value=3),
            patch("fcntl.ioctl", return_value=b"\x32\x00\x64\x00\x00\x00\x00\x00"),
            patch("claude_code_statusline.utils.terminal.os.close"),
        ):
            result = detect_terminal_width()
            assert result == 100

    def test_falls_back_to_columns_env(self):
        with (
            patch(
                "claude_code_statusline.utils.terminal.os.get_terminal_size",
                side_effect=OSError,
            ),
            patch(
                "claude_code_statusline.utils.terminal.os.open",
                side_effect=OSError,
            ),
            patch.dict(
                "claude_code_statusline.utils.terminal.os.environ",
                {"COLUMNS": "80"},
            ),
        ):
            result = detect_terminal_width()
            assert result == 80

    def test_returns_none_when_all_fail(self):
        with (
            patch(
                "claude_code_statusline.utils.terminal.os.get_terminal_size",
                side_effect=OSError,
            ),
            patch(
                "claude_code_statusline.utils.terminal.os.open",
                side_effect=OSError,
            ),
            patch.dict(
                "claude_code_statusline.utils.terminal.os.environ",
                {},
                clear=True,
            ),
        ):
            result = detect_terminal_width()
            assert result is None

    def test_ignores_zero_width_from_stderr(self):
        with (
            patch(
                "claude_code_statusline.utils.terminal.os.get_terminal_size"
            ) as mock_size,
            patch(
                "claude_code_statusline.utils.terminal.os.open",
                side_effect=OSError,
            ),
            patch.dict(
                "claude_code_statusline.utils.terminal.os.environ",
                {},
                clear=True,
            ),
        ):
            mock_size.return_value.columns = 0
            result = detect_terminal_width()
            assert result is None
