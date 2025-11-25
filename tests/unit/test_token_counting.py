import pytest
from claude_code_statusline.common import (
    is_real_compact_boundary,
    should_exclude_line,
    extract_message_content_chars,
    calculate_total_tokens,
    ParsedTranscript,
)
from claude_code_statusline.calibrate import _find_compact_boundary_line


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

    def test_finds_last_boundary_when_multiple(self):
        """Critical: with multiple compactions, only count after the LAST one."""
        lines = [
            '{"type":"user","message":{"content":"Very old"}}',
            '{"type":"system","subtype":"compact_boundary","compactMetadata":{"trigger":"auto"}}',
            '{"type":"user","message":{"content":"Old"}}',
            '{"type":"system","subtype":"compact_boundary","compactMetadata":{"trigger":"manual"}}',
            '{"type":"user","message":{"content":"Current"}}',
        ]
        assert _find_compact_boundary_line(lines) == 4


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

    def test_excludes_toolUseResult(self):
        """Tool results are stored separately, not in main context."""
        data = {"type": "user", "toolUseResult": {"output": "result"}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_excludes_snapshot(self):
        """File snapshots are metadata, not counted."""
        data = {"type": "file-history-snapshot", "snapshot": {}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_excludes_isMeta_flag(self):
        """Lines marked as meta are not sent to Claude."""
        data = {"type": "user", "isMeta": True}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

    def test_excludes_thinkingMetadata(self):
        """Thinking metadata is not sent to Claude."""
        data = {"type": "assistant", "thinkingMetadata": {"duration": 1000}}
        should_exclude, _ = should_exclude_line(data)
        assert should_exclude is True

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

    def test_includes_system_overhead_and_reserved(self):
        """Verify total includes conversation + overhead + reserved."""
        transcript = ParsedTranscript(context_chars=4000)
        tokens = calculate_total_tokens(transcript)

        conversation_tokens = 4000 // 4
        assert tokens > conversation_tokens

    def test_zero_context_still_has_overhead(self):
        """Even empty sessions have system overhead and reserved."""
        transcript = ParsedTranscript(context_chars=0)
        tokens = calculate_total_tokens(transcript)

        assert tokens > 0
