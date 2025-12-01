"""Performance benchmarks using pytest-benchmark for automatic tracking."""

import json

from pathlib import Path

import pytest

from claude_code_statusline.parsers.jsonl import parse_transcript
from claude_code_statusline.utils.models import get_context_limit


def generate_large_transcript(num_lines: int, output_path: Path) -> None:
    """Generate a realistic JSONL transcript for benchmarking."""
    with open(output_path, "w") as f:
        f.write(json.dumps({"sessionId": "perf-test-session"}) + "\n")
        for i in range(num_lines):
            if i % 2 == 0:
                msg = {
                    "type": "user",
                    "message": {"role": "user", "content": f"Msg {i} " * 10},
                }
            else:
                msg = {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": f"Resp {i} " * 20},
                }
            f.write(json.dumps(msg) + "\n")


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Benchmarks using pytest-benchmark fixture for automatic stats and history."""

    def test_transcript_parsing_1k(self, benchmark, tmp_path):
        """Benchmark parsing a 1K line transcript."""
        transcript = tmp_path / "perf_1k.jsonl"
        generate_large_transcript(1000, transcript)

        # benchmark() runs the function multiple times and collects stats
        result = benchmark(parse_transcript, str(transcript))
        assert result.is_jsonl is True

    def test_transcript_parsing_10k(self, benchmark, tmp_path):
        """Benchmark parsing a 10K line transcript."""
        transcript = tmp_path / "perf_10k.jsonl"
        generate_large_transcript(10000, transcript)

        result = benchmark(parse_transcript, str(transcript))
        assert result.is_jsonl is True

    def test_model_lookup_known(self, benchmark):
        """Benchmark known Claude model context limit lookup."""
        benchmark(get_context_limit, "claude-sonnet-4-20250514")
