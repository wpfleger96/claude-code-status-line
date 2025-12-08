import json
import tempfile

import pytest

from claude_code_statusline.parsers.jsonl import (
    ParsedTranscript,
    calculate_total_tokens,
    extract_message_content_chars,
    is_real_compact_boundary,
    should_exclude_line,
)
from claude_code_statusline.parsers.tokens import parse_transcript


@pytest.mark.unit
class TestCompactBoundaryDetection:
    """Test compact boundary detection - critical for knowing where to start counting."""

    def test_valid_compact_boundary(self):
        data = {
            "type": "system",
            "subtype": "compact_boundary",
            "compactMetadata": {"trigger": "manual"},
        }
        assert is_real_compact_boundary(data) is True

    def test_missing_compact_metadata_is_not_boundary(self):
        """Ensure we don't falsely detect boundaries without proper metadata."""
        data = {"type": "system", "subtype": "compact_boundary"}
        assert is_real_compact_boundary(data) is False


@pytest.mark.unit
class TestLineExclusion:
    """Test which lines are excluded from token counting."""

    def test_excludes_summary_type(self):
        """Summary lines are UI-only, not sent to Claude."""
        data = {"type": "summary"}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_excludes_system_type(self):
        """System lines are metadata, not sent to Claude."""
        data = {"type": "system"}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_includes_toolUseResult(self):
        """Tool results contain message content and should be counted."""
        data = {"type": "user", "toolUseResult": {"output": "result"}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is False

    def test_excludes_snapshot(self):
        """File snapshots are metadata, not counted."""
        data = {"type": "file-history-snapshot", "snapshot": {}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_includes_isMeta_flag(self):
        """Lines with isMeta contain message content and should be counted."""
        data = {"type": "user", "isMeta": True}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is False

    def test_includes_thinkingMetadata(self):
        """Lines with thinkingMetadata contain message content and should be counted."""
        data = {"type": "assistant", "thinkingMetadata": {"duration": 1000}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is False

    def test_excludes_leafUuid(self):
        """Leaf UUID tracking is metadata, not counted."""
        data = {"type": "user", "leafUuid": "abc-123"}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_includes_valid_user_message(self):
        """Regular user messages SHOULD be counted."""
        data = {"type": "user", "message": {"role": "user", "content": "Hello"}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is False


@pytest.mark.unit
class TestImageFiltering:
    """Test that base64 images don't inflate token count."""

    def test_filters_out_base64_images(self):
        """Critical: base64 images should NOT be counted as text tokens."""
        large_base64 = "A" * 100000
        data = {
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Here is an image:"},
                    {
                        "type": "image",
                        "source": {"type": "base64", "data": large_base64},
                    },
                ],
            }
        }

        chars = extract_message_content_chars(data)

        assert chars < 1000

    def test_counts_text_alongside_images(self):
        """Text content next to images should still be counted."""
        data = {
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Description of the image"},
                    {"type": "image", "source": {"type": "base64", "data": "abc123"}},
                ],
            }
        }

        chars = extract_message_content_chars(data)
        assert chars > 0


@pytest.mark.unit
class TestTokenCalculation:
    """Test the token calculation formula."""

    def test_includes_system_overhead(self):
        """Verify total includes conversation + overhead."""
        transcript = ParsedTranscript(context_chars=4000)
        tokens = calculate_total_tokens(transcript)

        conversation_tokens = int(4000 // 3.31)
        assert tokens > conversation_tokens

    def test_zero_context_still_has_overhead(self):
        """Even empty sessions have system overhead."""
        transcript = ParsedTranscript(context_chars=0)
        tokens = calculate_total_tokens(transcript)

        assert tokens > 0


@pytest.mark.unit
class TestTokenParserCompactBoundary:
    """Test that tokens.py parser handles compact boundaries correctly."""

    def test_resets_token_counts_on_compact_boundary(self):
        """Critical: tokens before compact boundary should not be counted."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # Message with usage before compact boundary
            f.write(
                json.dumps(
                    {
                        "sessionId": "old-session-123",
                        "message": {
                            "usage": {
                                "input_tokens": 10000,
                                "output_tokens": 5000,
                                "cache_read_input_tokens": 2000,
                            }
                        },
                        "timestamp": "2025-01-01T10:00:00Z",
                    }
                )
                + "\n"
            )

            # Compact boundary
            f.write(
                json.dumps(
                    {
                        "sessionId": "old-session-123",
                        "type": "system",
                        "subtype": "compact_boundary",
                        "compactMetadata": {"trigger": "manual"},
                        "timestamp": "2025-01-01T11:00:00Z",
                    }
                )
                + "\n"
            )

            # Message with usage after compact boundary (should be counted)
            f.write(
                json.dumps(
                    {
                        "sessionId": "new-session-456",
                        "message": {
                            "usage": {
                                "input_tokens": 100,
                                "output_tokens": 50,
                                "cache_read_input_tokens": 20,
                            },
                            "stop_reason": "end_turn",
                        },
                        "timestamp": "2025-01-01T12:00:00Z",
                    }
                )
                + "\n"
            )

            transcript_path = f.name

        try:
            token_metrics, _ = parse_transcript(transcript_path)

            # Only tokens after boundary should be counted
            assert token_metrics.input_tokens == 100
            assert token_metrics.output_tokens == 50
            assert token_metrics.cached_tokens == 20
            assert token_metrics.total_tokens == 170

            # Should detect compact boundary
            assert token_metrics.had_compact_boundary is True

            # Should track the new session ID
            assert token_metrics.session_id == "new-session-456"
        finally:
            import os

            os.unlink(transcript_path)

    def test_no_compact_boundary_counts_all_tokens(self):
        """Normal sessions without compaction should count all tokens."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "session-123",
                        "message": {
                            "usage": {"input_tokens": 100, "output_tokens": 50},
                            "stop_reason": "end_turn",
                        },
                        "timestamp": "2025-01-01T10:00:00Z",
                    }
                )
                + "\n"
            )

            f.write(
                json.dumps(
                    {
                        "sessionId": "session-123",
                        "message": {
                            "usage": {"input_tokens": 200, "output_tokens": 100},
                            "stop_reason": "end_turn",
                        },
                        "timestamp": "2025-01-01T11:00:00Z",
                    }
                )
                + "\n"
            )

            transcript_path = f.name

        try:
            token_metrics, _ = parse_transcript(transcript_path)

            # Should count all tokens
            assert token_metrics.input_tokens == 300
            assert token_metrics.output_tokens == 150
            assert token_metrics.total_tokens == 450

            # Should not detect compact boundary
            assert token_metrics.had_compact_boundary is False

            # Should track session ID
            assert token_metrics.session_id == "session-123"
        finally:
            import os

            os.unlink(transcript_path)
