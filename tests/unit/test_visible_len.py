"""Unit tests for visible_len ANSI stripping."""

from claude_code_statusline.utils.colors import colorize, visible_len


class TestVisibleLen:
    def test_plain_text(self):
        assert visible_len("hello world") == 11

    def test_empty_string(self):
        assert visible_len("") == 0

    def test_strips_single_color(self):
        colored = colorize("hello", "red")
        assert visible_len(colored) == 5

    def test_strips_bold_color(self):
        colored = colorize("test", "cyan", bold=True)
        assert visible_len(colored) == 4

    def test_strips_multiple_sequences(self):
        text = colorize("foo", "red") + " | " + colorize("bar", "green")
        assert visible_len(text) == 9  # "foo" + " | " + "bar"

    def test_no_color_passthrough(self):
        assert visible_len("no color") == 8

    def test_dim_code(self):
        text = "\033[2m|\033[0m"
        assert visible_len(text) == 1

    def test_progress_bar_characters(self):
        text = colorize("●●●○○○", "green")
        assert visible_len(text) == 6
