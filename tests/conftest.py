import pytest
from pathlib import Path


def pytest_configure(config):
    """Register custom test markers."""
    config.addinivalue_line("markers", "unit: Unit tests that do not perform real I/O")
    config.addinivalue_line("markers", "integration: Integration tests with mocked I/O")


@pytest.fixture
def mock_stdin(monkeypatch):
    """Factory fixture to mock stdin with custom content."""
    import io
    import sys

    def _mock_stdin(content: str):
        monkeypatch.setattr(sys, "stdin", io.StringIO(content))

    return _mock_stdin


@pytest.fixture
def sample_input_payload():
    """Sample statusline input payload."""
    return {
        "session_id": "abc123-def456",
        "workspace": {"current_dir": "/path/to/project"},
        "transcript_path": "/path/to/transcript.jsonl",
        "model": {"id": "claude-sonnet-4-5-20250929", "display_name": "Sonnet 4.5"},
        "cost": {
            "total_cost_usd": 1.50,
            "total_lines_added": 100,
            "total_lines_removed": 25,
        },
        "version": "2.0.53",
    }


@pytest.fixture
def basic_session_file():
    """Basic session transcript for simple parsing tests."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return fixtures_dir / "basic_session.jsonl"


@pytest.fixture
def compact_session_file():
    """Session with compact boundary for testing token counting."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return fixtures_dir / "session_with_compact.jsonl"


@pytest.fixture
def image_session_file():
    """Session with image for testing base64 filtering."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return fixtures_dir / "session_with_image.jsonl"


@pytest.fixture
def forked_session_file():
    """Forked session with mixed session IDs in JSONL content."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return fixtures_dir / "forked_session.jsonl"
