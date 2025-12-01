import json

import pytest

from claude_code_statusline.parsers.jsonl import parse_transcript
from claude_code_statusline.statusline import parse_input_data


@pytest.mark.integration
class TestPayloadParsing:
    """Test stdin payload parsing including session_id extraction."""

    def test_extracts_session_id_from_payload(self, mock_stdin, sample_input_payload):
        """Critical: session_id must be extracted for forked session support."""
        mock_stdin(json.dumps(sample_input_payload))

        data = parse_input_data()

        assert data.get("session_id") == "abc123-def456"

    def test_handles_missing_session_id(self, mock_stdin):
        """Backwards compatibility: old payloads without session_id."""
        payload = {"workspace": {"current_dir": "/test"}, "model": {"id": "test"}}
        mock_stdin(json.dumps(payload))

        data = parse_input_data()

        assert data.get("session_id", "") == ""

    def test_handles_invalid_json(self, mock_stdin):
        """Graceful degradation on malformed input."""
        mock_stdin("not valid json")

        data = parse_input_data()

        assert data.get("workspace", {}).get("current_dir", "") == ""
        assert data.get("session_id", "") == ""


@pytest.mark.integration
class TestSessionIdFallback:
    """Test session_id prioritization: payload > JSONL fallback."""

    def test_payload_session_id_takes_priority(self, mock_stdin, forked_session_file):
        """When payload has session_id, use it over JSONL content."""
        payload = {
            "session_id": "payload-session-id",
            "transcript_path": str(forked_session_file),
            "workspace": {"current_dir": "/test"},
            "model": {"id": "claude-sonnet-4-5"},
        }
        mock_stdin(json.dumps(payload))

        data = parse_input_data()

        assert data.get("session_id") == "payload-session-id"

    def test_falls_back_to_jsonl_session_id(self, forked_session_file):
        """When payload lacks session_id, fall back to JSONL parsing."""
        transcript = parse_transcript(str(forked_session_file))

        assert transcript.session_id != ""
