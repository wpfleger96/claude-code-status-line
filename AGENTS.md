# AGENTS.md

CLI tool that generates a formatted status line for Claude Code, displaying model, directory, git status, context/token usage, session cost, and elapsed time by parsing JSONL transcript files.

## Quick Commands

```bash
just                  # Quick quality check (sync, type-check, lint-check, format-check)
just sync             # Install dependencies (uv sync)
just test             # Run tests (uv run pytest)
just check-all        # All quality checks + tests
just ci               # Match CI locally
just pre-commit       # Pre-commit with auto-fix (type-check, lint, format, test)
just lint             # Fix linting issues (ruff check --fix)
just format           # Format code (ruff format)

uv run pytest tests/unit/test_file.py           # Single file
uv run pytest tests/unit/test_file.py::test_fn  # Single test
uv run pytest -m performance                    # Performance tests (excluded by default)
```

## Project Structure

```
src/claude_code_statusline/
├── statusline.py          # Main CLI entry point
├── renderer.py            # Status line rendering
├── types.py               # Dataclasses (RenderContext, TokenMetrics, etc.)
├── config/
│   ├── loader.py          # Config file loading with mtime caching
│   └── schema.py          # Pydantic validation schemas
├── parsers/
│   ├── jsonl.py           # JSONL transcript parser
│   └── tokens.py          # Token counting with compact boundary detection
├── utils/                 # Shared utilities (colors, git, formatting)
└── widgets/
    ├── base.py            # Abstract Widget base class
    ├── registry.py        # @register_widget() decorator
    └── builtin/           # 14 built-in widgets
tests/
├── unit/                  # Unit tests (no I/O)
├── integration/           # Integration tests (mocked I/O)
├── performance/           # Benchmarks (opt-in)
└── fixtures/              # Test data (JSONL transcripts)
```

## Tech Stack

- Python 3.13 (see `.python-version`)
- Package manager: uv
- Task runner: just
- Dependencies: pyyaml, pydantic
- Linting: ruff (isort, pyflakes, pyupgrade, bugbear)
- Type checking: mypy (strict mode)
- Testing: pytest, pytest-cov, pytest-benchmark

## Key Patterns

**Widget System**: All widgets extend `Widget` base class with `render(context: RenderContext) -> Optional[str]`. Register with `@register_widget(display_name, default_color, description, fallback_text)`.

**RenderContext**: Dataclass passed to all widgets containing `data`, `token_metrics`, `git_status`, `session_metrics`, `subscription_info`.

**Parallel I/O**: `statusline.py` uses `ThreadPoolExecutor(max_workers=3)` for transcript parsing, subscription loading, and model prefetch.

**Config Caching**: `config/loader.py` caches config files by mtime to avoid re-reading unchanged files.

## Testing

```bash
just test                           # Full suite (excludes performance)
uv run pytest -m unit               # Unit tests only
uv run pytest -m integration        # Integration tests only
uv run pytest -m performance        # Performance benchmarks
```

Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.performance`

Fixtures in `tests/conftest.py`: `mock_stdin`, `sample_input_payload`, `basic_session_file`, `compact_session_file`

## Common Gotchas

1. **Compact boundary resets tokens**: Token counting resets when `/compact` boundary detected - tests mark this as "Critical"
2. **Base64 images must be filtered**: Images excluded from token counting - tests mark this as "Critical"
3. **Session ID priority**: After `/compact`, session_id from transcript takes priority over payload session_id
4. **V1 config auto-deleted**: V1 configs automatically deleted and replaced with V2 format
5. **Performance tests opt-in**: Excluded by default, run with `uv run pytest -m performance`
6. **Hooks in `.hooks/`**: Custom hooks in `.hooks/` directory (not `.git/hooks/`) - install manually

## Key Files by Task

| Task | Files |
|------|-------|
| Add new widget | `widgets/builtin/`, `widgets/registry.py` |
| Modify token counting | `parsers/tokens.py`, `tests/unit/test_token_counting.py` |
| Change status line rendering | `renderer.py`, `config/defaults.py` |
| Update config schema | `config/schema.py`, `config/loader.py` |
| Add CLI option | `statusline.py` |
| Modify git status display | `utils/git.py`, `widgets/builtin/git.py` |
