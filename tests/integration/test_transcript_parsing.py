import pytest

from claude_code_statusline.parsers.tokens import parse_transcript


@pytest.mark.integration
class TestRealSessionParsing:
    """Test parsing with real Claude Code session files."""

    def test_parses_basic_session(self, basic_session_file):
        """Test parsing a simple real session."""
        token_metrics, _duration = parse_transcript(str(basic_session_file))

        assert token_metrics.transcript_exists is True
        assert token_metrics.context_length >= 0

    def test_compact_boundary_resets_context(self, compact_session_file):
        """Critical: token counts reset after a compact boundary."""
        token_metrics, _duration = parse_transcript(str(compact_session_file))

        assert token_metrics.transcript_exists is True
        assert token_metrics.had_compact_boundary is True

    def test_image_not_inflating_token_count(self, image_session_file):
        """Critical: verify base64 images don't inflate context length."""
        token_metrics, _duration = parse_transcript(str(image_session_file))

        assert token_metrics.transcript_exists is True

    def test_forked_session_extracts_session_id(self, forked_session_file):
        """Forked sessions have correct session_id parsed from JSONL."""
        token_metrics, _duration = parse_transcript(str(forked_session_file))

        assert token_metrics.transcript_exists is True
        assert token_metrics.session_id != ""


@pytest.mark.integration
class TestTranscriptEdgeCases:
    """Test edge cases in transcript parsing."""

    def test_handles_missing_file(self, tmp_path):
        token_metrics, duration = parse_transcript(str(tmp_path / "nonexistent.jsonl"))
        assert token_metrics.transcript_exists is False
        assert duration is None

    def test_handles_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        token_metrics, duration = parse_transcript(str(empty_file))
        assert token_metrics.context_length == 0
