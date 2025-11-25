import json
import pytest
from claude_code_statusline.statusline import parse_input_data
from claude_code_statusline.common import parse_transcript


@pytest.mark.integration
class TestPayloadParsing:
    """Test stdin payload parsing including session_id extraction."""

    def test_extracts_session_id_from_payload(self, mock_stdin, sample_input_payload):
        """Critical: session_id must be extracted for forked session support."""
        mock_stdin(json.dumps(sample_input_payload))

        cwd, transcript_path, model_id, model_name, cost_data, version, session_id = (
            parse_input_data()
        )

        assert session_id == "abc123-def456"

    def test_handles_missing_session_id(self, mock_stdin):
        """Backwards compatibility: old payloads without session_id."""
        payload = {"workspace": {"current_dir": "/test"}, "model": {"id": "test"}}
        mock_stdin(json.dumps(payload))

        cwd, transcript_path, model_id, model_name, cost_data, version, session_id = (
            parse_input_data()
        )

        assert session_id == ""

    def test_handles_invalid_json(self, mock_stdin):
        """Graceful degradation on malformed input."""
        mock_stdin("not valid json")

        cwd, transcript_path, model_id, model_name, cost_data, version, session_id = (
            parse_input_data()
        )

        assert cwd == ""
        assert session_id == ""


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

        cwd, transcript_path, model_id, model_name, cost_data, version, session_id = (
            parse_input_data()
        )

        assert session_id == "payload-session-id"

    def test_falls_back_to_jsonl_session_id(self, forked_session_file):
        """When payload lacks session_id, fall back to JSONL parsing."""
        transcript = parse_transcript(str(forked_session_file))

        assert transcript.session_id != ""
