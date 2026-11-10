import json
import re

import pytest

from claude_code_statusline.config import loader
from claude_code_statusline.parsers.tokens import parse_transcript
from claude_code_statusline.renderer import render_status_line_with_config
from claude_code_statusline.statusline import parse_input_data
from claude_code_statusline.types import RenderContext


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
        token_metrics, _duration = parse_transcript(str(forked_session_file))

        assert token_metrics.session_id != ""


@pytest.mark.integration
class TestRateLimitOutput:
    """Test that the payload's rate_limits field reaches the rendered status line."""

    def test_rate_limits_payload_renders_usage_widgets(
        self, mock_stdin, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.setattr(loader, "_cached_config", None)
        monkeypatch.setattr(loader, "_cached_mtime", 0.0)
        payload = {
            "model": {"display_name": "Opus"},
            "rate_limits": {
                "five_hour": {"used_percentage": 23.7},
                "seven_day": {"used_percentage": 81},
            },
        }
        mock_stdin(json.dumps(payload))

        output = render_status_line_with_config(RenderContext(data=parse_input_data()))

        plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
        assert "5h: 24%" in plain
        assert "7d: 81%" in plain
