from unittest.mock import patch

import pytest

from claude_code_statusline.statusline import resolve_terminal_title
from claude_code_statusline.types import TokenMetrics
from claude_code_statusline.utils.terminal import set_terminal_title


@pytest.mark.unit
class TestSetTerminalTitle:
    def test_returns_false_when_gpg_tty_not_set(self):
        with patch.dict("os.environ", {}, clear=True):
            assert set_terminal_title("test") is False

    def test_returns_false_when_title_empty_after_sanitize(self):
        with patch.dict("os.environ", {"GPG_TTY": "/dev/pts/0"}):
            assert set_terminal_title("\x1b\x07\x0a") is False

    def test_returns_false_when_not_a_tty(self):
        with (
            patch.dict("os.environ", {"GPG_TTY": "/dev/pts/0"}),
            patch("claude_code_statusline.utils.terminal.os.open", return_value=3),
            patch(
                "claude_code_statusline.utils.terminal.os.isatty", return_value=False
            ),
            patch("claude_code_statusline.utils.terminal.os.close"),
        ):
            assert set_terminal_title("test") is False

    def test_returns_false_on_open_oserror(self):
        with (
            patch.dict("os.environ", {"GPG_TTY": "/dev/pts/0"}),
            patch("claude_code_statusline.utils.terminal.os.open", side_effect=OSError),
        ):
            assert set_terminal_title("test") is False

    def test_writes_osc2_sequence_on_success(self):
        with (
            patch.dict("os.environ", {"GPG_TTY": "/dev/pts/0"}),
            patch("claude_code_statusline.utils.terminal.os.open", return_value=3),
            patch("claude_code_statusline.utils.terminal.os.isatty", return_value=True),
            patch("claude_code_statusline.utils.terminal.os.write") as mock_write,
            patch("claude_code_statusline.utils.terminal.os.close"),
        ):
            result = set_terminal_title("my-session")
            assert result is True
            mock_write.assert_called_once_with(3, b"\033]2;my-session\007")

    def test_strips_control_characters(self):
        with (
            patch.dict("os.environ", {"GPG_TTY": "/dev/pts/0"}),
            patch("claude_code_statusline.utils.terminal.os.open", return_value=3),
            patch("claude_code_statusline.utils.terminal.os.isatty", return_value=True),
            patch("claude_code_statusline.utils.terminal.os.write") as mock_write,
            patch("claude_code_statusline.utils.terminal.os.close"),
        ):
            set_terminal_title("te\x1b\x07st\x00na\x9cme")
            mock_write.assert_called_once_with(3, b"\033]2;testname\007")

    def test_truncates_to_100_chars(self):
        with (
            patch.dict("os.environ", {"GPG_TTY": "/dev/pts/0"}),
            patch("claude_code_statusline.utils.terminal.os.open", return_value=3),
            patch("claude_code_statusline.utils.terminal.os.isatty", return_value=True),
            patch("claude_code_statusline.utils.terminal.os.write") as mock_write,
            patch("claude_code_statusline.utils.terminal.os.close"),
        ):
            long_title = "a" * 200
            set_terminal_title(long_title)
            written = mock_write.call_args[0][1]
            # OSC2 prefix \x1b]2; (4 bytes) + 100 chars + BEL (1 byte) = 105 bytes
            assert len(written) == 105


@pytest.mark.unit
class TestResolveTerminalTitle:
    def test_returns_session_name_when_present(self):
        data = {"session_name": "my-session"}
        result = resolve_terminal_title(data, None)
        assert result == "my-session"

    def test_returns_slug_when_no_session_name(self):
        data: dict[str, object] = {}
        metrics = TokenMetrics(slug="auto-generated-slug")
        result = resolve_terminal_title(data, metrics)
        assert result == "auto-generated-slug"

    def test_session_name_takes_precedence_over_slug(self):
        data = {"session_name": "explicit-name"}
        metrics = TokenMetrics(slug="auto-slug")
        result = resolve_terminal_title(data, metrics)
        assert result == "explicit-name"

    def test_returns_git_branch_when_no_name_or_slug(self):
        data = {"workspace": {"current_dir": "/some/path"}}
        metrics = TokenMetrics()
        with patch("claude_code_statusline.statusline.get_git_status") as mock_git:
            mock_git.return_value.branch = "feature/my-branch"
            result = resolve_terminal_title(data, metrics)
            assert result == "feature/my-branch"

    def test_returns_empty_when_no_data(self):
        data: dict[str, object] = {}
        metrics = TokenMetrics()
        with patch("claude_code_statusline.statusline.get_git_status") as mock_git:
            mock_git.return_value.branch = None
            result = resolve_terminal_title(data, metrics)
            assert result == ""

    def test_returns_empty_with_none_metrics(self):
        data: dict[str, object] = {}
        result = resolve_terminal_title(data, None)
        assert result == ""
