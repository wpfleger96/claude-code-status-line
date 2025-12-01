import pytest

from claude_code_statusline.parsers.jsonl import parse_transcript


@pytest.mark.integration
class TestRealSessionParsing:
    """Test parsing with real Claude Code session files."""

    def test_parses_basic_session(self, basic_session_file):
        """Test parsing a simple real session."""
        result = parse_transcript(str(basic_session_file))

        assert result.is_jsonl is True
        assert result.context_chars > 0

    def test_compact_boundary_excludes_old_content(self, compact_session_file):
        """Critical: verify content before compact boundary is NOT counted."""
        result = parse_transcript(str(compact_session_file))

        assert result.boundaries_found > 0
        assert result.is_jsonl is True
        # After compact boundary, context_chars should be less than total file
        assert result.context_chars < result.total_file_chars

    def test_image_not_inflating_token_count(self, image_session_file):
        """Critical: verify base64 images don't inflate character count."""
        result = parse_transcript(str(image_session_file))

        assert result.is_jsonl is True

        file_size = image_session_file.stat().st_size

        assert result.context_chars < (file_size * 0.5)

    def test_forked_session_extracts_session_id(self, forked_session_file):
        """Forked sessions have correct session_id parsed from JSONL."""
        result = parse_transcript(str(forked_session_file))

        assert result.is_jsonl is True
        assert result.session_id != ""


@pytest.mark.integration
class TestTranscriptEdgeCases:
    """Test edge cases in transcript parsing."""

    def test_handles_missing_file(self, tmp_path):
        result = parse_transcript(str(tmp_path / "nonexistent.jsonl"))
        assert result.context_chars == 0
        assert result.is_jsonl is False

    def test_handles_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        result = parse_transcript(str(empty_file))
        assert result.is_jsonl is False
